"""Tests for SOP runner progression."""

import pytest
from asynccraft.skins.ops_dispatch.sop_runner import (
    SOPRunner as DispatchSOPRunner,
    DISPATCH_SOP,
    GateDecision,
    StepType,
)
from asynccraft.skins.deal_flow.sop_runner import (
    SOPRunner as DealFlowSOPRunner,
    DEAL_FLOW_SOP,
    GateDecision as DealFlowGateDecision,
)


@pytest.mark.asyncio
async def test_dispatch_sop_starts_at_first_step(db_session):
    """SOP starts at the ingest step."""
    runner = DispatchSOPRunner(DISPATCH_SOP, db_session)
    first_step = runner.start()
    
    assert first_step is not None
    assert first_step.id == "ingest"
    assert runner.current_step_id == "ingest"


@pytest.mark.asyncio
async def test_dispatch_sop_advances_to_first_gate(db_session):
    """SOP auto-advances through non-gate steps to first gate."""
    runner = DispatchSOPRunner(DISPATCH_SOP, db_session)
    runner.start()
    
    gate, events = await runner.advance_to(runner.current_step_id)
    
    assert gate is not None
    assert gate.id == "compliance-check"
    assert gate.step_type == StepType.GATE
    assert len(events) > 0
    assert "ingest" in runner.completed_steps
    assert "create-load" in runner.completed_steps
    assert "add-equipment" in runner.completed_steps


@pytest.mark.asyncio
async def test_dispatch_sop_gate_approval_advances(db_session):
    """Approving a gate advances to next step."""
    runner = DispatchSOPRunner(DISPATCH_SOP, db_session)
    runner.start()
    
    # Advance to first gate
    gate, events = await runner.advance_to(runner.current_step_id)
    assert gate.id == "compliance-check"
    
    # Approve the gate
    next_gate, new_events = await runner.handle_gate_decision(
        gate.id, GateDecision.APPROVE
    )
    
    assert next_gate is not None
    assert next_gate.id == "driver-confirm"
    assert "ask-drivers" in runner.completed_steps


@pytest.mark.asyncio
async def test_dispatch_sop_gate_rejection_takes_branch(db_session):
    """Rejecting a gate takes the failure branch."""
    runner = DispatchSOPRunner(DISPATCH_SOP, db_session)
    runner.start()
    
    # Advance to first gate
    gate, events = await runner.advance_to(runner.current_step_id)
    assert gate.id == "compliance-check"
    
    # Reject the gate
    next_gate, new_events = await runner.handle_gate_decision(
        gate.id, GateDecision.REJECT
    )
    
    # Should go to escalate branch (terminal)
    assert next_gate is None
    assert "compliance-escalate" in runner.completed_steps


@pytest.mark.asyncio
async def test_dispatch_sop_full_happy_path(db_session):
    """Test full SOP walkthrough with all approvals."""
    runner = DispatchSOPRunner(DISPATCH_SOP, db_session)
    runner.start()
    
    # Start and advance to first gate
    gate, events = await runner.advance_to(runner.current_step_id)
    assert gate.id == "compliance-check"
    
    # Approve compliance
    gate, events = await runner.handle_gate_decision(gate.id, GateDecision.APPROVE)
    assert gate.id == "driver-confirm"
    
    # Approve driver
    gate, events = await runner.handle_gate_decision(gate.id, GateDecision.APPROVE)
    assert gate.id == "weather-check"
    
    # Reject weather (clear weather, continue)
    gate, events = await runner.handle_gate_decision(gate.id, GateDecision.REJECT)
    
    # Should complete rest of flow
    assert gate is None
    assert "delivery-windows" in runner.completed_steps
    assert "coordinator" in runner.completed_steps
    assert "delivery" in runner.completed_steps
    assert "pod-billing" in runner.completed_steps


@pytest.mark.asyncio
async def test_deal_flow_sop_starts_at_first_step(db_session):
    """Deal flow SOP starts at ingest step."""
    runner = DealFlowSOPRunner(DEAL_FLOW_SOP, db_session)
    first_step = runner.start()
    
    assert first_step is not None
    assert first_step.id == "ingest"
    assert runner.current_step_id == "ingest"


@pytest.mark.asyncio
async def test_deal_flow_sop_advances_to_first_gate(db_session):
    """Deal flow auto-advances to first gate."""
    runner = DealFlowSOPRunner(DEAL_FLOW_SOP, db_session)
    runner.start()
    
    gate, events = await runner.advance_to(runner.current_step_id)
    
    assert gate is not None
    assert gate.id == "kyc-gate"
    assert len(events) > 0
    assert "ingest" in runner.completed_steps
    assert "score" in runner.completed_steps


@pytest.mark.asyncio
async def test_deal_flow_sop_kyc_approval(db_session):
    """Approving KYC gate advances to partner notify."""
    runner = DealFlowSOPRunner(DEAL_FLOW_SOP, db_session)
    runner.start()
    
    # Advance to KYC gate
    gate, events = await runner.advance_to(runner.current_step_id)
    assert gate.id == "kyc-gate"
    
    # Approve KYC
    next_gate, new_events = await runner.handle_gate_decision(
        gate.id, DealFlowGateDecision.APPROVE
    )
    
    assert next_gate is not None
    assert next_gate.id == "partner-notify"


@pytest.mark.asyncio
async def test_deal_flow_sop_kyc_rejection(db_session):
    """Rejecting KYC gate terminates flow."""
    runner = DealFlowSOPRunner(DEAL_FLOW_SOP, db_session)
    runner.start()
    
    # Advance to KYC gate
    gate, events = await runner.advance_to(runner.current_step_id)
    assert gate.id == "kyc-gate"
    
    # Reject KYC
    next_gate, new_events = await runner.handle_gate_decision(
        gate.id, DealFlowGateDecision.REJECT
    )
    
    # Should go to reject branch (terminal)
    assert next_gate is None
    assert "kyc-reject" in runner.completed_steps


@pytest.mark.asyncio
async def test_deal_flow_sop_full_happy_path(db_session):
    """Test full deal flow with all approvals."""
    runner = DealFlowSOPRunner(DEAL_FLOW_SOP, db_session)
    runner.start()
    
    # Advance to KYC gate
    gate, events = await runner.advance_to(runner.current_step_id)
    assert gate.id == "kyc-gate"
    
    # Approve KYC
    gate, events = await runner.handle_gate_decision(
        gate.id, DealFlowGateDecision.APPROVE
    )
    assert gate.id == "partner-notify"
    
    # Approve partner notify
    gate, events = await runner.handle_gate_decision(
        gate.id, DealFlowGateDecision.APPROVE
    )
    
    # Should complete flow
    assert gate is None
    assert "crm-writeback" in runner.completed_steps
    assert "audit" in runner.completed_steps


@pytest.mark.asyncio
async def test_sop_events_recorded(db_session):
    """SOP runner records events as it progresses."""
    runner = DispatchSOPRunner(DISPATCH_SOP, db_session)
    runner.start()
    
    gate, events = await runner.advance_to(runner.current_step_id)
    
    assert len(events) > 0
    
    # Check that log events were recorded
    log_events = [e for e in events if e["type"] == "log"]
    assert len(log_events) >= 3  # ingest, create-load, add-equipment
    
    # Check compliance events
    compliance_events = [e for e in events if e["type"] == "compliance"]
    assert len(compliance_events) > 0
