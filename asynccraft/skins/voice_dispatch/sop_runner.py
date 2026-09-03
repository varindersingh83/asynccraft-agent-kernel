"""SOP (Standard Operating Procedure) runner for Voice Dispatch workflow."""

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


# Voice Dispatch SOP Definition
VOICE_DISPATCH_SOP = [
    SOPStep(
        id="call-ingest",
        label="Ingest Call",
        step_type=StepType.AUTO,
        next_step="transcribe",
        log_event="After-hours call received: Driver Mike Rodriguez, 22:10 CST from I-55 south of Springfield IL",
    ),
    SOPStep(
        id="transcribe",
        label="Transcribe Voice",
        step_type=StepType.AUTO,
        tool_name="transcribe_call",
        tool_args_template={
            "call_id": "CALL-092326-2210",
            "caller": "Mike Rodriguez (Driver)",
            "duration_seconds": 145,
            "transcript": "Hey dispatch, this is Mike on truck 2847. I'm about 30 miles south of Springfield on I-55. Reefer unit is showing alarm - temp climbing. Carrying perishable freight to Chicago. Need help ASAP.",
        },
        next_step="extract-fields",
        log_event="Transcription complete: 145 seconds, reefer alarm reported, I-55 Springfield IL area",
    ),
    SOPStep(
        id="extract-fields",
        label="Extract Fields",
        step_type=StepType.AUTO,
        tool_name="extract_fields",
        tool_args_template={
            "transcript": "Hey dispatch, this is Mike on truck 2847. I'm about 30 miles south of Springfield on I-55. Reefer unit is showing alarm...",
            "location": "I-55 S, 30mi S of Springfield IL",
            "asset_id": "TRUCK-2847",
            "issue_type": "reefer_alarm",
            "severity": "emergency",
        },
        next_step="severity-gate",
        log_event="Fields extracted: Location I-55 Springfield, Asset TRUCK-2847, Issue: Reefer alarm (perishable cargo)",
    ),
    SOPStep(
        id="severity-gate",
        label="Emergency Assessment",
        step_type=StepType.GATE,
        tool_name="assess_emergency_severity",
        tool_args_template={
            "issue_type": "reefer_alarm",
            "severity": "emergency",
            "time_of_day": "after_hours",
            "cargo_sensitive": True,
        },
        on_approve="propose-tech",
        on_reject="queue-morning",
        log_event="Severity: EMERGENCY (reefer alarm, perishable cargo, after-hours)",
    ),
    SOPStep(
        id="queue-morning",
        label="Queue for Morning",
        step_type=StepType.AUTO,
        next_step=None,  # Terminal branch
        log_event="Non-emergency: Queued for morning dispatch (routine maintenance request)",
    ),
    SOPStep(
        id="propose-tech",
        label="Propose Tech Assignment",
        step_type=StepType.AUTO,
        tool_name="propose_tech_assignment",
        tool_args_template={
            "location": "I-55 S, 30mi S of Springfield IL",
            "issue_type": "reefer_alarm",
            "tech_name": "Carlos Martinez",
            "tech_id": "TECH-104",
            "eta_minutes": 45,
        },
        next_step="assign-approve",
        log_event="Tech proposed: Carlos Martinez (TECH-104) from Springfield depot, ETA 45 minutes",
    ),
    SOPStep(
        id="assign-approve",
        label="Approve Assignment?",
        step_type=StepType.GATE,
        tool_name="approve_assignment",
        tool_args_template={
            "tech_name": "Carlos Martinez",
            "tech_id": "TECH-104",
            "eta_minutes": 45,
            "asset_id": "TRUCK-2847",
        },
        on_approve="notify-shipper",
        on_reject="assignment-hold",
        log_event="Assignment ready for approval (Ops Manager: Alex Rivera)",
    ),
    SOPStep(
        id="assignment-hold",
        label="Hold / Reassign",
        step_type=StepType.AUTO,
        next_step=None,  # Terminal branch
        log_event="Assignment rejected: Flagged for manual reassignment or hold",
    ),
    SOPStep(
        id="notify-shipper",
        label="Notify Shipper?",
        step_type=StepType.GATE,
        tool_name="approve_shipper_notification",
        tool_args_template={
            "shipper_name": "Fresh Foods Distributors",
            "shipper_contact": "dispatch@freshfoodsdist.com",
            "eta_message": "Reefer technician dispatched to truck 2847, ETA 45 minutes. Will update on resolution.",
            "tech_name": "Carlos Martinez",
        },
        on_approve="send-notification",
        on_reject="create-wo",
        log_event="Shipper notification draft ready: Fresh Foods Distributors",
    ),
    SOPStep(
        id="send-notification",
        label="Send Customer ETA",
        step_type=StepType.AUTO,
        next_step="create-wo",
        log_event="Shipper notified: dispatch@freshfoodsdist.com - Tech en route, ETA 45 min",
    ),
    SOPStep(
        id="create-wo",
        label="Create Work Order",
        step_type=StepType.AUTO,
        tool_name="create_work_order",
        tool_args_template={
            "asset_id": "TRUCK-2847",
            "tech_id": "TECH-104",
            "issue_type": "reefer_alarm",
            "location": "I-55 S, 30mi S of Springfield IL",
        },
        next_step="audit",
        log_event="Work order WO-28470 created: TRUCK-2847, reefer alarm, Tech Carlos Martinez assigned",
    ),
    SOPStep(
        id="audit",
        label="Audit + Billing Touch",
        step_type=StepType.AUTO,
        next_step=None,  # Terminal success
        log_event="Voice dispatch complete: WO created, tech dispatched, shipper notified, billing flagged for after-hours fee",
        compliance_event="Audit trail: Call from Mike Rodriguez (TRUCK-2847), Emergency reefer alarm, Tech TECH-104 dispatched 22:30 CST, WO-28470",
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
        first_step = VOICE_DISPATCH_SOP[0]
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
