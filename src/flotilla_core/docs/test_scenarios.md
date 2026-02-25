# Flotilla Canonical Reference Scenarios

**Version:** 1.0  
**Durability Model:** CAS (optimistic concurrency via versioned writes)  
**Checkpoint Model:** Snapshot-based  
**Runtime Model:** Stateless orchestration  
**Thread Model:** Append-only log

---

## Scenario 1 — Weather Forecast Agent (CAS Baseline)

### 1. Domain

A user asks:

> "What's the weather in Austin tomorrow?"

The agent:
- Extracts city and date
- Calls a WeatherTool (external HTTP API)
- Summarizes result
- Returns response

### 2. Architectural Shape

- Single agent
- Single external tool
- No subagents
- No HITL
- One checkpoint boundary (`message_final`)
- Stateless runtime

This is the minimum viable CAS-safe agent execution.

### 3. Required Runtime Guarantees

#### CAS Invariants
- Each `ThreadEntry` append must increment version atomically.
- No two runtime instances may write the same version.
- Resume must fail if version mismatch occurs.

#### Determinism Invariants
- Replay from checkpoint must produce identical final output.
- Tool result must not execute twice after resume.
- No duplicate `AgentOutput` entries allowed.

### 4. Baseline Execution Flow

1. Append `UserInputEntry` (version N → N+1)
2. Agent emits `tool_call`
3. Tool executes (external API)
4. Agent emits `message_final`
5. Append `AgentOutputEntry` (version N+2)
6. Write `ExecutionSnapshot(version=N+2)`

### 5. CAS Stress Variants

#### Variant A — Concurrent Resume Attempt

**Simulate:** Two runtime instances attempt resume at version N+2.

**Expected:**
- Only one instance succeeds writing N+3.
- Second instance fails CAS.
- No duplicate output.

#### Variant B — Crash After Tool Execution Before Checkpoint

Kill runtime after tool result returned but before snapshot write.

**On resume:**
- Tool must **NOT** re-execute if result already appended.
- Either tool result persisted in `ThreadEntry`, or `continuation_state` proves tool completion.
- No duplicate HTTP calls.

#### Variant C — 500 Concurrent Weather Requests

**Simulate:** 500 threads across 10 runtime instances.

**Expected:**
- No deadlocks
- Version monotonic per thread
- No cross-thread contamination
- No memory bleed between runtime instances

### 6. Why This Scenario Exists

This scenario forces the runtime to prove:
- Tool execution boundaries are safe
- CAS version enforcement works
- Snapshot resume is deterministic
- Stateless runtime is truly stateless

> If this breaks, the framework is unsafe at the most basic level.

---

## Scenario 2 — Enterprise Software Approval Workflow (CAS + HITL Stress)

### 1. Domain

User submits:

> "Request installation of Tableau on my corporate laptop."

**Workflow:**
1. `IntakeAgent` validates request.
2. `LicenseTool` checks license pool.
3. If insufficient: invoke `PurchaseSubAgent`, emit Suspend *(Finance Approval Required)*.
4. Finance user resumes.
5. `PurchaseTool` executes.
6. `InstallSubAgent` invoked.
7. `InstallTool` executes.
8. Final output returned.

### 2. Architectural Shape

- Root agent
- Two subagents
- Multiple tools
- Conditional branching
- HITL suspend/resume
- Long-running execution
- Multiple checkpoint boundaries
- CAS enforced at every append

This scenario stresses the entire architecture.

### 3. Required Runtime Guarantees

#### Thread Log Guarantees
- Append-only
- `parent_entry_id` must always match causal chain
- No duplicate `SuspendEntry`
- No `ResumeEntry` without prior `SuspendEntry`

#### CAS Guarantees
- Resume must fail if thread version has advanced.
- Concurrent finance approvals must not create duplicate purchases.
- Only one `ResumeEntry` accepted per suspend boundary.

#### Checkpoint Guarantees
- Snapshot created on: Suspend, Final output
- Snapshot cleared or superseded after resume.
- `continuation_state` must be deterministic.

### 4. Baseline Execution Flow

| Step | Event | Version |
|------|-------|---------|
| 1 | `UserInputEntry` | v1 |
| 2 | `IntakeAgent` parses structured request | — |
| 3 | `LicenseTool` returns insufficient | v2 |
| 4 | `PurchaseSubAgent` invoked | — |
| 5 | Agent emits `SuspendEntry` | v3 |
| 6 | `Snapshot(version=3, suspended=True)` | — |
| — | *Runtime halts* | — |
| 7 | Finance submits `ResumeEntry` (CAS v3→v4) | v4 |
| 8 | `PurchaseTool` executes | v5 |
| 9 | `InstallSubAgent` invoked | — |
| 10 | `InstallTool` executes | v6 |
| 11 | Agent emits `AgentOutputEntry` | v7 |
| 12 | `Snapshot(version=7, suspended=False)` | — |

