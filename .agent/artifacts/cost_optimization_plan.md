# 💰 Cost Optimization Implementation Plan
## Target: ~30 INR (~$0.36 USD) per workflow run

**Current Estimated Cost per Run**: ~80-120 INR (~$1-1.50 USD)
**Target Cost per Run**: ~30 INR (~$0.36 USD)
**Required Reduction**: 60-75%

---

## 📊 Current Cost Analysis

Based on your codebase analysis:

### Token Consumption by Phase
| Phase | Est. Input Tokens | Est. Output Tokens | Est. Cost (Gemini 2.5 Flash) |
|-------|-------------------|--------------------|-----------------------------|
| Analysis | 4,000 | 2,000 | $0.003 |
| Architecture | 8,000 | 6,000 | $0.005 |
| Frontend Mock | 15,000 | 12,000 | $0.010 |
| Screenshot Verify | 5,000 | 2,000 | $0.002 |
| Contracts | 8,000 | 4,000 | $0.004 |
| Backend Models | 10,000 | 8,000 | $0.007 |
| Backend Routers | 12,000 | 10,000 | $0.008 |
| Backend Main | 8,000 | 6,000 | $0.005 |
| Testing Backend | 15,000 | 10,000 | $0.009 |
| Frontend Integration | 12,000 | 10,000 | $0.008 |
| Testing Frontend | 12,000 | 8,000 | $0.007 |
| Preview Final | 3,000 | 1,000 | $0.001 |
| **Marcus Supervision (per step)** | ~4,000 × 12 | ~2,000 × 12 | ~$0.024 |
| **Retries (estimated 3-4)** | ~40,000 | ~25,000 | ~$0.025 |
| **TOTAL** | ~156,000+ | ~110,000+ | **~$0.12-0.15** |

### Cost Drivers (Priority Order)
1. **Marcus Supervision Overhead** - 12 reviews × ~6K tokens = ~72K tokens (~$0.02/run)
2. **Retries from Quality Failures** - 15-25% of tokens wasted on rejected outputs
3. **Verbose Prompts** - Large static prompts sent every call (~50% of input)
4. **Full File Context** - Entire files sent even for small changes
5. **Unused Context** - Contracts/architecture sent when not needed

---

## 🚀 Phase 1: Prompt Optimization (40% Reduction Target)

### 1.1 Compress Agent Prompts (Files: `app/llm/prompts/*.py`)

**Priority: HIGH | Estimated Savings: 20-25%**

| Agent | Current Prompt Size | Target Size | Method |
|-------|---------------------|-------------|--------|
| Derek | ~4,500 tokens | ~2,000 tokens | Remove examples, use bullet points |
| Victoria | ~2,000 tokens | ~800 tokens | Condense architecture rules |
| Luna | ~1,500 tokens | ~700 tokens | Simplify test patterns |
| Marcus | ~3,000 tokens | ~1,200 tokens | Compress review criteria |

**Implementation:**

```python
# NEW: app/llm/prompts/compressed.py

# Instead of verbose prose, use structured minimal format:
DEREK_COMPRESSED = """Role: Derek, Full-Stack Dev
Tech: FastAPI+Beanie, React+shadcn/ui, TailwindCSS v4
Output: JSON {thinking, files: [{path, content}]}

Rules:
- Docker imports: `from app.X` not `from backend.app.X`
- data-testid on all interactive elements
- VITE_API_URL for API calls
- Complete files only, max 5 files
- Max 400 lines per file

Quality: testid✓, imports✓, complete✓"""

# ~300 tokens vs ~4,500 tokens = 93% reduction in prompt size
```

### 1.2 Static Prompt Caching (Files: `app/llm/adapter.py`, `app/llm/prompt_management.py`)

**Priority: HIGH | Estimated Savings: 15-20%**

Gemini supports **prompt caching** - cache the system prompt so it's not re-tokenized every call.

