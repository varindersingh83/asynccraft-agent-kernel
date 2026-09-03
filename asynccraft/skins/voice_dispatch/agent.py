"""Agent configuration and samples for Voice Dispatch workflow."""


def get_sample_calls() -> list[dict]:
    """Get sample inbound voice calls for demo."""
    return [
        {
            "call_id": "CALL-092326-2210",
            "caller_name": "Mike Rodriguez",
            "caller_role": "Driver",
            "received_at": "2026-09-03T22:10:00Z",
            "duration_seconds": 145,
            "transcript": "Hey dispatch, this is Mike on truck 2847. I'm about 30 miles south of Springfield on I-55. Reefer unit is showing alarm - temp climbing. Carrying perishable freight to Chicago. Need help ASAP.",
            "location": "I-55 S, 30mi S of Springfield IL",
            "asset_id": "TRUCK-2847",
            "issue_type": "reefer_alarm",
            "severity": "emergency",
            "cargo_sensitive": True,
        },
        {
            "call_id": "CALL-092326-2145",
            "caller_name": "Sarah Johnson",
            "caller_role": "Driver",
            "received_at": "2026-09-03T21:45:00Z",
            "duration_seconds": 98,
            "transcript": "This is Sarah, truck 1923. I'm at the rest area on I-94 near Battle Creek. Low tire pressure warning on left rear dual. Should I continue to Detroit or need roadside?",
            "location": "I-94 Rest Area, Battle Creek MI",
            "asset_id": "TRUCK-1923",
            "issue_type": "tire_pressure_low",
            "severity": "routine",
            "cargo_sensitive": False,
        },
        {
            "call_id": "CALL-092326-2335",
            "caller_name": "David Kim",
            "caller_role": "Driver",
            "received_at": "2026-09-03T23:35:00Z",
            "duration_seconds": 187,
            "transcript": "Hey, it's David in truck 3104. I'm westbound on I-90 near the Illinois-Wisconsin border. Engine warning light just came on, and I'm hearing a knocking sound. Hauling auto parts to Chicago - not temp sensitive but time-sensitive delivery tomorrow 8 AM.",
            "location": "I-90 WB, IL-WI border",
            "asset_id": "TRUCK-3104",
            "issue_type": "engine_warning",
            "severity": "emergency",
            "cargo_sensitive": False,
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
