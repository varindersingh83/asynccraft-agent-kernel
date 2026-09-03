"""SOP (Standard Operating Procedure) runner for Dispatch workflow."""

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
    billing_event: str | None = None


# Dispatch SOP Definition
DISPATCH_SOP = [
    SOPStep(
        id="ingest",
        label="Ingest Email",
        step_type=StepType.AUTO,
        next_step="create-load",
        log_event="Email received from customer: Load request for shipment",
    ),
    SOPStep(
        id="create-load",
        label="Create Load",
        step_type=StepType.AUTO,
        next_step="add-equipment",
        log_event="Load created in TMS: shp_demo_001",
    ),
    SOPStep(
        id="add-equipment",
        label="Add Equipment + Driver",
        step_type=StepType.AUTO,
        next_step="compliance-check",
        log_event="Equipment assigned: Truck #789, Driver: Mike Torres",
    ),
    SOPStep(
        id="compliance-check",
        label="Compliance Check",
        step_type=StepType.GATE,
        tool_name="check_compliance",
        tool_args_template={
            "shipment_id": "shp_demo_001",
            "driver_id": "drv_mike_torres",
            "truck_id": "truck_789",
            "check_types": ["insurance", "license", "weight_limit"],
        },
        on_approve="ask-drivers",
        on_reject="compliance-escalate",
        compliance_event="Compliance check: Insurance ✓, License ✓, Weight limit needs review",
    ),
    SOPStep(
        id="compliance-escalate",
        label="Escalate / Hold",
        step_type=StepType.AUTO,
        next_step=None,  # Terminal branch
        log_event="Compliance failure: Escalated to ops manager for manual review",
    ),
    SOPStep(
        id="ask-drivers",
        label="Ask Drivers",
        step_type=StepType.AUTO,
        next_step="driver-confirm",
        log_event="Confirmation request sent to driver via mobile app",
    ),
    SOPStep(
        id="driver-confirm",
        label="Driver Confirmed?",
        step_type=StepType.GATE,
        tool_name="confirm_driver_acceptance",
        tool_args_template={
            "driver_id": "drv_mike_torres",
            "shipment_id": "shp_demo_001",
            "pickup_time": "2026-09-04 08:00",
        },
        on_approve="traffic-weather",
        on_reject="re-ask-broker",
        log_event="Driver response pending...",
    ),
    SOPStep(
        id="re-ask-broker",
        label="Re-ask / Broker",
        step_type=StepType.AUTO,
        next_step=None,  # Terminal branch (would loop back in real system)
        log_event="Driver declined: Searching alternative drivers or brokering load",
    ),
    SOPStep(
        id="traffic-weather",
        label="Traffic + Weather",
        step_type=StepType.AUTO,
        next_step="weather-check",
        log_event="Conditions checked: I-95 Baltimore to NYC, Clear skies, Moderate traffic",
    ),
    SOPStep(
        id="weather-check",
        label="Severe Weather?",
        step_type=StepType.GATE,
        tool_name="assess_weather_risk",
        tool_args_template={
            "route": "I-95 Baltimore to NYC",
            "shipment_id": "shp_demo_001",
            "weather_conditions": "Potential storm system approaching PA",
        },
        on_approve="reroute-approval",  # Severe weather -> reroute
        on_reject="delivery-windows",   # Clear weather -> continue
        log_event="Weather assessment: Storm risk 40%, winds 25mph forecast",
    ),
    SOPStep(
        id="reroute-approval",
        label="Reroute / Delay",
        step_type=StepType.AUTO,
        next_step="delivery-windows",
        log_event="Reroute approved: Taking I-81 alternate route, +45min ETA adjustment",
    ),
    SOPStep(
        id="delivery-windows",
        label="Delivery Windows",
        step_type=StepType.AUTO,
        next_step="coordinator",
        log_event="Delivery window confirmed: 2026-09-04 14:00-16:00 EST",
    ),
    SOPStep(
        id="coordinator",
        label="Assign Coordinator",
        step_type=StepType.AUTO,
        next_step="delivery",
        log_event="Coordinator assigned: Sarah Kim (ops_coord_003)",
    ),
    SOPStep(
        id="delivery",
        label="Delivery",
        step_type=StepType.AUTO,
        next_step="pod-billing",
        log_event="Delivery in progress: Truck en route to destination",
    ),
    SOPStep(
        id="pod-billing",
        label="POD → Billing",
        step_type=StepType.AUTO,
        next_step=None,  # Terminal success
        log_event="POD received and verified",
        billing_event="Invoice generated: INV-2026-0042, Amount: $2,450.00",
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
        first_step = DISPATCH_SOP[0]
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
            
            if step.billing_event:
                events.append({
                    "type": "billing",
                    "step_id": current_id,
                    "message": step.billing_event,
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
