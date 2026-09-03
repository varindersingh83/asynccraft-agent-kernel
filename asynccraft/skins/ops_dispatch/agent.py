"""Ops/Dispatch specialist agent."""

from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.messages import AIMessage
from asynccraft.kernel.agents import BaseAgent, AgentState
from asynccraft.kernel.tools import get_tool_registry


class OpsDispatchAgent(BaseAgent):
    """Handles logistics exception routing and resolution."""

    def __init__(self) -> None:
        super().__init__("ops_dispatch_specialist", "Handles logistics exception management")

    async def invoke(self, state: AgentState, session: AsyncSession) -> AgentState:
        input_data = state["input_data"]
        exception_type = input_data.get("exception_type", "unknown")
        severity = input_data.get("severity", "medium")

        state["messages"].append(
            AIMessage(
                content=f"Analyzing {exception_type} exception (severity: {severity})"
            )
        )

        if severity == "critical":
            approval_id = await self.request_tool_execution(
                "escalate_to_manager",
                {
                    "exception_id": input_data.get("exception_id", "exc_001"),
                    "severity": severity,
                    "summary": input_data.get("description", "Critical exception"),
                },
                state,
                session,
            )
            state["pending_approvals"].append(approval_id)
        elif exception_type == "delayed_delivery":
            approval_id = await self.request_tool_execution(
                "update_delivery_eta",
                {
                    "shipment_id": input_data.get("shipment_id", "shp_001"),
                    "new_eta": input_data.get("new_eta", "2024-01-15 14:00"),
                    "delay_reason": input_data.get("reason", "Traffic delay"),
                },
                state,
                session,
            )
            state["pending_approvals"].append(approval_id)
        else:
            approval_id = await self.request_tool_execution(
                "notify_dispatcher",
                {
                    "dispatcher_id": "disp_main",
                    "message": f"{exception_type}: {input_data.get('description', 'N/A')}",
                    "priority": severity,
                },
                state,
                session,
            )
            state["pending_approvals"].append(approval_id)

        state["messages"].append(
            AIMessage(content=f"Proposed action awaiting approval (ID: {approval_id})")
        )
        return state


def get_sample_exceptions() -> list[dict[str, Any]]:
    """Sample exception data for testing."""
    return [
        {
            "exception_id": "exc_001",
            "exception_type": "delayed_delivery",
            "severity": "medium",
            "shipment_id": "shp_12345",
            "truck_id": "truck_789",
            "description": "Truck delayed 2 hours due to traffic on I-95",
            "current_location": "Baltimore, MD",
            "destination": "New York, NY",
            "original_eta": "2024-01-15 12:00",
            "new_eta": "2024-01-15 14:00",
            "reason": "Heavy traffic accident on I-95",
        },
        {
            "exception_id": "exc_002",
            "exception_type": "vehicle_breakdown",
            "severity": "critical",
            "truck_id": "truck_456",
            "shipment_id": "shp_67890",
            "description": "Truck engine failure - requires tow and transfer",
            "current_location": "Philadelphia, PA",
            "destination": "Boston, MA",
            "estimated_repair_time": "6+ hours",
        },
        {
            "exception_id": "exc_003",
            "exception_type": "weather_delay",
            "severity": "high",
            "shipment_id": "shp_11223",
            "description": "Severe storm warning - route closure expected",
            "affected_route": "I-80 through PA mountains",
            "delay_estimate": "4-6 hours",
        },
    ]
