# ArborMind Learning Layer - The 10 Requirements

## Implementation Status: ✅ COMPLETE

This document describes the 10 requirements for perfect failure memory and tool execution observability.

---

## Requirement 1: Hard Epistemic Boundary ✅

**File:** `boundary.py`

**What it does:**
- Makes it **impossible** (not unlikely) for ArborMind to read cognition data
- Separate database file (`failure_memory.db` vs `arbormind.db`)
- Separate module namespace (`learning.*` vs `observation.*`)
- Runtime assertions prevent accidental access

**Forbidden data (CANNOT be read by learning layer):**
- `decisions` table
- `supervisor_verdicts` table
- `confidence`, `verdict`, `quality_score`, `rejection_reasons`
- `attention`, `reason`, `action`, `outcome`

**Rule:** If it can be joined, it will be abused.

---

## Requirement 2: Failure Memory v2 Canonical Table ✅

**File:** `failure_memory.py`

**Schema (v2):**
```sql
CREATE TABLE failures_v1 (
    id TEXT PRIMARY KEY,              -- UUID
    created_at TEXT NOT NULL,         -- ISO8601 UTC
    run_id TEXT NOT NULL,
    step TEXT NOT NULL,
    agent TEXT,
    primary_class TEXT NOT NULL,      -- F1-F9
    scope TEXT NOT NULL,              -- entity_local|step_local|cross_step|systemic
    signals_json TEXT NOT NULL,       -- JSON array of AtomicSignal
    raw_error TEXT,
    raw_diff TEXT,
    retry_index INTEGER DEFAULT 0,
    is_hard_failure INTEGER DEFAULT 0,
    schema_version INTEGER NOT NULL,
    canon_version INTEGER NOT NULL,
    -- v2: TEMPORAL TRUTH INVARIANCE
    interpretation_context_hash TEXT, -- Hash for quick drift detection
    interpretation_context_json TEXT  -- Full frozen context
)
```

**Properties:**
- UUID primary key (not auto-increment)
- Append-only (no updates, no deletes)
- Mandatory `primary_class`
- Explicit `scope`
- Atomic `signals[]`
- `retry_index` tracking
- `is_hard_failure` flag
- Schema version frozen
- **v2: Interpretation context captured**

---

## Requirement 3: Failure Class Canon (F1-F9) ✅

**File:** `failure_canon.py`

**The 9 Canonical Classes:**

| ID | Name | Description | Retryable | Typical Scope |
|----|------|-------------|-----------|---------------|
| F1 | Invariant Violation | Output violates a declared invariant | ✅ | entity_local |
| F2 | Parse Failure | Output could not be parsed | ✅ | step_local |
| F3 | Truncation | Output was cut off | ✅ | step_local |
| F4 | Quality Rejection | Supervisor rejected for quality | ✅ | entity_local |
| F5 | Timeout | Operation exceeded time budget | ✅ | systemic |
| F6 | Dependency Missing | Required upstream artifact missing | ❌ | cross_step |
| F7 | Runtime Exception | Unhandled code exception | ❌ | systemic |
| F8 | Semantic Conflict | Output conflicts with existing artifacts | ✅ | cross_step |
| F9 | External Failure | External system failed | ✅ | systemic |

**Properties:**
- Finite alphabet (exactly 9 classes)
- One and only one primary class per failure
- Immutable definitions
- Code-defined, versioned, referenced by ID

---

## Requirement 4: Signal Extraction Without Interpretation ✅

**File:** `signal_extractor.py`

**What it extracts:**
- Exception types (e.g., `TypeError`, `ValueError`)
- File paths
- Line numbers
- Missing identifiers
- Failed imports
- Type mismatches
- HTTP status codes
- Timeout values
- Diff lines (+/-)

**Rules:**
- No LLM
- No heuristics with intent
- No collapsing
- No summarization
- Pure regex matching
- Same input → same output (always)

**Signal Properties:**
- Small
- Countable
- Repeatable
- Hashable

