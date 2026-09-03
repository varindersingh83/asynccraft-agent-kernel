"""Tools for deal flow triage."""

from typing import Any
from asynccraft.kernel.tools import Tool, ToolResult


class CreateCRMDealTool(Tool):
    """Create deal record in CRM."""

    @property
    def name(self) -> str:
        return "create_crm_deal"

    @property
    def description(self) -> str:
        return "Create new deal record in CRM system"

    async def execute(self, **kwargs: Any) -> ToolResult:
        company_name = kwargs.get("company_name", "")
        stage = kwargs.get("stage", "prospect")
        score = kwargs.get("score", 0)

        return ToolResult(
            success=True,
            data={
                "deal_id": f"deal_{hash(company_name) % 10000:04d}",
                "company_name": company_name,
                "stage": stage,
                "score": score,
                "owner": "auto_assigned",
                "mock": True,
            },
        )

    def preview(self, **kwargs: Any) -> str:
        company_name = kwargs.get("company_name", "")
        stage = kwargs.get("stage", "prospect")
        score = kwargs.get("score", 0)
        return f"Create CRM deal for {company_name} (stage: {stage}, score: {score})"


class SendPartnerNotificationTool(Tool):
    """Notify partner about high-value deal."""

    @property
    def name(self) -> str:
        return "send_partner_notification"

    @property
    def description(self) -> str:
        return "Send notification to partner about promising deal"

    async def execute(self, **kwargs: Any) -> ToolResult:
        partner_email = kwargs.get("partner_email", "")
        company_name = kwargs.get("company_name", "")
        summary = kwargs.get("summary", "")

        return ToolResult(
            success=True,
            data={
                "notification_id": f"notif_{hash(partner_email + company_name) % 10000:04d}",
                "partner_email": partner_email,
                "company_name": company_name,
                "summary": summary,
                "channel": "email+slack",
                "mock": True,
            },
        )

    def preview(self, **kwargs: Any) -> str:
        partner_email = kwargs.get("partner_email", "")
        company_name = kwargs.get("company_name", "")
        return f"Notify {partner_email} about {company_name} deal opportunity"


class SchedulePartnerCallTool(Tool):
    """Schedule intro call with partner."""

    @property
    def name(self) -> str:
        return "schedule_partner_call"

    @property
    def description(self) -> str:
        return "Schedule introduction call between partner and founder"

    async def execute(self, **kwargs: Any) -> ToolResult:
        company_name = kwargs.get("company_name", "")
        partner_email = kwargs.get("partner_email", "")
        proposed_time = kwargs.get("proposed_time", "")

        return ToolResult(
            success=True,
            data={
                "meeting_id": f"meet_{hash(company_name + partner_email) % 10000:04d}",
                "company_name": company_name,
                "partner_email": partner_email,
                "proposed_time": proposed_time,
                "calendar_invite_sent": True,
                "mock": True,
            },
        )

    def preview(self, **kwargs: Any) -> str:
        company_name = kwargs.get("company_name", "")
        partner_email = kwargs.get("partner_email", "")
        proposed_time = kwargs.get("proposed_time", "")
        return f"Schedule call: {partner_email} <> {company_name} at {proposed_time}"


class UpdateDealStageTool(Tool):
    """Update deal stage in pipeline."""

    @property
    def name(self) -> str:
        return "update_deal_stage"

    @property
    def description(self) -> str:
        return "Move deal to new stage in pipeline"

    async def execute(self, **kwargs: Any) -> ToolResult:
        deal_id = kwargs.get("deal_id", "")
        new_stage = kwargs.get("new_stage", "")
        reason = kwargs.get("reason", "")

        return ToolResult(
            success=True,
            data={
                "deal_id": deal_id,
                "new_stage": new_stage,
                "reason": reason,
                "automation_triggered": True,
                "mock": True,
            },
        )

    def preview(self, **kwargs: Any) -> str:
        deal_id = kwargs.get("deal_id", "")
        new_stage = kwargs.get("new_stage", "")
        reason = kwargs.get("reason", "")
        return f"Move deal {deal_id} to {new_stage} (reason: {reason})"


class AddDealNoteTool(Tool):
    """Add research note to deal."""

    @property
    def name(self) -> str:
        return "add_deal_note"

    @property
    def description(self) -> str:
        return "Add research or analysis note to deal record"

    @property
    def requires_approval(self) -> bool:
        return False

    async def execute(self, **kwargs: Any) -> ToolResult:
        deal_id = kwargs.get("deal_id", "")
        note = kwargs.get("note", "")

        return ToolResult(
            success=True,
            data={
                "deal_id": deal_id,
                "note_id": f"note_{hash(note) % 10000:04d}",
                "note": note,
                "mock": True,
            },
        )

    def preview(self, **kwargs: Any) -> str:
        deal_id = kwargs.get("deal_id", "")
        note = kwargs.get("note", "")[:50]
        return f"Add note to deal {deal_id}: '{note}...'"
