"""Tests for HITL approval enforcement."""

import pytest
from asynccraft.kernel.models import AgentRun, ApprovalStatus
from asynccraft.kernel.approval import ApprovalService
from asynccraft.kernel.agents import AgentOrchestrator
from asynccraft.skins.ops_dispatch.tools import NotifyDispatcherTool


@pytest.mark.asyncio
async def test_approval_required_before_execution(db_session):
    """Tool execution cannot happen without approval."""
    orchestrator = AgentOrchestrator(db_session)
    run = await orchestrator.create_run("ops_dispatch", {"test": "data"})

    approval_service = ApprovalService(db_session)
    tool = NotifyDispatcherTool()

    approval = await approval_service.request_approval(
        run.id,
        tool,
        {"dispatcher_id": "test", "message": "test", "priority": "normal"},
    )

    assert approval.status == ApprovalStatus.PENDING
    assert approval.tool_name == "notify_dispatcher"


@pytest.mark.asyncio
async def test_approval_workflow(db_session):
    """Full approval workflow: request -> approve -> execute."""
    orchestrator = AgentOrchestrator(db_session)
    run = await orchestrator.create_run("ops_dispatch", {"test": "data"})

    approval_service = ApprovalService(db_session)
    tool = NotifyDispatcherTool()

    approval = await approval_service.request_approval(
        run.id,
        tool,
        {"dispatcher_id": "test", "message": "test message", "priority": "high"},
    )

    assert approval.status == ApprovalStatus.PENDING
    assert not await approval_service.is_approved(approval.approval_id)

    approved = await approval_service.approve(approval.approval_id, "test_user", "Looks good")

    assert approved.status == ApprovalStatus.APPROVED
    assert approved.approver_name == "test_user"
    assert approved.approval_note == "Looks good"
    assert await approval_service.is_approved(approval.approval_id)

    result = await tool.execute(
        dispatcher_id="test", message="test message", priority="high"
    )
    assert result.success

    execution = await approval_service.record_execution(approval.id, result)
    assert execution.result["success"] is True


@pytest.mark.asyncio
async def test_rejection_workflow(db_session):
    """Rejection workflow: request -> reject."""
    orchestrator = AgentOrchestrator(db_session)
    run = await orchestrator.create_run("ops_dispatch", {"test": "data"})

    approval_service = ApprovalService(db_session)
    tool = NotifyDispatcherTool()

    approval = await approval_service.request_approval(
        run.id,
        tool,
        {"dispatcher_id": "test", "message": "test", "priority": "normal"},
    )

    rejected = await approval_service.reject(
        approval.approval_id, "test_user", "Not necessary"
    )

    assert rejected.status == ApprovalStatus.REJECTED
    assert rejected.approver_name == "test_user"
    assert rejected.approval_note == "Not necessary"
    assert not await approval_service.is_approved(approval.approval_id)


@pytest.mark.asyncio
async def test_cannot_approve_twice(db_session):
    """Cannot approve already decided approval."""
    orchestrator = AgentOrchestrator(db_session)
    run = await orchestrator.create_run("ops_dispatch", {"test": "data"})

    approval_service = ApprovalService(db_session)
    tool = NotifyDispatcherTool()

    approval = await approval_service.request_approval(
        run.id,
        tool,
        {"dispatcher_id": "test", "message": "test", "priority": "normal"},
    )

    await approval_service.approve(approval.approval_id, "user1")

    with pytest.raises(ValueError, match="is not pending"):
        await approval_service.approve(approval.approval_id, "user2")


@pytest.mark.asyncio
async def test_audit_trail_preserved(db_session):
    """Approval audit trail is preserved."""
    orchestrator = AgentOrchestrator(db_session)
    run = await orchestrator.create_run("ops_dispatch", {"test": "data"})

    approval_service = ApprovalService(db_session)
    tool = NotifyDispatcherTool()

    approval = await approval_service.request_approval(
        run.id,
        tool,
        {"dispatcher_id": "disp_001", "message": "urgent", "priority": "high"},
    )

    await approval_service.approve(approval.approval_id, "alice@example.com", "Approved for test")

    retrieved = await approval_service.get_approval(approval.approval_id)
    assert retrieved is not None
    assert retrieved.approver_name == "alice@example.com"
    assert retrieved.approval_note == "Approved for test"
    assert retrieved.tool_name == "notify_dispatcher"
    assert retrieved.tool_args["dispatcher_id"] == "disp_001"
    assert retrieved.decided_at is not None