---

## Requirement 5: Explicit Scope Assignment ✅

**File:** `failure_canon.py` (FailureScope enum)

**The 4 Scopes:**

| Scope | Description |
|-------|-------------|
| `ENTITY_LOCAL` | Failure is local to a single entity (e.g., one model file) |
| `STEP_LOCAL` | Failure is local to a single step (e.g., backend_models) |
| `CROSS_STEP` | Failure spans multiple steps (e.g., frontend depends on backend) |
| `SYSTEMIC` | Failure is system-wide (e.g., API failures, token limits) |

**Rules:**
- Every failure MUST declare scope at creation time
- No inference later
- No retroactive correction
- If scope is wrong, meaning still stabilizes
- If scope is missing, meaning never does

---

## Requirement 6: One-Way Ingestion Contract ✅

**File:** `ingestion.py`

**API:**
```python
from app.arbormind.learning import ingest_failure, FailureClass, FailureScope

ingest_failure(
    run_id="run_123",
    step="backend_models",
    primary_class=FailureClass.F1_INVARIANT_VIOLATION,
    scope=FailureScope.ENTITY_LOCAL,
    raw_error="Error message here",
    agent="Derek",
)
```

**Convenience functions:**
- `ingest_invariant_violation()` → F1
- `ingest_parse_failure()` → F2
- `ingest_truncation()` → F3
- `ingest_quality_rejection()` → F4
- `ingest_timeout()` → F5
- `ingest_dependency_missing()` → F6
- `ingest_runtime_exception()` → F7
- `ingest_semantic_conflict()` → F8
- `ingest_external_failure()` → F9

**Rules:**
- Write-only
- Append-only
- Irreversible
- No updates
- No deletes
- No "mark as resolved"

**Failures are historical facts, not tickets.**

---

## Requirement 7: Delay All Cognition ✅

**Enforcement:** By design

**What must be delayed:**
- ❌ Dashboards
- ❌ Ranking
- ❌ Clustering
- ❌ Learning
- ❌ Fixing
- ❌ "Just checking patterns"

**The read methods in `failure_memory.py` are:**
- Documented as "offline learning only"
- Not exposed in the ingestion API
- Only accessible via the inspection CLI tool

**The inspection tool (`inspect_failures.py`) is for humans only.**

---

## Requirement 8: Temporal Truth Invariance ✅

**File:** `interpretation_context.py`

**The Problem:**
Storing "what failed" is not enough if the meaning of that failure
can change when the system evolves.

**What must be frozen at the time of each failure:**
1. Signal extractor version + rules hash
2. Active invariants (which rules were in force)
3. Scope semantics (what each scope meant)
4. Canon definitions (what F1-F9 meant)

**The Guarantee:**
> "A failure recorded today can be understood identically in 6 months,
> even if the codebase has completely changed."

**Implementation:**
Each failure record includes:
- `interpretation_context_hash` - Short hash for quick comparison
- `interpretation_context_json` - Full frozen context for reconstruction

**Context Drift Detection:**
```python
from app.arbormind.learning import verify_context_compatibility, context_drift_warning

# Check if stored failure was recorded under current rules
is_compatible = verify_context_compatibility(stored_hash)

# Get human-readable warning if context changed
warning = context_drift_warning(stored_hash)
# ⚠️ CONTEXT DRIFT: This failure was recorded under context 'abc123' 
# but current context is 'xyz789'. Interpretation rules may have changed.
```

**What v1 records show:**
Records created before v2 have `NULL` context, which is displayed as:
```
Context: ⚠️ MISSING (v1 record)
```

This is **honest** - we don't pretend to know what rules were active.

---

## File Structure

