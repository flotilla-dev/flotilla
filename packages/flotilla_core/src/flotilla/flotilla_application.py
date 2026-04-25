from __future__ import annotations

import sys
from typing import Any, Dict, Type, get_type_hints, Optional

from flotilla.config.errors import FlotillaConfigurationError
from flotilla.container.flotilla_container import FlotillaContainer
from flotilla.telemetry.telemetry_policy import TelemetryPolicy
from flotilla.telemetry.logger_telemetry import LoggerTelemetry


class FlotillaApplication:
    """
    Top-level lifecycle owner for a Flotilla application.

    Applications subclass FlotillaApplication to declare required services
    using type annotations. These services are resolved from the container
    during the build() phase and exposed as read-only attributes.

    Example:

        class MyApplication(FlotillaApplication):
            kafka_consumer: KafkaConsumer
            email_service: EmailService

    Services are resolved once during build() and stored internally on the
    application instance using a private attribute naming convention:

        kafka_consumer → _kafka_consumer

    Access is provided via __getattr__ without modifying the class structure.

    FlotillaApplication is responsible for:

      - managing application lifecycle (start, run, shutdown)
      - resolving declared services from the container
      - exposing services to application code
      - providing telemetry during application lifecycle

    This class intentionally does NOT:

      - expose the container
      - perform dependency injection during runtime
      - manage agent execution (handled by FlotillaRuntime)

    Lifecycle:

        Bootstrap.run()
            ↓
        container created
            ↓
        application created
            ↓
        _attach_container()
            ↓
        build()
            ↓
        start()
            ↓
        run()  (optional blocking execution)
    """

    def __init__(self, telemetry: Optional[TelemetryPolicy] = None):

        self._telemetry = telemetry or LoggerTelemetry()

        self._container = None
        self._built = False
        self._started = False
        self._run = False
        self._shutdown = False

        # cache of declared annotations
        self._annotations: Dict[str, Type[Any]] = {}

    # ------------------------------------------------------------------
    # Container Wiring
    # ------------------------------------------------------------------

    def _attach_container(self, container: FlotillaContainer) -> None:
        if self._container is not None:
            raise FlotillaConfigurationError("Container already attached")
        self._container = container

    # ------------------------------------------------------------------
    # Build Phase
    # ------------------------------------------------------------------

    def build(self) -> None:
        """
        Resolve declared services from the container.

        This method inspects the application class annotations, retrieves
        matching components from the container by type, and stores them
        on the application instance.

        build() must be called before start().
        """

        if self._container is None:
            raise RuntimeError("Container must be attached before build()")

        if self._built:
            raise RuntimeError("Application already built")

        annotations = self._collect_annotations()

        for name, service_type in annotations.items():

            if name == "telemetry":
                continue

            private_name = f"_{name}"

            if hasattr(self, private_name):
                raise FlotillaConfigurationError(f"Service storage attribute '{private_name}' already exists")

            service = self._container.find_one_by_type(service_type)

            setattr(self, private_name, service)

            self._annotations[name] = service

            self._install_property(name)

        self._execute_build()

        self._built = True

    # ------------------------------------------------------------------
    # Annotation Collection
    # ------------------------------------------------------------------

    def _collect_annotations(self) -> Dict[str, Type[Any]]:
        """
        Collect merged annotations across the class hierarchy.

        Results are cached per application class.
        """
        merged: Dict[str, Type[Any]] = {}

        for base in reversed(type(self).__mro__):

            if base is object:
                continue

            try:
                hints = get_type_hints(base)
            except Exception:
                hints = getattr(base, "__annotations__", {})

            merged.update(hints)

        return {k: v for k, v in merged.items() if not k.startswith("_")}

    def _install_property(self, name: str) -> None:
        cls = type(self)

        # already installed by a previous instance/build
        if name in cls.__dict__:
            return

        private_name = f"_{name}"

        def getter(instance, attr=private_name):
            return getattr(instance, attr)

        setattr(cls, name, property(getter))

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """
        Start the application.

        Subclasses override this method to initialize application resources.
        """
        self._assert_built()
        self._execute_start()
        self._started = True

    def run(self, **kwargs) -> None:
        """
        Optional blocking execution loop.

        Applications may override this method to run long-lived services
        such as HTTP servers or message consumers.
        """
        try:
            self._run = True
            self._execute_run(**kwargs)
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        """
        Shutdown the application and release resources.
        """
        if self._shutdown:
            return

        self._shutdown = True
        self._execute_shutdown()
        self._container = None
        self._started = False

    # ----------------------------
    # Public Accessors
    # ----------------------------

    @property
    def started(self) -> bool:
        return self._started

    @property
    def telemetry(self) -> TelemetryPolicy:
        return self._telemetry

    # -------------------------
    # Lifecycle helpers
    # -------------------------
    def _assert_started(self):
        if not self.started:
            raise RuntimeError("Application not started")

    def _assert_built(self):
        if not self._built:
            raise RuntimeError("Application must be built before start()")

    def _execute_build(self):
        """
        Lifecycle method that allows subclasses execute within the build lifecycle of the FlotillaApplication
        """
        pass

    def _execute_start(self):
        """
        Lifecycle method that allows subclasses execute within the start lifecycle of the FlotillaApplication
        """
        pass

    def _execute_run(self, **kwargs):
        """
        Lifecycle method that allows subclasses execute within the run lifecycle of the FlotillaApplication
        """
        pass

    def _execute_shutdown(self):
        """
        Lifecycle method that allows subclasses execute within the shutdown lifecycle of the FlotillaApplication
        """
        pass
