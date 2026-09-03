"""SOP (Standard Operating Procedure) runner for Inbox Triage workflow."""

from dataclasses import dataclass
from enum import Enum
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession


class StepType(str, Enum):
    """Type of SOP step."""
    AUTO = "auto"  # Auto-advance without approval
    GATE = "gate"  # Requires HITL approval to proceed


class GateDecision(str, Enum):
    """Gate decision outcome."""
    APPROVE = "approve"
    REJECT = "reject"


@dataclass
class SOPStep:
    """Definition of an SOP step."""
    id: str
    label: str
    step_type: StepType
    tool_name: str | None = None
    tool_args_template: dict[str, Any] | None = None
    
    # For branch gates: what happens on approve/reject
    on_approve: str | None = None  # Next step ID on approval
    on_reject: str | None = None   # Next step ID on rejection
    
    # For auto steps: just the next step
    next_step: str | None = None
    
    # Audit/logging metadata
    log_event: str | None = None
    compliance_event: str | None = None


# Inbox Triage SOP Definition
INBOX_TRIAGE_SOP = [
    SOPStep(
        id="ingest",
        label="Ingest Ticket",
        step_type=StepType.AUTO,
        next_step="classify",
        log_event="Lakeshore Logistics (Chicago) inbox: Prairie Foods (Des Moines) detention claim, Load L-55212 Chicago→Dallas",
    ),
    SOPStep(
        id="classify",
        label="Classify Ticket Type",
        step_type=StepType.AUTO,
        tool_name="classify_ticket",
        tool_args_template={
            "subject": "Detention charges - Load L-55212",
            "body_preview": "We're claiming 4 hours detention at Dallas consignee for Load L-55212...",
            "sender": "billing@prairiefoods.com",
            "category": "billing-exception",
        },
        next_step="severity-gate",
        log_event="Classification: BILLING-EXCEPTION (not WISMO — those auto-reply, contrast logged)",
    ),
    SOPStep(
        id="severity-gate",
        label="Exception Gate",
        step_type=StepType.GATE,
        tool_name="assess_severity",
        tool_args_template={
            "category": "billing-exception",
            "dollar_amount": 380.0,
            "sla_risk": False,
            "severity": "high",
        },
        on_approve="draft-reply",
        on_reject="junk-archive",
        log_event="Exception severity: HIGH ($380 detention, requires liability gate)",
    ),
    SOPStep(
        id="junk-archive",
        label="WISMO Auto-Reply",
        step_type=StepType.AUTO,
        next_step=None,  # Terminal branch
        log_event="WISMO auto-reply sent, logged for contrast (no billing liability)",
    ),
    SOPStep(
        id="draft-reply",
        label="Draft Detention Reply + TMS Exception",
        step_type=StepType.AUTO,
        next_step="reply-approve",
        log_event="Draft reply: $380 detention concession proposed, TMS exception EXC-55212 prepared",
    ),
    SOPStep(
        id="reply-approve",
        label="Jane Ortiz (Billing) HITL Gate",
        step_type=StepType.GATE,
        tool_name="approve_reply",
        tool_args_template={
            "to_email": "billing@prairiefoods.com",
            "subject": "RE: Detention charges - Load L-55212",
            "draft_preview": "Thank you for contacting us. We acknowledge the 4-hour detention at Dallas. Proposed concession: $380...",
            "concession_amount": 380.0,
        },
        on_approve="sla-escalate",
        on_reject="reply-hold",
        log_event="Jane Ortiz (Billing) liability gate: $380 concession before customer reply",
    ),
    SOPStep(
        id="reply-hold",
        label="Hold / Edit Reply",
        step_type=StepType.AUTO,
        next_step=None,  # Terminal branch
        log_event="Concession rejected by Jane Ortiz: flagged for manual edit or escalation",
    ),
    SOPStep(
        id="sla-escalate",
        label="Manager Escalate?",
        step_type=StepType.GATE,
        tool_name="check_escalate_needed",
        tool_args_template={
            "dollar_amount": 380.0,
            "sla_risk": False,
            "threshold": 500.0,
            "severity": "high",
        },
        on_approve="escalate-manager",
        on_reject="post-tms",
        log_event="Escalation check: $380 (below $500 threshold), no manager escalation needed",
    ),
    SOPStep(
        id="escalate-manager",
        label="Escalate to Manager",
        step_type=StepType.AUTO,
        next_step="post-tms",
        log_event="Escalated: Manager notified for high-$ concession review",
    ),
    SOPStep(
        id="post-tms",
        label="Post TMS Exception",
        step_type=StepType.AUTO,
        tool_name="post_tms_exception",
        tool_args_template={
            "load_id": "L-55212",
            "category": "billing-exception",
            "resolution": "$380 detention concession approved, Prairie Foods notified",
        },
        next_step="audit",
        log_event="TMS exception EXC-55212 posted: Load L-55212 Chicago→Dallas, $380 detention",
    ),
    SOPStep(
        id="audit",
        label="Audit + Compliance Log",
        step_type=StepType.AUTO,
        next_step=None,  # Terminal success
        log_event="Lakeshore Logistics inbox triage complete: Reply sent, TMS exception logged",
        compliance_event="Audit: Billing-exception, Jane Ortiz approved $380 concession, Prairie Foods notified, EXC-55212 logged",
    ),
]


