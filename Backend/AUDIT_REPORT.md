# GenCode Studio Backend Audit Report

**Audit Date:** December 11, 2025  
**Audit Type:** Comprehensive Read-Only Backend Audit  
**Scope:** All Python code, configuration, dependencies, and tests  
**Auditor:** Antigravity AI  

---

## Executive Summary

| Metric | Status |
|--------|--------|
| **Overall Health** | 🟡 YELLOW |
| **Critical Issues** | 0 |
| **High Severity** | 3 |
| **Medium Severity** | 5 |
| **Low Severity** | 6 |
| **Files Examined** | 135 |

### Top 3 Risks

1. **Version mismatch** between `requirements.txt` and `requirements.lock` - several packages have different versions which could cause dependency conflicts in production
2. **Blocking `os.walk()` calls** in several files can block the async event loop for large projects
3. **In-memory state storage** will be lost on server restart - no persistence layer for critical workflow state

### Positive Findings ✅

- Strong path traversal protection with `resolve()` and `validate_project_id()`
- Good use of `asyncio.Lock` for race condition prevention in workflow state
- Comprehensive budget management with per-step policies
- Layered validation with pre-flight checks before expensive LLM reviews
- Proper deprecation warnings in legacy modules
- All subprocess calls are async (no blocking `subprocess.run`)
- No `eval()` or dangerous `exec()` patterns found

---

## Detailed Findings

### 🔴 High Severity

#### DEP-001: Version Mismatch Between requirements.txt and requirements.lock

| Field | Value |
|-------|-------|
| **Location** | `requirements.txt` vs `requirements.lock` |
| **Type** | Inconsistency |
| **Confidence** | High |

**Description:**  
`requirements.txt` specifies `fastapi==0.115.6` but `requirements.lock` has `fastapi==0.122.0`. Similar mismatches exist for:
- `beanie` (1.27.0 vs 2.0.0)
- `motor` (3.6.0 vs 3.7.1)
- `cryptography` (44.0.0 vs 46.0.1)

**Suggested Fix:**  
Regenerate `requirements.lock` using `pip freeze > requirements.lock` after installing from `requirements.txt`, or update `requirements.txt` to match deployed versions.

---

#### STATE-001: In-Memory Workflow State Not Persisted

| Field | Value |
|-------|-------|
| **Location** | `app/orchestration/state.py:16-20` |
| **Type** | Logic |
| **Confidence** | High |

**Description:**  
Critical workflow state (`_running_workflows`, `_paused_workflows`, `_project_intents`) is stored in global dicts. Server restart loses all state.

```python
# app/orchestration/state.py lines 16-20:
_paused_workflows: Dict[str, Dict[str, Any]] = {}
_project_intents: Dict[str, Dict[str, Any]] = {}
_original_requests: Dict[str, str] = {}
_running_workflows: Dict[str, bool] = {}
_active_managers: Dict[str, Any] = {}
```

**Suggested Fix:**  
Use the existing checkpoint system (`CheckpointManagerV2`) or persist critical state to MongoDB using the existing Beanie setup.

---

#### STATE-002: Deployment State Not Persisted to Database

| Field | Value |
|-------|-------|
| **Location** | `app/api/deployment.py:36-37` |
| **Type** | Logic |
| **Confidence** | High |

**Description:**  
Deployment configurations are stored in `_deployments` dict. Comment says "would be in DB in production". All deployment configs lost on restart.

**Suggested Fix:**  
Create a `Deployment` Beanie model similar to `Project` model and persist to MongoDB.

---

### 🟡 Medium Severity

#### ASYNC-001: Blocking os.walk() in Async Context

| Field | Value |
|-------|-------|
| **Location** | Multiple files |
| **Type** | Performance |
| **Confidence** | High |

**Files Needing Fix:**
- `app/tracking/snapshots.py:42`
- `app/handlers/frontend_integration.py:108`
- `app/agents/sub_agents.py:76`

**Note:** `app/supervision/supervisor.py` already wraps `os.walk` in `asyncio.to_thread()` (line 566) - this is the correct pattern.

**Suggested Fix:**  
Wrap all `os.walk()` calls with `asyncio.to_thread()`:
```python
# Before (blocking):
for root, _, files in os.walk(project_path):
    ...

# After (non-blocking):
def _walk_sync(path):
    return list(os.walk(path))
    
for root, _, files in await asyncio.to_thread(_walk_sync, project_path):
    ...
```

