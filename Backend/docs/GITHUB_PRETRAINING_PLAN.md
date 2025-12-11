# GitHub Pre-Training System for Self-Evolving Agents

**Author:** GenCode AI Team  
**Status:** Planning  
**Created:** 2024-12-12  
**Related:** `ATTENTION_SYSTEM.md`, `app/learning/`, `app/attention/`

---

## Executive Summary

This document outlines the plan to **pre-train the GenCode self-evolving agent system** using public GitHub repositories as a training database. Instead of starting with zero knowledge (cold start), the system will be seeded with patterns extracted from millions of real-world code examples.

---

## 1. The Problem: Cold Start

### Current State
The self-evolution system (`v_vector_store.py`, `evolution.py`) learns from:
- Routing decisions → Outcomes (success/failure)
- Quality scores → EMA-adjusted V-vectors

### The Issue
- **Day 1:** Zero training data
- **Week 1:** Maybe 10-50 data points
- **Month 1:** Still not enough for reliable patterns

The system needs **hundreds of examples per context type** before evolution becomes meaningful.

### The Solution
Mine GitHub for pre-existing patterns that represent "what works" in the real world.

---

## 2. What GitHub Can Teach

| Data Source | Extraction Method | Target Store | Learning Signal |
|:------------|:------------------|:-------------|:----------------|
| Repo file structure | Tree analysis | V-Vector Store | File context width per archetype |
| Commit messages | Regex + NLP | Pattern/Failure Store | Fix patterns + sizes |
| Commit diffs | Diff parsing | V-Vector Store | `max_edits` calibration |
| Issues → PRs | Link analysis | Pattern Store | Error → Solution mappings |
| Star counts | API | V-Vector Store | Quality/confidence signals |
| README content | NLP classification | V-Vector Store | Archetype identification |
| package.json | JSON parsing | V-Vector Store | Tool selection patterns |
| Error logs in issues | Regex extraction | Failure Store | Anti-patterns |

---

## 3. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     GITHUB PRE-TRAINING PIPELINE                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌───────────────────┐     ┌───────────────────┐     ┌──────────────────┐  │
│   │   GitHub API      │────▶│   Repo Analyzer   │────▶│  Pattern        │  │
│   │   + Search        │     │   (per category)   │     │  Extractor      │  │
│   └───────────────────┘     └───────────────────┘     └────────┬─────────┘  │
│                                                                 │           │
│                                                                 ▼           │
│   ┌───────────────────┐     ┌───────────────────┐     ┌──────────────────┐  │
│   │   Curated Repo    │────▶│   Commit Miner    │────▶│  Fix Pattern    │  │
│   │   List            │     │   (diffs + msgs)   │     │  Extractor      │  │
│   └───────────────────┘     └───────────────────┘     └────────┬─────────┘  │
│                                                                 │           │
│                                                                 ▼           │
│                                                        ┌──────────────────┐ │
│                                                        │  Training Data   │ │
│                                                        │  Transformer     │ │
│                                                        └────────┬─────────┘ │
│                                                                 │           │
│                 ┌───────────────────────────────────────────────┼───────┐   │
│                 ▼                       ▼                       ▼       │   │
│   ┌──────────────────────┐  ┌──────────────────────┐  ┌────────────────┐│   │
│   │   v_vector_history   │  │   pattern_memory     │  │ failure_memory ││   │
│   │   .db                │  │   .db                │  │ .db            ││   │
│   └──────────────────────┘  └──────────────────────┘  └────────────────┘│   │
│                                                                         │   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Data Sources & Extraction Strategy

### 4.1 Curated High-Quality Repos

**Purpose:** Extract patterns from known-excellent codebases.

