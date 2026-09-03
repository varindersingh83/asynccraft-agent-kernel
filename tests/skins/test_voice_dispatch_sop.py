"""Tests for Voice Dispatch SOP runner."""

import pytest
from asynccraft.skins.voice_dispatch.sop_runner import (
    SOPRunner,
    VOICE_DISPATCH_SOP,
    GateDecision,
    StepType,
)


class MockSession:
    """Mock async session for testing."""
    pass


@pytest.mark.asyncio
async def test_voice_dispatch_sop_starts_at_call_ingest():
    """Test Voice Dispatch SOP starts at call-ingest step."""
    session = MockSession()
    runner = SOPRunner(VOICE_DISPATCH_SOP, session)
    
    first_step = runner.start()
    assert first_step.id == "call-ingest"
    assert runner.current_step_id == "call-ingest"


@pytest.mark.asyncio
async def test_voice_dispatch_advances_to_first_gate():
    """Test SOP auto-advances to first gate (severity-gate)."""
    session = MockSession()
    runner = SOPRunner(VOICE_DISPATCH_SOP, session)
    
    runner.start()
    gate, events = await runner.advance_to(runner.current_step_id)
    
    assert gate is not None
    assert gate.id == "severity-gate"
    assert gate.step_type == StepType.GATE
    assert len(events) == 4  # call-ingest, transcribe, extract-fields, severity-gate


@pytest.mark.asyncio
async def test_voice_dispatch_severity_gate_approve_path():
    """Test approving severity gate advances to assign-approve."""
    session = MockSession()
    runner = SOPRunner(VOICE_DISPATCH_SOP, session)
    
    runner.start()
    gate, _ = await runner.advance_to(runner.current_step_id)
    assert gate.id == "severity-gate"
    
    # Approve severity gate (emergency)
    next_gate, events = await runner.handle_gate_decision(gate.id, GateDecision.APPROVE)
    assert next_gate is not None
    assert next_gate.id == "assign-approve"


@pytest.mark.asyncio
async def test_voice_dispatch_severity_gate_reject_path():
    """Test rejecting severity gate goes to queue-morning (terminal)."""
    session = MockSession()
    runner = SOPRunner(VOICE_DISPATCH_SOP, session)
    
    runner.start()
    gate, _ = await runner.advance_to(runner.current_step_id)
    assert gate.id == "severity-gate"
    
    # Reject severity gate (routine)
    next_gate, events = await runner.handle_gate_decision(gate.id, GateDecision.REJECT)
    assert next_gate is None  # Terminal branch
    assert runner.is_complete()


@pytest.mark.asyncio
async def test_voice_dispatch_assignment_approve_advances():
    """Test assignment approval gate advances to notify-shipper check."""
    session = MockSession()
    runner = SOPRunner(VOICE_DISPATCH_SOP, session)
    
    runner.start()
    await runner.advance_to(runner.current_step_id)
    await runner.handle_gate_decision("severity-gate", GateDecision.APPROVE)
    
    # Should be at assign-approve gate now
    assert runner.current_step_id == "assign-approve"
    
    # Approve assignment
    next_gate, events = await runner.handle_gate_decision("assign-approve", GateDecision.APPROVE)
    assert next_gate is not None
    assert next_gate.id == "notify-shipper"


@pytest.mark.asyncio
async def test_voice_dispatch_full_happy_path():
    """Test full Voice Dispatch SOP happy path."""
    session = MockSession()
    runner = SOPRunner(VOICE_DISPATCH_SOP, session)
    
    runner.start()
    
    # Advance to severity-gate
    gate, _ = await runner.advance_to(runner.current_step_id)
    assert gate.id == "severity-gate"
    
    # Approve severity (emergency)
    gate, _ = await runner.handle_gate_decision("severity-gate", GateDecision.APPROVE)
    assert gate.id == "assign-approve"
    
    # Approve assignment
    gate, _ = await runner.handle_gate_decision("assign-approve", GateDecision.APPROVE)
    assert gate.id == "notify-shipper"
    
    # Approve shipper notification
    gate, _ = await runner.handle_gate_decision("notify-shipper", GateDecision.APPROVE)
    assert gate is None  # SOP complete
    assert runner.is_complete()
    
    # Check all steps completed
    completed = runner.get_completed_steps()
    assert "call-ingest" in completed
    assert "transcribe" in completed
    assert "extract-fields" in completed
    assert "propose-tech" in completed
    assert "send-notification" in completed
    assert "create-wo" in completed
    assert "audit" in completed


@pytest.mark.asyncio
async def test_voice_dispatch_skip_notification_path():
    """Test path when shipper notification is skipped."""
    session = MockSession()
    runner = SOPRunner(VOICE_DISPATCH_SOP, session)
    
    runner.start()
    
    # Advance to severity-gate
    gate, _ = await runner.advance_to(runner.current_step_id)
    
    # Approve severity
    gate, _ = await runner.handle_gate_decision("severity-gate", GateDecision.APPROVE)
    
    # Approve assignment
    gate, _ = await runner.handle_gate_decision("assign-approve", GateDecision.APPROVE)
    assert gate.id == "notify-shipper"
    
    # Reject shipper notification (skip it)
    gate, _ = await runner.handle_gate_decision("notify-shipper", GateDecision.REJECT)
    assert gate is None  # Should complete after create-wo
    assert runner.is_complete()
    
    # Check that notification was NOT sent
    completed = runner.get_completed_steps()
    assert "send-notification" not in completed
    assert "create-wo" in completed
    assert "audit" in completed


@pytest.mark.asyncio
async def test_voice_dispatch_assignment_reject_path():
    """Test rejecting assignment goes to hold (terminal)."""
    session = MockSession()
    runner = SOPRunner(VOICE_DISPATCH_SOP, session)
    
    runner.start()
    gate, _ = await runner.advance_to(runner.current_step_id)
    
    # Approve severity
    gate, _ = await runner.handle_gate_decision("severity-gate", GateDecision.APPROVE)
    assert gate.id == "assign-approve"
    
    # Reject assignment
    gate, _ = await runner.handle_gate_decision("assign-approve", GateDecision.REJECT)
    assert gate is None  # Terminal branch
    assert runner.is_complete()
    
    completed = runner.get_completed_steps()
    assert "assignment-hold" in completed


@pytest.mark.asyncio
async def test_voice_dispatch_events_logged():
    """Test that log events are captured."""
    session = MockSession()
    runner = SOPRunner(VOICE_DISPATCH_SOP, session)
    
    runner.start()
    _, events = await runner.advance_to(runner.current_step_id)
    
    assert len(events) > 0
    assert any(e["type"] == "log" for e in events)
    assert any("Mike Rodriguez" in e["message"] or "Springfield" in e["message"] for e in events)
