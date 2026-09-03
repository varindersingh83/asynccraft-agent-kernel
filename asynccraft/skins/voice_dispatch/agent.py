"""Agent configuration and samples for Voice Dispatch workflow."""


def get_sample_calls() -> list[dict]:
    """Get sample inbound voice calls for demo."""
    return [
        {
            "call_id": "CALL-092326-1430",
            "caller_name": "Carrier: Pinnacle Transport",
            "caller_role": "Carrier Rep",
            "received_at": "2026-09-03T14:30:00Z",
            "duration_seconds": 142,
            "transcript": "Cold Chain Logistics broker desk, this is Pinnacle Transport. We can cover your ATL to Dallas reefer load #18402. MC 123456, FMCSA cleared, $2,600 for the lane. Can you send rate-con?",
            "route": "ATL→DAL",
            "load_id": "#18402",
            "carrier_name": "Pinnacle Transport",
            "mc_number": "MC-123456",
            "rate_quoted": 2600.0,
            "rate_ceiling": 2800.0,
            "fmcsa_status": "cleared",
            "equipment_type": "reefer",
        },
        {
            "call_id": "CALL-092326-1515",
            "caller_name": "Carrier: Atlas Freight",
            "caller_role": "Carrier Rep",
            "received_at": "2026-09-03T15:15:00Z",
            "duration_seconds": 98,
            "transcript": "This is Atlas Freight calling about Dallas lanes. Can cover ATL to DAL reefers, MC 789012. What's the rate for load #18402?",
            "route": "ATL→DAL",
            "load_id": "#18402",
            "carrier_name": "Atlas Freight",
            "mc_number": "MC-789012",
            "rate_quoted": 2750.0,
            "rate_ceiling": 2800.0,
            "fmcsa_status": "cleared",
            "equipment_type": "reefer",
        },
        {
            "call_id": "CALL-092326-1600",
            "caller_name": "Carrier: Speedy Logistics",
            "caller_role": "Carrier Rep",
            "received_at": "2026-09-03T16:00:00Z",
            "duration_seconds": 125,
            "transcript": "Hey, Speedy Logistics here. Heard you have a reefer ATL to Dallas. MC 345678, can do it for $2,900. We're ready to roll.",
            "route": "ATL→DAL",
            "load_id": "#18402",
            "carrier_name": "Speedy Logistics",
            "mc_number": "MC-345678",
            "rate_quoted": 2900.0,
            "rate_ceiling": 2800.0,
            "fmcsa_status": "pending",
            "equipment_type": "reefer",
        },
    ]


def get_agent_config() -> dict:
    """Get agent configuration for voice dispatch skin."""
    return {
        "name": "Voice Dispatch Agent",
        "description": "Automate voice-to-work-order pipeline with transcription, field extraction, and HITL approval gates",
        "model": "gpt-4",
        "temperature": 0.7,
        "max_tokens": 2000,
    }
