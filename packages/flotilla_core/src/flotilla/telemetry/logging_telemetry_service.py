from flotilla.telemetry.telemetry_service import TelemetryService
from flotilla.telemetry.telemetry_event import TelemetryEvent, Severity
from typing import Optional
import logging


class LoggingTelemetryService(TelemetryService):
    """
    TelemetryService implementation that emits events through stdlib logging.

    Runtime and framework components use TelemetryService for best-effort
    observation. This implementation maps TelemetryEvent severity to logging
    levels and forwards event metadata as structured logging extras.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        self._logger = logger or logging.getLogger("flotilla.telemetry")

    def emit(self, event: TelemetryEvent) -> None:
        try:
            level = self._map_severity(event.severity)

            self._logger.log(
                level,
                event.event_type,
                extra={
                    "component": event.component,
                    "timestamp": event.timestamp.isoformat(),
                    "context": event.context,
                    **event.attributes,
                },
            )

        except Exception:
            # Telemetry must not be failure-fatal
            pass

    def _map_severity(self, severity: Severity) -> int:
        if severity == Severity.DEBUG:
            return logging.DEBUG
        elif severity == Severity.INFO:
            return logging.INFO
        elif severity == Severity.WARNING:
            return logging.WARNING
        elif severity == Severity.ERROR:
            return logging.ERROR
        return logging.INFO