```python
# NEW: app/llm/prompt_cache.py

from typing import Dict, Optional
import hashlib

class PromptCache:
    """Cache static prompts to reduce input tokens."""
    
    # Gemini 1.5+ supports cached context
    _cached_prompts: Dict[str, str] = {}
    _cache_tokens_saved: int = 0
    
    @classmethod
    def get_or_cache(cls, agent: str, prompt: str) -> tuple[str, bool]:
        """
        Returns (prompt, is_cached).
        If cached, we can tell Gemini to use cached_content.
        """
        key = hashlib.md5(f"{agent}:{prompt[:100]}".encode()).hexdigest()
        
        if key in cls._cached_prompts:
            cls._cache_tokens_saved += len(prompt) // 4
            return key, True  # Return cache key
        
        cls._cached_prompts[key] = prompt
        return prompt, False
```

### 1.3 Context Compression for Files (Files: `app/llm/context_optimizer.py`)

Enhance existing differential context with **file summarization**:

```python
# ADD to app/llm/context_optimizer.py

def summarize_file(path: str, content: str, max_lines: int = 20) -> str:
    """
    Create a compressed summary of a file.
    Keep: imports, class/function signatures, core logic
    Remove: docstrings, comments, whitespace
    """
    lines = content.split('\n')
    
    if len(lines) <= max_lines:
        return content
    
    summary_lines = []
    
    for line in lines:
        stripped = line.strip()
        
        # Always keep imports
        if stripped.startswith(('import ', 'from ')):
            summary_lines.append(line)
            continue
            
        # Always keep class/function definitions
        if stripped.startswith(('class ', 'def ', 'async def ')):
            summary_lines.append(line)
            continue
            
        # Keep decorated lines
        if stripped.startswith('@'):
            summary_lines.append(line)
            continue
    
    # Add truncation marker
    summary_lines.append(f"\n# ... {len(lines) - len(summary_lines)} more lines ...")
    
    return '\n'.join(summary_lines)


def build_file_context_compressed(
    files: List[Dict[str, str]], 
    step_name: str,
    max_total_tokens: int = 4000
) -> str:
    """Build compressed file context for a step."""
    
    # Filter to relevant files for this step
    relevant = filter_by_relevance(step_name, files, max_files=5)
    
    context_parts = []
    tokens_used = 0
    
    for file in relevant:
        path = file.get("path", "")
        content = file.get("content", "")
        
        # Summarize large files
        if len(content) > 1000:
            content = summarize_file(path, content, max_lines=30)
        
        file_tokens = len(content) // 4
        
        if tokens_used + file_tokens > max_total_tokens:
            break
            
        context_parts.append(f"### {path}\n```\n{content}\n```")
        tokens_used += file_tokens
    
    return '\n\n'.join(context_parts)
```

---

## 🎯 Phase 2: Supervision Optimization (30% Reduction Target)

### 2.1 Skip Supervision for Low-Risk Steps

**Priority: HIGH | Estimated Savings: 15-20%**

Not all steps need Marcus's review. Pre-flight validation catches most issues.

```python
# MODIFY: app/workflow/supervision/quality_gate.py

# Steps that can skip full LLM supervision
SKIP_SUPERVISION_STEPS = {
    "analysis",           # Output is just analysis, no code
    "architecture",       # Already validated by structural compiler
    "screenshot_verify",  # Visual only, no code
    "preview_final",      # Just showing the app
}

# Steps that need lightweight supervision only
LIGHTWEIGHT_SUPERVISION_STEPS = {
    "contracts",          # Markdown file, pre-flight check is enough
    "backend_main",       # Small file, pre-flight check is enough
}

async def check_quality_gate(
    step_name: str,
    output: Dict,
    project_id: str,
) -> QualityResult:
    """
    3-tier supervision:
    - SKIP: No LLM call, just pre-flight
    - LIGHTWEIGHT: Quick schema check, no full review
    - FULL: Complete Marcus review
    """
    
    # Tier 1: Skip supervision entirely
    if step_name in SKIP_SUPERVISION_STEPS:
        return QualityResult(passed=True, score=8, notes="Auto-approved (skip tier)")
    
    # Tier 2: Lightweight check (schema validation only)
    if step_name in LIGHTWEIGHT_SUPERVISION_STEPS:
        valid = await validate_output_schema(output)
        return QualityResult(
            passed=valid, 
            score=7 if valid else 4, 
            notes="Schema-validated (lightweight tier)"
        )
    
    # Tier 3: Full supervision (existing logic)
    return await marcus_review(output, project_id, step_name)
```

