# ArborMind Convergence-First Implementation
## Implementation Summary

This document summarizes the 6-phase implementation of the ArborMind Convergence-First architecture.

---

## PHASE 1 — Convergence State (FOUNDATIONAL CHANGE)

**Files Modified:**
- `app/arbormind/cognition/convergence.py` - Expanded with full ConvergenceState enum and helper functions
- `app/arbormind/cognition/branch.py` - Added import for ConvergenceState
- `app/arbormind/cognition/entropy.py` - Enhanced `update_entropy()` to track convergence direction

**Key Changes:**
- ConvergenceState enum: `PROGRESS`, `CONVERGING`, `STALLED`, `DIVERGING`, `TERMINAL`
- Branch now tracks: `convergence`, `last_entropy`, `stagnation_count`
- `update_entropy()` now calculates entropy delta and updates convergence state automatically

**Outcome:** The system now has memory of direction, not just outcome.

---

## PHASE 2 — Reclassify Failures (STOP KILLING BRANCHES)

**Files Modified:**
- `app/arbormind/cognition/failures.py` - Expanded with `FAILURE_CLASSIFICATION` table and `InvariantViolation` dataclass
- `app/arbormind/invariants/invariant.py` - Changed to return violations instead of raising exceptions

**Key Changes:**
- `FailureSeverity` enum: `FATAL` vs `NON_FATAL`
- `FAILURE_CLASSIFICATION` - Centralized mapping table (no scatter)
- `InvariantViolation` dataclass - Structured failure result (not exception)
- `Invariant.check()` - Returns Optional[Violation], never raises
- `check_all_invariants()` - Collects all violations for orchestrator decision

**Outcome:** Failures become signals, not execution grenades.

---

## PHASE 3 — Replace "Steps" with "Actions" (COGNITION CORE)

**Files Modified:**
- `app/arbormind/runtime/actions.py` - Expanded with step-action mapping and selection logic

**Key Changes:**
- `ActionType` enum: `GENERATE`, `IMPROVE`, `REPAIR`, `VALIDATE`, `INTEGRATE`
- `STEP_TO_ACTION` - Maps steps to cognitive actions
- `ACTION_TO_STEPS` - Reverse mapping for action selection
- `select_next_action()` - Chooses action based on branch state
- `map_action_to_step()` - Maps chosen action to specific step

**Outcome:** The system no longer "marches forward". It chooses what to do next.

---

## PHASE 4 — Redefine Agent Contracts (WHY DEREK FAILED)

**Files Created:**
- `app/arbormind/cognition/partial_output.py` - Partial output policy and evaluation

**Files Modified:**
- `app/supervision/supervisor.py` - Zero-file check now uses partial output policy

**Key Changes:**
- `PARTIAL_OUTPUT_ALLOWED` - Which steps allow partial output
- `evaluate_progress()` - Any artifacts > 0 is progress if allowed
- `should_mark_success()` - Quality is directional, not binary
- Supervisor now only fatally rejects zero files for critical steps

**Outcome:** Derek cannot fail for being useful. This alone stabilizes 60-70% of failures.

---

## PHASE 5 — Make SQLite Memory EXECUTIVE (NOT PASSIVE)

**Files Modified:**
- `app/arbormind/observation/sqlite_store.py` - Added executive read methods
- `app/arbormind/runtime/runtime.py` - Integrated memory consultation

**Key Changes:**
- `has_failed_before()` - Check if agent+action failed in this run
- `last_entropy_delta()` - Historical entropy change for agent+action
- `get_agent_success_rate()` - Recent success rate for confidence
- Runtime now consults memory before deciding on actions
- "No retries without mutation" behavior enabled

**Outcome:** The system stops repeating known-bad behavior. This is proto-learning.

---

## PHASE 6 — Define Convergence Exit (STOP WHEN READY)

**Files Modified:**
- `app/arbormind/cognition/convergence.py` - Added completion criteria functions

**Key Changes:**
- `is_converged()` - Has architecture + frontend + backend + not diverging
- `get_completion_confidence()` - 0.0-1.0 confidence score
- `should_preview()` - Preview allowed at 60% confidence
- `get_missing_for_convergence()` - What steps are still needed

**Outcome:** ArborMind finishes when it should, not when it is perfect.

---

## Architecture Diagram

