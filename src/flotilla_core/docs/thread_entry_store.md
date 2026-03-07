# ThreadEntryStore Specification (v1.1-draft)

## 1. Executive Summary

### Purpose

`ThreadEntryStore` is the authoritative durable persistence API for:

- `ThreadEntry`
- Embedded `ContentPart` payloads

It provides:

- Append-only durability
- Store-assigned identity (`entry_id`)
- Store-assigned timestamps
- Strict per-thread ordering
- Atomic conditional append predicates (CAS)

`ThreadEntryStore` is a durable log and concurrency primitive, not a lifecycle engine.

### What It Does Not Do

`ThreadEntryStore` MUST NOT:

- Create threads implicitly during append
- Interpret lifecycle semantics (start vs. terminal meaning)
- Infer predicates from `ThreadEntry.type`
- Implement orchestration logic
- Implement suspend routing
- Implement timeout logic
- Issue `ResumeToken`s

---

## 2. System Architecture Context

`ThreadEntryStore` sits below:

- `FlotillaRuntime` (exclusive appender for execution-phase entries)
- `ThreadService` (thread identity lifecycle only)

`ThreadEntryStore` is the sole source of truth used to reconstruct `ThreadContext`.

---

## 3. Canonical Types / Interfaces

### ThreadEntryStore Interface

`ThreadEntryStore` MUST expose:

```python
class ThreadEntryStore:

    async def create_thread(self) -> str:
        ...

    async def load(self, thread_id: str) -> list[ThreadEntry]:
        ...

    async def append(
        self,
        entry: ThreadEntry,
        expected_previous_entry_id: str | None = None,
    ) -> ThreadEntry:
        ...
```

### Interface Semantics

- `create_thread()` creates a durable thread identity record and returns the durable `thread_id`.
- `load()` returns all entries for `thread_id` in strict durable order.
- `append()` is atomic and conditional. On success, it returns the fully realized immutable `ThreadEntry` with store-assigned `entry_id` and `timestamp`. On predicate failure, it MUST raise `AppendConflictError`.


### AppendConflictError

AppendConflictError
- Raised when expected_previous_entry_id does not match current tail.
- Represents a CAS conflict.
- Does NOT imply storage failure.

---

## 4. Behavioral Contract

### 4.1 Thread Creation

`create_thread(thread_id=None)` MUST:

- Generate a globally unique `thread_id`
- Durably persist it
- Return that `thread_id`

`create_thread(thread_id=<value>)` MUST:

- Create the thread if it does not exist
- Raise a store error if it already exists (no silent reuse)

Thread creation is used by `ThreadService` (outside runtime).

### 4.2 Thread Existence Requirement for Append

`append()` MUST:

- Fail with a store error if `entry.thread_id` does not exist
- MUST NOT implicitly create threads during append

### 4.3 Append-Only Immutability

`ThreadEntryStore` MUST:

- Persist `ThreadEntry` as immutable records
- Never update or delete an existing entry
- If entry.entry_id or entry.timestamp is non-null at append time, the store MUST reject the append and raise an `AppendConflictError`

### 4.4 Store-Assigned Identity

On successful `append()`:

- Store MUST generate and persist a globally unique `entry_id` and assign a timestamp of when the entry was appended to the log in UTC
- Return fully realized immutable ThreadEntry

### 4.5 Store-Assigned Timestamp

On successful `append()`:

- Store MUST assign and persist a store-authoritative timestamp.
- Timestamp MUST be immutable once persisted.
- Timestamps MUST be monotonically non-decreasing in the store's durable order for a given thread.
- Client timestamps MUST NOT be used as authoritative.

### 4.6 Strict Per-Thread Ordering

For a given `thread_id`:

- Entries MUST have a strict total durable order.
- `load(thread_id)` MUST return entries in that order.
- The store MUST NOT reorder entries.

### 4.7 Append Semantics (Model 2)

`expected_previous_entry_id` enforces strict linked-list CAS.

Append MUST succeed if and only if:
-   If thread is empty:
    -   `expected_previous_entry_id` is `None`
    -   `entry.previous_entry_id` is `None`
        
-   If thread is non-empty:
    -   `current_tail.entry_id == expected_previous_entry_id`
    -   `entry.previous_entry_id == current_tail.entry_id`

The store MUST validate that entry.previous_entry_id == expected_previous_entry_id.        

If predicate fails:
-   Store MUST raise `AppendConflictError`
-   No durable mutation performed
    

---

## 5. ContentPart Persistence

`ThreadEntryStore` MUST:

- Persist `ContentPart` as structured serialized data (e.g., JSON)
- Preserve full fidelity
- Not mutate content
- Not reorder the `ContentPart` list

---

## 6. Error Handling Rules

- Storage/constraint failures not representable as predicate failure MUST raise a store error.
- Thread-not-found on `append()` MUST raise a store error.
- Predicate failure raises error in `append()`

---

## 7. Related Specifications

- Thread Model (`ThreadEntry` / `ThreadContext`)
- ContentPart