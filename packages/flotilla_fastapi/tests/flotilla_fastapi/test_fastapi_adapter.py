import pytest
import asyncio
import inspect
from typing import AsyncIterator, List, Optional

from fastapi.testclient import TestClient

from flotilla_fastapi.handler import HTTPHandler

from flotilla_fastapi.adapter import FastAPIAdapter
from flotilla_fastapi.routes import routes

from flotilla_fastapi.interceptor import HTTPRequestInterceptor
from flotilla_fastapi.exception_handler import HTTPExceptionHandler
from fastapi.responses import JSONResponse


# --------------------------------------------------
# Test Utilities
# --------------------------------------------------


class FakeContainer:
    """
    Minimal test double for FlotillaContainer
    """

    def __init__(self, instances):
        self._instances = instances

    def find_instances_by_type(self, base_type):
        return [i for i in self._instances if isinstance(i, base_type)]


# --------------------------------------------------
# Test Handlers
# --------------------------------------------------


class SimpleHandler(HTTPHandler):

    @routes.get("/hello")
    async def hello(self):
        return {"message": "hello"}


class DIHandler(HTTPHandler):

    def __init__(self, value: str):
        self.value = value

    @routes.get("/di")
    async def get_value(self):
        return {"value": self.value}


class StreamingHandler(HTTPHandler):

    @routes.get("/stream")
    async def stream(self) -> AsyncIterator[dict]:
        async def generator():
            for i in range(3):
                yield {"event": i}
                await asyncio.sleep(0)

        return generator()


class MultipleRouteHandler(HTTPHandler):

    @routes.get("/a")
    async def a(self):
        return {"a": 1}

    @routes.get("/b")
    async def b(self):
        return {"b": 2}


# --------------------------------------------------
# Fixtures
# --------------------------------------------------


@pytest.fixture
def build_app():
    def _build(
        handlers: Optional[List[HTTPHandler]] = None,
        exception_handlers: Optional[List[HTTPExceptionHandler]] = None,
        interceptors: Optional[List[HTTPRequestInterceptor]] = None,
    ):
        adapter = FastAPIAdapter(
            handlers=handlers or [],
            exception_handlers=exception_handlers or [],
            interceptors=interceptors or [],
        )
        adapter.start()
        return adapter.app

    return _build


# --------------------------------------------------
# Tests
# --------------------------------------------------


def test_route_registration(build_app):
    app = build_app(handlers=[SimpleHandler()])

    client = TestClient(app)

    response = client.get("/hello")

    assert response.status_code == 200
    assert response.json() == {"message": "hello"}


def test_handler_invocation(build_app):
    app = build_app(handlers=[SimpleHandler()])

    client = TestClient(app)

    response = client.get("/hello")

    assert response.status_code == 200
    assert response.json()["message"] == "hello"


def test_dependency_injection(build_app):
    handler = DIHandler(value="injected")

    app = build_app(handlers=[handler])
    client = TestClient(app)

    response = client.get("/di")

    assert response.status_code == 200
    assert response.json() == {"value": "injected"}


def test_multiple_handlers(build_app):
    app = build_app(handlers=[SimpleHandler(), MultipleRouteHandler()])

    client = TestClient(app)

    r1 = client.get("/hello")
    r2 = client.get("/a")
    r3 = client.get("/b")

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 200


def test_async_iterator_streaming(build_app):
    app = build_app(handlers=[StreamingHandler()])
    client = TestClient(app)

    response = client.get("/stream")

    # We don’t enforce exact SSE format yet (v1),
    # just ensure streaming response is returned
    assert response.status_code == 200

    # Depending on your implementation, this may vary:
    # You might return text/event-stream or JSON lines
    content = response.text

    assert "event" in content


def test_non_streaming_passthrough(build_app):
    class Handler(HTTPHandler):

        @routes.get("/data")
        async def data(self):
            return {"x": 1}

    app = build_app(handlers=[Handler()])
    client = TestClient(app)

    response = client.get("/data")

    assert response.status_code == 200
    assert response.json() == {"x": 1}


def test_only_http_handler_instances_are_used(build_app):

    class NotAHandler:
        pass

    app = build_app(handlers=[SimpleHandler(), NotAHandler()])

    client = TestClient(app)

    response = client.get("/hello")

    assert response.status_code == 200


