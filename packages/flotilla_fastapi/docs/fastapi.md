# Flotilla FastAPI Integration Specification (v1.0-final)

----------

## 1. Executive Summary

### Purpose

This specification defines the FastAPI integration layer for Flotilla.

It provides:

-   HTTP transport binding for Flotilla applications
-   Declarative route definition via decorators
-   Integration with FlotillaContainer for dependency injection
-   Support for synchronous and streaming execution
-   General-purpose handler model (runtime optional)
-   Middleware-based interception and exception handling

This integration is implemented as an **external extension library** (`flotilla-fastapi`) and is not part of `flotilla-core`.

----------

### Design Goals

The integration MUST:

-   Preserve Flotilla’s deterministic, DI-driven architecture
-   Provide a FastAPI-native developer experience
-   Support both runtime and non-runtime handlers
-   Avoid reimplementation of FastAPI features
-   Remain transport-only (no business logic, no state management)

----------

### Non-Goals

The integration MUST NOT:

-   Redefine runtime semantics or IO contracts
-   Introduce alternate execution state models
-   Manage ThreadContext lifecycle
-   Replace FastAPI routing, validation, or OpenAPI features
-   Require use of FlotillaRuntime

----------

## 2. Architectural Context
```
HTTP Client  
 ↓  
FastAPI (ASGI)  
 ↓  
Flotilla FastAPI Adapter  
 ↓  
HTTPHandler (DI-managed)  
 ↓  
Application Services / FlotillaRuntime
```
----------

### Boundary Ownership
| Concern | Owner |
|--|--|
| HTTP transport | FastAPI |
| Dependency injection | FlotillaContainer |
| Application logic | HTTPHandler |
| Agent execution | FlotillaRuntime |
| Execution state | ThreadContext |

----------

### State Model

-   `ThreadContext` is the only Flotilla-managed execution state
-   All components in this integration MUST be stateless
-   No request-scoped DI exists

----------

## 3. Design Principles

----------

### 3.1 Transport Adapter Only

The integration MUST:

-   translate HTTP → handler invocation
-   translate handler return → HTTP response

It MUST NOT:

-   implement business logic
-   mutate execution state
-   interpret runtime semantics

----------

### 3.2 General-Purpose Handler Model

Handlers are general-purpose endpoints.

They MAY:

-   call `FlotillaRuntime`
-   use `ContentPart`
-   return `RuntimeResponse` / `RuntimeEvent`

They are NOT required to do so.

----------

### 3.3 Declarative Routing

Routes are defined via decorators that:

-   record metadata
-   defer binding until startup

----------

### 3.4 DI as Source of Truth

All components MUST be constructed via `FlotillaContainer`.

`FastAPI` MUST NOT construct application components.

----------

### 3.5 Stateless Singleton Model

All handlers, interceptors, and exception handlers MUST:

-   be singletons
-   be stateless
-   be thread-safe

----------

### 3.6 FastAPI Owns HTTP Semantics

`FastAPI` remains responsible for:

-   request parsing
-   validation
-   `OpenAPI` schema creation
-   serialization

----------

## 4. Component Model

----------

## 4.1 HTTPHandler

### Definition

A singleton DI-managed class exposing HTTP route methods.

----------

### Responsibilities

-   orchestrate request handling
-   invoke services (runtime or otherwise)
-   return response

----------

### Capabilities

Handlers MAY:

-   call `FlotillaRuntime`
-   construct `RuntimeRequest`
-   use `ContentPart`
-   return:
    -   `RuntimeResponse`
    -   `AsyncIterator[RuntimeEvent]`
    -   JSON
    -   `FastAPI` Response

----------

### Invariants

Handlers MUST:

-   be stateless
-   be thread-safe
-   use constructor DI only
-   not access container directly

----------

## 4.2 RouteDecorator (`routes.*`)

----------

### Definition

A passive decorator that records route metadata.

----------

### Supported Forms

@routes.get(path, **kwargs)  
@routes.post(path, **kwargs)

----------

### Behavior

The decorator MUST:

-   capture HTTP method, path
-   capture all `**kwargs` unchanged
-   attach metadata

It MUST NOT:

-   bind routes
-   validate kwargs
-   depend on FastAPI

----------

## 4.3 RouteDefinition
| Field | Description |
|--|--|
| method | HTTP method
| path | route path |
| kwargs | FastAPI kwargs |
| method_name | method |

Decorators MUST NOT modify function behavior or wrap execution.  
They serve only as metadata carriers.
----------

## 4.4 FastAPIAdapter

----------

### Responsibilities

-   create or receive FastAPI app
-   discover handlers
-   bind routes
-   inject interceptors
-   inject exception handlers

----------

### Binding
```python
app.add_api_route(path, endpoint, methods=[method], **kwargs)
```
----------

### Endpoint Construction Pipeline

For each discovered route, the adapter MUST construct the endpoint using the following pipeline:

1. Resolve handler instance from container
2. Resolve bound method using `method_name`
3. Create endpoint callable that invokes the bound method
4. Apply wrapper hook (no-op in v1)
5. Apply execution wrapper (response normalization and streaming)
6. Register endpoint with FastAPI

This pipeline MUST be executed during application startup and MUST NOT occur at request time.

### Wrapper Hook (Future Extension)

The adapter MUST include a wrapper application step in the endpoint construction pipeline.

In v1, this step MUST be a no-op.

This hook exists to support future decorator-driven behavior (e.g. authentication, rate limiting) without modifying handler implementations.

