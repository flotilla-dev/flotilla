from abc import ABC, abstractmethod

from flotilla.telemetry.telemetry_event import TelemetryEvent


class TelemetryService(ABC):
    """
    Best-effort sink for framework telemetry events.

    Runtime and framework components call this service when they want to
    observe significant behavior, failures, or lifecycle milestones. The
    service translates TelemetryEvent objects into logs, metrics, traces,
    audit events, or other external telemetry systems.

    Telemetry must never influence runtime correctness. Implementations should
    avoid raising, and callers may defensively ignore telemetry failures.
    """

    @abstractmethod
    def emit(self, event: TelemetryEvent) -> None: ...
