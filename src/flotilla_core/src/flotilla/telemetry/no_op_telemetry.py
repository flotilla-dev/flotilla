from flotilla.telemetry.telemetry_policy import TelemetryPolicy
from flotilla.telemetry.telemetry_event import TelemetryEvent


class NoOpTelemetryPolicy(TelemetryPolicy):
    """Simple TelemetryPolicy that takes no action"""

    def emit(self, event: TelemetryEvent):
        pass
