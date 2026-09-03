"""Tools for Invoice/AP Exception workflow."""

from asynccraft.kernel.tools import Tool, ToolResult


class AssessThreeWayMatchTool(Tool):
    """Assess 3-way match between PO, Invoice, and Receipt."""
    
    name = "assess_three_way_match"
    description = "Perform 3-way match validation for AP processing"
    
    async def execute(
        self,
        invoice_id: str,
        po_id: str,
        receipt_id: str,
        discrepancies: list[dict],
        **kwargs
    ) -> ToolResult:
        """Execute 3-way match assessment."""
        has_discrepancies = len(discrepancies) > 0
        return ToolResult(
            success=True,
            message=f"3-way match: {'FAIL - Discrepancies found' if has_discrepancies else 'PASS - Clean match'}",
            data={
                "invoice_id": invoice_id,
                "po_id": po_id,
                "receipt_id": receipt_id,
                "match_passed": not has_discrepancies,
                "discrepancies": discrepancies,
            }
        )


class ApproveAPCorrectionTool(Tool):
    """Approve or reject a proposed AP correction."""
    
    name = "approve_ap_correction"
    description = "Review and approve invoice correction before posting to AP"
    
    async def execute(
        self,
        invoice_id: str,
        correction_type: str,
        original_amount: float,
        corrected_amount: float,
        delta: float,
        reason: str,
        **kwargs
    ) -> ToolResult:
        """Execute AP correction approval."""
        return ToolResult(
            success=True,
            message=f"AP correction for {invoice_id}: {correction_type} adjustment ${abs(delta):.2f}",
            data={
                "invoice_id": invoice_id,
                "correction_type": correction_type,
                "original_amount": original_amount,
                "corrected_amount": corrected_amount,
                "delta": delta,
                "reason": reason,
            }
        )


class CheckVendorComplianceTool(Tool):
    """Check vendor compliance status before posting invoice."""
    
    name = "check_vendor_compliance"
    description = "Verify vendor payment terms, credit status, and compliance"
    
    async def execute(
        self,
        vendor_id: str,
        vendor_name: str,
        checks: list[str],
        invoice_amount: float,
        **kwargs
    ) -> ToolResult:
        """Execute vendor compliance check."""
        all_clear = True  # Mock: assume all checks pass
        return ToolResult(
            success=True,
            message=f"Vendor compliance: {vendor_name} ({vendor_id}) - {'All checks passed' if all_clear else 'Issues found'}",
            data={
                "vendor_id": vendor_id,
                "vendor_name": vendor_name,
                "checks_performed": checks,
                "invoice_amount": invoice_amount,
                "compliance_passed": all_clear,
            }
        )


class PostToAPTool(Tool):
    """Post invoice to Accounts Payable ledger."""
    
    name = "post_to_ap"
    description = "Post approved invoice to AP system"
    
    async def execute(
        self,
        invoice_id: str,
        amount: float,
        vendor_name: str,
        due_date: str,
        **kwargs
    ) -> ToolResult:
        """Execute AP posting."""
        return ToolResult(
            success=True,
            message=f"AP entry created: {invoice_id} for ${amount:.2f} due {due_date}",
            data={
                "invoice_id": invoice_id,
                "amount": amount,
                "vendor_name": vendor_name,
                "due_date": due_date,
                "posted_at": "2026-09-03T11:45:00Z",
            }
        )
