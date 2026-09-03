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
from asynccraft.skins.crm_followup.agent import get_sample_leads
from asynccraft.skins.invoice_ap.agent import get_sample_invoices
from asynccraft.skins.inbox_triage.agent import get_sample_tickets
from asynccraft.skins.voice_dispatch.agent import get_sample_calls
from asynccraft.skins.ops_dispatch.sop_runner import (
    SOPRunner as DispatchSOPRunner,
    DISPATCH_SOP,
    GateDecision as DispatchGateDecision,
)
from asynccraft.skins.deal_flow.sop_runner import (
    SOPRunner as DealFlowSOPRunner,
    DEAL_FLOW_SOP,
    GateDecision as DealFlowGateDecision,
)
from asynccraft.skins.crm_followup.sop_runner import (
    SOPRunner as CRMFollowupSOPRunner,
    CRM_FOLLOWUP_SOP,
    GateDecision as CRMGateDecision,
)
from asynccraft.skins.invoice_ap.sop_runner import (
    SOPRunner as InvoiceAPSOPRunner,
    INVOICE_AP_SOP,
    GateDecision as InvoiceAPGateDecision,
)
from asynccraft.skins.inbox_triage.sop_runner import (
    SOPRunner as InboxTriageSOPRunner,
    INBOX_TRIAGE_SOP,
    GateDecision as InboxTriageGateDecision,
)
from asynccraft.skins.voice_dispatch.sop_runner import (
    SOPRunner as VoiceDispatchSOPRunner,
    VOICE_DISPATCH_SOP,
    GateDecision as VoiceDispatchGateDecision,
)

router = APIRouter()

env = Environment(loader=FileSystemLoader("asynccraft/ui/templates"), cache_size=0)
env.filters["tojson"] = lambda x: json.dumps(x, indent=2)

templates = Jinja2Templates(env=env)

MOCK_OPERATORS = [
    {"id": "john_chen", "name": "John Chen", "role": "Dispatcher"},
    {"id": "jane_park", "name": "Jane Park", "role": "Sales Manager"},
    {"id": "alex_rivera", "name": "Alex Rivera", "role": "Ops Manager"},
    {"id": "sam_okonkwo", "name": "Sam Okonkwo", "role": "Finance Controller"},
]

