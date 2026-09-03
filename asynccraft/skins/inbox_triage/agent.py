"""Agent configuration and samples for Inbox Triage workflow."""


def get_sample_tickets() -> list[dict]:
    """Get sample inbound tickets for demo."""
    return [
        {
            "subject": "Delay - Chicago to Detroit LTL shipment",
            "sender": "dispatch@midwestfreight.com",
            "sender_name": "Midwest Freight Dispatch",
            "received_at": "2026-09-03T09:15:00Z",
            "body_preview": "Our driver reports 4-hour delay at consignee due to closed dock. Detention charges expected. Load CHI-DET-092426.",
            "load_id": "CHI-DET-092426",
            "category": "delay",
            "severity": "high",
            "dollar_amount": 450.0,
            "sla_risk": True,
        },
        {
            "subject": "Accessorial charge dispute - Dallas dock fee",
            "sender": "billing@texasshippers.com",
            "sender_name": "Texas Shippers Inc",
            "received_at": "2026-09-03T10:30:00Z",
            "body_preview": "We received an invoice with $275 dock fee that was not in the original quote. Please review Load DAL-CHI-092326.",
            "load_id": "DAL-CHI-092326",
            "category": "accessorial",
            "severity": "routine",
            "dollar_amount": 275.0,
            "sla_risk": False,
        },
        {
            "subject": "Claim - Damaged freight Toronto inbound",
            "sender": "ops@torontowarehouse.ca",
            "sender_name": "Toronto Warehouse Operations",
            "received_at": "2026-09-03T11:00:00Z",
            "body_preview": "Received 8 pallets with visible damage (water exposure). Photos attached. Load TOR-CHI-092226. Claim estimated $2,100.",
            "load_id": "TOR-CHI-092226",
            "category": "claim",
            "severity": "critical",
            "dollar_amount": 2100.0,
            "sla_risk": True,
        },
    ]


def get_agent_config() -> dict:
    """Get agent configuration for inbox triage skin."""
    return {
        "name": "Inbox Triage Agent",
        "description": "Automate ops inbox exception handling with classification, reply drafting, and HITL approval gates",
        "model": "gpt-4",
        "temperature": 0.7,
        "max_tokens": 2000,
    }
