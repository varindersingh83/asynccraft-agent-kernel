"""Tools for CRM Follow-up workflow."""

from asynccraft.kernel.tools import Tool, ToolResult


class AssessLeadScoreTool(Tool):
    """Assess if a lead score meets the threshold for immediate follow-up."""
    
    name = "assess_lead_score"
    description = "Evaluate lead score and determine if it meets threshold for sales follow-up"
    
    async def execute(
        self,
        company_name: str,
        lead_score: int,
        fit_signals: list[str],
        threshold: int = 70,
        **kwargs
    ) -> ToolResult:
        """Execute lead score assessment."""
        meets_threshold = lead_score >= threshold
        return ToolResult(
            success=True,
            message=f"Lead score assessment: {company_name} scored {lead_score}/100 ({'meets' if meets_threshold else 'below'} threshold {threshold})",
            data={
                "company_name": company_name,
                "lead_score": lead_score,
                "threshold": threshold,
                "meets_threshold": meets_threshold,
                "fit_signals": fit_signals,
            }
        )


class ApproveEmailDraftTool(Tool):
    """Approve or reject a draft follow-up email before sending."""
    
    name = "approve_email_draft"
    description = "Review and approve draft follow-up email to a lead"
    
    async def execute(
        self,
        to_email: str,
        subject: str,
        preview: str,
        company: str,
        **kwargs
    ) -> ToolResult:
        """Execute email draft approval."""
        return ToolResult(
            success=True,
            message=f"Email draft ready for {company}: '{subject}' → {to_email}",
            data={
                "to_email": to_email,
                "subject": subject,
                "preview": preview,
                "company": company,
                "draft_id": f"draft_{company.lower().replace(' ', '_')}_{hash(to_email) % 10000}",
            }
        )


class CheckManagerReviewNeededTool(Tool):
    """Check if a deal requires manager review before proceeding."""
    
    name = "check_manager_review_needed"
    description = "Determine if deal size or rep experience requires manager approval"
    
    async def execute(
        self,
        deal_size_estimate: int,
        rep_experience_days: int,
        company_tier: str,
        threshold: int = 50000,
        **kwargs
    ) -> ToolResult:
        """Execute manager review check."""
        needs_review = deal_size_estimate >= threshold or rep_experience_days < 60
        return ToolResult(
            success=True,
            message=f"Manager review {'required' if needs_review else 'not required'} (deal size: ${deal_size_estimate:,}, threshold: ${threshold:,})",
            data={
                "deal_size_estimate": deal_size_estimate,
                "threshold": threshold,
                "needs_review": needs_review,
                "rep_experience_days": rep_experience_days,
                "company_tier": company_tier,
            }
        )


class UpdateCRMStageTool(Tool):
    """Update CRM record with new stage and owner."""
    
    name = "update_crm_stage"
    description = "Update CRM stage and ownership after follow-up"
    
    async def execute(
        self,
        company_name: str,
        new_stage: str,
        owner: str,
        **kwargs
    ) -> ToolResult:
        """Execute CRM stage update."""
        return ToolResult(
            success=True,
            message=f"CRM updated: {company_name} → {new_stage} (Owner: {owner})",
            data={
                "company_name": company_name,
                "new_stage": new_stage,
                "owner": owner,
                "updated_at": "2026-09-03T11:42:00Z",
            }
        )
