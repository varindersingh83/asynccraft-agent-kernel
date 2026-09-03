"""Human-in-the-loop approval service."""

import uuid
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from asynccraft.kernel.models import Approval, ApprovalStatus, ToolExecution
from asynccraft.kernel.tools import Tool, ToolResult


class ApprovalService:
    """Manages HITL approval workflow."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def request_approval(
        self, run_id: int, tool: Tool, tool_args: dict[str, Any]
    ) -> Approval:
        """Create approval request for a tool execution."""
        approval = Approval(
            approval_id=f"appr_{uuid.uuid4().hex[:16]}",
            run_id=run_id,
            tool_name=tool.name,
            tool_args=tool_args,
            preview_description=tool.preview(**tool_args),
            status=ApprovalStatus.PENDING,
        )
        self.session.add(approval)
        await self.session.commit()
        await self.session.refresh(approval)
        return approval

    async def get_pending_approvals(self, run_id: int | None = None) -> list[Approval]:
        """Get all pending approvals, optionally filtered by run."""
        query = select(Approval).where(Approval.status == ApprovalStatus.PENDING)
        if run_id:
            query = query.where(Approval.run_id == run_id)
        result = await self.session.execute(query.order_by(Approval.created_at.desc()))
        return list(result.scalars().all())

    async def get_approval(self, approval_id: str) -> Approval | None:
        """Get approval by ID."""
        result = await self.session.execute(
            select(Approval).where(Approval.approval_id == approval_id)
        )
        return result.scalar_one_or_none()

    async def approve(
        self, approval_id: str, approver_name: str, note: str | None = None
    ) -> Approval:
        """Approve a pending request."""
        approval = await self.get_approval(approval_id)
        if not approval:
            raise ValueError(f"Approval {approval_id} not found")
        if approval.status != ApprovalStatus.PENDING:
            raise ValueError(f"Approval {approval_id} is not pending (status: {approval.status})")

        approval.status = ApprovalStatus.APPROVED
        approval.approver_name = approver_name
        approval.approval_note = note
        approval.decided_at = datetime.now(timezone.utc)

        await self.session.commit()
        await self.session.refresh(approval)
        return approval

    async def reject(
        self, approval_id: str, approver_name: str, note: str | None = None
    ) -> Approval:
        """Reject a pending request."""
        approval = await self.get_approval(approval_id)
        if not approval:
            raise ValueError(f"Approval {approval_id} not found")
        if approval.status != ApprovalStatus.PENDING:
            raise ValueError(f"Approval {approval_id} is not pending")

        approval.status = ApprovalStatus.REJECTED
        approval.approver_name = approver_name
        approval.approval_note = note
        approval.decided_at = datetime.now(timezone.utc)

        await self.session.commit()
        await self.session.refresh(approval)
        return approval

    async def record_execution(self, approval_id: int, result: ToolResult) -> ToolExecution:
        """Record tool execution result."""
        execution = ToolExecution(
            approval_id=approval_id, result={"success": result.success, "data": result.data}
        )
        self.session.add(execution)
        await self.session.commit()
        await self.session.refresh(execution)
        return execution

    async def is_approved(self, approval_id: str) -> bool:
        """Check if an approval has been granted."""
        approval = await self.get_approval(approval_id)
        return approval is not None and approval.status == ApprovalStatus.APPROVED
