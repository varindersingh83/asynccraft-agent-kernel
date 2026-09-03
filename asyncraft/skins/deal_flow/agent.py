"""Deal flow triage specialist agent."""

from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.messages import AIMessage
from asynccraft.kernel.agents import BaseAgent, AgentState


class DealFlowAgent(BaseAgent):
    """Handles VC deal flow triage and scoring."""

    def __init__(self) -> None:
        super().__init__("deal_flow_specialist", "Handles VC deal triage and partner routing")

    async def invoke(self, state: AgentState, session: AsyncSession) -> AgentState:
        input_data = state["input_data"]
        company_name = input_data.get("company_name", "Unknown")
        score = self._calculate_score(input_data)

        state["messages"].append(
            AIMessage(content=f"Analyzing pitch from {company_name} (score: {score}/100)")
        )

        if score >= 80:
            approval_id = await self.request_tool_execution(
                "send_partner_notification",
                {
                    "partner_email": "partner@vcfirm.com",
                    "company_name": company_name,
                    "summary": f"High-scoring pitch ({score}/100): {input_data.get('pitch_summary', 'N/A')}",
                },
                state,
                session,
            )
            state["pending_approvals"].append(approval_id)

            approval_id2 = await self.request_tool_execution(
                "schedule_partner_call",
                {
                    "company_name": company_name,
                    "partner_email": "partner@vcfirm.com",
                    "proposed_time": "Next Tuesday 2pm",
                },
                state,
                session,
            )
            state["pending_approvals"].append(approval_id2)

        elif score >= 60:
            approval_id = await self.request_tool_execution(
                "create_crm_deal",
                {
                    "company_name": company_name,
                    "stage": "qualified",
                    "score": score,
                },
                state,
                session,
            )
            state["pending_approvals"].append(approval_id)
        else:
            approval_id = await self.request_tool_execution(
                "create_crm_deal",
                {
                    "company_name": company_name,
                    "stage": "nurture",
                    "score": score,
                },
                state,
                session,
            )
            state["pending_approvals"].append(approval_id)

        state["messages"].append(AIMessage(content=f"Actions proposed, awaiting approval"))
        return state

    def _calculate_score(self, pitch_data: dict[str, Any]) -> int:
        """Simple scoring heuristic for demo."""
        score = 50

        if pitch_data.get("has_revenue", False):
            score += 15
        if pitch_data.get("team_size", 0) >= 5:
            score += 10
        if pitch_data.get("funding_raised", 0) > 0:
            score += 10
        if pitch_data.get("market_size_millions", 0) >= 100:
            score += 15

        return min(score, 100)


def get_sample_pitches() -> list[dict[str, Any]]:
    """Sample pitch data for testing."""
    return [
        {
            "company_name": "RocketShip AI",
            "pitch_summary": "AI-powered logistics optimization for mid-market freight",
            "has_revenue": True,
            "arr": 500000,
            "team_size": 8,
            "funding_raised": 1200000,
            "market_size_millions": 500,
            "stage": "Series A",
            "contact_email": "founder@rocketship.ai",
        },
        {
            "company_name": "HealthTech Labs",
            "pitch_summary": "Remote patient monitoring for chronic conditions",
            "has_revenue": True,
            "arr": 200000,
            "team_size": 4,
            "funding_raised": 500000,
            "market_size_millions": 2000,
            "stage": "Seed",
            "contact_email": "ceo@healthtechlabs.com",
        },
        {
            "company_name": "DevTools Pro",
            "pitch_summary": "Developer productivity suite for distributed teams",
            "has_revenue": False,
            "arr": 0,
            "team_size": 2,
            "funding_raised": 0,
            "market_size_millions": 50,
            "stage": "Pre-seed",
            "contact_email": "founders@devtools.pro",
        },
    ]
