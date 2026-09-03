"""Tools for Invoice/AP Exception workflow."""

from typing import Any
from asynccraft.kernel.tools import Tool, ToolResult


class AssessThreeWayMatchTool(Tool):
    """Assess 3-way match between PO, Invoice, and Receipt."""
    
    @property
    def name(self) -> str:
        return "assess_three_way_match"
    
    @property
    def description(self) -> str:
        return "Perform 3-way match validation for AP processing"
    
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute 3-way match assessment."""
        invoice_id = kwargs.get("invoice_id", "unknown")
        po_id = kwargs.get("po_id", "unknown")
        receipt_id = kwargs.get("receipt_id", "unknown")
        discrepancies = kwargs.get("discrepancies", [])
        
        has_discrepancies = len(discrepancies) > 0
        return ToolResult(
            success=True,
            data={
                "invoice_id": invoice_id,
                "po_id": po_id,
                "receipt_id": receipt_id,
                "match_passed": not has_discrepancies,
                "discrepancies": discrepancies,
            }
        )
    
    def preview(self, **kwargs: Any) -> str:
        has_discrepancies = len(kwargs.get("discrepancies", [])) > 0
        status = "FAIL - Discrepancies found" if has_discrepancies else "PASS - Clean match"
        return f"3-way match: {status}"


class ApproveAPCorrectionTool(Tool):
    """Approve or reject a proposed AP correction."""
    
    @property
    def name(self) -> str:
        return "approve_ap_correction"
    
    @property
    def description(self) -> str:
        return "Review and approve invoice correction before posting to AP"
    
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute AP correction approval."""
        invoice_id = kwargs.get("invoice_id", "unknown")
        correction_type = kwargs.get("correction_type", "")
        original_amount = kwargs.get("original_amount", 0.0)
        corrected_amount = kwargs.get("corrected_amount", 0.0)
        delta = kwargs.get("delta", 0.0)
        reason = kwargs.get("reason", "")
        
        return ToolResult(
            success=True,
            data={
                "invoice_id": invoice_id,
                "correction_type": correction_type,
                "original_amount": original_amount,
                "corrected_amount": corrected_amount,
                "delta": delta,
                "reason": reason,
            }
        )
    
    def preview(self, **kwargs: Any) -> str:
        invoice_id = kwargs.get("invoice_id", "unknown")
        correction_type = kwargs.get("correction_type", "")
        delta = kwargs.get("delta", 0.0)
        return f"AP correction for {invoice_id}: {correction_type} adjustment ${abs(delta):.2f}"


class CheckVendorComplianceTool(Tool):
    """Check vendor compliance status before posting invoice."""
    
    @property
    def name(self) -> str:
        return "check_vendor_compliance"
    
    @property
    def description(self) -> str:
        return "Verify vendor payment terms, credit status, and compliance"
    
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute vendor compliance check."""
        vendor_id = kwargs.get("vendor_id", "unknown")
        vendor_name = kwargs.get("vendor_name", "")
        checks = kwargs.get("checks", [])
        invoice_amount = kwargs.get("invoice_amount", 0.0)
        
        all_clear = True  # Mock: assume all checks pass
        return ToolResult(
            success=True,
            data={
                "vendor_id": vendor_id,
                "vendor_name": vendor_name,
                "checks_performed": checks,
                "invoice_amount": invoice_amount,
                "compliance_passed": all_clear,
            }
        )
    
    def preview(self, **kwargs: Any) -> str:
        vendor_name = kwargs.get("vendor_name", "")
        vendor_id = kwargs.get("vendor_id", "unknown")
        all_clear = True
        status = "All checks passed" if all_clear else "Issues found"
        return f"Vendor compliance: {vendor_name} ({vendor_id}) - {status}"


class PostToAPTool(Tool):
    """Post invoice to Accounts Payable ledger."""
    
    @property
    def name(self) -> str:
        return "post_to_ap"
    
    @property
    def description(self) -> str:
        return "Post approved invoice to AP system"
    
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute AP posting."""
        invoice_id = kwargs.get("invoice_id", "unknown")
        amount = kwargs.get("amount", 0.0)
        vendor_name = kwargs.get("vendor_name", "")
        due_date = kwargs.get("due_date", "")
        
        return ToolResult(
            success=True,
            data={
                "invoice_id": invoice_id,
                "amount": amount,
                "vendor_name": vendor_name,
                "due_date": due_date,
                "posted_at": "2026-09-03T11:45:00Z",
            }
        )
    
    def preview(self, **kwargs: Any) -> str:
        invoice_id = kwargs.get("invoice_id", "unknown")
        amount = kwargs.get("amount", 0.0)
        due_date = kwargs.get("due_date", "")
        return f"AP entry created: {invoice_id} for ${amount:.2f} due {due_date}"