```python
CURATED_REPOS = {
    "backend_patterns": [
        "tiangolo/fastapi",           # FastAPI patterns
        "encode/starlette",           # ASGI patterns
        "pydantic/pydantic",          # Validation patterns
        "mongodb/motor",              # MongoDB async patterns
    ],
    "frontend_patterns": [
        "shadcn-ui/ui",               # Component patterns
        "vercel/next.js",             # React/Next patterns
        "vitejs/vite",                # Build tool patterns
        "tailwindlabs/tailwindcss",   # Styling patterns
    ],
    "fullstack_patterns": [
        "reflex-dev/reflex",          # Full-stack Python
        "zauberzeug/nicegui",         # Python UI
        "streamlit/streamlit",        # Data apps
    ],
    "admin_dashboards": [
        "marmelab/react-admin",       # Admin UI patterns
        "refinedev/refine",           # Admin framework
    ],
}
```

**Extract:**
- File structure conventions
- Naming patterns
- Module organization
- Configuration defaults

### 4.2 GitHub Search API Mining

**Purpose:** Find repos matching specific archetypes.

```python
SEARCH_QUERIES = {
    "admin_dashboard": 'topic:admin-dashboard language:python stars:>50',
    "crud_api": 'topic:fastapi topic:crud stars:>20',
    "saas_app": 'topic:saas topic:python stars:>100',
    "ecommerce": 'topic:ecommerce language:javascript stars:>50',
    "portfolio": 'topic:portfolio topic:react stars:>30',
}
```

**Extract:**
- Common file patterns per archetype
- Average file counts
- Technology combinations

### 4.3 Commit History Mining

**Purpose:** Learn what fixes look like.

```python
COMMIT_PATTERNS = {
    "syntax_fix": [
        r"fix:\s*syntax",
        r"fix:\s*indentation",
        r"fix:\s*typo",
    ],
    "dependency_fix": [
        r"fix:\s*import",
        r"add:\s*dependency",
        r"update:\s*requirements",
    ],
    "logic_fix": [
        r"fix:\s*bug",
        r"fix:\s*logic",
        r"fix:\s*behavior",
    ],
}
```

**Extract:**
- Average diff size per fix type → `max_edits`
- File count per fix → context width
- Success patterns (merged PRs)

### 4.4 Issue → PR Link Mining

**Purpose:** Learn error-to-solution mappings.

```
Issue: "TypeError: undefined is not a function"
  └── Linked PR: "Fix: use optional chaining"
      └── Files changed: 2
      └── Lines changed: +5, -3
      
→ Pattern: TypeError + undefined → check for optional chaining
→ V-Vector: {max_edits: 2, apply_diff: true}
```

---

## 5. Data Transformation

### 5.1 File Structure → FILE_CONTEXT_MODES

```python
# From repo analysis:
admin_dashboard_repos = analyze_repos("admin_dashboard")

# Average file counts:
# - backend: 15 files
# - frontend: 25 files
# - total: 40 files

# Transform to V-vector:
{
    "context_type": "file_context",
    "archetype": "admin_dashboard",
    "option": "broad",
    "evolved_value": {
        "max_files": 15,
        "use_summaries": False,
        "include_tests": True
    },
    "confidence": 0.85,
    "sample_count": 150  # From 150 repos
}
```

### 5.2 Commits → REPAIR_STRATEGIES

```python
# From commit mining:
syntax_fix_commits = mine_commits("syntax_fix")

# Average diff size: 2.3 lines
# Median diff size: 1 line
# Success rate: 95% (merged)

# Transform to V-vector:
{
    "context_type": "repair_strategy",
    "archetype": "*",  # Universal
    "option": "syntax_fix",
    "evolved_value": {
        "max_edits": 2,
        "apply_diff": True,
        "verify_after_fix": True
    },
    "confidence": 0.95,
    "sample_count": 5000
}
```

### 5.3 Issues → FAILURE_PATTERNS

```python
# From issue mining:
common_errors = extract_error_patterns(issues)

# "ModuleNotFoundError: No module named 'X'"
# Fix: pip install X
# Occurrence: 2500 times

# Transform to Failure Store entry:
{
    "archetype": "*",
    "agent": "repair_strategy",
    "step": "syntax_fix",  # WRONG strategy for this
    "error_type": "strategy_mismatch",
    "description": "ModuleNotFoundError should use dependency_fix, not syntax_fix",
    "occurrence_count": 2500
}
```