### 2.2 Batch Supervision Calls

Instead of reviewing each step individually, batch review at critical checkpoints:

```python
# NEW: app/workflow/supervision/batch_review.py

BATCH_CHECKPOINTS = {
    "post_frontend": ["frontend_mock", "contracts"],
    "post_backend": ["backend_models", "backend_routers", "backend_main"],
    "post_integration": ["frontend_integration"],
}

async def batch_review(
    checkpoint: str,
    step_outputs: Dict[str, Any],
    project_id: str,
) -> Dict[str, QualityResult]:
    """
    Review multiple steps in a single LLM call.
    
    Instead of:
      - 1 LLM call per step × ~4K tokens = 12K+ tokens
    
    We do:
      - 1 LLM call for 3 steps × ~6K tokens = 6K tokens
      - 50% reduction in supervision tokens
    """
    steps = BATCH_CHECKPOINTS.get(checkpoint, [])
    
    if not steps:
        return {}
    
    # Build combined review prompt
    combined_prompt = f"""
BATCH REVIEW: {checkpoint}
Review all {len(steps)} step outputs and return JSON:
{{
  "step_name": {{"passed": bool, "score": 1-10, "notes": "..."}},
  ...
}}
"""
    
    for step in steps:
        output = step_outputs.get(step, {})
        combined_prompt += f"\n\n=== {step.upper()} ===\n{summarize_output(output)}"
    
    result = await llm_call(combined_prompt, max_tokens=2000)
    return parse_batch_results(result)
```

### 2.3 Conditional Retries with Token Budget

**Priority: MEDIUM | Estimated Savings: 10-15%**

```python
# MODIFY: app/workflow/handlers/*.py

class RetryBudgetManager:
    """Manage retry token budget per workflow."""
    
    def __init__(self, max_retry_tokens: int = 30000):  # ~30K tokens for retries
        self.max_tokens = max_retry_tokens
        self.used_tokens = 0
    
    def can_retry(self, estimated_tokens: int) -> bool:
        return self.used_tokens + estimated_tokens <= self.max_tokens
    
    def record_retry(self, tokens: int):
        self.used_tokens += tokens
    
    @property
    def remaining(self) -> int:
        return self.max_tokens - self.used_tokens


# In step handlers:
async def step_handler_with_budget(project_id: str, budget: RetryBudgetManager, ...):
    """
    Only retry if within token budget.
    Otherwise, accept "good enough" and move on.
    """
    result = await execute_step(...)
    
    if not result.passed:
        retry_cost = estimate_retry_tokens(result)
        
        if budget.can_retry(retry_cost) and result.score >= 5:
            budget.record_retry(retry_cost)
            result = await retry_step(...)
        else:
            # Accept as-is if score >= 5 and no budget
            if result.score >= 5:
                result.passed = True  # Accept with warnings
```

---

## ⚡ Phase 3: Model & Provider Optimization (20% Reduction Target)

### 3.1 Tiered Model Selection

Use cheaper models for simpler tasks:

```python
# NEW: app/llm/model_router.py

MODEL_TIERS = {
    # Tier 1: Complex reasoning (architecture, complex code)
    "premium": {
        "gemini": "gemini-2.0-flash",  # $0.15/$0.60 per 1M
        "openai": "gpt-4o-mini",       # $0.15/$0.60 per 1M
    },
    
    # Tier 2: Standard coding tasks
    "standard": {
        "gemini": "gemini-2.0-flash",  # Same, fast
        "openai": "gpt-4o-mini",
    },
    
    # Tier 3: Simple tasks (formatting, validation)
    "economy": {
        "gemini": "gemini-2.0-flash-lite",  # Hypothetical cheaper tier
        "ollama": "qwen2.5-coder:7b",       # Free (local)
    },
}

STEP_MODEL_TIER = {
    "analysis": "standard",
    "architecture": "premium",
    "frontend_mock": "standard",
    "contracts": "economy",
    "backend_models": "standard",
    "backend_routers": "standard",
    "backend_main": "economy",
    "testing_backend": "standard",
    "frontend_integration": "standard",
    "testing_frontend": "standard",
    "preview_final": "economy",
    
    # Supervision tiers
    "supervision": "economy",        # Most supervision is simple
    "supervision_critical": "standard",  # Only for critical reviews
}

def get_model_for_step(step: str, provider: str) -> str:
    tier = STEP_MODEL_TIER.get(step, "standard")
    return MODEL_TIERS[tier].get(provider, MODEL_TIERS["standard"][provider])
```

### 3.2 Local Model for Cheap Tasks

Use Ollama for tasks that don't need cloud models:

```python
# Steps that can use local Ollama
LOCAL_SAFE_STEPS = {
    "contracts",        # Markdown generation
    "supervision",      # Simple review
    "backend_main",     # Boilerplate code
    "preview_final",    # Just status
}

async def call_with_fallback(step: str, prompt: str, ...):
    """Try local first for cheap tasks, fall back to cloud if needed."""
    
    if step in LOCAL_SAFE_STEPS:
        try:
            result = await ollama.call(prompt, model="qwen2.5-coder:7b", ...)
            return result  # Free!
        except Exception:
            pass  # Fall through to cloud
    
    # Cloud fallback
    return await gemini.call(prompt, ...)
```

---

## 📋 Phase 4: Workflow Optimization (10% Reduction Target)

### 4.1 Step Consolidation

Combine related steps to reduce LLM calls:

```python
# CURRENT: 12 steps = 12+ LLM calls
# OPTIMIZED: 8 steps = 8 LLM calls

CONSOLIDATED_STEPS = {
    # Combine backend steps
    "backend_full": ["backend_models", "backend_routers", "backend_main"],
    
    # Combine testing
    "testing_full": ["testing_backend", "testing_frontend"],
}

# Derek generates all backend files in ONE call instead of 3
async def step_backend_full(...):
    """
    Single call generates:
    - models.py
    - routers/*.py  
    - main.py
    
    Saves: 2 LLM calls × ~15K tokens = 30K tokens (~$0.02)
    """
```

### 4.2 Aggressive Context Filtering

Only send what's needed per step:

```python
# MODIFY: app/llm/prompt_management.py

STEP_CONTEXT_NEEDS = {
    "frontend_mock": {
        "needs_architecture": True,
        "needs_contracts": False,
        "needs_files": ["src/"],
        "max_file_tokens": 2000,
    },
    "backend_routers": {
        "needs_architecture": False,
        "needs_contracts": True,
        "needs_files": ["models.py", "schemas.py"],
        "max_file_tokens": 1500,
    },
    "frontend_integration": {
        "needs_architecture": False,
        "needs_contracts": True,
        "needs_files": ["src/lib/api.js", "src/pages/"],
        "max_file_tokens": 2000,
    },
}

def build_minimal_context(step: str, project_state: Dict) -> str:
    """Build the absolute minimum context for a step."""
    needs = STEP_CONTEXT_NEEDS.get(step, {})
    parts = []
    
    if needs.get("needs_architecture"):
        # Only first 500 chars
        parts.append(project_state["architecture"][:500])
    
    if needs.get("needs_contracts"):
        # Only endpoint list, not full spec
        parts.append(extract_endpoint_list(project_state["contracts"]))
    
    # Only relevant files, summarized
    if needs.get("needs_files"):
        files = filter_files(project_state["files"], needs["needs_files"])
        parts.append(build_file_context_compressed(
            files, step, needs.get("max_file_tokens", 2000)
        ))
    
    return "\n\n".join(parts)
```

