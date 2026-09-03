"""UI module with HTMX-based operator interface."""

import json
from jinja2 import Environment, FileSystemLoader
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from asynccraft.kernel.database import get_db
from asynccraft.kernel.models import AgentRun, Approval, ApprovalStatus, SOPRunState
from asynccraft.kernel.approval import ApprovalService
from asynccraft.kernel.agents import AgentOrchestrator
from asynccraft.kernel.config import get_settings
from asynccraft.kernel.tools import get_tool_registry, Tool, ToolResult
from asynccraft.skins.ops_dispatch.agent import get_sample_exceptions
from asynccraft.skins.deal_flow.agent import get_sample_pitches
from asynccraft.skins.ops_dispatch.sop_runner import (
    SOPRunner as DispatchSOPRunner,
    DISPATCH_SOP,
    GateDecision,
)
from asynccraft.skins.deal_flow.sop_runner import (
    SOPRunner as DealFlowSOPRunner,
    DEAL_FLOW_SOP,
    GateDecision as DealFlowGateDecision,
)

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
    """Create a demo run with SOP-based workflow."""
    if skin == "ops_dispatch":
        samples = get_sample_exceptions()
        input_data = samples[0]
    else:
        samples = get_sample_pitches()
        input_data = samples[0]
    
    orchestrator = AgentOrchestrator(session)
    run = await orchestrator.create_run(skin, input_data)
    
    # Initialize SOP runner
    if skin == "ops_dispatch":
        sop_runner = DispatchSOPRunner(DISPATCH_SOP, session)
    else:
        sop_runner = DealFlowSOPRunner(DEAL_FLOW_SOP, session)
    
    # Start SOP and auto-advance to first gate
    sop_runner.start()
    first_gate, events = await sop_runner.advance_to(sop_runner.current_step_id)
    
    # Create SOP state record
    sop_state = SOPRunState(
        run_id=run.id,
        current_step_id=sop_runner.current_step_id,
        completed_steps=sop_runner.get_completed_steps(),
        events=events,
        is_complete=first_gate is None,
    )
    session.add(sop_state)
    await session.commit()
    await session.refresh(sop_state)
    
    # Create approval for the first gate step
    if first_gate:
        approval_service = ApprovalService(session)
        
        # Create a preview description with gate context
        gate_description = f"{first_gate.label} gate check"
        if first_gate.tool_args_template:
            gate_description += f": {', '.join(f'{k}={v}' for k, v in list(first_gate.tool_args_template.items())[:2])}"
        
        approval = Approval(
            approval_id=f"appr_{run.run_id}_{first_gate.id}",
            run_id=run.id,
            tool_name=first_gate.tool_name or f"gate_{first_gate.id}",
            tool_args=first_gate.tool_args_template or {},
            preview_description=gate_description,
            status=ApprovalStatus.PENDING,
        )
        session.add(approval)
        await session.commit()
    
    # Get pending approvals
    approval_service = ApprovalService(session)
    pending = await approval_service.get_pending_approvals()
    
    # Get recent decisions
    query = select(Approval).where(
        Approval.status.in_([ApprovalStatus.APPROVED, ApprovalStatus.REJECTED])
    ).order_by(Approval.decided_at.desc()).limit(5)
    result = await session.execute(query)
    recent_decisions = list(result.scalars().all())
    
    return templates.TemplateResponse(
        request=request,
        name="approval_queue.html",
        context={
            "pending_approvals": pending,
            "mock_operators": MOCK_OPERATORS,
            "recent_decisions": recent_decisions,
            "current_skin": skin,
            "sop_state": sop_state,
        },
    )


