"""SOP (Standard Operating Procedure) runner for Invoice/AP Exception workflow."""

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


# Invoice/AP SOP Definition
INVOICE_AP_SOP = [
    SOPStep(
        id="ingest",
        label="Ingest Invoice",
        step_type=StepType.AUTO,
        next_step="three-way-match",
        log_event="Invoice received: INV-2026-0891 from Acme Parts Supply (Chicago, IL)",
    ),
    SOPStep(
        id="three-way-match",
        label="3-Way Match",
        step_type=StepType.AUTO,
        next_step="match-result",
        log_event="Running 3-way match: PO-4523 vs Invoice INV-2026-0891 vs Receipt GR-7821",
    ),
    SOPStep(
        id="match-result",
        label="Match Pass/Fail?",
        step_type=StepType.GATE,
        tool_name="assess_three_way_match",
        tool_args_template={
            "invoice_id": "INV-2026-0891",
            "po_id": "PO-4523",
            "receipt_id": "GR-7821",
            "discrepancies": [
                {"type": "quantity", "po_qty": 100, "invoice_qty": 105, "received_qty": 100},
                {"type": "unit_price", "po_price": 24.50, "invoice_price": 24.50},
            ],
        },
        on_approve="auto-post",  # Match passed
        on_reject="propose-correction",  # Mismatch found
        log_event="Mismatch detected: Invoice qty 105 > PO qty 100 (Overage: 5 units × $24.50)",
    ),
    SOPStep(
        id="auto-post",
        label="Auto-post (Clean Match)",
        step_type=StepType.AUTO,
        next_step="gl-writeback",
        log_event="Clean match: Auto-posting to AP without manual review",
    ),
    SOPStep(
        id="propose-correction",
        label="Propose Correction",
        step_type=StepType.AUTO,
        next_step="correction-approve",
        log_event="Proposed resolution: Accept overage (5 units) as valid, adjust PO to 105 units",
    ),
    SOPStep(
        id="correction-approve",
        label="Approve Correction?",
        step_type=StepType.GATE,
        tool_name="approve_ap_correction",
        tool_args_template={
            "invoice_id": "INV-2026-0891",
            "correction_type": "quantity_overage",
            "original_amount": 2450.00,
            "corrected_amount": 2572.50,
            "delta": 122.50,
            "reason": "Vendor shipped 5 extra units (within tolerance), buyer accepted",
        },
        on_approve="vendor-check",
        on_reject="exception-hold",
        log_event="Correction pending approval: +$122.50 overage adjustment",
    ),
    SOPStep(
        id="exception-hold",
        label="Exception Hold",
        step_type=StepType.AUTO,
        next_step=None,  # Terminal branch
        log_event="Correction rejected: Invoice placed on hold for AP manager review",
    ),
    SOPStep(
        id="vendor-check",
        label="Vendor Compliance?",
        step_type=StepType.GATE,
        tool_name="check_vendor_compliance",
        tool_args_template={
            "vendor_id": "VEN-00234",
            "vendor_name": "Acme Parts Supply",
            "checks": ["payment_terms_current", "no_open_disputes", "credit_limit"],
            "invoice_amount": 2572.50,
        },
        on_approve="post-to-ap",
        on_reject="vendor-hold",
        compliance_event="Vendor check: Payment terms current, no disputes, credit OK",
    ),
    SOPStep(
        id="vendor-hold",
        label="Vendor Hold",
        step_type=StepType.AUTO,
        next_step=None,  # Terminal branch
        log_event="Vendor compliance issue: Invoice held pending resolution",
    ),
    SOPStep(
        id="post-to-ap",
        label="Post to AP",
        step_type=StepType.AUTO,
        next_step="gl-writeback",
        log_event="Invoice posted to AP: $2,572.50, Due date: 2026-10-03 (Net 30)",
        billing_event="AP entry created: INV-2026-0891, Amount: $2,572.50, Vendor: Acme Parts Supply",
    ),
    SOPStep(
        id="gl-writeback",
        label="GL Writeback",
        step_type=StepType.AUTO,
        next_step="audit",
        log_event="GL updated: Dr. Inventory $2,572.50, Cr. Accounts Payable $2,572.50",
    ),
    SOPStep(
        id="audit",
        label="Audit + Compliance Log",
        step_type=StepType.AUTO,
        next_step=None,  # Terminal success
        log_event="Invoice processed: INV-2026-0891 cleared, AP posted, GL synced",
        compliance_event="Audit trail: 3-way match override approved, correction $122.50, posted by John Chen",
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
        first_step = INVOICE_AP_SOP[0]
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
