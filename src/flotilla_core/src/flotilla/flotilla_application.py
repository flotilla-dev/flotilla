from flotilla.container.flotilla_container import FlotillaContainer
from flotilla.runtime.flotilla_runtime import FlotillaRuntime
from flotilla.thread.thread_service import ThreadService


class FlotillaApplication:
    """
    Top-level lifecycle owner for a Flotilla application.

    FlotillaApplication is responsible for:
      - orchestrating configuration loading via ConfigLoader
      - constructing and building the FlotillaContainer
      - registering application-owned builders and contributors
      - managing application startup and shutdown state

    This class intentionally does NOT:
      - perform dependency injection directly
      - expose configuration loading internals
      - own framework wiring logic

    Configuration is supplied declaratively via ConfigurationSource and
    SecretResolver instances. The resolved configuration is materialized
    as a FlotillaSettings object during startup and passed into the container.

    A FlotillaApplication instance is single-start and single-container:
      - start() builds exactly one container
      - container access is only valid after start()
      - shutdown() invalidates the container

    This class serves as the primary integration point for real runtimes
    (CLI, FastAPI, workers, etc.).
    """

    def __init__(self, runtime: FlotillaRuntime, thread_service: ThreadService):
        """ """
        self._runtime = runtime
        self._thead_service = thread_service
        self._container = None
        self._started = False

    # ----------------------------
    # Build lifecycle
    # ----------------------------

    def start(self):
        """
        Start the application and build the Flotilla container.

        This method performs the full startup lifecycle:
        1. Load and merge configuration from the provided ConfigurationSources
        2. Resolve secret references using the provided SecretResolvers
        3. Construct a FlotillaSettings snapshot
        4. Build and validate the FlotillaContainer
        5. Mark the application as started

        After this method completes successfully:
        - the application is considered started
        - the container property becomes accessible
        - all registered builders and contributors have been applied

        Calling start() more than once is not supported.
        """
        self._started = True

    def shutdown(self):
        if not self._started:
            return

        # Optional: graceful teardown hooks later
        self._container = None
        self._runtime = None
        self._thead_service = None
        self._started = False

    # ----------------------------
    # Public Accessors
    # ----------------------------

    @property
    def started(self) -> bool:
        return self._started

    @property
    def runtime(self) -> FlotillaRuntime:
        self._assert_started()
        return self._runtime

    @property
    def thread_service(self) -> ThreadService:
        self._assert_started()
        return self._thead_service

    # -------------------------------
    # Private Helpers
    # -------------------------------

    def _attach_container(self, container: FlotillaContainer) -> None:
        if self._container is not None:
            raise RuntimeError("Container already attached to application")
        self._container = container

    def _assert_started(self):
        if not self.started:
            raise RuntimeError("Application not started")