## 5. Handler Execution Model

----------

### Flow
```
HTTP Request  
 ↓  
FastAPI routing  
 ↓  
Adapter wrapper  
 ↓  
Handler method  
 ↓  
Return value  
 ↓  
HTTP response
```

Handler methods MUST be invoked as bound methods on singleton handler instances.  
The adapter MUST NOT create new handler instances per request.

----------

### Dependency Resolution

-   handler instance resolved via container
-   no per-request instantiation

----------

## 6. Return Type Model

----------

### Supported Returns
| Type | Behavior |
|--|--|
| RuntimeResponse | JSON passthrough
| AsyncIterator[RuntimeEvent] | streamed |
| JSON | FastAPI default |
| Response | passthrough |


### Execution Wrapper

The adapter MUST wrap each endpoint with an execution wrapper responsible for:

- awaiting handler execution
- detecting return types at runtime
- normalizing responses

The execution wrapper MUST:

- detect `AsyncIterator` via runtime inspection
- convert async iterators into streaming HTTP responses (SSE or equivalent)
- pass through `Response` objects unchanged
- pass through JSON-compatible objects to FastAPI

The execution wrapper MUST NOT:

- rely on type annotations for behavior
- perform business logic
----------

### Adapter Rule

> Adapter MUST detect return type and adapt behavior.

----------

## 7. Runtime Integration (Optional)

----------

### Runtime Usage

Handlers MAY call:
```python
runtime.run(request)  
runtime.stream(request)
```
----------

### Runtime IO

When used, handlers MUST follow `FlotillaRuntime` I/O contract  
(see )

----------

### ContentPart

When interacting with `FlotillaRuntime`, content MUST use `ContentPart`  
(see )

----------

### Non-runtime handlers

-   no requirement to use `ContentPart`
-   may return arbitrary JSON

----------

## 8. Streaming Model

----------

### Source


- Any object implementing `AsyncIterator` (detected at runtime)

Streaming detection MUST be based on runtime inspection (e.g. presence of `__aiter__`) and MUST NOT rely solely on type annotations.

----------

### Transport

-   SHOULD use SSE

----------

### Rules

-   events MUST be ordered
-   exactly one terminal event
-   content preserved

----------

## 9. Error Handling

----------

### Runtime Errors

-   returned as `RuntimeResponse(type=ERROR)`
-   content MUST use `ContentPart`

----------

### Handler Exceptions

-   routed through exception handling system
-   mapped to HTTP response

----------

## 10. Deployment Model

----------

### Modes

-   Embedded (Flotilla runs server)
-   Hosted (external ASGI server)

----------

### Startup
```
Bootstrap → Container.build → Adapter.init → App ready
```
----------

## 11. FastAPIAdapter Initialization Lifecycle

All route discovery, endpoint construction, and registration MUST occur during startup.  
No route binding or endpoint transformation may occur at request time.

----------

### Phases

----------

#### Phase 1 — App Creation

-   create or receive FastAPI app

----------

#### Phase 2 — Route Binding

-   discover handlers
-   register routes

----------

#### Phase 3 — Interceptor Injection

-   inject middleware
-   inject exception handlers

----------

#### Phase 4 — Finalization

-   lock configuration
-   prevent mutation

----------

#### Phase 5 — Execution

-   run or return app

----------

### Constraint

> No structural mutation allowed after finalization.

----------

## 12. Interceptor Component Model

----------

### 12.1 Overview

Interceptors are DI-managed components for HTTP cross-cutting concerns.

Two types:

-   `HTTPRequestInterceptor`
-   `HTTPExceptionHandler`

----------

## 12.2 HTTPRequestInterceptor

----------

### Definition

Base class for middleware.

----------

### Interface
```python
class  HTTPRequestInterceptor:  
  async  def  dispatch(self, request, call_next):  
  return  await  call_next(request)
```
----------

### Rules

-   MUST be stateless
-   MUST be thread-safe
-   MUST be DI-managed

----------

## 12.3 HTTPExceptionHandler

----------

### Definition

Base class for exception mapping.

----------

### Interface
```python
class  HTTPExceptionHandler:  
  exception_type: Type[Exception] =  Exception  
  
  async  def  handle(self, request, exc):  
  raise  exc
```
----------

### Rules

-   MUST define exception_type
-   MUST return HTTP response
-   MUST be stateless

----------

## 12.4 Discovery

Adapter MUST discover via:
```python
container.find_instances_by_type(...)
```
----------

## 12.5 Injection

----------

### Middleware
```python
app.add_middleware(BaseHTTPMiddleware, dispatch=...)
```
----------

### Exception Handlers
```python
app.add_exception_handler(exception_type, handler)
```
----------

### Ordering

-   MUST be deterministic
-   defined by container registration order

----------

### Conflict Rule

> Only one exception handler per exception type.  
> Multiple registrations MUST raise configuration error.

----------

## 13. Invariants

The system MUST guarantee:

1.  Handlers are singleton, stateless, thread-safe
2.  Interceptors are singleton and stateless
3.  Route decorators are declarative only
4.  All routes registered at startup
5.  Middleware and exception handlers injected after route binding
6.  No mutation after app finalization
7.  `FlotillaContainer` owns all components
8.  FastAPI owns HTTP semantics
9.  Runtime remains transport-agnostic
10.  `ThreadContext` is never managed by FastAPI
11.  Adapter is non-invasive
12.  `ContentPart` required only for runtime interaction