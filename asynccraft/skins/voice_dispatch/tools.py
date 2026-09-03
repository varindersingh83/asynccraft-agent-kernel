"""Tools for Voice Dispatch workflow."""

from typing import Any
from asynccraft.kernel.tools import Tool, ToolResult


class TranscribeCallTool(Tool):
    """Transcribe inbound voice call to text."""
    
    @property
    def name(self) -> str:
        return "transcribe_call"
    
    @property
    def description(self) -> str:
        return "Transcribe voice call audio to text for processing"
    
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute call transcription."""
        call_id = kwargs.get("call_id", "")
        caller = kwargs.get("caller", "")
        duration_seconds = kwargs.get("duration_seconds", 0)
        transcript = kwargs.get("transcript", "")
        
        return ToolResult(
            success=True,
            data={
                "call_id": call_id,
                "caller": caller,
                "duration_seconds": duration_seconds,
                "transcript": transcript,
                "transcribed_at": "2026-09-03T22:15:00Z",
            }
        )
    
    def preview(self, **kwargs: Any) -> str:
        caller = kwargs.get("caller", "")
        duration_seconds = kwargs.get("duration_seconds", 0)
        return f"Transcribe call from {caller} ({duration_seconds}s duration)"


class ExtractFieldsTool(Tool):
    """Extract structured fields from call transcript."""
    
    @property
    def name(self) -> str:
        return "extract_fields"
    
    @property
    def description(self) -> str:
        return "Extract location, asset, severity, and issue details from transcript"
    
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute field extraction."""
        transcript = kwargs.get("transcript", "")
        location = kwargs.get("location", "")
        asset_id = kwargs.get("asset_id", "")
        issue_type = kwargs.get("issue_type", "")
        severity = kwargs.get("severity", "routine")
        
        return ToolResult(
            success=True,
            data={
                "location": location,
                "asset_id": asset_id,
                "issue_type": issue_type,
                "severity": severity,
                "confidence": 0.89,
            }
        )
    
    def preview(self, **kwargs: Any) -> str:
        location = kwargs.get("location", "")
        asset_id = kwargs.get("asset_id", "")
        issue_type = kwargs.get("issue_type", "")
        return f"Extract fields: {issue_type} at {location} (Asset: {asset_id})"


class AssessEmergencySeverityTool(Tool):
    """Assess if call is after-hours emergency requiring immediate dispatch."""
    
    @property
    def name(self) -> str:
        return "assess_emergency_severity"
    
    @property
    def description(self) -> str:
        return "Determine if issue is emergency requiring after-hours response vs morning queue"
    
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute emergency severity assessment."""
        issue_type = kwargs.get("issue_type", "")
        severity = kwargs.get("severity", "routine")
        time_of_day = kwargs.get("time_of_day", "business_hours")
        cargo_sensitive = kwargs.get("cargo_sensitive", False)
        
        is_emergency = severity == "emergency" or (cargo_sensitive and issue_type in ["reefer_alarm", "breakdown"])
        return ToolResult(
            success=True,
            data={
                "issue_type": issue_type,
                "severity": severity,
                "is_emergency": is_emergency,
                "time_of_day": time_of_day,
                "cargo_sensitive": cargo_sensitive,
            }
        )
    
    def preview(self, **kwargs: Any) -> str:
        issue_type = kwargs.get("issue_type", "")
        severity = kwargs.get("severity", "routine")
        is_emergency = severity == "emergency"
        status = "EMERGENCY" if is_emergency else "routine"
        return f"Emergency assessment: {status} ({issue_type}, {severity} severity)"


class ProposeTechAssignmentTool(Tool):
    """Propose nearest technician for assignment."""
    
    @property
    def name(self) -> str:
        return "propose_tech_assignment"
    
    @property
    def description(self) -> str:
        return "Find and propose nearest available technician with ETA"
    
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute tech proposal."""
        location = kwargs.get("location", "")
        issue_type = kwargs.get("issue_type", "")
        tech_name = kwargs.get("tech_name", "")
        tech_id = kwargs.get("tech_id", "")
        eta_minutes = kwargs.get("eta_minutes", 0)
        
        return ToolResult(
            success=True,
            data={
                "location": location,
                "issue_type": issue_type,
                "tech_name": tech_name,
                "tech_id": tech_id,
                "eta_minutes": eta_minutes,
                "distance_miles": eta_minutes / 1.2,
            }
        )
    
    def preview(self, **kwargs: Any) -> str:
        tech_name = kwargs.get("tech_name", "")
        eta_minutes = kwargs.get("eta_minutes", 0)
        location = kwargs.get("location", "")
        return f"Tech proposal: {tech_name} → {location} (ETA {eta_minutes} min)"


