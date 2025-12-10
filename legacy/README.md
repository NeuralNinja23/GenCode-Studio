# Legacy Files

This folder contains legacy code that was moved from the main codebase during the refactoring to the new modular architecture.

**Date Archived:** December 5, 2025

## Files Moved

### From `backend/app/agents/`
| File | Size | Description |
|------|------|-------------|
| `workflows.py` | 112 KB | Original monolithic workflow engine with all E1 logic |
| `integration.py` | 13 KB | Old integration layer |
| `integration_playbooks.py` | 2 KB | Integration playbooks |
| `dependency_fixer.py` | 6 KB | Dependency fixing utilities |

### From `backend/app/lib/`
| File | Size | Description |
|------|------|-------------|
| `llm_provider_adapter.py` | 20 KB | Old LLM provider adapter |
| `secrets.py` | 5 KB | Secrets management (unused) |
| `monitoring.py` | 1 KB | Monitoring utilities (unused) |

### From `backend/`
| File | Size | Description |
|------|------|-------------|
| `templates.zip` | 19 KB | Redundant template archive |
| `routes.txt` | 2 KB | Debug file |
| `test_result.txt` | 7 KB | Debug output |

## Why These Were Removed

1. **workflows.py** - Replaced by `app/workflow/engine.py` and handlers in `app/workflow/handlers/`
2. **integration.py / integration_playbooks.py** - Not imported anywhere
3. **dependency_fixer.py** - Not imported anywhere
4. **llm_provider_adapter.py** - Replaced by `app/llm/adapter.py`
5. **secrets.py / monitoring.py** - Unused utility files

## New Architecture

The codebase now uses a modular architecture:

```
app/
├── core/           # Config, constants, types, logging
├── workflow/       # Workflow engine + step handlers
├── llm/            # LLM adapter + providers
├── api/            # API routes
├── tracking/       # Cost/quality tracking
├── persistence/    # File writing
├── sandbox/        # Docker sandbox management
└── testing/        # Self-healing tests
```

## Restoration

If you need to restore any of these files, simply move them back to their original locations.
