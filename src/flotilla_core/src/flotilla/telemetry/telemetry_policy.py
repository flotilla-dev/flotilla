from typing import Protocol, runtime_checkable
from flotilla.telemetry.telemetry_event import TelemetryEvent


@runtime_checkable
class TelemetryPolicy(Protocol):

    def emit(self, event: TelemetryEvent) -> None: ...
