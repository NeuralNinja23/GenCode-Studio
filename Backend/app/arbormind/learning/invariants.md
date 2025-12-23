# ArborMind Learning Invariants

## Mandatory Rules (Non-Negotiable)

### 1. Temporal Separation
**Learning MUST NOT run inside execution.**

- ✅ Learning is a batch job or background task
- ✅ Learning runs after execution completes
- ❌ Learning MUST NOT be called from handlers
- ❌ Learning MUST NOT be called from runtime.cycle()

### 2. Zero Pollution
**Handlers MUST NOT read from learning.**

- ✅ Handlers read from `priors/` (optional, gated)
- ❌ Handlers MUST NOT import from `learning/`
- ❌ Handlers MUST NOT read from ledger files directly
- ✅ Priors are static configuration, not live queries

### 3. Non-Prescriptive Authority
**Learning MAY NOT override decisions.**

- ✅ Learning computes statistics
- ✅ Learning updates priors (weights, biases)
- ❌ Learning MUST NOT force tool selection
- ❌ Learning MUST NOT block execution paths

### 4. Prior Influence Only
**Learning MAY ONLY influence priors.**

- ✅ Example: `tool_success_rate` updates `ToolPriors.weights`
- ✅ Priors are multipliers (e.g., `score * prior`)
- ❌ Priors MUST NOT change from 0.5 to 0.0 (no total blocks)
- ❌ Priors range: `[0.2, 2.0]` (max 5x boost/penalty)

### 5. Append-Only Logs
**Observations are append-only.**

- ✅ Observer appends events to ledger
- ❌ Observer MUST NOT modify existing events
- ❌ Observer MUST NOT delete events
- ✅ Ledger corruption MUST NOT crash execution

### 6. Deletion Safety
**Deleting the ledger must not change behavior.**

- ✅ If ledger is missing, system uses default priors
- ✅ Ledger is observational, not operational
- ❌ System MUST NOT depend on ledger for correctness

---

## Enforcement

### Code Review Checklist
Before merging any PR:

- [ ] No `from app.arbormind.learning import` in `handlers/`
- [ ] No `from app.arbormind.learning import` in `runtime/`
- [ ] Learning functions have `# OFFLINE ONLY` comment
- [ ] Observer is fail-safe (try/except, doesn't halt execution)

### Test Coverage
Add these tests:

```python
def test_learning_not_imported_by_handlers():
    """Ensure handlers don't import learning layer."""
    handler_files = Path("app/handlers").glob("*.py")
    for f in handler_files:
        content = f.read_text()
        assert "from app.arbormind.learning" not in content

def test_observer_failure_doesnt_halt_execution():
    """Observer exceptions must be caught silently."""
    # Mock ledger that raises
    # Verify execution continues
    pass

def test_ledger_deletion_safe():
    """Deleting ledger doesn't break system."""
    # Delete ledger file
    # Run workflow
    # Assert workflow completes successfully
    pass
```

---

## Violation Response

**If any invariant is violated:**

1. Immediate rollback of changes
2. Review architectural assumptions
3. Consider if the feature belongs in `cognition/` instead
4. Document why the invariant was challenged

**No exceptions.** These invariants protect ArborMind from cognitive collapse.