---

#### VALID-001: Project Status Transitions Lack Formal Guards

| Field | Value |
|-------|-------|
| **Location** | `app/models/project.py:13` |
| **Type** | Logic |
| **Confidence** | High |

**Description:**  
`Project.status` has allowed values in a comment but no validation. Status can be set to any string.

```python
# Current:
status: str = "created"  # created, analyzing, building, completed, failed

# Recommended:
from typing import Literal
status: Literal["created", "analyzing", "building", "completed", "failed"] = "created"
```

---

#### ATOMIC-001: Non-Atomic File Operations in Workflow Scaffolding

| Field | Value |
|-------|-------|
| **Location** | `app/workflow/engine.py:282-352` |
| **Type** | Logic |
| **Confidence** | High |

**Description:**  
Scaffolding copies multiple template directories. If any copy fails mid-process, the project is left in an inconsistent state.

**Suggested Fix:**  
Use a temp directory and move atomically after all copies succeed, or implement rollback on failure.

---

#### TEST-001: Test Coverage Limited to Smoke Tests

| Field | Value |
|-------|-------|
| **Location** | `tests/` |
| **Type** | Test |
| **Confidence** | High |

**Description:**  
Only 3 test files with basic smoke/sanity checks. No unit tests for business logic, no integration tests for API endpoints.

**Files to Add:**
- Unit tests for path validation
- Unit tests for workflow state transitions
- Unit tests for budget calculations
- Integration tests for project CRUD
- Integration tests for workflow start/stop

---

### 🟢 Low Severity

| ID | Title | Location |
|----|-------|----------|
| SEC-001 | Encryption key validation mismatch | `app/lib/secrets.py:26-27` |
| LOGIC-001 | Threading Lock in async context | `app/orchestration/budget_manager.py:159` |
| CONFIG-001 | Default model mismatch | `app/core/config.py:18` vs `.env.example:36` |
| PERF-001 | N+1 pattern in project listing | `app/api/projects.py:136-171` |
| DB-001 | MongoDB URI parsing edge cases | `app/db/__init__.py:28` |
| SEC-002 | CORS wildcard warning not enforced | `app/main.py:91-95` |

---

## Correctness Statements

### ✅ Workflow State Management
**Verdict:** CORRECT with caveats

`WorkflowStateManager.try_start_workflow()` uses `asyncio.Lock` to atomically check and set running state (lines 51-70). This prevents race conditions where two requests could both think they started the workflow.

**Caveat:** State is in-memory only. Server restart loses state.

### ✅ Path Traversal Protection
**Verdict:** CORRECT

`get_safe_project_path()` in `app/api/workspace.py` (lines 37-56):
- Validates project_id with regex: `^[a-zA-Z0-9_-]{1,100}$`
- Uses `resolve()` to handle symlink attacks
- Verifies resolved path stays within workspaces_dir

### ✅ Budget Management
**Verdict:** CORRECT

`BudgetManager` tracks usage per step with configurable policies. `allowed_attempts_for_step()` calculates remaining budget and returns 0 if exhausted. Cost estimation uses conservative multipliers (2x-4x).

### ✅ Pre-flight Validation
**Verdict:** CORRECT

`preflight_check()` validates all files before expensive LLM review:
- AST parsing catches Python syntax errors
- Bracket counting catches JS issues
- Auto-fixes are applied for common patterns
- Only valid files proceed to Marcus review

### ✅ WebSocket Connection Management
**Verdict:** CORRECT

`ConnectionManager` uses `asyncio.Lock` for thread-safe connect/disconnect. `send_to_project` takes a snapshot of connections under lock before iterating.

---

## State Machine Analysis

### Project Status

| Transition | Valid |
|------------|-------|
| created → analyzing | ✅ |
| analyzing → building | ✅ |
| building → completed | ✅ |
| building → failed | ✅ |
| any → failed | ✅ (on error) |

**Guards:** ❌ MISSING - status is a plain string with no validation

### Workflow State

| Transition | Valid |
|------------|-------|
| not_started → running | ✅ (try_start_workflow returns True) |
| running → paused | ✅ |
| paused → running | ✅ |
| running → stopped | ✅ |

**Guards:** ✅ PRESENT - `try_start_workflow` uses Lock for atomic check-and-set

---

## Complexity Analysis

