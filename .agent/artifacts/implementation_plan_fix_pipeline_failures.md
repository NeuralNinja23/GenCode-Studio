# Implementation Plan: Fix Pipeline Failures

**Created:** 2025-12-10  
**Status:** Ready for approval  
**Estimated Effort:** Medium (2-3 hours)

---

## Executive Summary

The workflow pipeline failed at multiple stages due to **template/generated code mismatches**, **LLM output truncation**, and **quality gate rejections**. This plan addresses the root causes in priority order.

---

## 🔴 A. Pipeline-Stopping Failures (CRITICAL - Fix First)

### A.1 Backend Tests Fail: `init_db` ImportError

**Root Cause:**  
The healing template in `self_healing_manager.py` (lines 189-233) uses:
```python
from app.database import init_db
await init_db()
```

But the generated `database.py` (from Derek in backend_models step) uses:
```python
async def initiate_database():  # ← Different name!
```

**Additionally:** The backend handler prompt (line 561) teaches Derek to use `init_db`, but Derek generated `initiate_database()` - this indicates the prompt instruction was ignored.

**Files to Fix:**
1. `Backend/app/workflow/self_healing_manager.py` - Update template to match what Derek generates
2. `Backend/app/workflow/handlers/backend.py` - Strengthen the example to use explicit function name

**Solution:**
```python
# Option A: Make template dynamic (read function name from database.py)
# Option B: Force Derek to ALWAYS use init_db (add explicit example)
# Option C: Make healing template use initiate_database (matches Derek's natural output)
```

**Recommended:** Option B - Force consistent naming by providing complete database.py example in the prompt

---

### A.2 Frontend Build/Container Fails

**Root Cause:**  
`docker compose up FAILED` repeatedly. Without container logs, likely causes are:
1. Missing dependencies in `package.json`
2. JSX syntax errors in generated components
3. Import errors (missing components or incorrect paths)

**Investigation Required:**
- Check generated `frontend/src/lib/api.js` (was truncated on first attempt)
- Check shadcn components added to `/components/ui/` (policy violation flagged)
- Verify `package.json` dependencies match imports

**Files to Investigate:**
1. `workspaces/clean-modern-todo-app-features/frontend/package.json`
2. `workspaces/clean-modern-todo-app-features/frontend/src/lib/api.js`
3. `workspaces/clean-modern-todo-app-features/frontend/src/pages/Home.jsx`
4. `workspaces/clean-modern-todo-app-features/frontend/src/components/TaskCard.jsx`

**Solution:**
1. Add build validation step BEFORE container startup
2. Improve `frontend_integration.py` handler to validate JSX syntax
3. Add fallback for corrupted api.js (already exists but may need fixing)

---

### A.3 Preview Final Blocked

**Root Cause:** Dependency on testing_backend and testing_frontend - will auto-resolve when A.1 and A.2 are fixed.

**No direct fix needed.**

---

## 🟡 B. Quality Gate Failures (Improve Code Quality)

### B.1 Frontend Mock - Quality 4/10

**Issues Flagged by Marcus:**
1. Placeholder `<h1>` text ("Build a clean, modern todo app")
2. Home embedding TasksPage directly (architectural issue)
3. Missing `data-testid="page-title"`
4. Non-standard Badge variants (`success`, `warning`)
5. Non-functional placeholder callbacks

**Files to Fix:**
1. `Backend/app/workflow/handlers/frontend_mock.py` - Add explicit instructions:
   - NEVER use user request as title
   - Home = dashboard summary, not embed
   - List required data-testid attributes
   - List valid Shadcn Badge variants

**Solution:**
```python
# Add to prompt in frontend_mock.py:
"""
⚠️ CRITICAL UI RULES:
1. Home.jsx is a DASHBOARD - do NOT embed entire pages
2. Page title must be descriptive (e.g., "Task Manager" not "Build a...")
3. REQUIRED data-testid attributes:
   - data-testid="page-root" on main container
   - data-testid="page-title" on <h1>
4. Badge variants: ONLY use "default", "secondary", "destructive", "outline"
"""
```

---

### B.2 Backend Main - Quality 1/10 (Syntax Error)

**Issues:**
- Incomplete function/class definitions (empty body)
- Python SyntaxError at line 24

**Root Cause:** LLM output truncation - the model stopped mid-function.

**Files to Fix:**
1. `Backend/app/workflow/handlers/backend.py` - Add complete main.py example
2. `Backend/app/workflow/self_healing_manager.py` - Template already exists but needs alignment

**Solution:**
- Increase `max_tokens` for backend_main step
- Add `stop_sequences` to prevent truncation
- Make template smarter: read existing routers from filesystem

---

### B.3 Frontend Integration - Quality 7/10

**Issues:**
1. Missing `data-testid="page-root"`
2. Using `app-title` instead of `page-title`
3. Adding files to `/components/ui/` (policy violation)
4. `data-testid="task-list-card"` on wrapper

**Files to Fix:**
1. `Backend/app/workflow/handlers/frontend_integration.py` - Add explicit testid requirements
2. Add post-processing to auto-fix testid issues (use `ui_beautifier.py`)