```
app/arbormind/learning/
├── __init__.py              # Exports all modules
├── boundary.py              # Requirement 1: Epistemic boundary
├── failure_canon.py         # Requirements 3 & 5: F1-F9 + Scopes
├── failure_memory.py        # Requirement 2: Canonical table (v2)
├── ingestion.py             # Requirement 6: One-way ingestion
├── signal_extractor.py      # Requirement 4: Dumb tokenization
├── interpretation_context.py # Requirement 8: Temporal truth invariance
├── inspect_failures.py      # Offline CLI tool (humans only)
├── pattern_extractor.py     # Legacy (kept for compatibility)
└── THE_7_REQUIREMENTS.md    # This documentation
```

---

## The Final Test

> "If I disappear for 6 months and come back, can ArborMind still tell me what actually breaks — without knowing what we tried to do about it?"

**Answer: YES**

The failure memory stores:
- What failed (step, agent)
- How it failed (F1-F9 class)
- Where it failed (scope)
- Raw signals (tokens)
- **v2: What those classifications meant at the time (interpretation context)**

It does NOT store:
- What decision was made
- Whether it was approved
- Why it was done
- How confident the system was

---

## Usage

### Inspect failures
```bash
cd Backend
python app/arbormind/learning/inspect_failures.py all --signals
```

### Watch database
```bash
# PowerShell
while ($true) { python app/arbormind/learning/inspect_failures.py recent --limit 5; Start-Sleep 2; cls }
```

### Record a failure (from FAST)
```python
from app.arbormind.learning import ingest_invariant_violation, FailureScope

ingest_invariant_violation(
    run_id=current_run_id,
    step="backend_models",
    error_message="Entity 'User' missing required field 'email'",
    scope=FailureScope.ENTITY_LOCAL,
    agent="Derek",
    retry_index=0,
)
```

### Check context drift
```python
from app.arbormind.learning import get_context_hash, verify_context_compatibility

# Current context hash
print(f"Current: {get_context_hash()}")

# Check if a stored record is compatible
is_ok = verify_context_compatibility(some_stored_hash)
```

---

## What "Perfect" Does NOT Mean

Perfect does NOT mean:
- Zero failures
- Smart fixes
- Elegant retries
- High success rate
- Fewer tokens
- Faster convergence

Those are **optimization goals**.

This is **truth infrastructure**.

---

## The 8th Requirement: Why It Matters

Without Requirement 8, you could have:
1. Recorded "F1 occurred at step X"
2. Changed what F1 means
3. Looked back and misinterpreted the record

**With Requirement 8:**
- Each record carries its own interpretation key
- Context drift is automatically detected
- Old records remain valid under their original semantics
- No silent meaning corruption

**The invariant:**
> Same input + same context = same meaning (forever)

---

## Requirement 9: Tool Invocation Trace (TIT) ✅

**File:** `app/arbormind/observation/tool_trace.py`

**Purpose:** Expose execution topology WITHOUT influencing it.

TIT answers: "What actually happened?"
NOT: "Why?" or "What should we do?"

**Non-Negotiable Constraints:**

| Constraint | Status |
|------------|--------|
| Append-only | ✅ |
| Write-through (no buffering) | ✅ |
| No interpretation | ✅ |
| No dependency on Arbormind decisions | ✅ |
| Failure-safe (never crash execution) | ✅ |
| Opt-out capable (`ARBORMIND_TIT=0`) | ✅ |

**Schema (v1):**
```sql
CREATE TABLE tool_invocations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Lineage
    run_id TEXT NOT NULL,
    branch_id TEXT,
    decision_id INTEGER,
    step TEXT NOT NULL,
    agent TEXT NOT NULL,
    
    -- Tool identity
    tool_name TEXT NOT NULL,
    tool_type TEXT NOT NULL,  -- 'plan_invocation', 'llm', 'process'
    
    -- Invocation context
    invocation_index INTEGER,
    called_at DATETIME NOT NULL,
    duration_ms INTEGER,
    
    -- Raw I/O (truncated to 2KB)
    input_summary TEXT,
    output_summary TEXT,
    
    -- Result
    status TEXT NOT NULL,  -- 'success', 'failure', 'timeout', 'aborted'
    error_type TEXT,
    error_message TEXT,
    
    -- Resource signals
    tokens_used INTEGER,
    model_name TEXT,
    retries INTEGER DEFAULT 0,
    
    -- Integrity
    schema_version INTEGER DEFAULT 1
);
```