---

## 💰 Projected Savings Summary

| Optimization | Token Reduction | Cost Savings |
|--------------|-----------------|--------------|
| **Phase 1: Prompt Optimization** | | |
| - Compressed prompts | ~50K tokens | ~$0.02 |
| - Static prompt caching | ~30K tokens | ~$0.01 |
| - File summarization | ~20K tokens | ~$0.008 |
| **Phase 2: Supervision** | | |
| - Skip low-risk reviews | ~30K tokens | ~$0.01 |
| - Batch reviews | ~15K tokens | ~$0.005 |
| - Token-budgeted retries | ~20K tokens | ~$0.008 |
| **Phase 3: Model Selection** | | |
| - Tiered models | Variable | ~$0.01 |
| - Local model for cheap tasks | ~30K tokens | ~$0.012 (free) |
| **Phase 4: Workflow** | | |
| - Step consolidation | ~30K tokens | ~$0.01 |
| - Aggressive filtering | ~15K tokens | ~$0.006 |
| **TOTAL SAVINGS** | ~240K tokens | **~$0.09** |
| **ORIGINAL COST** | ~266K tokens | ~$0.12-0.15 |
| **NEW COST** | ~100K tokens | **~$0.03-0.04** |
| **INR EQUIVALENT** | | **₹25-33 INR** ✅ |

---

## 🗂️ Implementation Roadmap

### Week 1: Quick Wins (Phase 1)
- [ ] Compress agent prompts (50% size reduction)
- [ ] Implement file summarization
- [ ] Add step-based context filtering

### Week 2: Supervision Overhaul (Phase 2)
- [ ] Add skip-supervision for safe steps
- [ ] Implement batch reviews
- [ ] Add retry budget manager

### Week 3: Model Routing (Phase 3)
- [ ] Implement model tier routing
- [ ] Add Ollama fallback for cheap tasks
- [ ] Test local model quality

### Week 4: Workflow Optimization (Phase 4)
- [ ] Consolidate backend steps
- [ ] Consolidate testing steps
- [ ] Final testing and validation

---

## 📊 Monitoring & Validation

Add cost tracking dashboard to verify savings:

```python
# ENHANCE: app/tracking/cost.py

async def log_run_cost(project_id: str):
    """Log final cost breakdown for analysis."""
    summary = get_cost_summary(project_id)
    
    print(f"""
    ═══════════════════════════════════════
    💰 COST REPORT: {project_id}
    ═══════════════════════════════════════
    Total Input Tokens:  {summary['total_input_tokens']:,}
    Total Output Tokens: {summary['total_output_tokens']:,}
    
    Estimated Cost (USD): ${summary['total_estimated_cost']:.4f}
    Estimated Cost (INR): ₹{summary['total_estimated_cost'] * 84:.2f}
    
    By Step:
    {format_step_breakdown(summary['by_step'])}
    
    Retry Waste:
    {format_retry_waste(summary['detailed_calls'])}
    ═══════════════════════════════════════
    """)
```

---

## ✅ Success Criteria

1. **Average cost per run**: ≤ ₹30 INR ($0.36 USD)
2. **Token usage per run**: ≤ 120K total tokens
3. **Quality maintained**: Average Marcus score ≥ 7.0
4. **No increase in failure rate**: ≤ 10% retry rate

---

*Created: December 9, 2025*
*Target: 30 INR per workflow run*
