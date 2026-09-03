"""Tools for CRM Follow-up workflow."""

from typing import Any
from asynccraft.kernel.tools import Tool, ToolResult


class AssessLeadScoreTool(Tool):
    """Assess if a lead score meets the threshold for immediate follow-up."""
    
    @property
    def name(self) -> str:
        return "assess_lead_score"
    
    @property
    def description(self) -> str:
        return "Evaluate lead score and determine if it meets threshold for sales follow-up"
    
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute lead score assessment."""
        company_name = kwargs.get("company_name", "unknown")
        lead_score = kwargs.get("lead_score", 0)
        fit_signals = kwargs.get("fit_signals", [])
        threshold = kwargs.get("threshold", 70)
        
        meets_threshold = lead_score >= threshold
        return ToolResult(
            success=True,
            data={
                "company_name": company_name,
                "lead_score": lead_score,
                "threshold": threshold,
                "meets_threshold": meets_threshold,
                "fit_signals": fit_signals,
            }
        )
    
    def preview(self, **kwargs: Any) -> str:
        company_name = kwargs.get("company_name", "unknown")
        lead_score = kwargs.get("lead_score", 0)
        threshold = kwargs.get("threshold", 70)
        status = "meets" if lead_score >= threshold else "below"
        return f"Lead score assessment: {company_name} scored {lead_score}/100 ({status} threshold {threshold})"


class ApproveEmailDraftTool(Tool):
    """Approve or reject a draft follow-up email before sending."""
    
    @property
    def name(self) -> str:
        return "approve_email_draft"
    
    @property
    def description(self) -> str:
        return "Review and approve draft follow-up email to a lead"
    
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute email draft approval."""
        to_email = kwargs.get("to_email", "")
        subject = kwargs.get("subject", "")
        preview_text = kwargs.get("preview", "")
        company = kwargs.get("company", "")
        
        return ToolResult(
            success=True,
            data={
                "to_email": to_email,
                "subject": subject,
                "preview": preview_text,
                "company": company,
                "draft_id": f"draft_{company.lower().replace(' ', '_')}_{hash(to_email) % 10000}",
            }
        )
    
    def preview(self, **kwargs: Any) -> str:
        company = kwargs.get("company", "")
        subject = kwargs.get("subject", "")
        to_email = kwargs.get("to_email", "")
        return f"Email draft ready for {company}: '{subject}' → {to_email}"


class CheckManagerReviewNeededTool(Tool):
    """Check if a deal requires manager review before proceeding."""
    
    @property
    def name(self) -> str:
        return "check_manager_review_needed"
    
    @property
    def description(self) -> str:
        return "Determine if deal size or rep experience requires manager approval"
    
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute manager review check."""
        deal_size_estimate = kwargs.get("deal_size_estimate", 0)
        rep_experience_days = kwargs.get("rep_experience_days", 0)
        company_tier = kwargs.get("company_tier", "unknown")
        threshold = kwargs.get("threshold", 50000)
        
        needs_review = deal_size_estimate >= threshold or rep_experience_days < 60
        return ToolResult(
            success=True,
            data={
                "deal_size_estimate": deal_size_estimate,
                "threshold": threshold,
                "needs_review": needs_review,
                "rep_experience_days": rep_experience_days,
                "company_tier": company_tier,
            }
        )
    
    def preview(self, **kwargs: Any) -> str:
        deal_size_estimate = kwargs.get("deal_size_estimate", 0)
        threshold = kwargs.get("threshold", 50000)
        status = "required" if deal_size_estimate >= threshold else "not required"
        return f"Manager review {status} (deal size: ${deal_size_estimate:,}, threshold: ${threshold:,})"


class UpdateCRMStageTool(Tool):
    """Update CRM record with new stage and owner."""
    
    @property
    def name(self) -> str:
        return "update_crm_stage"
    
    @property
    def description(self) -> str:
        return "Update CRM stage and ownership after follow-up"
    
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute CRM stage update."""
        company_name = kwargs.get("company_name", "")
        new_stage = kwargs.get("new_stage", "")
        owner = kwargs.get("owner", "")
        
        return ToolResult(
            success=True,
            data={
                "company_name": company_name,
                "new_stage": new_stage,
                "owner": owner,
                "updated_at": "2026-09-03T11:42:00Z",
            }
        )
    
    def preview(self, **kwargs: Any) -> str:
        company_name = kwargs.get("company_name", "")
        new_stage = kwargs.get("new_stage", "")
        owner = kwargs.get("owner", "")
        return f"CRM updated: {company_name} → {new_stage} (Owner: {owner})"
