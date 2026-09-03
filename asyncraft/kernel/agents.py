"""Agent orchestration using LangGraph."""

import uuid
from typing import Any, TypedDict
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from asynccraft.kernel.models import AgentRun, AgentMessage, RunStatus
from asynccraft.kernel.tools import get_tool_registry, Tool
from asynccraft.kernel.approval import ApprovalService


class AgentState(TypedDict):
    """State passed between agents in the graph."""

    messages: list[BaseMessage]
    run_id: str
    skin: str
    input_data: dict[str, Any]
    current_agent: str
    pending_approvals: list[str]
    tool_results: dict[str, Any]
    final_output: dict[str, Any] | None


class BaseAgent:
    """Base agent with HITL approval integration."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    async def invoke(self, state: AgentState, session: AsyncSession) -> AgentState:
        """Process state and return updated state."""
        raise NotImplementedError

    async def request_tool_execution(
        self, tool_name: str, tool_args: dict[str, Any], state: AgentState, session: AsyncSession
    ) -> str:
        """Request approval for tool execution."""
        registry = get_tool_registry()
        tool = registry.get(tool_name)
        if not tool:
            raise ValueError(f"Tool {tool_name} not found in registry")

        result = await session.execute(
            select(AgentRun.id).where(AgentRun.run_id == state["run_id"])
        )
        run_db_id = result.scalar_one()

        approval_service = ApprovalService(session)
        approval = await approval_service.request_approval(run_db_id, tool, tool_args)
        return approval.approval_id


class CommanderAgent(BaseAgent):
    """Routes work to specialist agents."""

    def __init__(self) -> None:
        super().__init__("commander", "Routes incoming requests to appropriate specialist agents")

    async def invoke(self, state: AgentState, session: AsyncSession) -> AgentState:
        state["messages"].append(
            AIMessage(content=f"Commander routing {state['skin']} request to specialist agents")
        )
        state["current_agent"] = "specialist"
        return state


class SpecialistAgent(BaseAgent):
    """Domain-specific agent that proposes actions."""

    def __init__(self, skin: str):
        super().__init__(f"specialist_{skin}", f"Handles {skin} domain logic")
        self.skin = skin

    async def invoke(self, state: AgentState, session: AsyncSession) -> AgentState:
        state["messages"].append(
            AIMessage(content=f"Specialist analyzing {self.skin} request and proposing actions")
        )
        state["current_agent"] = "approval_gate"
        return state


def create_agent_graph(skin: str) -> StateGraph:
    """Create LangGraph workflow for the given skin."""

    async def commander_node(state: AgentState) -> AgentState:
        return state

    async def specialist_node(state: AgentState) -> AgentState:
        return state

    async def should_continue(state: AgentState) -> str:
        if state.get("pending_approvals"):
            return "approval_gate"
        if state.get("final_output"):
            return END
        return "specialist"

    graph = StateGraph(AgentState)
    graph.add_node("commander", commander_node)
    graph.add_node("specialist", specialist_node)

    graph.set_entry_point("commander")
    graph.add_edge("commander", "specialist")
    graph.add_conditional_edges("specialist", should_continue)

    return graph


class AgentOrchestrator:
    """Orchestrates agent runs with persistence."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_run(self, skin: str, input_data: dict[str, Any]) -> AgentRun:
        """Create a new agent run."""
        run = AgentRun(
            run_id=f"run_{uuid.uuid4().hex[:16]}",
            skin=skin,
            status=RunStatus.PENDING,
            input_data=input_data,
        )
        self.session.add(run)
        await self.session.commit()
        await self.session.refresh(run)
        return run

    async def log_message(
        self, run_id: int, agent_name: str, message_type: str, content: dict[str, Any]
    ) -> AgentMessage:
        """Log an agent message."""
        message = AgentMessage(
            run_id=run_id, agent_name=agent_name, message_type=message_type, content=content
        )
        self.session.add(message)
        await self.session.commit()
        return message

    async def update_run_status(
        self, run_id: int, status: RunStatus, output_data: dict[str, Any] | None = None
    ) -> None:
        """Update run status and output."""
        result = await self.session.execute(
            select(AgentRun).where(AgentRun.id == run_id)
        )
        run = result.scalar_one()
        run.status = status
        if output_data:
            run.output_data = output_data
        await self.session.commit()
