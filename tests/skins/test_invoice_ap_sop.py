"""Tests for Invoice/AP SOP runner."""

import pytest
from asyncraft.skins.invoice_ap.sop_runner import (
    SOPRunner,
    INVOICE_AP_SOP,
    GateDecision,
    StepType,
)


class MockSession:
    """Mock async session for testing."""
    pass


@pytest.mark.asyncio
async def test_invoice_ap_sop_starts_at_ingest():
    """Test Invoice/AP SOP starts at ingest step."""
    session = MockSession()
    runner = SOPRunner(INVOICE_AP_SOP, session)
    
    first_step = runner.start()
    assert first_step.id == "ingest"
    assert runner.current_step_id == "ingest"


@pytest.mark.asyncio
async def test_invoice_ap_advances_to_match_gate():
    """Test SOP auto-advances to first gate (match-result)."""
    session = MockSession()
    runner = SOPRunner(INVOICE_AP_SOP, session)
    
    runner.start()
    gate, events = await runner.advance_to(runner.current_step_id)
    
    assert gate is not None
    assert gate.id == "match-result"
    assert gate.step_type == StepType.GATE
    assert len(events) == 3  # ingest, three-way-match, match-result


@pytest.mark.asyncio
async def test_invoice_ap_match_pass_auto_posts():
    """Test clean 3-way match auto-posts to AP."""
    session = MockSession()
    runner = SOPRunner(INVOICE_AP_SOP, session)
    
    runner.start()
    gate, _ = await runner.advance_to(runner.current_step_id)
    assert gate.id == "match-result"
    
    # Approve (clean match)
    next_gate, events = await runner.handle_gate_decision(gate.id, GateDecision.APPROVE)
    assert next_gate is None  # Auto-post path completes
    assert runner.is_complete()


@pytest.mark.asyncio
async def test_invoice_ap_match_fail_proposes_correction():
    """Test 3-way match failure proposes correction."""
    session = MockSession()
    runner = SOPRunner(INVOICE_AP_SOP, session)
    
    runner.start()
    gate, _ = await runner.advance_to(runner.current_step_id)
    assert gate.id == "match-result"
    
    # Reject (mismatch found)
    next_gate, events = await runner.handle_gate_decision(gate.id, GateDecision.REJECT)
    assert next_gate is not None
    assert next_gate.id == "correction-approve"


@pytest.mark.asyncio
async def test_invoice_ap_correction_approval_advances_to_vendor_check():
    """Test correction approval advances to vendor compliance check."""
    session = MockSession()
    runner = SOPRunner(INVOICE_AP_SOP, session)
    
    runner.start()
    await runner.advance_to(runner.current_step_id)
    await runner.handle_gate_decision("match-result", GateDecision.REJECT)
    
    # Should be at correction-approve gate
    assert runner.current_step_id == "correction-approve"
    
    # Approve correction
    next_gate, events = await runner.handle_gate_decision("correction-approve", GateDecision.APPROVE)
    assert next_gate is not None
    assert next_gate.id == "vendor-check"


@pytest.mark.asyncio
async def test_invoice_ap_correction_reject_holds():
    """Test correction rejection puts invoice on hold."""
    session = MockSession()
    runner = SOPRunner(INVOICE_AP_SOP, session)
    
    runner.start()
    await runner.advance_to(runner.current_step_id)
    await runner.handle_gate_decision("match-result", GateDecision.REJECT)
    
    # Reject correction
    next_gate, events = await runner.handle_gate_decision("correction-approve", GateDecision.REJECT)
    assert next_gate is None  # Terminal hold
    assert runner.is_complete()


@pytest.mark.asyncio
async def test_invoice_ap_full_exception_path():
    """Test full Invoice/AP exception handling path."""
    session = MockSession()
    runner = SOPRunner(INVOICE_AP_SOP, session)
    
    runner.start()
    
    # Advance to match gate
    gate, _ = await runner.advance_to(runner.current_step_id)
    assert gate.id == "match-result"
    
    # Reject match (mismatch found)
    gate, _ = await runner.handle_gate_decision("match-result", GateDecision.REJECT)
    assert gate.id == "correction-approve"
    
    # Approve correction
    gate, _ = await runner.handle_gate_decision("correction-approve", GateDecision.APPROVE)
    assert gate.id == "vendor-check"
    
    # Approve vendor compliance
    gate, _ = await runner.handle_gate_decision("vendor-check", GateDecision.APPROVE)
    assert gate is None  # SOP complete
    assert runner.is_complete()
    
    # Check all steps completed
    completed = runner.get_completed_steps()
    assert "ingest" in completed
    assert "three-way-match" in completed
    assert "propose-correction" in completed
    assert "post-to-ap" in completed
    assert "gl-writeback" in completed
    assert "audit" in completed


@pytest.mark.asyncio
async def test_invoice_ap_events_include_billing():
    """Test that billing events are captured."""
    session = MockSession()
    runner = SOPRunner(INVOICE_AP_SOP, session)
    
    runner.start()
    
    # Go through exception path to completion
    await runner.advance_to(runner.current_step_id)
    await runner.handle_gate_decision("match-result", GateDecision.REJECT)
    await runner.handle_gate_decision("correction-approve", GateDecision.APPROVE)
    _, final_events = await runner.handle_gate_decision("vendor-check", GateDecision.APPROVE)
    
    # Check for billing events
    all_events = runner.events + final_events
    billing_events = [e for e in all_events if e.get("type") == "billing"]
    assert len(billing_events) > 0
