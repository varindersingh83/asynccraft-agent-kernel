"""SOP (Standard Operating Procedure) runner for CRM Follow-up workflow."""

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


# CRM Follow-up SOP Definition
CRM_FOLLOWUP_SOP = [
    SOPStep(
        id="ingest",
        label="Ingest Lead",
        step_type=StepType.AUTO,
        next_step="enrich",
        log_event="Inbound lead received: TechFlow Logistics, Chicago IL (form submission)",
    ),
    SOPStep(
        id="enrich",
        label="Enrich + Score",
        step_type=StepType.AUTO,
        next_step="score-gate",
        log_event="Enrichment complete: Company size 120 employees, Annual revenue ~$15M, Industry: Supply Chain",
    ),
    SOPStep(
        id="score-gate",
        label="Score Threshold?",
        step_type=StepType.GATE,
        tool_name="assess_lead_score",
        tool_args_template={
            "company_name": "TechFlow Logistics",
            "lead_score": 78,
            "fit_signals": ["mid-market", "existing_tech_stack", "budget_authority"],
            "threshold": 70,
        },
        on_approve="draft-email",
        on_reject="low-score-nurture",
        log_event="Lead score: 78/100 (Mid-market fit, buying authority confirmed)",
    ),
    SOPStep(
        id="low-score-nurture",
        label="Low Score → Nurture",
        step_type=StepType.AUTO,
        next_step=None,  # Terminal branch
        log_event="Below threshold: Added to nurture campaign, no immediate follow-up",
    ),
    SOPStep(
        id="draft-email",
        label="Draft Follow-up Email",
        step_type=StepType.AUTO,
        next_step="email-approve",
        log_event="Email drafted: Personalized follow-up for TechFlow Logistics (Chicago warehouse ops angle)",
    ),
    SOPStep(
        id="email-approve",
        label="Approve Email Send?",
        step_type=StepType.GATE,
        tool_name="approve_email_draft",
        tool_args_template={
            "to_email": "sam.johnson@techflow-logistics.com",
            "subject": "RE: Your inquiry about route optimization",
            "preview": "Hi Sam, Thanks for reaching out about optimizing your Chicago-Dallas lanes...",
            "company": "TechFlow Logistics",
        },
        on_approve="needs-manager-review",
        on_reject="email-hold",
        log_event="Email draft ready for approval (sales rep: Jane Park)",
    ),
    SOPStep(
        id="email-hold",
        label="Hold / Edit",
        step_type=StepType.AUTO,
        next_step=None,  # Terminal branch
        log_event="Email send rejected: Flagged for manual edit or hold",
    ),
    SOPStep(
        id="needs-manager-review",
        label="Manager Review?",
        step_type=StepType.GATE,
        tool_name="check_manager_review_needed",
        tool_args_template={
            "deal_size_estimate": 45000,
            "rep_experience_days": 90,
            "company_tier": "mid-market",
            "threshold": 50000,
        },
        on_approve="manager-escalate",
        on_reject="send-email",
        log_event="Deal size check: $45K (below manager review threshold)",
    ),
    SOPStep(
        id="manager-escalate",
        label="Escalate to Manager",
        step_type=StepType.AUTO,
        next_step="send-email",
        log_event="Escalated: Manager review requested for high-value deal (Alex Rivera notified)",
    ),
    SOPStep(
        id="send-email",
        label="Send Email",
        step_type=StepType.AUTO,
        next_step="crm-update",
        log_event="Email sent to sam.johnson@techflow-logistics.com at 2026-09-03 11:42 EST",
    ),
    SOPStep(
        id="crm-update",
        label="CRM Writeback",
        step_type=StepType.AUTO,
        next_step="audit",
        log_event="CRM updated: TechFlow Logistics moved to 'Contacted' stage, Owner: Jane Park",
    ),
    SOPStep(
        id="audit",
        label="Audit + Log",
        step_type=StepType.AUTO,
        next_step=None,  # Terminal success
        log_event="Follow-up sequence complete: Email sent, CRM synced, compliance logged",
        compliance_event="Audit trail: Lead TechFlow Logistics, Score 78, Email approved by Jane Park, Sent at 11:42 EST",
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
        first_step = CRM_FOLLOWUP_SOP[0]
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