def test_no_routes_if_no_decorators(build_app):

    class EmptyHandler(HTTPHandler):
        async def foo(self):
            return {"x": 1}

    app = build_app(handlers=[EmptyHandler()])
    client = TestClient(app)

    response = client.get("/foo")

    # should not exist
    assert response.status_code == 404


def test_multiple_routes_on_single_handler(build_app):
    app = build_app(handlers=[MultipleRouteHandler()])
    client = TestClient(app)

    assert client.get("/a").status_code == 200
    assert client.get("/b").status_code == 200


def test_async_handler_supported(build_app):

    class AsyncHandler(HTTPHandler):

        @routes.get("/async")
        async def async_route(self):
            await asyncio.sleep(0)
            return {"ok": True}

    app = build_app(handlers=[AsyncHandler()])
    client = TestClient(app)

    response = client.get("/async")

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_endpoint_signature_preserved(build_app):
    handler = SimpleHandler()
    app = build_app(handlers=[handler])

    route = next(r for r in app.routes if getattr(r, "path", None) == "/hello")
    sig = inspect.signature(route.endpoint)

    assert list(sig.parameters.keys()) == []


def test_endpoint_signature_preserved_with_parameters(build_app):
    class ParamHandler(HTTPHandler):

        @routes.get("/items/{item_id}")
        async def get_item(self, item_id: str):
            return {"item_id": item_id}

    app = build_app(handlers=[ParamHandler()])

    route = next(r for r in app.routes if getattr(r, "path", None) == "/items/{item_id}")
    sig = inspect.signature(route.endpoint)

    assert list(sig.parameters.keys()) == ["item_id"]


# --------------------------------------------------
# Params
# --------------------------------------------------


def test_path_parameter_binding(build_app):
    class Handler(HTTPHandler):

        @routes.get("/items/{item_id}")
        async def get_item(self, item_id: str):
            return {"item_id": item_id}

    app = build_app(handlers=[Handler()])
    client = TestClient(app)

    response = client.get("/items/abc123")

    assert response.status_code == 200
    assert response.json() == {"item_id": "abc123"}


def test_query_parameter_binding(build_app):
    class Handler(HTTPHandler):

        @routes.get("/search")
        async def search(self, q: str):
            return {"q": q}

    app = build_app(handlers=[Handler()])
    client = TestClient(app)

    response = client.get("/search?q=test-query")

    assert response.status_code == 200
    assert response.json() == {"q": "test-query"}


def test_optional_query_parameters(build_app):
    class Handler(HTTPHandler):

        @routes.get("/search")
        async def search(self, q: str = "default"):
            return {"q": q}

    app = build_app(handlers=[Handler()])
    client = TestClient(app)

    response = client.get("/search")

    assert response.status_code == 200
    assert response.json() == {"q": "default"}


from pydantic import BaseModel


def test_request_body_binding(build_app):
    class Payload(BaseModel):
        name: str

    class Handler(HTTPHandler):

        @routes.post("/items")
        async def create(self, payload: Payload):
            return {"name": payload.name}

    app = build_app(handlers=[Handler()])
    client = TestClient(app)

    response = client.post("/items", json={"name": "flotilla"})

    assert response.status_code == 200
    assert response.json() == {"name": "flotilla"}


def test_mixed_parameters(build_app):
    from pydantic import BaseModel

    class Payload(BaseModel):
        value: int

    class Handler(HTTPHandler):

        @routes.post("/items/{item_id}")
        async def update(self, item_id: str, payload: Payload, verbose: bool = False):
            return {
                "item_id": item_id,
                "value": payload.value,
                "verbose": verbose,
            }

    app = build_app(handlers=[Handler()])
    client = TestClient(app)

    response = client.post(
        "/items/xyz?verbose=true",
        json={"value": 42},
    )

    assert response.status_code == 200
    assert response.json() == {
        "item_id": "xyz",
        "value": 42,
        "verbose": True,
    }


def test_body_validation_error(build_app):
    from pydantic import BaseModel

    class Payload(BaseModel):
        value: int

    class Handler(HTTPHandler):

        @routes.post("/items")
        async def create(self, payload: Payload):
            return {"value": payload.value}

    app = build_app(handlers=[Handler()])
    client = TestClient(app)

    response = client.post("/items", json={"value": "not-an-int"})

    assert response.status_code == 422


