"""Agent configuration and samples for CRM Follow-up workflow."""


def get_sample_leads() -> list[dict]:
    """Get sample inbound leads for demo."""
    return [
        {
            "company_name": "TechFlow Logistics",
            "contact_name": "Sam Johnson",
            "contact_email": "sam.johnson@techflow-logistics.com",
            "city": "Chicago",
            "state": "IL",
            "country": "USA",
            "industry": "Supply Chain & Logistics",
            "employees": 120,
            "annual_revenue": 15000000,
            "source": "Website form submission",
            "initial_interest": "Route optimization for Chicago-Dallas lanes",
            "lead_score": 78,
        },
        {
            "company_name": "Midwest Distribution Partners",
            "contact_name": "Lisa Chen",
            "contact_email": "lchen@midwestdist.com",
            "city": "Detroit",
            "state": "MI",
            "country": "USA",
            "industry": "Wholesale Distribution",
            "employees": 85,
            "annual_revenue": 9500000,
            "source": "Referral",
            "initial_interest": "Multi-warehouse inventory management",
            "lead_score": 82,
        },
        {
            "company_name": "Northern Freight Solutions",
            "contact_name": "Mark Davis",
            "contact_email": "mdavis@northernfreight.ca",
            "city": "Toronto",
            "state": "ON",
            "country": "Canada",
            "industry": "Freight & Logistics",
            "employees": 200,
            "annual_revenue": 28000000,
            "source": "Trade show (Toronto Logistics Summit)",
            "initial_interest": "Cross-border compliance automation (US-Canada)",
            "lead_score": 91,
        },
    ]


def get_agent_config() -> dict:
    """Get agent configuration for CRM follow-up skin."""
    return {
        "name": "CRM Follow-up Agent",
        "description": "Automate inbound lead follow-up with enrichment, scoring, and email approval gates",
        "model": "gpt-4",
        "temperature": 0.7,
        "max_tokens": 2000,
    }