@router.post("/approve/{approval_id}", response_class=HTMLResponse)
async def approve(
    request: Request,
    approval_id: str,
    approver_name: str = Form(...),
    session: AsyncSession = Depends(get_db),
):
    """Approve an action and advance SOP."""
    approval_service = ApprovalService(session)
    await approval_service.approve(approval_id, approver_name)
    
    approval = await approval_service.get_approval(approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    
    # Execute the approved tool
    registry = get_tool_registry()
    tool = registry.get(approval.tool_name)
    if tool:
        result = await tool.execute(**approval.tool_args)
        await approval_service.record_execution(approval.id, result)
    
    # Check if this approval is part of an SOP run
    result = await session.execute(
        select(SOPRunState).where(SOPRunState.run_id == approval.run_id)
    )
    sop_state = result.scalar_one_or_none()
    
    if sop_state and not sop_state.is_complete:
        # Get the run to determine skin
        run_result = await session.execute(
            select(AgentRun).where(AgentRun.id == approval.run_id)
        )
        run = run_result.scalar_one()
        
        # Initialize SOP runner with current state
        if run.skin == "ops_dispatch":
            sop_runner = DispatchSOPRunner(DISPATCH_SOP, session)
        else:
            sop_runner = DealFlowSOPRunner(DEAL_FLOW_SOP, session)
        
        # Restore state
        sop_runner.current_step_id = sop_state.current_step_id
        sop_runner.completed_steps = sop_state.completed_steps.copy()
        
        # Handle gate decision (approve)
        next_gate, new_events = await sop_runner.handle_gate_decision(
            sop_state.current_step_id,
            GateDecision.APPROVE if run.skin == "ops_dispatch" else DealFlowGateDecision.APPROVE
        )
        
        # Update SOP state
        sop_state.current_step_id = sop_runner.current_step_id
        sop_state.completed_steps = sop_runner.get_completed_steps()
        sop_state.events = sop_state.events + new_events
        sop_state.is_complete = next_gate is None
        await session.commit()
        
        # Create approval for next gate if exists
        if next_gate:
            gate_description = f"{next_gate.label} gate check"
            if next_gate.tool_args_template:
                gate_description += f": {', '.join(f'{k}={v}' for k, v in list(next_gate.tool_args_template.items())[:2])}"
            
            next_approval = Approval(
                approval_id=f"appr_{run.run_id}_{next_gate.id}",
                run_id=run.id,
                tool_name=next_gate.tool_name or f"gate_{next_gate.id}",
                tool_args=next_gate.tool_args_template or {},
                preview_description=gate_description,
                status=ApprovalStatus.PENDING,
            )
            session.add(next_approval)
            await session.commit()
    
    pending = await approval_service.get_pending_approvals()
    
    query = select(Approval).where(
        Approval.status.in_([ApprovalStatus.APPROVED, ApprovalStatus.REJECTED])
    ).order_by(Approval.decided_at.desc()).limit(5)
    result = await session.execute(query)
    recent_decisions = list(result.scalars().all())
    
    return templates.TemplateResponse(
        request=request,
        name="approval_queue.html",
        context={
            "pending_approvals": pending,
            "mock_operators": MOCK_OPERATORS,
            "recent_decisions": recent_decisions,
            "sop_state": sop_state if sop_state else None,
        },
    )


@router.post("/reject/{approval_id}", response_class=HTMLResponse)
async def reject(
    request: Request,
    approval_id: str,
    approver_name: str = Form(...),
    session: AsyncSession = Depends(get_db),
):
    """Reject an action and handle SOP branch."""
    approval_service = ApprovalService(session)
    await approval_service.reject(approval_id, approver_name)
    
    approval = await approval_service.get_approval(approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    
    # Check if this approval is part of an SOP run
    result = await session.execute(
        select(SOPRunState).where(SOPRunState.run_id == approval.run_id)
    )
    sop_state = result.scalar_one_or_none()
    
    if sop_state and not sop_state.is_complete:
        # Get the run to determine skin
        run_result = await session.execute(
            select(AgentRun).where(AgentRun.id == approval.run_id)
        )
        run = run_result.scalar_one()
        
        # Initialize SOP runner with current state
        if run.skin == "ops_dispatch":
            sop_runner = DispatchSOPRunner(DISPATCH_SOP, session)
        else:
            sop_runner = DealFlowSOPRunner(DEAL_FLOW_SOP, session)
        
        # Restore state
        sop_runner.current_step_id = sop_state.current_step_id
        sop_runner.completed_steps = sop_state.completed_steps.copy()
        
        # Handle gate decision (reject)
        next_gate, new_events = await sop_runner.handle_gate_decision(
            sop_state.current_step_id,
            GateDecision.REJECT if run.skin == "ops_dispatch" else DealFlowGateDecision.REJECT
        )
        
        # Update SOP state
        sop_state.current_step_id = sop_runner.current_step_id
        sop_state.completed_steps = sop_runner.get_completed_steps()
        sop_state.events = sop_state.events + new_events
        sop_state.is_complete = next_gate is None
        await session.commit()
        
        # Create approval for next gate if exists (unlikely on reject paths, but possible)
        if next_gate:
            gate_description = f"{next_gate.label} gate check"
            if next_gate.tool_args_template:
                gate_description += f": {', '.join(f'{k}={v}' for k, v in list(next_gate.tool_args_template.items())[:2])}"
            
            next_approval = Approval(
                approval_id=f"appr_{run.run_id}_{next_gate.id}",
                run_id=run.id,
                tool_name=next_gate.tool_name or f"gate_{next_gate.id}",
                tool_args=next_gate.tool_args_template or {},
                preview_description=gate_description,
                status=ApprovalStatus.PENDING,
            )
            session.add(next_approval)
            await session.commit()
    
    pending = await approval_service.get_pending_approvals()
    
    query = select(Approval).where(
        Approval.status.in_([ApprovalStatus.APPROVED, ApprovalStatus.REJECTED])
    ).order_by(Approval.decided_at.desc()).limit(5)
    result = await session.execute(query)
    recent_decisions = list(result.scalars().all())
    
    return templates.TemplateResponse(
        request=request,
        name="approval_queue.html",
        context={
            "pending_approvals": pending,
            "mock_operators": MOCK_OPERATORS,
            "recent_decisions": recent_decisions,
            "sop_state": sop_state if sop_state else None,
        },
    )
