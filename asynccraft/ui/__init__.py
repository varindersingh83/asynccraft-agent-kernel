"""UI module with HTMX-based operator interface."""

import json
from jinja2 import Environment, FileSystemLoader
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from asynccraft.kernel.database import get_db
from asynccraft.kernel.models import AgentRun, Approval, ApprovalStatus
from asynccraft.kernel.approval import ApprovalService
from asynccraft.kernel.agents import AgentOrchestrator
from asynccraft.kernel.config import get_settings
from asynccraft.skins.ops_dispatch.agent import get_sample_exceptions
from asynccraft.skins.deal_flow.agent import get_sample_pitches

router = APIRouter()

env = Environment(loader=FileSystemLoader("asynccraft/ui/templates"), cache_size=0)
env.filters["tojson"] = lambda x: json.dumps(x, indent=2)

templates = Jinja2Templates(env=env)

MOCK_OPERATORS = [
    {"id": "john_chen", "name": "John Chen", "role": "Dispatcher"},
    {"id": "jane_park", "name": "Jane Park", "role": "Ops Manager"},
    {"id": "alex_rivera", "name": "Alex Rivera", "role": "Partner"},
    {"id": "sam_okonkwo", "name": "Sam Okonkwo", "role": "Analyst"},
]


@router.get("/", response_class=HTMLResponse)
async def index(request: Request, session: AsyncSession = Depends(get_db)):
    """Home page with approval queue."""
    approval_service = ApprovalService(session)
    pending = await approval_service.get_pending_approvals()
    
    query = select(AgentRun).order_by(AgentRun.created_at.desc()).limit(10)
    result = await session.execute(query)
    recent_runs = list(result.scalars().all())
    
    settings = get_settings()
    
    recent_q = (
        select(Approval)
        .where(Approval.status.in_([ApprovalStatus.APPROVED, ApprovalStatus.REJECTED]))
        .order_by(Approval.decided_at.desc())
        .limit(5)
    )
    recent_decisions = list((await session.execute(recent_q)).scalars().all())

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "pending_approvals": list(pending),
            "recent_runs": list(recent_runs),
            "active_skin": str(settings.active_skin),
            "mock_operators": MOCK_OPERATORS,
            "recent_decisions": recent_decisions,
        },
    )


@router.post("/demo-run", response_class=HTMLResponse)
async def create_demo_run(
    request: Request,
    skin: str = Form(...),
    session: AsyncSession = Depends(get_db),
):
    """Create a demo run with sample data."""
    if skin == "ops_dispatch":
        samples = get_sample_exceptions()
        input_data = samples[0]
    else:
        samples = get_sample_pitches()
        input_data = samples[0]
    
    orchestrator = AgentOrchestrator(session)
    run = await orchestrator.create_run(skin, input_data)
    
    if skin == "ops_dispatch":
        from asynccraft.skins.ops_dispatch.agent import OpsDispatchAgent
        agent = OpsDispatchAgent()
    else:
        from asynccraft.skins.deal_flow.agent import DealFlowAgent
        agent = DealFlowAgent()
    
    state = {
        "messages": [],
        "run_id": run.run_id,
        "skin": skin,
        "input_data": input_data,
        "current_agent": "specialist",
        "pending_approvals": [],
        "tool_results": {},
        "final_output": None,
    }
    
    await agent.invoke(state, session)
    
    approval_service = ApprovalService(session)
    pending = await approval_service.get_pending_approvals()
    
    return templates.TemplateResponse(
        request=request,
        name="approval_queue.html",
        context={
            "pending_approvals": pending,
            "mock_operators": MOCK_OPERATORS,
            "current_skin": skin,
        },
    )


@router.post("/approve/{approval_id}", response_class=HTMLResponse)
async def approve(
    request: Request,
    approval_id: str,
    approver_name: str = Form(...),
    session: AsyncSession = Depends(get_db),
):
    """Approve an action."""
    approval_service = ApprovalService(session)
    await approval_service.approve(approval_id, approver_name)
    
    from asynccraft.kernel.tools import get_tool_registry
    
    approval = await approval_service.get_approval(approval_id)
    if approval:
        registry = get_tool_registry()
        tool = registry.get(approval.tool_name)
        if tool:
            result = await tool.execute(**approval.tool_args)
            await approval_service.record_execution(approval.id, result)
    
    pending = await approval_service.get_pending_approvals()
    
    query = select(Approval).where(Approval.status.in_([ApprovalStatus.APPROVED, ApprovalStatus.REJECTED])).order_by(Approval.decided_at.desc()).limit(5)
    result = await session.execute(query)
    recent_decisions = list(result.scalars().all())
    
    return templates.TemplateResponse(
        request=request,
        name="approval_queue.html",
        context={
            "pending_approvals": pending,
            "mock_operators": MOCK_OPERATORS,
            "recent_decisions": recent_decisions,
        },
    )


@router.post("/reject/{approval_id}", response_class=HTMLResponse)
async def reject(
    request: Request,
    approval_id: str,
    approver_name: str = Form(...),
    session: AsyncSession = Depends(get_db),
):
    """Reject an action."""
    approval_service = ApprovalService(session)
    await approval_service.reject(approval_id, approver_name)
    
    pending = await approval_service.get_pending_approvals()
    
    query = select(Approval).where(Approval.status.in_([ApprovalStatus.APPROVED, ApprovalStatus.REJECTED])).order_by(Approval.decided_at.desc()).limit(5)
    result = await session.execute(query)
    recent_decisions = list(result.scalars().all())
    
    return templates.TemplateResponse(
        request=request,
        name="approval_queue.html",
        context={
            "pending_approvals": pending,
            "mock_operators": MOCK_OPERATORS,
            "recent_decisions": recent_decisions,
        },
    )
