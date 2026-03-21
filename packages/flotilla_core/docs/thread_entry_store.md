# ThreadEntryStore Specification (v1.1-draft)

  

## 1. Executive Summary


### Purpose

`ThreadEntryStore` is the authoritative durable persistence API for:

-  `ThreadEntry`
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

-  `FlotillaRuntime` (exclusive appender for execution-phase entries)
-  `ThreadService` (thread identity lifecycle only)

`ThreadEntryStore` is the sole source of truth used to reconstruct `ThreadContext`.

---

  

## 3. Canonical Types / Interfaces

### ThreadEntryStore Interface

`ThreadEntryStore` MUST expose:

```python
class  ThreadEntryStore:

async  def  create_thread(self) -> str:
...

async  def  load(self, thread_id: str) -> list[ThreadEntry]:
...

async  def  append(self, entry: ThreadEntry, expected_previous_entry_id: str | None = None,) -> ThreadEntry:
...

```

### Interface Semantics

-  `create_thread()` creates a durable thread identity record and returns the durable `thread_id`.
-  `load()` returns all entries for `thread_id` in strict durable order.
-  `append()` is atomic and conditional.

On success:
- The store MUST persist the entry
- The store MUST assign `entry_id` and `timestamp`
- The store MUST return the fully realized immutable `ThreadEntry`

The returned `ThreadEntry` is NOT authoritative state and MUST NOT be used to construct or mutate in-memory thread state.


### AppendConflictError

`AppendConflictError`

- Raised when append request is malformed or violates request-level invariants
- Represents a CAS predicate failure at the request level
- Does NOT imply storage failure
- Does NOT indicate concurrent execution conflict

---

## 4. Behavioral Contract

### 4.1 Thread Creation

`create_thread()` MUST:

- Generate a globally unique `thread_id`
- Durably persist it
- Return that `thread_id`


### 4.2 Thread Existence Requirement for Append

`append()` MUST:

- Fail with a store error if `entry.thread_id` does not exist
- MUST NOT implicitly create threads during append

### 4.3 Append-Only Immutability

`ThreadEntryStore` MUST:
  
- Persist `ThreadEntry` as immutable records
- Never update or delete an existing entry
- If `entry.entry_id` or `entry.timestamp` is non-null at append time, the store MUST reject the append and raise an `AppendConflictError`

### 4.4 Store-Assigned Identity

On successful `append()`:

- Store MUST generate and persist a globally unique `entry_id` and assign a timestamp of when the entry was appended to the log in UTC
- Return fully realized immutable ThreadEntry
- The store MUST also assign `entry_order` as part of the durable append operation.

### 4.5 Store-Assigned Timestamp

On successful `append()`:

- Store MUST assign and persist a store-authoritative timestamp.
- Timestamp MUST be immutable once persisted.
- Timestamps MUST be monotonically non-decreasing in the store's durable order for a given thread.
- Client-supplied timestamps MUST be rejected and MUST NOT be persisted

### 4.6 Strict Per-Thread Ordering

For a given `thread_id`:

- Entries MUST have a strict total durable order.
- This order MUST be represented by a store-assigned, strictly increasing integer field: `entry_order`.

#### entry_order Semantics

- `entry_order` MUST:
  - Start at 0 for the first entry in a thread
  - Increase by exactly 1 for each subsequent append
  - Be unique per `thread_id`
  - Be immutable once assigned

- The store MUST enforce:
  - No gaps in `entry_order`
  - No duplicate `entry_order` values within a thread

- `load(thread_id)` MUST return entries ordered by `entry_order ASC`

- The store MUST NOT reorder entries.

### 4.7 Append Semantics

`expected_previous_entry_id` enforces strict linked-list CAS.

Append MUST succeed if and only if:
- If thread is empty:  
-- `expected_previous_entry_id` is `None`  
-- `entry.previous_entry_id` is `None`  
  
- If thread is non-empty:  
-- `expected_previous_entry_id` == `current_tail.entry_id`  
-- `entry.previous_entry_id` == `current_tail.entry_id`  
  