class SOPRunner:
    """Manages SOP progression for a demo run."""
    
    def __init__(self, sop_steps: list[SOPStep], session: AsyncSession):
        self.steps_by_id = {step.id: step for step in sop_steps}
        self.session = session
        self.current_step_id: str | None = None
        self.completed_steps: list[str] = []
        self.events: list[dict[str, Any]] = []
    
    def get_step(self, step_id: str) -> SOPStep | None:
        """Get step definition by ID."""
        return self.steps_by_id.get(step_id)
    
    def start(self) -> SOPStep:
        """Start the SOP from the first step."""
        first_step = INBOX_TRIAGE_SOP[0]
        self.current_step_id = first_step.id
        return first_step
    
    async def advance_to(self, step_id: str) -> tuple[SOPStep | None, list[dict[str, Any]]]:
        """
        Advance to the given step and auto-progress through non-gate steps.
        
        Returns:
            (next_gate_step or None, events_generated)
        """
        events = []
        current_id = step_id
        
        while current_id:
            step = self.get_step(current_id)
            if not step:
                break
            
            self.current_step_id = current_id
            self.completed_steps.append(current_id)
            
            # Record events
            if step.log_event:
                events.append({
                    "type": "log",
                    "step_id": current_id,
                    "message": step.log_event,
                })
            
            if step.compliance_event:
                events.append({
                    "type": "compliance",
                    "step_id": current_id,
                    "message": step.compliance_event,
                })
            
            # Check if this is a gate (needs approval)
            if step.step_type == StepType.GATE:
                return step, events
            
            # Auto-advance to next step
            if step.next_step:
                current_id = step.next_step
            else:
                # Terminal step
                current_id = None
        
        # No gate found, SOP complete
        return None, events
    
    async def handle_gate_decision(
        self, step_id: str, decision: GateDecision
    ) -> tuple[SOPStep | None, list[dict[str, Any]]]:
        """
        Handle a gate decision (approve/reject) and advance SOP.
        
        Returns:
            (next_gate_step or None, events_generated)
        """
        step = self.get_step(step_id)
        if not step or step.step_type != StepType.GATE:
            return None, []
        
        if decision == GateDecision.APPROVE and step.on_approve:
            return await self.advance_to(step.on_approve)
        elif decision == GateDecision.REJECT and step.on_reject:
            return await self.advance_to(step.on_reject)
        else:
            # No branch defined, SOP complete
            return None, []
    
    def get_completed_steps(self) -> list[str]:
        """Get list of completed step IDs."""
        return self.completed_steps.copy()
    
    def is_complete(self) -> bool:
        """Check if SOP has reached a terminal state."""
        if not self.current_step_id:
            return True
        
        step = self.get_step(self.current_step_id)
        if not step:
            return True
        
        # If it's a gate, not complete yet
        if step.step_type == StepType.GATE:
            return False
        
        # If no next step, complete
        return not step.next_step