from fastapi import Request


def test_fastapi_request_injection(build_app):
    class Handler(HTTPHandler):

        @routes.get("/request-test")
        async def request_test(self, request: Request):
            return {"method": request.method}

    app = build_app(handlers=[Handler()])
    client = TestClient(app)

    response = client.get("/request-test")

    assert response.status_code == 200
    assert response.json() == {"method": "GET"}


# -----------------------------------------
# Exception
# -----------------------------------------


def test_custom_exception_handler_invoked(build_app):
    class MyError(Exception):
        pass

    class Handler(HTTPHandler):

        @routes.get("/boom")
        async def boom(self):
            raise MyError("something went wrong")

    class MyErrorHandler(HTTPExceptionHandler[MyError]):
        exception_type = MyError

        async def handle(self, request, exc):
            return JSONResponse(
                status_code=418,
                content={"error": str(exc)},
            )

    app = build_app(handlers=[Handler()], exception_handlers=[MyErrorHandler()])
    client = TestClient(app)

    response = client.get("/boom")

    assert response.status_code == 418
    assert response.json() == {"error": "something went wrong"}


def test_exception_handler_receives_request(build_app):
    class MyError(Exception):
        pass

    class Handler(HTTPHandler):

        @routes.get("/boom")
        async def boom(self):
            raise MyError("fail")

    class MyErrorHandler(HTTPExceptionHandler[MyError]):
        exception_type = MyError

        async def handle(self, request, exc):
            return JSONResponse(
                status_code=500,
                content={"path": request.url.path},
            )

    app = build_app(handlers=[Handler()], exception_handlers=[MyErrorHandler()])
    client = TestClient(app)

    response = client.get("/boom")

    assert response.status_code == 500
    assert response.json() == {"path": "/boom"}


def test_unhandled_exception_propagates(build_app):
    class MyError(Exception):
        pass

    class Handler(HTTPHandler):

        @routes.get("/boom")
        async def boom(self):
            raise MyError("unhandled")

    app = build_app(handlers=[Handler()])
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/boom")

    assert response.status_code == 500


def test_duplicate_exception_handlers_fail_startup():
    class MyError(Exception):
        pass

    class Handler1(HTTPExceptionHandler[MyError]):
        exception_type = MyError

        async def handle(self, request, exc):
            return JSONResponse(status_code=400, content={"a": 1})

    class Handler2(HTTPExceptionHandler[MyError]):
        exception_type = MyError

        async def handle(self, request, exc):
            return JSONResponse(status_code=500, content={"b": 2})

    adapter = FastAPIAdapter(handlers=[], exception_handlers=[Handler1(), Handler2()], interceptors=[])

    with pytest.raises(ValueError):
        adapter.start()


def test_only_http_exception_handler_instances_are_used(build_app):
    class MyError(Exception):
        pass

    class Handler(HTTPHandler):

        @routes.get("/boom")
        async def boom(self):
            raise MyError("fail")

    class MyErrorHandler(HTTPExceptionHandler[MyError]):
        exception_type = MyError

        async def handle(self, request, exc):
            return JSONResponse(status_code=400, content={"error": "handled"})

    app = build_app(handlers=[Handler()], exception_handlers=[MyErrorHandler()])
    client = TestClient(app)

    response = client.get("/boom")

    assert response.status_code == 400
    assert response.json() == {"error": "handled"}


from fastapi import HTTPException


def test_fastapi_http_exception_can_be_overridden(build_app):
    class Handler(HTTPHandler):

        @routes.get("/boom")
        async def boom(self):
            raise HTTPException(status_code=404, detail="missing")

    class MyHTTPExceptionHandler(HTTPExceptionHandler[HTTPException]):
        exception_type = HTTPException

        async def handle(self, request, exc):
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
            )

    app = build_app([Handler(), MyHTTPExceptionHandler()])
    client = TestClient(app)

    response = client.get("/boom")

    assert response.status_code == 404
    assert response.json() == {"detail": "missing"}


# -----------------------------------------------
# Interceptors
# -----------------------------------------------