**Hook Points (exactly 3):**

1. `execute_tool_plan()` - Primary hook, wraps every tool
2. `tool_sub_agent_caller()` - LLM boundary (tokens, model, retries)
3. `_async_run_command()` - Process boundary (exit code, stderr)

**What TIT Enables (after 10-20 runs):**
- Tool chains that precede failure
- Validators that never fail
- Guards that never guard
- Retry inflation patterns
- Windows-only failure topologies
- Token burn without validation benefit

**What TIT Does NOT Do (by design):**
- ❌ Tool scoring
- ❌ Tool ranking
- ❌ Tool avoidance
- ❌ "Better plan" inference
- ❌ Agent feedback loops

---

## Requirement 10: Capability-Based Tool Planning ✅

**Files:**
- `app/tools/capabilities.py` - Tool taxonomy
- `app/tools/planner.py` - Plan builder
- `app/tools/executor.py` - Linear executor
- `app/tools/planning.py` - Core primitives

**The Mental Shift:**

```
❌ WRONG:  Agent → decides tool → executes tool
✅ CORRECT: Agent → expresses intent → System selects tools → Executor runs → Observer records
```

**The Flow:**
```
Step → Capabilities → Eligible Tools → Ordered ToolPlan → Linear Execution
```

**Capability Taxonomy:**
- 36 tools tagged by CAPABILITY (what they DO, not what they ARE)
- 8 workflow steps mapped to required capabilities
- Automatic expansion: step → capabilities → tools

**Example Expansion:**

`backend_models` step expands to:
```
[PRE]  environment_guard
[PRE]  filereader
[PRE]  filelister
[PRE]  codeviewer
[PRE]  dbschemareader

[CORE] subagentcaller (Derek)

[POST] static_code_validator
[POST] syntaxvalidator
```

**Properties Achieved:**

| Property | Status |
|----------|--------|
| All 36 tools reachable | ✅ |
| No LLM autonomy | ✅ |
| Deterministic | ✅ |
| Observable | ✅ |
| Replayable | ✅ |
| Failure-analyzable | ✅ |

**ToolPlan Primitives:**
- `ToolPlan` - Frozen, immutable sequence of invocations
- `ToolInvocationPlan` - Single tool call spec (name, args, reason, required)
- `ToolInvocationResult` - Execution outcome
- `ToolPlanExecutionResult` - Full plan result
- `StepFailure` - Exception for required tool failures

**Linear Execution Rules:**
- No loops
- No retries
- No self-healing
- No reflection

Just execution of an explicit plan with full observability.

---

## Summary: The 10 Requirements

| # | Requirement | Purpose | File |
|---|-------------|---------|------|
| 1 | Hard Epistemic Boundary | Prevent learning from influencing decisions | `boundary.py` |
| 2 | Failure Memory v2 | Canonical failure storage | `failure_memory.py` |
| 3 | Failure Class Canon | F1-F9 taxonomy | `failure_canon.py` |
| 4 | Signal Extraction | Capture without interpretation | `signal_extractor.py` |
| 5 | Scope Classification | Failure blast radius | `failure_canon.py` |
| 6 | Ingestion Bridge | Connect FAST/Marcus to learning | `ingestion_bridge.py` |
| 7 | Hard Epistemic Enforcement | Runtime protection | `boundary.py` |
| 8 | Temporal Truth Invariance | Context preservation | `interpretation_context.py` |
| 9 | Tool Invocation Trace | Execution topology | `tool_trace.py` |
| 10 | Capability-Based Planning | Deterministic tool selection | `capabilities.py`, `planner.py` |

**The invariant for all 10:**
> Truth infrastructure, not optimization goals.