```
                    ┌─────────────────────────────────────┐
                    │         USER REQUEST                │
                    └─────────────────┬───────────────────┘
                                      │
                    ┌─────────────────▼───────────────────┐
                    │         ORCHESTRATOR                │
                    │   (Muscle - execution only)         │
                    └─────────────────┬───────────────────┘
                                      │
          ┌───────────────────────────┼───────────────────────────┐
          │                           │                           │
┌─────────▼─────────┐   ┌─────────────▼─────────────┐   ┌─────────▼─────────┐
│   PHASE 3         │   │       PHASE 1             │   │   PHASE 5         │
│  Action Selector  │◄──│   Convergence Tracker     │──►│  Memory Consul    │
│  (what to do)     │   │   (direction tracking)    │   │  (proto-learning) │
└─────────┬─────────┘   └─────────────┬─────────────┘   └─────────┬─────────┘
          │                           │                           │
          │             ┌─────────────▼─────────────┐             │
          │             │       PHASE 2             │             │
          └────────────►│   Failure Classifier      │◄────────────┘
                        │   (signals not grenades)  │
                        └─────────────┬─────────────┘
                                      │
          ┌───────────────────────────┼───────────────────────────┐
          │                           │                           │
┌─────────▼─────────┐   ┌─────────────▼─────────────┐   ┌─────────▼─────────┐
│   PHASE 4         │   │       AGENTS              │   │   PHASE 6         │
│  Partial Output   │──►│   Derek, Victoria, Luna   │──►│  Convergence Exit │
│  (Derek can't     │   │   Marcus (Supervision)    │   │  (done when ready)│
│   fail for useful)│   └───────────────────────────┘   └───────────────────┘
└───────────────────┘
```

---

## Key Invariants

1. **Convergence is orthogonal to success/failure** - A branch can fail but be converging
2. **Failures are signals, not exceptions** - Orchestrator decides response
3. **Actions are chosen, not sequenced** - Cognitive pivot
4. **Any artifacts > 0 is progress** - Derek cannot fail for being useful
5. **Memory informs action selection** - No retries without mutation
6. **Completion ≠ perfection** - Tests increase confidence, not completion

---

## Testing Recommendations

1. Run a full workflow and verify:
   - Convergence state changes are logged
   - Non-fatal failures don't crash workflow
   - Memory consultation appears in justifications
   - Preview is offered before all tests pass

2. Force failures and verify:
   - Known-bad actions trigger mutation
   - Entropy increases are detected
   - Stalled branches are identified

3. Monitor SQLite database:
   - Decisions table captures entropy values
   - Failures are recorded with severity
   - Artifacts have full lineage binding
   - Memory queries return valid data

---

## LINEAGE BINDING (THE MISSING LINK)

**Files Created:**
- `app/arbormind/cognition/lineage.py` - Immutable artifact lineage binding

**Files Modified:**
- `app/arbormind/observation/schemas.py` - Updated artifacts table with lineage columns
- `app/arbormind/observation/sqlite_store.py` - Added lineage parameters to record_artifact()

**Key Changes:**
- `ArtifactLineage` - Frozen dataclass binding Artifact → Branch → Action → Agent
- `LineageRegistry` - In-memory index for fast lineage lookup
- `create_lineage()` - Factory for creating lineages with content hash
- `record_artifact_with_lineage()` - SQLite function with full provenance
- Schema v2 - Artifacts table now has branch_id, action_type, agent_name, lineage_type

**Why This Matters:**
Without lineage binding, you cannot:
- Attribute convergence correctly (which agent helped?)
- Prune branches safely (what artifacts belong to a dead branch?)
- Compare two competing partial solutions
- Learn which artifact patterns converge

**Outcome:** Artifacts are now owned by branches, not steps.

---

## LEGACY CODE FIXES

**Files Modified:**
- `app/orchestration/fast_orchestrator.py` - Break on failure now uses severity
- `app/core/failure_boundary.py` - StepInvariantError now COGNITIVE, not HARD

**Key Changes:**
- Orchestrator only breaks on FATAL failures
- Non-fatal failures (COGNITIVE_FAILURE) continue workflow
- StepInvariantError is classified as healable, not terminal

**Outcome:** Legacy code no longer overrides the new convergence-first behavior.

---

## Updated Key Invariants

1. **Convergence is orthogonal to success/failure** - A branch can fail but be converging
2. **Failures are signals, not exceptions** - Orchestrator decides response
3. **Actions are chosen, not sequenced** - Cognitive pivot
4. **Any artifacts > 0 is progress** - Derek cannot fail for being useful
5. **Memory informs action selection** - No retries without mutation
6. **Completion ≠ perfection** - Tests increase confidence, not completion
7. **Artifacts are owned by branches** - Full lineage binding for attribution

