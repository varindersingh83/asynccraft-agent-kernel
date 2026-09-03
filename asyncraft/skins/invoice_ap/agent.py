"""Agent configuration and samples for Invoice/AP Exception workflow."""


def get_sample_invoices() -> list[dict]:
    """Get sample invoice exceptions for demo."""
    return [
        {
            "invoice_id": "INV-2026-0891",
            "vendor_name": "Acme Parts Supply",
            "vendor_id": "VEN-00234",
            "vendor_city": "Chicago",
            "vendor_state": "IL",
            "po_id": "PO-4523",
            "receipt_id": "GR-7821",
            "invoice_amount": 2572.50,
            "po_amount": 2450.00,
            "invoice_date": "2026-09-01",
            "due_date": "2026-10-01",
            "payment_terms": "Net 30",
            "discrepancy_type": "quantity_overage",
            "discrepancy_details": "Invoice qty 105 vs PO qty 100 (5 unit overage)",
        },
        {
            "invoice_id": "INV-2026-0892",
            "vendor_name": "Midwest Steel Distributors",
            "vendor_id": "VEN-00156",
            "vendor_city": "Detroit",
            "vendor_state": "MI",
            "po_id": "PO-4601",
            "receipt_id": "GR-7829",
            "invoice_amount": 18750.00,
            "po_amount": 19000.00,
            "invoice_date": "2026-09-02",
            "due_date": "2026-10-02",
            "payment_terms": "Net 30",
            "discrepancy_type": "price_variance",
            "discrepancy_details": "Unit price $18.75 vs PO $19.00 (favorable variance)",
        },
        {
            "invoice_id": "INV-2026-0893",
            "vendor_name": "Northern Equipment Leasing",
            "vendor_id": "VEN-00387",
            "vendor_city": "Toronto",
            "vendor_state": "ON",
            "po_id": "PO-4650",
            "receipt_id": "GR-7835",
            "invoice_amount": 5200.00,
            "po_amount": 5200.00,
            "invoice_date": "2026-09-03",
            "due_date": "2026-10-03",
            "payment_terms": "Net 30",
            "discrepancy_type": "none",
            "discrepancy_details": "Clean 3-way match (auto-post candidate)",
        },
    ]


def get_agent_config() -> dict:
    """Get agent configuration for Invoice/AP skin."""
    return {
        "name": "Invoice/AP Exception Agent",
        "description": "Automate invoice 3-way match, exception handling, and AP posting with approval gates",
        "model": "gpt-4",
        "temperature": 0.5,
        "max_tokens": 2000,
    }
