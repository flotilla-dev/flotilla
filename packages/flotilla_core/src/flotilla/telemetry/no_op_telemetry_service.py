from flotilla.telemetry.telemetry_service import TelemetryService
from flotilla.telemetry.telemetry_event import TelemetryEvent


class NoOpTelemetryService(TelemetryService):
    """
    TelemetryService implementation for apps that do not emit telemetry.

    Runtime and framework components may still call emit(), but this
    implementation intentionally drops every TelemetryEvent.
    """

    def emit(self, event: TelemetryEvent):
        pass