---

## 6. Implementation Plan

### Phase 1: Infrastructure (Week 1)

| Task | File | Description |
|:-----|:-----|:------------|
| 1.1 | `app/pretraining/__init__.py` | New module |
| 1.2 | `app/pretraining/github_client.py` | GitHub API wrapper with rate limiting |
| 1.3 | `app/pretraining/repo_analyzer.py` | Analyze repo structure |
| 1.4 | `app/pretraining/commit_miner.py` | Extract commit patterns |
| 1.5 | `app/pretraining/data_transformer.py` | Convert to training data |

### Phase 2: Curated Mining (Week 2)

| Task | Description |
|:-----|:------------|
| 2.1 | Mine curated repos (listed above) |
| 2.2 | Extract file structure patterns |
| 2.3 | Extract commit size distributions |
| 2.4 | Generate initial V-vector seeds |

### Phase 3: Search Mining (Week 3)

| Task | Description |
|:-----|:------------|
| 3.1 | Search for archetype-specific repos |
| 3.2 | Filter by quality (stars, activity) |
| 3.3 | Extract archetype-specific patterns |
| 3.4 | Generate per-archetype V-vectors |

### Phase 4: Commit Mining (Week 4)

| Task | Description |
|:-----|:------------|
| 4.1 | Mine commits from quality repos |
| 4.2 | Classify by fix type (regex + LLM) |
| 4.3 | Extract diff statistics |
| 4.4 | Generate repair strategy V-vectors |

### Phase 5: Issue Mining (Week 5)

| Task | Description |
|:-----|:------------|
| 5.1 | Extract closed issues with linked PRs |
| 5.2 | Parse error patterns from issue bodies |
| 5.3 | Match errors to solutions |
| 5.4 | Generate Pattern + Failure store entries |

### Phase 6: Integration (Week 6)

| Task | Description |
|:-----|:------------|
| 6.1 | Add `seed_from_github()` to VVectorStore |
| 6.2 | Add bulk import to PatternStore |
| 6.3 | Add bulk import to FailureStore |
| 6.4 | Create one-time seeding script |
| 6.5 | Create nightly refresh job (optional) |

---

## 7. File Structure

```
Backend/
├── app/
│   ├── pretraining/
│   │   ├── __init__.py
│   │   ├── github_client.py      # GitHub API with caching + rate limiting
│   │   ├── repo_analyzer.py      # Analyze repo structure
│   │   ├── commit_miner.py       # Mine commit history
│   │   ├── issue_miner.py        # Mine issues + PRs
│   │   ├── pattern_extractor.py  # Extract patterns from raw data
│   │   ├── data_transformer.py   # Transform to training format
│   │   └── seeder.py             # Seed learning databases
│   │
│   └── learning/
│       ├── v_vector_store.py     # Add: seed_from_github()
│       ├── pattern_store.py      # Add: bulk_import()
│       └── failure_store.py      # Add: bulk_import()
│
├── data/
│   └── pretraining/
│       ├── curated_repos.json    # Curated repo list
│       ├── search_queries.json   # GitHub search queries
│       ├── commit_patterns.json  # Regex patterns for commits
│       └── cache/                # Cached GitHub responses
│
├── scripts/
│   ├── pretrain_from_github.py   # One-time full pretraining
│   └── refresh_pretraining.py    # Nightly incremental refresh
│
└── docs/
    └── GITHUB_PRETRAINING_PLAN.md  # This document
```

---

## 8. API Rate Limits & Caching

### GitHub API Limits
- Unauthenticated: 60 requests/hour
- Authenticated: 5,000 requests/hour
- Search API: 30 requests/minute

### Caching Strategy
```python
# Cache all API responses
CACHE_CONFIG = {
    "repo_structure": "7 days",      # Repos don't change often
    "commit_history": "1 day",       # Commits are append-only
    "issues": "1 day",               # Issues change more
    "search_results": "12 hours",    # Rankings change
}
```

