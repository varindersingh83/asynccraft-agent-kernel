"""API routes for agent runs and approvals."""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from asynccraft.kernel.database import get_db
from asynccraft.kernel.models import AgentRun, Approval
from asynccraft.kernel.agents import AgentOrchestrator
from asynccraft.kernel.approval import ApprovalService
from asynccraft.kernel.tools import get_tool_registry
from asynccraft.kernel.config import get_settings

router = APIRouter()


class CreateRunRequest(BaseModel):
    skin: str
    input_data: dict[str, Any]


class ApprovalDecisionRequest(BaseModel):
    approver_name: str
    note: str | None = None


@router.post("/runs")
async def create_run(
    request: CreateRunRequest, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """Create a new agent run."""
    orchestrator = AgentOrchestrator(session)
    run = await orchestrator.create_run(request.skin, request.input_data)
    return {
        "run_id": run.run_id,
        "status": run.status,
        "skin": run.skin,
    }


@router.get("/runs/{run_id}")
async def get_run(run_id: str, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Get run details."""
    result = await session.execute(select(AgentRun).where(AgentRun.run_id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    return {
        "run_id": run.run_id,
        "skin": run.skin,
        "status": run.status,
        "input_data": run.input_data,
        "output_data": run.output_data,
        "created_at": run.created_at.isoformat(),
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
    }


@router.get("/runs")
async def list_runs(
    skin: str | None = None, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """List all runs."""
    query = select(AgentRun).order_by(AgentRun.created_at.desc())
    if skin:
        query = query.where(AgentRun.skin == skin)
    result = await session.execute(query)
    runs = result.scalars().all()
    
    return {
        "runs": [
            {
                "run_id": run.run_id,
                "skin": run.skin,
                "status": run.status,
                "created_at": run.created_at.isoformat(),
            }
            for run in runs
        ]
    }


@router.get("/approvals")
async def list_approvals(
    status: str | None = None, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """List approvals."""
    approval_service = ApprovalService(session)
    
    if status == "pending":
        approvals = await approval_service.get_pending_approvals()
    else:
        query = select(Approval).order_by(Approval.created_at.desc())
        if status:
            query = query.where(Approval.status == status)
        result = await session.execute(query)
        approvals = list(result.scalars().all())
    
    return {
        "approvals": [
            {
                "approval_id": appr.approval_id,
                "tool_name": appr.tool_name,
                "tool_args": appr.tool_args,
                "preview_description": appr.preview_description,
                "status": appr.status,
                "approver_name": appr.approver_name,
                "created_at": appr.created_at.isoformat(),
            }
            for appr in approvals
        ]
    }


@router.post("/approvals/{approval_id}/approve")
async def approve_action(
    approval_id: str,
    request: ApprovalDecisionRequest,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Approve a pending action."""
    approval_service = ApprovalService(session)
    approval = await approval_service.approve(approval_id, request.approver_name, request.note)
    
    registry = get_tool_registry()
    tool = registry.get(approval.tool_name)
    if tool and approval.status == "approved":
        result = await tool.execute(**approval.tool_args)
        await approval_service.record_execution(approval.id, result)
    
    return {
        "approval_id": approval.approval_id,
        "status": approval.status,
        "decided_at": approval.decided_at.isoformat() if approval.decided_at else None,
    }


@router.post("/approvals/{approval_id}/reject")
async def reject_action(
    approval_id: str,
    request: ApprovalDecisionRequest,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Reject a pending action."""
    approval_service = ApprovalService(session)
    approval = await approval_service.reject(approval_id, request.approver_name, request.note)
    
    return {
        "approval_id": approval.approval_id,
        "status": approval.status,
        "decided_at": approval.decided_at.isoformat() if approval.decided_at else None,
    }


@router.get("/tools")
async def list_tools() -> dict[str, Any]:
    """List available tools."""
    registry = get_tool_registry()
    return {"tools": [tool.model_dump() for tool in registry.list_tools()]}


@router.get("/config")
async def get_config() -> dict[str, Any]:
    """Get current configuration."""
    settings = get_settings()
    return {
        "active_skin": settings.active_skin,
        "debug": settings.debug,
    }
