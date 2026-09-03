"""SOP (Standard Operating Procedure) runner for Deal Flow workflow."""

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


# Deal Flow SOP Definition
DEAL_FLOW_SOP = [
    SOPStep(
        id="ingest",
        label="Ingest Pitch",
        step_type=StepType.AUTO,
        next_step="score",
        log_event="Pitch submission received from RocketShip AI",
    ),
    SOPStep(
        id="score",
        label="Score",
        step_type=StepType.AUTO,
        next_step="kyc-gate",
        log_event="Deal scored: 85/100 (Strong fit, Series A stage)",
    ),
    SOPStep(
        id="kyc-gate",
        label="KYC / Compliance",
        step_type=StepType.GATE,
        tool_name="verify_kyc_compliance",
        tool_args_template={
            "company_name": "RocketShip AI",
            "contact_email": "founder@rocketship.ai",
            "checks": ["identity", "aml", "sanctions"],
        },
        on_approve="partner-notify",
        on_reject="kyc-reject",
        compliance_event="KYC check: Identity verified, AML clear, awaiting sanctions review",
    ),
    SOPStep(
        id="kyc-reject",
        label="Reject / Hold",
        step_type=StepType.AUTO,
        next_step=None,  # Terminal branch
        log_event="KYC failure: Deal rejected or placed on hold for manual review",
    ),
    SOPStep(
        id="partner-notify",
        label="Notify Partner",
        step_type=StepType.GATE,
        tool_name="send_partner_notification",
        tool_args_template={
            "partner_email": "partner@vcfirm.com",
            "company_name": "RocketShip AI",
            "summary": "High-scoring pitch (85/100): AI logistics optimization",
        },
        on_approve="crm-writeback",
        on_reject=None,  # If rejected, stop here
        log_event="Partner notification prepared for Alex Rivera",
    ),
    SOPStep(
        id="crm-writeback",
        label="CRM Writeback",
        step_type=StepType.AUTO,
        next_step="audit",
        log_event="Deal created in CRM: RocketShip AI, Stage: Qualified, Partner: Alex Rivera",
    ),
    SOPStep(
        id="audit",
        label="Audit",
        step_type=StepType.AUTO,
        next_step=None,  # Terminal success
        log_event="Decision logged: Deal qualified and assigned to partner for follow-up",
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
        first_step = DEAL_FLOW_SOP[0]
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