# Skin Registry: centralizes skin metadata for tabs, deep links, and demos
SKIN_REGISTRY = {
    "ops_dispatch": {
        "id": "ops_dispatch",
        "name": "Dispatch SOP",
        "tagline": "Freight & Field Ops Automation",
        "pitch": "Automate freight dispatch from inbound load request to POD + billing. Dynamic gates for compliance (DOT/insurance), driver confirmation, and weather routing keep ops managers in control while the agent handles the workflow choreography. Perfect for trucking, 3PL, and field service companies managing 50+ loads per day.",
        "icon": "🚛",
        "get_samples": get_sample_exceptions,
        "sop_runner_class": DispatchSOPRunner,
        "sop_definition": DISPATCH_SOP,
        "gate_decision_class": DispatchGateDecision,
        "deep_link": "/demo/dispatch",
        "click_path": [
            "Inbound email triggers load creation in TMS",
            "Agent assigns equipment, driver, checks compliance (insurance, CDL, DOT hours)",
            "Human approves compliance gate → driver confirmation gate → weather risk gate",
            "Conditional branches: reject paths escalate/hold, approve paths advance to delivery",
            "Final step: POD received, invoice generated, compliance audit logged",
        ],
    },
    "crm_followup": {
        "id": "crm_followup",
        "name": "CRM Follow-up",
        "tagline": "SME Sales Lead Automation",
        "pitch": "Automate inbound lead follow-up for mid-market B2B sales teams. Agent enriches lead data, scores fit, drafts personalized follow-up emails, and routes to CRM — all with human approval gates before sending. Sales reps approve/reject email drafts; manager review triggers for high-value deals. Built for logistics software, supply chain SaaS, and B2B service companies.",
        "icon": "📧",
        "get_samples": get_sample_leads,
        "sop_runner_class": CRMFollowupSOPRunner,
        "sop_definition": CRM_FOLLOWUP_SOP,
        "gate_decision_class": CRMGateDecision,
        "deep_link": "/demo/crm",
        "click_path": [
            "Inbound lead (form submission) ingested with company details",
            "Agent enriches data (firmographics, tech stack), scores lead fit",
            "Score threshold gate: high-scoring leads → draft email, low → nurture campaign",
            "Human approves email draft before send (gate shows preview + subject line)",
            "Conditional manager review for high-value deals (>$50K estimate)",
            "Email sent → CRM updated with stage + owner → audit trail logged",
        ],
    },
    "invoice_ap": {
        "id": "invoice_ap",
        "name": "Invoice / AP Exception",
        "tagline": "Finance Exception Handling",
        "pitch": "Automate invoice 3-way match exceptions for AP teams. When PO/invoice/receipt don't match (qty variance, price discrepancy), the agent proposes corrections and routes to finance for approval. Human gates for correction approval and vendor compliance checks prevent errors while keeping AP flowing. Ideal for manufacturers, distributors, and ops-heavy SMEs processing 100+ invoices per month.",
        "icon": "💰",
        "get_samples": get_sample_invoices,
        "sop_runner_class": InvoiceAPSOPRunner,
        "sop_definition": INVOICE_AP_SOP,
        "gate_decision_class": InvoiceAPGateDecision,
        "deep_link": "/demo/invoice",
        "click_path": [
            "Invoice arrives → 3-way match runs (PO vs Invoice vs Receipt)",
            "Mismatch detected (e.g., qty overage: invoice 105 units vs PO 100 units)",
            "Agent proposes correction with $ delta ($122.50 overage within tolerance)",
            "Human approves correction gate (shows original/corrected amounts + reason)",
            "Vendor compliance gate checks payment terms, disputes, credit limit",
            "Invoice posted to AP → GL writeback → audit + compliance log complete",
        ],
    },
    "inbox_triage": {
        "id": "inbox_triage",
        "name": "Inbox Triage",
        "tagline": "Lakeshore Logistics Billing Desk",
        "pitch": "Lakeshore Logistics (Chicago) ops inbox automation. Prairie Foods (Des Moines) emails detention claim on Load L-55212 Chicago→Dallas. Agent classifies billing-exception (not WISMO — those auto-reply), drafts $380 concession reply + TMS exception. Jane Ortiz (Billing) is the liability HITL gate before any customer concession. Built for 3PL billing desks handling 50+ detention/accessorial disputes per week.",
        "icon": "📥",
        "get_samples": get_sample_tickets,
        "sop_runner_class": InboxTriageSOPRunner,
        "sop_definition": INBOX_TRIAGE_SOP,
        "gate_decision_class": InboxTriageGateDecision,
        "deep_link": "/demo/inbox",
        "click_path": [
            "Lakeshore Logistics inbox: Prairie Foods (Des Moines) emails detention on Load L-55212 Chicago→Dallas",
            "Agent classifies: BILLING-EXCEPTION (not WISMO — those auto-reply for contrast)",
            "Exception gate: HIGH severity $380 detention → draft reply, ROUTINE/WISMO → auto-reply",
            "Draft: $380 concession + TMS exception EXC-55212 prepared",
            "Jane Ortiz (Billing) HITL gate: Approve $380 concession before customer reply",
            "TMS exception posted → Prairie Foods notified → audit trail with compliance log",
        ],
    },
    "voice_dispatch": {
        "id": "voice_dispatch",
        "name": "Voice Dispatch",
        "tagline": "Cold Chain Carrier Booking (Phone Channel)",
        "pitch": "Cold Chain Logistics (Atlanta) broker desk inbound carrier call automation. Carrier covers ATL→DAL reefer Load #18402 at $2,600. Agent transcribes, extracts rate/MC, runs FMCSA/chameleon-MC diamond check, verifies $2,800 rate ceiling. John Hale HITL gate for rate-con send. Then outbound check-call + shipper-notify gate before TMS booking. Phone channel only — built for freight brokerages booking 100+ carrier calls per week.",
        "icon": "📞",
        "get_samples": get_sample_calls,
        "sop_runner_class": VoiceDispatchSOPRunner,
        "sop_definition": VOICE_DISPATCH_SOP,
        "gate_decision_class": VoiceDispatchGateDecision,
        "deep_link": "/demo/voice",
        "click_path": [
            "Cold Chain Logistics (Atlanta): Inbound carrier call for ATL→DAL reefer #18402",
            "Transcribe: Pinnacle Transport, MC-123456, $2,600 rate quoted",
            "FMCSA / chameleon-MC diamond gate: CLEARED (no fraud flags) → continue, FAIL → reject",
            "Rate ceiling check: $2,600 vs $2,800 ceiling → PASS (within budget)",
            "John Hale HITL gate: Approve $2,600 rate-con send to Pinnacle Transport",
            "Outbound check-call + shipper-notify gate → TMS booking BK-18402 → audit trail",
        ],
    },
}