These conditions ensure that the append operation both:  
- Is based on a non-stale view of the thread (CAS)  
- Extends the current tail without introducing branching (linked-list integrity)

The store MUST validate that:

- `entry.previous_entry_id` == `current_tail.entry_id`

This ensures strict linked-list integrity and prevents branching or disordered logs.

If predicate fails:

- If required fields are missing or invalid (see Section 6):
  → raise `AppendConflictError`

- If the append request does not match the current thread tail:
  → raise `ConcurrentThreadExecutionError`

No durable mutation MUST be performed in either case.

#### Ordering Assignment

On successful append:

- The store MUST assign `entry_order` as:

  - `0` if the thread is empty
  - `current_tail.entry_order + 1` otherwise

- Assignment of `entry_order` MUST be atomic with the append operation.

- The store MUST ensure that concurrent appends cannot produce:
  - Duplicate `entry_order`
  - Gaps in `entry_order`

### 4.8  Authoritative State Model

`ThreadContext` obtained via `load()` is the ONLY authoritative representation of thread state

`ThreadContext` MUST be treated as immutable

There is no supported mechanism to incrementally update or mutate a `ThreadContext` in memory

All state transitions MUST follow:
  1. append()
  2. load()

Any `ThreadEntry` returned from `append()` is informational only and MUST NOT be used as a substitute for `load()`

Any mismatch between the append request and the current thread tail MUST be treated as a concurrency conflict and MUST NOT be interpreted as a recoverable structural inconsistency.

### Core Invariant

The `ThreadEntryStore` enforces a single append invariant:

> Every append operation MUST extend the current tail of the thread.

There is exactly one valid next state for a thread:
- A new entry whose `previous_entry_id` references the current tail

Any deviation from this invariant MUST be treated as either:
- A malformed request (`AppendConflictError`), or
- A concurrency conflict (`ConcurrentThreadExecutionError`)

### 4.9 Load Behavior

`load(thread_id)` MUST:

- Return all entries for an existing thread in strict order
- Raise `ThreadNotFoundError` if the thread does not exist
---

## 5. ContentPart Persistence

`ThreadEntryStore` MUST:

- Persist `ContentPart` as structured serialized data (e.g., JSON)
- Serialization and deserialization MUST be lossless
- `ContentPart` ordering MUST be preserved exactly as provided
- Not mutate content
- Not reorder the `ContentPart` list

### 5.1 ContentPart Ordering

For each `ThreadEntry`:

- `ContentPart` instances MUST be persisted with an explicit positional index.
- Ordering MUST be preserved exactly as provided in `ThreadEntry.content`.
- Reconstruction MUST restore the exact original ordering.

---

## 6. Error Handling Rules

`ThreadEntryStore` MUST distinguish between two classes of append failure:

### 6.1 Predicate Failures (CAS Violations)  
  
The store MUST enforce append predicates and raise:  
  
- `AppendConflictError` — malformed or invalid request  
- `ConcurrentThreadExecutionError` — concurrency violation  
  
#### AppendConflictError  
Raised when:  
- `expected_previous_entry_id` is None for non-empty thread  
- `entry.previous_entry_id` is None for non-empty thread  
- Client attempts to supply `entry_id` or `timestamp`  
- First-append invariants are violated  
  
This represents a malformed or invalid request.  
  

#### ConcurrentThreadExecutionError

Raised when:
- `expected_previous_entry_id` does not match the current thread tail
- `entry.previous_entry_id` does not match the current thread tail

These conditions indicate that the caller's view of the thread is stale or inconsistent with the durable log.

Because `ThreadContext` is immutable and authoritative, any mismatch with the current tail MUST be treated as a concurrency conflict rather than a structural error.
  

### 6.2 Thread Existence Failures

- `ThreadNotFoundError` MUST be raised when appending to a non-existent thread

### 6.3 Storage Failures

- Infrastructure/storage failures MUST raise store-specific errors
- These MUST NOT be conflated with CAS failures

### 6.4 No Silent Failures

- All failures MUST be explicit exceptions
- No implicit retries or silent overwrites are allowed

---

## 7. Related Specifications

- Thread Model (`ThreadEntry` / `ThreadContext`)
- ContentPart