| Function | Complexity | Notes |
|----------|------------|-------|
| `list_projects` | O(n log n) + O(n) file reads | Consider pagination |
| `normalize_llm_output` | O(n) | Bounded by `_MAX_PARSING_DEPTH=3` |
| `supervised_agent_call` | O(r × f) | r=retries, f=files. Budget limits prevent unbounded retries |

---

## Prioritized Next Steps

| Priority | Action | Effort | Impact |
|----------|--------|--------|--------|
| 1 | Fix version mismatches in requirements | 15 min | Prevents dependency conflicts |
| 2 | Add `asyncio.to_thread()` to remaining `os.walk()` calls | 30 min | Prevents event loop blocking |
| 3 | Add status enum validation to Project model | 15 min | Prevents invalid status values |
| 4 | Persist deployment state to MongoDB | 1-2 hours | Deploy configs survive restarts |
| 5 | Add unit tests for critical business logic | 4-8 hours | Catches regressions |
| 6 | Implement workflow state persistence | 4-8 hours | Workflows survive restarts |

---

## Items Requiring Environment Access

| Item | Requires | Command |
|------|----------|---------|
| pytest execution | Python env + MongoDB | `cd Backend && pytest tests/ -v --cov=app` |
| Static type checking | mypy | `cd Backend && mypy app/ --ignore-missing-imports` |
| Dependency vulnerability scan | pip-audit | `cd Backend && pip-audit -r requirements.txt` |
| Vault integration | VAULT_URL + VAULT_TOKEN | Manual verification required |

---

## Files Examined

**Total: 135 Python files** across the entire backend codebase:

| Module | Files |
|--------|-------|
| **Core** | `app/main.py`, `app/config.py`, `app/core/config.py`, `app/core/constants.py`, `app/core/exceptions.py`, `app/core/logging.py`, `app/core/types.py` |
| **API Routes** | `app/api/agents.py`, `app/api/deployment.py`, `app/api/health.py`, `app/api/projects.py`, `app/api/providers.py`, `app/api/sandbox.py`, `app/api/tracking.py`, `app/api/workspace.py` |
| **Handlers** | `app/handlers/analysis.py`, `app/handlers/architecture.py`, `app/handlers/backend.py`, `app/handlers/contracts.py`, `app/handlers/frontend_integration.py`, `app/handlers/frontend_mock.py`, `app/handlers/preview.py`, `app/handlers/refine.py`, `app/handlers/screenshot_verify.py`, `app/handlers/testing_backend.py`, `app/handlers/testing_frontend.py` |
| **Orchestration** | `app/orchestration/attention_router.py`, `app/orchestration/budget_manager.py`, `app/orchestration/checkpoint.py`, `app/orchestration/context.py`, `app/orchestration/fast_orchestrator.py`, `app/orchestration/self_healing_manager.py`, `app/orchestration/state.py`, and 11 more |
| **LLM** | `app/llm/adapter.py`, `app/llm/prompts/derek.py`, `app/llm/prompts/luna.py`, `app/llm/prompts/marcus.py`, `app/llm/prompts/victoria.py`, `app/llm/providers/gemini.py`, `app/llm/providers/openai.py`, `app/llm/providers/anthropic.py` |
| **Sandbox** | `app/sandbox/sandbox_manager.py`, `app/sandbox/health_monitor.py`, `app/sandbox/log_streamer.py` |
| **Supervision** | `app/supervision/supervisor.py` |
| **Tools** | `app/tools/implementations.py`, `app/tools/registry.py` |
| **Lib** | `app/lib/file_system.py`, `app/lib/secrets.py`, `app/lib/websocket.py`, `app/lib/patch_engine.py` |
| **Persistence** | `app/persistence/validator.py`, `app/persistence/writer.py` |
| **Utils** | `app/utils/entity_discovery.py`, `app/utils/parser.py` |
| **Validation** | `app/validation/syntax_validator.py` |
| **Testing** | `app/testing/self_healing.py`, `app/testing/parallel.py` |
| **Tracking** | `app/tracking/snapshots.py`, `app/tracking/memory.py` |
| **Models** | `app/models/project.py`, `app/models/snapshot.py`, `app/models/workflow.py` |
| **DB** | `app/db/__init__.py` |
| **Tests** | `tests/conftest.py`, `tests/test_health.py`, `tests/test_smoke.py` |
| **Config** | `.env.example`, `requirements.txt`, `requirements.lock`, `pytest.ini` |

---

*Report generated by Antigravity AI on December 11, 2025*

