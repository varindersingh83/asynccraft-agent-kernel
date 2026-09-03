"""Tools for ops/dispatch exception handling."""

from typing import Any
from asynccraft.kernel.tools import Tool, ToolResult


class NotifyDispatcherTool(Tool):
    """Send notification to dispatcher about exception."""

    @property
    def name(self) -> str:
        return "notify_dispatcher"

    @property
    def description(self) -> str:
        return "Send urgent notification to dispatcher about an exception"

    async def execute(self, **kwargs: Any) -> ToolResult:
        dispatcher_id = kwargs.get("dispatcher_id", "unknown")
        message = kwargs.get("message", "")
        priority = kwargs.get("priority", "normal")

        return ToolResult(
            success=True,
            data={
                "notification_id": f"notif_{hash(message) % 10000:04d}",
                "dispatcher_id": dispatcher_id,
                "message": message,
                "priority": priority,
                "channel": "sms+slack",
                "mock": True,
            },
        )

    def preview(self, **kwargs: Any) -> str:
        dispatcher_id = kwargs.get("dispatcher_id", "unknown")
        message = kwargs.get("message", "")
        priority = kwargs.get("priority", "normal")
        return f"Send {priority.upper()} notification to dispatcher {dispatcher_id}: '{message}'"


class RerouteTruckTool(Tool):
    """Reroute truck to alternate destination."""

    @property
    def name(self) -> str:
        return "reroute_truck"

    @property
    def description(self) -> str:
        return "Update truck route to alternate destination"

    async def execute(self, **kwargs: Any) -> ToolResult:
        truck_id = kwargs.get("truck_id", "unknown")
        new_destination = kwargs.get("new_destination", "")
        reason = kwargs.get("reason", "")

        return ToolResult(
            success=True,
            data={
                "truck_id": truck_id,
                "new_destination": new_destination,
                "reason": reason,
                "eta_updated": True,
                "customer_notified": True,
                "mock": True,
            },
        )

    def preview(self, **kwargs: Any) -> str:
        truck_id = kwargs.get("truck_id", "unknown")
        new_destination = kwargs.get("new_destination", "")
        reason = kwargs.get("reason", "")
        return f"Reroute truck {truck_id} to {new_destination} (reason: {reason})"


class UpdateDeliveryETATool(Tool):
    """Update delivery ETA in system."""

    @property
    def name(self) -> str:
        return "update_delivery_eta"

    @property
    def description(self) -> str:
        return "Update expected delivery time and notify stakeholders"

    async def execute(self, **kwargs: Any) -> ToolResult:
        shipment_id = kwargs.get("shipment_id", "unknown")
        new_eta = kwargs.get("new_eta", "")
        delay_reason = kwargs.get("delay_reason", "")

        return ToolResult(
            success=True,
            data={
                "shipment_id": shipment_id,
                "new_eta": new_eta,
                "delay_reason": delay_reason,
                "customer_notified": True,
                "system_updated": True,
                "mock": True,
            },
        )

    def preview(self, **kwargs: Any) -> str:
        shipment_id = kwargs.get("shipment_id", "unknown")
        new_eta = kwargs.get("new_eta", "")
        delay_reason = kwargs.get("delay_reason", "")
        return f"Update shipment {shipment_id} ETA to {new_eta} (reason: {delay_reason})"


class EscalateToManagerTool(Tool):
    """Escalate exception to operations manager."""

    @property
    def name(self) -> str:
        return "escalate_to_manager"

    @property
    def description(self) -> str:
        return "Escalate critical exception to operations manager for decision"

    async def execute(self, **kwargs: Any) -> ToolResult:
        exception_id = kwargs.get("exception_id", "unknown")
        severity = kwargs.get("severity", "medium")
        summary = kwargs.get("summary", "")

        return ToolResult(
            success=True,
            data={
                "exception_id": exception_id,
                "severity": severity,
                "summary": summary,
                "escalated_to": "ops_manager",
                "ticket_created": True,
                "mock": True,
            },
        )

    def preview(self, **kwargs: Any) -> str:
        exception_id = kwargs.get("exception_id", "unknown")
        severity = kwargs.get("severity", "medium")
        summary = kwargs.get("summary", "")
        return (
            f"Escalate {severity.upper()} exception {exception_id} to manager: '{summary}'"
        )
