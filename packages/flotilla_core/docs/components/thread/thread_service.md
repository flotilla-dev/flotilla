# ThreadService Specification (v1.0-draft)

## 1. Executive Summary

`ThreadService` is the application-facing service for creating and reading Flotilla threads.

It exists so applications can create durable thread identities with required thread metadata and optional creation-time attributes without exposing append operations directly.

`ThreadService` is a thin boundary over `ThreadEntryStore`.

## 2. Architectural Context

`ThreadService` sits above `ThreadEntryStore` and below application or adapter code.

Applications use `ThreadService` before invoking `FlotillaRuntime`. Runtime requests require an existing `thread_id`; runtime does not create threads implicitly.

## 3. Core Concepts

### CreateThreadRequest

`CreateThreadRequest` contains the durable metadata needed to create a thread.

Required fields:

- `title`

Optional fields:

- `created_by`
- `attributes`

### Thread

`Thread` is the durable thread metadata record returned from creation and load operations.

### ThreadAttribute

`ThreadAttribute` is a creation-time child of a thread. Attributes are application-defined key/value pairs and are immutable after creation.

## 4. Responsibilities

`ThreadService` is responsible for:

- Creating threads from `CreateThreadRequest`.
- Returning durable thread metadata.
- Returning immutable creation-time thread attributes.
- Loading the durable `ThreadEntry` log for application inspection.
- Preventing application code from appending entries directly.

## 5. Non-Responsibilities

`ThreadService` is NOT responsible for:

- Appending `ThreadEntry` records.
- Running agents or orchestration.
- Enforcing runtime lifecycle rules.
- Authorizing thread access.
- Adding, updating, or deleting thread attributes after creation.

## 6. Behavioral Contract

`create_thread(request)` MUST delegate to `ThreadEntryStore.create_thread(request)` and return the created `Thread`.

`load_thread(thread_id)` MUST return durable thread metadata or fail if the thread does not exist.

`load_thread_attributes(thread_id)` MUST return immutable creation-time attributes for the thread or fail if the thread does not exist.

`load(thread_id)` MUST return the durable ordered `ThreadEntry` log for the thread or fail if the thread does not exist.

`ThreadService` MUST NOT expose append APIs.

## 7. Related Specifications

- [Thread Model](thread_model.md)
- [ThreadEntryStore](thread_entry_store.md)
- [FlotillaRuntime](../runtime/flotilla_runtime.md)