def test_interceptor_is_invoked(build_app):
    class Handler(HTTPHandler):

        @routes.get("/test")
        async def test(self):
            return {"ok": True}

    class Interceptor(HTTPRequestInterceptor):
        def __init__(self):
            self.called = False

        async def dispatch(self, request, call_next):
            self.called = True
            return await call_next(request)

    interceptor = Interceptor()

    app = build_app([Handler(), interceptor])
    client = TestClient(app)

    response = client.get("/test")

    assert response.status_code == 200
    assert interceptor.called is True


def test_interceptor_is_invoked(build_app):
    class Handler(HTTPHandler):

        @routes.get("/test")
        async def test(self):
            return {"ok": True}

    class Interceptor(HTTPRequestInterceptor):
        def __init__(self):
            self.called = False

        async def dispatch(self, request, call_next):
            self.called = True
            return await call_next(request)

    interceptor = Interceptor()

    app = build_app(handlers=[Handler()], interceptors=[interceptor])
    client = TestClient(app)

    response = client.get("/test")

    assert response.status_code == 200
    assert interceptor.called is True


def test_interceptor_can_short_circuit(build_app):
    class Handler(HTTPHandler):

        @routes.get("/test")
        async def test(self):
            return {"ok": True}

    class Interceptor(HTTPRequestInterceptor):

        async def dispatch(self, request, call_next):
            return JSONResponse(status_code=403, content={"error": "blocked"})

    app = build_app([Handler(), Interceptor()])
    client = TestClient(app)

    response = client.get("/test")

    assert response.status_code == 403
    assert response.json() == {"error": "blocked"}


def test_interceptor_can_short_circuit(build_app):
    class Handler(HTTPHandler):

        @routes.get("/test")
        async def test(self):
            return {"ok": True}

    class Interceptor(HTTPRequestInterceptor):

        async def dispatch(self, request, call_next):
            return JSONResponse(status_code=403, content={"error": "blocked"})

    app = build_app(handlers=[Handler()], interceptors=[Interceptor()])
    client = TestClient(app)

    response = client.get("/test")

    assert response.status_code == 403
    assert response.json() == {"error": "blocked"}


def test_only_interceptor_instances_are_used(build_app):
    class Handler(HTTPHandler):

        @routes.get("/test")
        async def test(self):
            return {"ok": True}

    class Interceptor(HTTPRequestInterceptor):
        async def dispatch(self, request, call_next):
            return await call_next(request)

    class NotAnInterceptor:
        pass

    app = build_app([Handler(), Interceptor(), NotAnInterceptor()])
    client = TestClient(app)

    response = client.get("/test")

    assert response.status_code == 200


def test_interceptor_receives_request(build_app):
    class Handler(HTTPHandler):

        @routes.get("/test")
        async def test(self):
            return {"ok": True}

    class Interceptor(HTTPRequestInterceptor):

        async def dispatch(self, request, call_next):
            assert request.url.path == "/test"
            return await call_next(request)

    app = build_app([Handler(), Interceptor()])
    client = TestClient(app)

    response = client.get("/test")

    assert response.status_code == 200


def test_interceptor_receives_request(build_app):
    class Handler(HTTPHandler):

        @routes.get("/test")
        async def test(self):
            return {"ok": True}

    class Interceptor(HTTPRequestInterceptor):

        async def dispatch(self, request, call_next):
            assert request.url.path == "/test"
            return await call_next(request)

    app = build_app([Handler(), Interceptor()])
    client = TestClient(app)

    response = client.get("/test")

    assert response.status_code == 200


def test_interceptor_can_read_request_headers(build_app):
    class Handler(HTTPHandler):

        @routes.get("/test")
        async def test(self):
            return {"ok": True}

    class Interceptor(HTTPRequestInterceptor):
        def __init__(self):
            self.header_value = None

        async def dispatch(self, request, call_next):
            self.header_value = request.headers.get("x-test-header")
            return await call_next(request)

    interceptor = Interceptor()

    app = build_app(handlers=[Handler()], interceptors=[interceptor])
    client = TestClient(app)

    response = client.get("/test", headers={"x-test-header": "hello"})

    assert response.status_code == 200
    assert interceptor.header_value == "hello"