def get_skin_config(skin_id: str) -> dict:
    """Get skin configuration from registry."""
    return SKIN_REGISTRY.get(skin_id, SKIN_REGISTRY["ops_dispatch"])


@router.get("/", response_class=HTMLResponse)
async def index(request: Request, session: AsyncSession = Depends(get_db), skin: str | None = None):
    """Home page with approval queue and skin selector."""
    approval_service = ApprovalService(session)
    pending = await approval_service.get_pending_approvals()
    
    query = select(AgentRun).order_by(AgentRun.created_at.desc()).limit(10)
    result = await session.execute(query)
    recent_runs = list(result.scalars().all())
    
    # Support deep link via query param
    active_skin = skin if skin in SKIN_REGISTRY else "ops_dispatch"
    
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
            "active_skin": active_skin,
            "skin_registry": SKIN_REGISTRY,
            "mock_operators": MOCK_OPERATORS,
            "recent_decisions": recent_decisions,
        },
    )


# Deep link routes
@router.get("/demo/dispatch", response_class=HTMLResponse)
async def demo_dispatch(request: Request, session: AsyncSession = Depends(get_db)):
    """Deep link to Dispatch demo."""
    return await index(request, session, skin="ops_dispatch")


@router.get("/demo/crm", response_class=HTMLResponse)
async def demo_crm(request: Request, session: AsyncSession = Depends(get_db)):
    """Deep link to CRM Follow-up demo."""
    return await index(request, session, skin="crm_followup")


@router.get("/demo/invoice", response_class=HTMLResponse)
async def demo_invoice(request: Request, session: AsyncSession = Depends(get_db)):
    """Deep link to Invoice/AP demo."""
    return await index(request, session, skin="invoice_ap")


@router.get("/demo/inbox", response_class=HTMLResponse)
async def demo_inbox(request: Request, session: AsyncSession = Depends(get_db)):
    """Deep link to Inbox Triage demo."""
    return await index(request, session, skin="inbox_triage")


@router.get("/demo/voice", response_class=HTMLResponse)
async def demo_voice(request: Request, session: AsyncSession = Depends(get_db)):
    """Deep link to Voice Dispatch demo."""
    return await index(request, session, skin="voice_dispatch")


@router.post("/demo-run", response_class=HTMLResponse)
async def create_demo_run(
    request: Request,
    skin: str = Form(...),
    session: AsyncSession = Depends(get_db),
):
    """Create a demo run with SOP-based workflow."""
    skin_config = get_skin_config(skin)
    
    # Get sample data for the skin
    samples = skin_config["get_samples"]()
    input_data = samples[0]
    
    orchestrator = AgentOrchestrator(session)
    run = await orchestrator.create_run(skin, input_data)
    
    # Initialize SOP runner
    sop_runner = skin_config["sop_runner_class"](skin_config["sop_definition"], session)
    
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
        
        skin_config = get_skin_config(run.skin)
        sop_runner = skin_config["sop_runner_class"](skin_config["sop_definition"], session)
        
        # Restore state
        sop_runner.current_step_id = sop_state.current_step_id
        sop_runner.completed_steps = sop_state.completed_steps.copy()
        
        # Handle gate decision (approve)
        GateDecision = skin_config["gate_decision_class"]
        next_gate, new_events = await sop_runner.handle_gate_decision(
            sop_state.current_step_id,
            GateDecision.APPROVE
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
        
        skin_config = get_skin_config(run.skin)
        sop_runner = skin_config["sop_runner_class"](skin_config["sop_definition"], session)
        
        # Restore state
        sop_runner.current_step_id = sop_state.current_step_id
        sop_runner.completed_steps = sop_state.completed_steps.copy()
        
        # Handle gate decision (reject)
        GateDecision = skin_config["gate_decision_class"]
        next_gate, new_events = await sop_runner.handle_gate_decision(
            sop_state.current_step_id,
            GateDecision.REJECT
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
