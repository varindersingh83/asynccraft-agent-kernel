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
        log_event="Cold Chain Logistics (Atlanta) broker desk: inbound carrier call for Load #18402 (ATL→DAL reefer)",
    ),
    SOPStep(
        id="transcribe",
        label="Transcribe Voice",
        step_type=StepType.AUTO,
        tool_name="transcribe_call",
        tool_args_template={
            "call_id": "CALL-092326-1430",
            "caller": "Carrier: Pinnacle Transport",
            "duration_seconds": 142,
            "transcript": "Cold Chain Logistics broker desk, this is Pinnacle Transport. We can cover your ATL to Dallas reefer load #18402. MC 123456, FMCSA cleared, $2,600 for the lane. Can you send rate-con?",
        },
        next_step="extract-fields",
        log_event="Transcription: Pinnacle Transport, MC-123456, ATL→DAL reefer #18402, $2,600 rate quoted",
    ),
    SOPStep(
        id="extract-fields",
        label="Extract Fields",
        step_type=StepType.AUTO,
        tool_name="extract_fields",
        tool_args_template={
            "transcript": "Cold Chain Logistics broker desk, this is Pinnacle Transport. We can cover your ATL to Dallas reefer load #18402...",
            "carrier_name": "Pinnacle Transport",
            "mc_number": "MC-123456",
            "load_id": "#18402",
            "route": "ATL→DAL",
            "rate_quoted": 2600.0,
        },
        next_step="severity-gate",
        log_event="Fields: Carrier Pinnacle Transport, MC-123456, Load #18402 ATL→DAL, Rate $2,600",
    ),
    SOPStep(
        id="severity-gate",
        label="FMCSA / Chameleon-MC Diamond Gate",
        step_type=StepType.GATE,
        tool_name="check_fmcsa_compliance",
        tool_args_template={
            "carrier_name": "Pinnacle Transport",
            "mc_number": "MC-123456",
            "fmcsa_status": "cleared",
        },
        on_approve="propose-tech",
        on_reject="queue-morning",
        log_event="FMCSA check: Pinnacle Transport (MC-123456) → CLEARED (no chameleon MC flags)",
    ),
    SOPStep(
        id="queue-morning",
        label="FMCSA Hold / Reject",
        step_type=StepType.AUTO,
        next_step=None,  # Terminal branch
        log_event="FMCSA failed or chameleon MC detected: carrier rejected, phone note logged",
    ),
    SOPStep(
        id="propose-tech",
        label="Check Rate Ceiling",
        step_type=StepType.AUTO,
        tool_name="check_rate_ceiling",
        tool_args_template={
            "carrier_name": "Pinnacle Transport",
            "rate_quoted": 2600.0,
            "rate_ceiling": 2800.0,
        },
        next_step="assign-approve",
        log_event="Rate check: $2,600 vs $2,800 ceiling → PASS (within budget)",
    ),
    SOPStep(
        id="assign-approve",
        label="John Hale Rate-Con HITL Gate",
        step_type=StepType.GATE,
        tool_name="approve_rate_con",
        tool_args_template={
            "carrier_name": "Pinnacle Transport",
            "rate_quoted": 2600.0,
            "load_id": "#18402",
            "route": "ATL→DAL",
        },
        on_approve="notify-shipper",
        on_reject="assignment-hold",
        log_event="John Hale gate: Rate-con approval before send ($2,600 to Pinnacle Transport)",
    ),
    SOPStep(
        id="assignment-hold",
        label="Hold / Negotiate",
        step_type=StepType.AUTO,
        next_step=None,  # Terminal branch
        log_event="Rate-con rejected by John Hale: flagged for renegotiation or alternate carrier",
    ),
    SOPStep(
        id="notify-shipper",
        label="Outbound Check-Call + Shipper Notify Gate",
        step_type=StepType.GATE,
        tool_name="approve_shipper_notification",
        tool_args_template={
            "shipper_name": "Atlanta Cold Storage",
            "shipper_contact": "dispatch@atlcold.com",
            "eta_message": "Carrier Pinnacle Transport confirmed for Load #18402 ATL→DAL. Pickup scheduled tomorrow 8 AM.",
            "tech_name": "Pinnacle Transport",
        },
        on_approve="send-notification",
        on_reject="create-wo",
        log_event="Shipper notification + outbound check-call gate: Atlanta Cold Storage",
    ),
    SOPStep(
        id="send-notification",
        label="Send Shipper Notification",
        step_type=StepType.AUTO,
        next_step="create-wo",
        log_event="Shipper notified: dispatch@atlcold.com - Carrier confirmed, pickup 8 AM",
    ),
    SOPStep(
        id="create-wo",
        label="Create Load Booking",
        step_type=StepType.AUTO,
        tool_name="create_load_booking",
        tool_args_template={
            "load_id": "#18402",
            "carrier_name": "Pinnacle Transport",
            "rate_quoted": 2600.0,
            "route": "ATL→DAL",
        },
        next_step="audit",
        log_event="Load booking BK-18402 created: Pinnacle Transport, $2,600, ATL→DAL reefer",
    ),
    SOPStep(
        id="audit",
        label="Audit + Phone Channel Log",
        step_type=StepType.AUTO,
        next_step=None,  # Terminal success
        log_event="Cold Chain Logistics carrier booking complete: Rate-con sent, shipper notified, TMS booked",
        compliance_event="Audit: Phone channel, Pinnacle Transport (MC-123456), $2,600 approved by John Hale, Load #18402 ATL→DAL booked",
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