### Rate Limit Handling
```python
async def github_request(url):
    await rate_limiter.acquire()  # Wait if needed
    response = await http.get(url)
    if response.status == 403:
        await asyncio.sleep(response.headers["X-RateLimit-Reset"])
    return response
```

---

## 9. Quality Filters

### Repo Quality Criteria
```python
QUALITY_THRESHOLDS = {
    "min_stars": 20,              # Some popularity
    "min_commits": 50,            # Active development
    "max_days_since_update": 365, # Not abandoned
    "has_readme": True,           # Documented
    "has_license": True,          # Proper OSS
}
```

### Commit Quality Criteria
```python
COMMIT_FILTERS = {
    "exclude_merge_commits": True,
    "exclude_bot_commits": True,
    "min_diff_lines": 1,
    "max_diff_lines": 500,        # Skip huge refactors
    "require_message_pattern": True,
}
```

---

## 10. Expected Outcomes

### Data Volume Targets

| Store | Target Entries | Source |
|:------|:---------------|:-------|
| V-Vector Store | 500+ evolved vectors | Curated + Search |
| Pattern Store | 1,000+ success patterns | Commits + PRs |
| Failure Store | 500+ anti-patterns | Issues + failed commits |

### Coverage Targets

| Archetype | Target Confidence |
|:----------|:------------------|
| admin_dashboard | 85%+ (many examples) |
| crud_api | 90%+ (very common) |
| saas_app | 70%+ (varied) |
| ecommerce | 75%+ (common patterns) |
| portfolio | 80%+ (simple structure) |

---

## 11. Risks & Mitigations

| Risk | Impact | Mitigation |
|:-----|:-------|:-----------|
| API rate limits | Slow extraction | Aggressive caching + auth token |
| Low-quality repos in search | Bad training data | Quality filters + star threshold |
| Outdated patterns | Wrong patterns | Filter by last update date |
| License issues | Legal risk | Only use MIT/Apache licensed repos |
| Pattern extraction errors | Corrupt data | Validate before inserting |

---

## 12. Success Criteria

### Phase 1 Success
- [ ] Can fetch repos from GitHub API
- [ ] Can cache responses
- [ ] Rate limiting works

### Phase 2 Success
- [ ] Extracted patterns from 50+ curated repos
- [ ] Generated 100+ initial V-vectors

### Full Success
- [ ] 500+ V-vectors seeded
- [ ] System performs better on Day 1 than cold start
- [ ] Patterns match real-world usage

---

## 13. Future Extensions

1. **Continuous Learning:** Nightly job to fetch new patterns
2. **User Repo Mining:** Let users opt-in their private repos
3. **Stack Overflow Mining:** Extract error patterns from SO
4. **LLM Classification:** Use GPT to classify commits more accurately
5. **Cross-Language Learning:** Extract patterns from non-Python repos

---

## Appendix A: Sample Training Data

### V-Vector Entry
```json
{
  "context_type": "repair_strategy",
  "archetype": "crud_api",
  "option": "dependency_fix",
  "evolved_value": {
    "max_edits": 1,
    "apply_diff": false,
    "verify_after_fix": true,
    "retry_on_fail": 1
  },
  "confidence": 0.88,
  "sample_count": 342,
  "source": "github:commit_mining",
  "source_repos": ["tiangolo/fastapi", "encode/starlette"]
}
```

### Pattern Entry
```json
{
  "archetype": "admin_dashboard",
  "agent": "backend_implementation",
  "step": "router_creation",
  "quality_score": 9.2,
  "pattern": {
    "file_pattern": "app/routers/{entity}.py",
    "imports": ["fastapi", "beanie"],
    "structure": "CRUD endpoints with dependency injection"
  },
  "source": "github:repo_analysis",
  "sample_count": 89
}
```

### Failure Entry
```json
{
  "archetype": "*",
  "agent": "repair_strategy",
  "step": "syntax_fix",
  "error_type": "strategy_mismatch",
  "description": "Using syntax_fix for ModuleNotFoundError always fails. Use dependency_fix instead.",
  "occurrence_count": 156,
  "source": "github:issue_mining"
}
```

---

**Document End**
