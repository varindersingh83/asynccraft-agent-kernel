"""Tests for CRM Follow-up SOP runner."""

import pytest
from asynccraft.skins.crm_followup.sop_runner import (
    SOPRunner,
    CRM_FOLLOWUP_SOP,
    GateDecision,
    StepType,
)


class MockSession:
    """Mock async session for testing."""
    pass


@pytest.mark.asyncio
async def test_crm_followup_sop_starts_at_ingest():
    """Test CRM follow-up SOP starts at ingest step."""
    session = MockSession()
    runner = SOPRunner(CRM_FOLLOWUP_SOP, session)
    
    first_step = runner.start()
    assert first_step.id == "ingest"
    assert runner.current_step_id == "ingest"


@pytest.mark.asyncio
async def test_crm_followup_advances_to_first_gate():
    """Test SOP auto-advances to first gate (score-gate)."""
    session = MockSession()
    runner = SOPRunner(CRM_FOLLOWUP_SOP, session)
    
    runner.start()
    gate, events = await runner.advance_to(runner.current_step_id)
    
    assert gate is not None
    assert gate.id == "score-gate"
    assert gate.step_type == StepType.GATE
    assert len(events) == 3  # ingest, enrich, score-gate


@pytest.mark.asyncio
async def test_crm_followup_score_gate_approve_path():
    """Test approving score gate advances to draft-email."""
    session = MockSession()
    runner = SOPRunner(CRM_FOLLOWUP_SOP, session)
    
    runner.start()
    gate, _ = await runner.advance_to(runner.current_step_id)
    assert gate.id == "score-gate"
    
    # Approve score gate
    next_gate, events = await runner.handle_gate_decision(gate.id, GateDecision.APPROVE)
    assert next_gate is not None
    assert next_gate.id == "email-approve"


@pytest.mark.asyncio
async def test_crm_followup_score_gate_reject_path():
    """Test rejecting score gate goes to low-score-nurture (terminal)."""
    session = MockSession()
    runner = SOPRunner(CRM_FOLLOWUP_SOP, session)
    
    runner.start()
    gate, _ = await runner.advance_to(runner.current_step_id)
    assert gate.id == "score-gate"
    
    # Reject score gate
    next_gate, events = await runner.handle_gate_decision(gate.id, GateDecision.REJECT)
    assert next_gate is None  # Terminal branch
    assert runner.is_complete()


@pytest.mark.asyncio
async def test_crm_followup_email_approve_advances():
    """Test email approval gate advances to manager review check."""
    session = MockSession()
    runner = SOPRunner(CRM_FOLLOWUP_SOP, session)
    
    runner.start()
    await runner.advance_to(runner.current_step_id)
    await runner.handle_gate_decision("score-gate", GateDecision.APPROVE)
    
    # Should be at email-approve gate now
    assert runner.current_step_id == "email-approve"
    
    # Approve email
    next_gate, events = await runner.handle_gate_decision("email-approve", GateDecision.APPROVE)
    assert next_gate is not None
    assert next_gate.id == "needs-manager-review"


@pytest.mark.asyncio
async def test_crm_followup_full_happy_path():
    """Test full CRM follow-up SOP happy path."""
    session = MockSession()
    runner = SOPRunner(CRM_FOLLOWUP_SOP, session)
    
    runner.start()
    
    # Advance to score-gate
    gate, _ = await runner.advance_to(runner.current_step_id)
    assert gate.id == "score-gate"
    
    # Approve score (high score)
    gate, _ = await runner.handle_gate_decision("score-gate", GateDecision.APPROVE)
    assert gate.id == "email-approve"
    
    # Approve email send
    gate, _ = await runner.handle_gate_decision("email-approve", GateDecision.APPROVE)
    assert gate.id == "needs-manager-review"
    
    # Reject manager review (deal size below threshold)
    gate, _ = await runner.handle_gate_decision("needs-manager-review", GateDecision.REJECT)
    assert gate is None  # SOP complete
    assert runner.is_complete()
    
    # Check all steps completed
    completed = runner.get_completed_steps()
    assert "ingest" in completed
    assert "enrich" in completed
    assert "draft-email" in completed
    assert "send-email" in completed
    assert "crm-update" in completed
    assert "audit" in completed


@pytest.mark.asyncio
async def test_crm_followup_events_logged():
    """Test that log events are captured."""
    session = MockSession()
    runner = SOPRunner(CRM_FOLLOWUP_SOP, session)
    
    runner.start()
    _, events = await runner.advance_to(runner.current_step_id)
    
    assert len(events) > 0
    assert any(e["type"] == "log" for e in events)
    assert any("TechFlow Logistics" in e["message"] for e in events)