class ApproveAssignmentTool(Tool):
    """Approve or hold technician assignment."""
    
    @property
    def name(self) -> str:
        return "approve_assignment"
    
    @property
    def description(self) -> str:
        return "Review and approve technician assignment before dispatch"
    
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute assignment approval."""
        tech_name = kwargs.get("tech_name", "")
        tech_id = kwargs.get("tech_id", "")
        eta_minutes = kwargs.get("eta_minutes", 0)
        asset_id = kwargs.get("asset_id", "")
        
        return ToolResult(
            success=True,
            data={
                "tech_name": tech_name,
                "tech_id": tech_id,
                "eta_minutes": eta_minutes,
                "asset_id": asset_id,
                "assignment_id": f"ASGN-{hash(tech_id) % 100000}",
            }
        )
    
    def preview(self, **kwargs: Any) -> str:
        tech_name = kwargs.get("tech_name", "")
        asset_id = kwargs.get("asset_id", "")
        eta_minutes = kwargs.get("eta_minutes", 0)
        return f"Assignment approval: {tech_name} to Asset {asset_id} (ETA {eta_minutes} min)"


class ApproveShipperNotificationTool(Tool):
    """Approve or skip customer notification."""
    
    @property
    def name(self) -> str:
        return "approve_shipper_notification"
    
    @property
    def description(self) -> str:
        return "Approve sending ETA notification to shipper/customer"
    
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute shipper notification approval."""
        shipper_name = kwargs.get("shipper_name", "")
        shipper_contact = kwargs.get("shipper_contact", "")
        eta_message = kwargs.get("eta_message", "")
        tech_name = kwargs.get("tech_name", "")
        
        return ToolResult(
            success=True,
            data={
                "shipper_name": shipper_name,
                "shipper_contact": shipper_contact,
                "eta_message": eta_message,
                "tech_name": tech_name,
            }
        )
    
    def preview(self, **kwargs: Any) -> str:
        shipper_name = kwargs.get("shipper_name", "")
        shipper_contact = kwargs.get("shipper_contact", "")
        tech_name = kwargs.get("tech_name", "")
        return f"Shipper notification: {shipper_name} ({shipper_contact}) - Tech {tech_name} dispatched"


class CreateWorkOrderTool(Tool):
    """Create work order in dispatch system."""
    
    @property
    def name(self) -> str:
        return "create_work_order"
    
    @property
    def description(self) -> str:
        return "Create work order with asset, tech, and issue details"
    
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute work order creation."""
        asset_id = kwargs.get("asset_id", "")
        tech_id = kwargs.get("tech_id", "")
        issue_type = kwargs.get("issue_type", "")
        location = kwargs.get("location", "")
        
        return ToolResult(
            success=True,
            data={
                "asset_id": asset_id,
                "tech_id": tech_id,
                "issue_type": issue_type,
                "location": location,
                "work_order_id": f"WO-{hash(asset_id) % 100000}",
                "created_at": "2026-09-03T22:30:00Z",
            }
        )
    
    def preview(self, **kwargs: Any) -> str:
        asset_id = kwargs.get("asset_id", "")
        tech_id = kwargs.get("tech_id", "")
        issue_type = kwargs.get("issue_type", "")
        return f"Work order: Asset {asset_id} → {issue_type} (Tech: {tech_id})"
