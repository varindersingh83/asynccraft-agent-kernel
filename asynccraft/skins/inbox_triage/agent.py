"""Agent configuration and samples for Inbox Triage workflow."""


def get_sample_tickets() -> list[dict]:
    """Get sample inbound tickets for demo."""
    return [
        {
            "subject": "Detention charges - Load L-55212",
            "sender": "billing@prairiefoods.com",
            "sender_name": "Prairie Foods (Des Moines)",
            "received_at": "2026-09-03T09:15:00Z",
            "body_preview": "We're claiming 4 hours detention at Dallas consignee for Load L-55212 (Chicago→Dallas). Driver arrived on time but dock was full. Please advise on concession.",
            "load_id": "L-55212",
            "route": "Chicago→Dallas",
            "category": "billing-exception",
            "severity": "high",
            "dollar_amount": 380.0,
            "sla_risk": False,
            "billing_contact": "Jane Ortiz",
        },
        {
            "subject": "Where is my shipment? Load L-54893",
            "sender": "customer@midwestdist.com",
            "sender_name": "Midwest Distribution",
            "received_at": "2026-09-03T10:15:00Z",
            "body_preview": "Can you provide ETA for Load L-54893? Expected yesterday but no update.",
            "load_id": "L-54893",
            "route": "Dallas→Chicago",
            "category": "wismo",
            "severity": "routine",
            "dollar_amount": 0.0,
            "sla_risk": False,
        },
        {
            "subject": "Accessorial dispute - Load L-55100",
            "sender": "ap@texasfoods.com",
            "sender_name": "Texas Foods Corp",
            "received_at": "2026-09-03T11:00:00Z",
            "body_preview": "Invoice shows $275 liftgate fee not in original rate confirmation. Load L-55100 (Des Moines→Dallas). Please review.",
            "load_id": "L-55100",
            "route": "Des Moines→Dallas",
            "category": "billing-exception",
            "severity": "routine",
            "dollar_amount": 275.0,
            "sla_risk": False,
            "billing_contact": "Jane Ortiz",
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
