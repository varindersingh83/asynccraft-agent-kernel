"""Eval harness runner."""

import asyncio
from typing import Any
from sqlalchemy import select
from asynccraft.kernel.database import async_session_maker
from asynccraft.kernel.models import Approval, ApprovalStatus
from asynccraft.kernel.agents import AgentOrchestrator
from asynccraft.skins.ops_dispatch.agent import OpsDispatchAgent
from asynccraft.skins.deal_flow.agent import DealFlowAgent


class EvalCase:
    """Single evaluation case."""

    def __init__(
        self,
        name: str,
        skin: str,
        input_data: dict[str, Any],
        expected_tool: str,
        expected_arg_check: dict[str, Any] | None = None,
    ):
        self.name = name
        self.skin = skin
        self.input_data = input_data
        self.expected_tool = expected_tool
        self.expected_arg_check = expected_arg_check or {}

    async def run(self) -> tuple[bool, str]:
        """Run eval case and return (passed, message)."""
        async with async_session_maker() as session:
            orchestrator = AgentOrchestrator(session)
            run = await orchestrator.create_run(self.skin, self.input_data)

            if self.skin == "ops_dispatch":
                agent = OpsDispatchAgent()
            else:
                agent = DealFlowAgent()

            state = {
                "messages": [],
                "run_id": run.run_id,
                "skin": self.skin,
                "input_data": self.input_data,
                "current_agent": "specialist",
                "pending_approvals": [],
                "tool_results": {},
                "final_output": None,
            }

            await agent.invoke(state, session)

            result = await session.execute(
                select(Approval)
                .where(Approval.run_id == run.id)
                .where(Approval.status == ApprovalStatus.PENDING)
            )
            approvals = list(result.scalars().all())

            if not approvals:
                return False, "No approval requests created"

            approval = approvals[0]
            if approval.tool_name != self.expected_tool:
                return (
                    False,
                    f"Expected tool {self.expected_tool}, got {approval.tool_name}",
                )

            for key, expected_val in self.expected_arg_check.items():
                actual_val = approval.tool_args.get(key)
                if actual_val != expected_val:
                    return (
                        False,
                        f"Expected {key}={expected_val}, got {actual_val}",
                    )

            return True, "Pass"


EVAL_CASES = [
    EvalCase(
        name="ops_dispatch_critical_escalation",
        skin="ops_dispatch",
        input_data={
            "exception_id": "exc_test_001",
            "exception_type": "critical_failure",
            "severity": "critical",
            "description": "Critical system failure",
        },
        expected_tool="escalate_to_manager",
        expected_arg_check={"severity": "critical"},
    ),
    EvalCase(
        name="ops_dispatch_delayed_delivery",
        skin="ops_dispatch",
        input_data={
            "exception_id": "exc_test_002",
            "exception_type": "delayed_delivery",
            "severity": "medium",
            "shipment_id": "shp_test_123",
            "new_eta": "2024-01-20 15:00",
            "reason": "Weather delay",
        },
        expected_tool="update_delivery_eta",
        expected_arg_check={"shipment_id": "shp_test_123"},
    ),
    EvalCase(
        name="deal_flow_high_score",
        skin="deal_flow",
        input_data={
            "company_name": "TestCo High Score",
            "has_revenue": True,
            "team_size": 10,
            "funding_raised": 2000000,
            "market_size_millions": 500,
        },
        expected_tool="send_partner_notification",
    ),
    EvalCase(
        name="deal_flow_medium_score",
        skin="deal_flow",
        input_data={
            "company_name": "TestCo Medium Score",
            "has_revenue": True,
            "team_size": 3,
            "funding_raised": 0,
            "market_size_millions": 50,
        },
        expected_tool="create_crm_deal",
        expected_arg_check={"company_name": "TestCo Medium Score"},
    ),
]


async def run_evals() -> None:
    """Run all eval cases."""
    print("Running Asyncraft Agent Kernel Evals\n")
    print("=" * 60)

    results = []
    for case in EVAL_CASES:
        try:
            passed, message = await case.run()
            results.append((case.name, passed, message))
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"{status}: {case.name}")
            if not passed:
                print(f"  └─ {message}")
        except Exception as e:
            results.append((case.name, False, str(e)))
            print(f"✗ ERROR: {case.name}")
            print(f"  └─ {e}")

    print("\n" + "=" * 60)
    passed_count = sum(1 for _, passed, _ in results if passed)
    total_count = len(results)
    print(f"Results: {passed_count}/{total_count} passed")

    if passed_count < total_count:
        print("\nFailed cases:")
        for name, passed, message in results:
            if not passed:
                print(f"  - {name}: {message}")
        exit(1)
    else:
        print("\n✓ All evals passed")
        exit(0)