**Solution:**
```python
# Add to prompt:
"""
⚠️ NEVER modify files in frontend/src/components/ui/
⚠️ REQUIRED data-testid names (exact match):
   - page-root (NOT home-page)
   - page-title (NOT app-title)
"""
```

---

## 🟠 C. LLM Truncation/Integrity Failures (Systemic)

### C.1 Multiple Steps Have "Incomplete function or class definition"

**Affected Steps:**
- Architecture (both attempts)
- Frontend Mock (attempt 1)
- Backend Models (both attempts)
- Backend Main (both attempts)
- Frontend Integration (attempt 1)

**Root Cause:** `llm_output_integrity.py` detects patterns like:
```regex
r"def\s+\w+\([^)]*\)\s*:\s*$"  # Function with no body
r"async\s+def\s+\w+\([^)]*\)\s*:\s*$"  # Async function with no body
```

The LLM is truncating output before completing function bodies.

**Files to Fix:**
1. `Backend/app/agents/gemini_agent.py` (or relevant provider) - Increase max_tokens
2. `Backend/app/workflow/supervision/supervisor.py` - Add token limit awareness
3. All handlers - Add explicit "DO NOT truncate" instructions with stop sequences

**Solution:**
```python
# In gemini_agent.py or equivalent:
generation_config = {
    "max_output_tokens": 12000,  # Increase from current value
    "stop_sequences": ["```\n\n", "<<EOF"],  # Prevent early stops
}
```

---

### C.2 JSON Parse Failures

**Affected:**
- Frontend Integration attempt 1: "Truncated JS file detected: frontend/src/lib/api.js"
- All repair attempts failed, no valid files extracted

**Root Cause:** LLM output JSON contains truncated file content, breaking the JSON structure.

**Files to Fix:**
1. `Backend/app/workflow/engine_v2/json_parser.py` (or equivalent)
2. Add partial file recovery - extract complete files even if some are truncated

**Solution:**
- Improve JSON salvage logic to handle partial files
- Log truncated files but don't reject entire output

---

## 🔵 D. Non-Blocking Improvements

### D.1 Screenshot Capture on Windows

**Current Behavior:** Skipped on Windows, code-based analysis only.

**Files to Fix:**
1. `Backend/app/workflow/handlers/screenshot_verify.py` - Document Windows limitation
2. Add Playwright screenshot as alternative (headless browser)

---

### D.2 Missing Design Tokens

**Issue:** UI review flagged missing design token system.

**Files to Fix:**
1. `Backend/app/workflow/handlers/architecture.py` - Add design tokens generation
2. Create `frontend/src/design/theme.ts` template

---

## 📋 Implementation Order

### Phase 1: Critical Fixes (Stop Pipeline Failures)
| Priority | Task | File(s) | Est. Time |
|----------|------|---------|-----------|
| P0 | Fix `init_db` vs `initiate_database` mismatch | `self_healing_manager.py`, `backend.py` | 15 min |
| P0 | Add build validation before Docker | `testing_frontend.py` | 20 min |
| P0 | Fix frontend api.js fallback | `fallback_api_agent.py` | 10 min |

### Phase 2: Quality Improvements
| Priority | Task | File(s) | Est. Time |
|----------|------|---------|-----------|
| P1 | Add explicit data-testid rules | `frontend_mock.py`, `frontend_integration.py` | 20 min |
| P1 | Fix Badge variant instructions | `frontend_mock.py` | 10 min |
| P1 | Prevent Home from embedding pages | `frontend_mock.py` | 15 min |

### Phase 3: LLM Truncation Prevention
| Priority | Task | File(s) | Est. Time |
|----------|------|---------|-----------|
| P2 | Increase max_tokens for agents | `gemini_agent.py`, handlers | 15 min |
| P2 | Add stop_sequences to prevent truncation | `gemini_agent.py` | 10 min |
| P2 | Improve JSON salvage for partial files | `json_parser.py` | 30 min |

### Phase 4: Polish (Optional)
| Priority | Task | File(s) | Est. Time |
|----------|------|---------|-----------|
| P3 | Add design token generation | `architecture.py` | 30 min |
| P3 | Windows screenshot alternative | `screenshot_verify.py` | 20 min |

---

## Verification Checklist

After implementing fixes, run a new workflow and verify:

- [ ] Backend tests pass (`pytest -q` succeeds)
- [ ] Frontend container starts (`docker compose up` succeeds)
- [ ] Frontend build completes (`npm run build` succeeds)
- [ ] Quality score ≥ 6/10 for all steps
- [ ] No "Incomplete function" integrity errors
- [ ] Preview final step runs

---

## Summary

| Category | Issues | Root Cause | Fix Complexity |
|----------|--------|------------|----------------|
| **A. Critical** | 3 | Template mismatch, build failures | Medium |
| **B. Quality** | 3 | Missing prompt instructions | Easy |
| **C. Truncation** | 5+ | LLM token limits, no stop sequences | Medium |
| **D. Polish** | 2 | Platform limitations | Optional |

**Total Estimated Time:** 2.5 - 3 hours

---

*Approve this plan to begin implementation, or request modifications.*
