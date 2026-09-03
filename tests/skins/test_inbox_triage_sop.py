"""Tests for Inbox Triage SOP runner."""

import pytest
from asynccraft.skins.inbox_triage.sop_runner import (
    SOPRunner,
    INBOX_TRIAGE_SOP,
    GateDecision,
    StepType,
)


class MockSession:
    """Mock async session for testing."""
    pass


@pytest.mark.asyncio
async def test_inbox_triage_sop_starts_at_ingest():
    """Test Inbox Triage SOP starts at ingest step."""
    session = MockSession()
    runner = SOPRunner(INBOX_TRIAGE_SOP, session)
    
    first_step = runner.start()
    assert first_step.id == "ingest"
    assert runner.current_step_id == "ingest"


@pytest.mark.asyncio
async def test_inbox_triage_advances_to_first_gate():
    """Test SOP auto-advances to first gate (severity-gate)."""
    session = MockSession()
    runner = SOPRunner(INBOX_TRIAGE_SOP, session)
    
    runner.start()
    gate, events = await runner.advance_to(runner.current_step_id)
    
    assert gate is not None
    assert gate.id == "severity-gate"
    assert gate.step_type == StepType.GATE
    assert len(events) == 3  # ingest, classify, severity-gate


@pytest.mark.asyncio
async def test_inbox_triage_severity_gate_approve_path():
    """Test approving severity gate advances to reply-approve."""
    session = MockSession()
    runner = SOPRunner(INBOX_TRIAGE_SOP, session)
    
    runner.start()
    gate, _ = await runner.advance_to(runner.current_step_id)
    assert gate.id == "severity-gate"
    
    # Approve severity gate (high/critical severity)
    next_gate, events = await runner.handle_gate_decision(gate.id, GateDecision.APPROVE)
    assert next_gate is not None
    assert next_gate.id == "reply-approve"


@pytest.mark.asyncio
async def test_inbox_triage_severity_gate_reject_path():
    """Test rejecting severity gate goes to junk-archive (terminal)."""
    session = MockSession()
    runner = SOPRunner(INBOX_TRIAGE_SOP, session)
    
    runner.start()
    gate, _ = await runner.advance_to(runner.current_step_id)
    assert gate.id == "severity-gate"
    
    # Reject severity gate (routine)
    next_gate, events = await runner.handle_gate_decision(gate.id, GateDecision.REJECT)
    assert next_gate is None  # Terminal branch
    assert runner.is_complete()


@pytest.mark.asyncio
async def test_inbox_triage_reply_approve_advances():
    """Test reply approval gate advances to sla-escalate check."""
    session = MockSession()
    runner = SOPRunner(INBOX_TRIAGE_SOP, session)
    
    runner.start()
    await runner.advance_to(runner.current_step_id)
    await runner.handle_gate_decision("severity-gate", GateDecision.APPROVE)
    
    # Should be at reply-approve gate now
    assert runner.current_step_id == "reply-approve"
    
    # Approve reply
    next_gate, events = await runner.handle_gate_decision("reply-approve", GateDecision.APPROVE)
    assert next_gate is not None
    assert next_gate.id == "sla-escalate"


@pytest.mark.asyncio
async def test_inbox_triage_full_happy_path():
    """Test full Inbox Triage SOP happy path."""
    session = MockSession()
    runner = SOPRunner(INBOX_TRIAGE_SOP, session)
    
    runner.start()
    
    # Advance to severity-gate
    gate, _ = await runner.advance_to(runner.current_step_id)
    assert gate.id == "severity-gate"
    
    # Approve severity (high/critical)
    gate, _ = await runner.handle_gate_decision("severity-gate", GateDecision.APPROVE)
    assert gate.id == "reply-approve"
    
    # Approve reply send
    gate, _ = await runner.handle_gate_decision("reply-approve", GateDecision.APPROVE)
    assert gate.id == "sla-escalate"
    
    # Reject escalation (below threshold)
    gate, _ = await runner.handle_gate_decision("sla-escalate", GateDecision.REJECT)
    assert gate is None  # SOP complete
    assert runner.is_complete()
    
    # Check all steps completed
    completed = runner.get_completed_steps()
    assert "ingest" in completed
    assert "classify" in completed
    assert "draft-reply" in completed
    assert "post-tms" in completed
    assert "audit" in completed


@pytest.mark.asyncio
async def test_inbox_triage_escalation_path():
    """Test escalation path when SLA risk is high."""
    session = MockSession()
    runner = SOPRunner(INBOX_TRIAGE_SOP, session)
    
    runner.start()
    
    # Advance to severity-gate
    gate, _ = await runner.advance_to(runner.current_step_id)
    
    # Approve severity
    gate, _ = await runner.handle_gate_decision("severity-gate", GateDecision.APPROVE)
    
    # Approve reply
    gate, _ = await runner.handle_gate_decision("reply-approve", GateDecision.APPROVE)
    assert gate.id == "sla-escalate"
    
    # Approve escalation
    gate, _ = await runner.handle_gate_decision("sla-escalate", GateDecision.APPROVE)
    assert gate is None  # Should complete after escalate-manager and post-tms
    assert runner.is_complete()
    
    # Check escalation step was completed
    completed = runner.get_completed_steps()
    assert "escalate-manager" in completed


@pytest.mark.asyncio
async def test_inbox_triage_events_logged():
    """Test that log events are captured."""
    session = MockSession()
    runner = SOPRunner(INBOX_TRIAGE_SOP, session)
    
    runner.start()
    _, events = await runner.advance_to(runner.current_step_id)
    
    assert len(events) > 0
    assert any(e["type"] == "log" for e in events)
    assert any("Chicago" in e["message"] or "Detroit" in e["message"] for e in events)