### 5. CAS Stress Variants

#### Variant A — Double Finance Approval (Concurrent Resume)

Two finance officers submit resume simultaneously.

**Expected:**
- Only one `ResumeEntry` written.
- Second fails CAS due to version mismatch.
- No duplicate purchase.
- No duplicate install.

#### Variant B — Crash After Suspend Before Snapshot

Kill runtime after writing `SuspendEntry` but before writing snapshot.

**On restart:**
- Resume must still work.
- Snapshot reconstruction must derive state from thread log.
- No orphaned suspend state.

#### Variant C — Crash During Install

Kill runtime after `PurchaseTool` executed but before `InstallTool` completion.

**On resume:**
- `InstallTool` must not execute twice unless idempotent.
- `continuation_state` must reflect correct subagent step.

#### Variant D — Long-Running Abandonment

`SuspendEntry` exists with no resume for 48 hours.

**Expected:**
- Thread remains consistent.
- Resume still valid.
- No runtime memory required to maintain state.

### 6. Why This Scenario Exists

This scenario validates:
- HITL durability correctness
- CAS protection integrity
- Subagent orchestration soundness
- Long-running workflow viability
- Deterministic resume across process restarts
- Enterprise-grade concurrency handling

> If this passes under load, Flotilla is production-ready.

---

## Scenario 3 — Customer Refund Resolution Agent
*(Moderate Complexity, No HITL, Multi-Step Tool Orchestration)*

### 1. Domain

A customer submits:

> "I want a refund for order #84721. The item arrived damaged."

The agent must:
1. Validate order exists.
2. Check refund eligibility policy.
3. Check if refund already issued.
4. If eligible:
   - Issue refund via `PaymentTool`.
   - Update order status.
5. Return structured + natural language response.

No human approval. No suspend. But multiple tool calls and conditional logic. This is extremely realistic in enterprise systems.

### 2. Architectural Shape

- Single root agent
- Multiple tools
- Conditional branching
- Multi-step execution
- Transaction-like semantics
- No HITL
- Multiple checkpoint boundaries possible
- CAS enforced per append

This stresses orchestration without human interruption.

### 3. Why This Is the Perfect Middle Case

**It introduces:**
- Multi-step tool orchestration
- Cross-tool dependency
- State validation before mutation
- Side effects (refund money)
- Idempotency requirements
- Crash recovery mid-sequence
- Logical consistency across steps

**But avoids:**
- Subagents
- HITL complexity
- Long-lived suspended threads

It's the sweet spot.

### 4. Baseline Execution Flow

| Step | Event | Version |
|------|-------|---------|
| 1 | `UserInputEntry` | v1 |
| 2 | Agent parses `order_id` | — |
| 3 | `OrderLookupTool` → returns order details | v2 |
| 4 | `EligibilityTool` → returns `eligible=true` | v3 |
| 5 | `RefundStatusTool` → returns not refunded | v4 |
| 6 | `PaymentTool` → executes refund | v5 |
| 7 | `OrderUpdateTool` → marks refunded | v6 |
| 8 | Agent emits `AgentOutputEntry` | v7 |
| 9 | `Snapshot(version=7)` | — |

### 5. Required Runtime Guarantees

#### CAS Invariants
- Each tool result append increments version atomically.
- No step executes twice due to resume.
- Refund must not process twice under concurrent resume.

#### Deterministic Resume Invariants

If runtime crashes after:

**Case A — After `PaymentTool` but Before `OrderUpdateTool`**

Resume must:
- Detect refund already processed, OR
- `continuation_state` indicates next step is `OrderUpdateTool`.
- `PaymentTool` must **NOT** execute twice.

**Case B — After `OrderUpdateTool` but Before Final Output**

Resume must:
- Skip refund.
- Skip update.
- Produce final output.

**Case C — Concurrent Duplicate Requests**

Two users submit the same refund simultaneously.

**Expected:**
- Only one refund processed.
- Second execution sees updated order state.
- No double charge reversal.

This stresses CAS + tool idempotency.

### 6. Observability Requirements

Thread log must show:
- Clear sequence of tool calls
- No skipped versions
- No duplicate tool entries
- Deterministic `parent_entry_id` linkage

You must be able to reconstruct exactly:
- Whether refund occurred
- At which version
- Which runtime instance executed it