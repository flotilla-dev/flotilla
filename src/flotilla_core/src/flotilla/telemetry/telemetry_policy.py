from typing import Protocol
from flotilla.telemetry.telemetry_event import TelemetryEvent


class TelemetryPolicy(Protocol):

    def emit(self, event: TelemetryEvent) -> None: ...
