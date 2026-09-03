"""Tools for Inbox Triage workflow."""

from typing import Any
from asynccraft.kernel.tools import Tool, ToolResult


class ClassifyTicketTool(Tool):
    """Classify incoming ticket type (billing-exception vs WISMO auto-reply)."""
    
    @property
    def name(self) -> str:
        return "classify_ticket"
    
    @property
    def description(self) -> str:
        return "Classify inbound ticket: billing-exception (detention/accessorial) or WISMO (auto-reply)"
    
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute ticket classification."""
        subject = kwargs.get("subject", "")
        body_preview = kwargs.get("body_preview", "")
        sender = kwargs.get("sender", "")
        category = kwargs.get("category", "billing-exception")
        
        return ToolResult(
            success=True,
            data={
                "subject": subject,
                "category": category,
                "sender": sender,
                "body_preview": body_preview,
                "confidence": 0.94,
            }
        )
    
    def preview(self, **kwargs: Any) -> str:
        subject = kwargs.get("subject", "")
        category = kwargs.get("category", "billing-exception")
        return f"Classify: '{subject}' → {category.upper()} (94% confidence)"


class AssessSeverityTool(Tool):
    """Assess if ticket requires immediate attention vs routine handling."""
    
    @property
    def name(self) -> str:
        return "assess_severity"
    
    @property
    def description(self) -> str:
        return "Determine if ticket is high/critical severity requiring immediate response"
    
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute severity assessment."""
        category = kwargs.get("category", "")
        dollar_amount = kwargs.get("dollar_amount", 0)
        sla_risk = kwargs.get("sla_risk", False)
        severity = kwargs.get("severity", "routine")
        
        is_urgent = severity in ["high", "critical"]
        return ToolResult(
            success=True,
            data={
                "category": category,
                "severity": severity,
                "is_urgent": is_urgent,
                "dollar_amount": dollar_amount,
                "sla_risk": sla_risk,
            }
        )
    
    def preview(self, **kwargs: Any) -> str:
        severity = kwargs.get("severity", "routine")
        dollar_amount = kwargs.get("dollar_amount", 0)
        status = "URGENT" if severity in ["high", "critical"] else "routine"
        return f"Severity assessment: {status} (${dollar_amount:,.2f}, {severity} priority)"


class ApproveReplyTool(Tool):
    """Jane Ortiz (Billing) HITL gate before any concession/reply."""
    
    @property
    def name(self) -> str:
        return "approve_reply"
    
    @property
    def description(self) -> str:
        return "Jane Ortiz (Billing) liability gate: approve concession before customer reply"
    
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute reply approval by Jane Ortiz."""
        to_email = kwargs.get("to_email", "")
        subject = kwargs.get("subject", "")
        draft_preview = kwargs.get("draft_preview", "")
        concession_amount = kwargs.get("concession_amount", 0.0)
        
        return ToolResult(
            success=True,
            data={
                "to_email": to_email,
                "subject": subject,
                "draft_preview": draft_preview,
                "concession_amount": concession_amount,
                "approver": "Jane Ortiz (Billing)",
                "draft_id": f"draft_L{hash(to_email) % 10000}",
            }
        )
    
    def preview(self, **kwargs: Any) -> str:
        concession_amount = kwargs.get("concession_amount", 0.0)
        to_email = kwargs.get("to_email", "")
        return f"Jane Ortiz (Billing) gate: ${concession_amount:.0f} concession → {to_email}"


class CheckEscalateNeededTool(Tool):
    """Check if situation requires manager escalation."""
    
    @property
    def name(self) -> str:
        return "check_escalate_needed"
    
    @property
    def description(self) -> str:
        return "Determine if issue requires manager escalation due to $ amount or SLA risk"
    
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute escalation check."""
        dollar_amount = kwargs.get("dollar_amount", 0)
        sla_risk = kwargs.get("sla_risk", False)
        threshold = kwargs.get("threshold", 1000)
        severity = kwargs.get("severity", "routine")
        
        needs_escalate = dollar_amount >= threshold or sla_risk or severity == "critical"
        return ToolResult(
            success=True,
            data={
                "dollar_amount": dollar_amount,
                "threshold": threshold,
                "needs_escalate": needs_escalate,
                "sla_risk": sla_risk,
                "severity": severity,
            }
        )
    
    def preview(self, **kwargs: Any) -> str:
        dollar_amount = kwargs.get("dollar_amount", 0)
        sla_risk = kwargs.get("sla_risk", False)
        threshold = kwargs.get("threshold", 1000)
        status = "required" if dollar_amount >= threshold or sla_risk else "not required"
        return f"Manager escalation {status} (${dollar_amount:,.2f}, SLA risk: {sla_risk})"


class PostTMSExceptionTool(Tool):
    """Post exception to TMS system for tracking."""
    
    @property
    def name(self) -> str:
        return "post_tms_exception"
    
    @property
    def description(self) -> str:
        return "Create TMS exception record with ticket details and resolution"
    
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute TMS exception posting."""
        load_id = kwargs.get("load_id", "")
        category = kwargs.get("category", "")
        resolution = kwargs.get("resolution", "")
        
        return ToolResult(
            success=True,
            data={
                "load_id": load_id,
                "category": category,
                "resolution": resolution,
                "exception_id": f"EXC-{hash(load_id) % 100000}",
                "posted_at": "2026-09-03T13:45:00Z",
            }
        )
    
    def preview(self, **kwargs: Any) -> str:
        load_id = kwargs.get("load_id", "")
        category = kwargs.get("category", "")
        resolution = kwargs.get("resolution", "")
        return f"TMS exception: Load {load_id} → {category.upper()} ({resolution})"
