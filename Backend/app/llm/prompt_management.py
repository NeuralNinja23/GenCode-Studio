# app/llm/prompt_management.py
"""
PHASE 1: Prompt Management System
Split prompts into Core (static, cacheable) + Context (dynamic, minimal)
Target: 30-40% token reduction
"""
from typing import Dict, List, Optional, Any
from pathlib import Path


# ============================================================
# CORE PROMPT COMPONENTS (Static - Send Once, Cache)
# ============================================================

CORE_RULES = {
    "victoria": """You are Victoria, Senior Solutions Architect.

ROLE: Design scalable, clean, maintainable architectures.

OUTPUT FORMAT:
- architecture.md ONLY (system design + UI design system)
⚠️ DO NOT generate contracts.md - Marcus creates that in Step 5 after frontend mock!

CRITICAL RULES:
1. Archetype-aware design (admin_dashboard, saas_app, etc.)
2. Vibe-aligned UI tokens (dark_hacker, minimal_light, etc.)
3. Complete UI Design System in architecture.md
4. MongoDB + Beanie ODM patterns
5. React + shadcn/ui (New York v4)

QUALITY FOCUS:
- Completeness (8pts)
- Archetype alignment (1pt)
- Specificity (1pt)

Keep response under 12K tokens.""",

    "derek": """You are Derek, Senior Full-Stack Developer.

ROLE: Implement clean, working code following architecture.

TECH STACK:
- Frontend: React 18, Vite, shadcn/ui, TailwindCSS
- Backend: FastAPI, Beanie ODM, MongoDB
- Testing: pytest, Playwright

CRITICAL RULES:
1. Docker imports: Use `app.X` NOT `backend.app.X`
2. data-testid on all interactive elements
3. VITE_API_URL for API calls
4. Field(default_factory=list) for mutable defaults
5. model_dump() not .dict()

QUALITY FOCUS:
- Code correctness (3pts)
- Archetype alignment (2pts)
- testid compliance (2pts)
- UI design system (2pts)
- Completeness (1pt)

Keep response under 10K tokens.""",

    "luna": """You are Luna, QA and DevOps Engineer.

ROLE: Test applications with Playwright E2E tests.

FOCUS: Functional testing (not visual QA - Marcus handles that).

CRITICAL RULES:
1. Use data-testid selectors
2. API-independent tests (works in Docker)
3. Archetype-specific patterns
4. Frontend port: 5174
5. Smoke tests for all pages

QUALITY FOCUS:
- Coverage (4pts)
- Selector quality (2pts)
- Reliability (2pts)
- Edge cases (1pt)
- Archetype alignment (1pt)

Keep response under 8K tokens.""",

    "marcus": """You are Marcus, Lead AI Architect & Supervisor.

ROLE: Review code quality, ensure standards, orchestrate team.

3-LAYER QUALITY GATES:
1. Pre-flight validation (auto-fix syntax)
2. Tiered review (FULL/LIGHTWEIGHT/PREFLIGHT_ONLY)
3. LLM supervision (you)

REVIEW LEVELS:
- FULL: routers, models, main.py, App.jsx
- LIGHTWEIGHT: components, pages, utils
- PREFLIGHT_ONLY: configs, mocks

QUALITY SCORING:
- 8-10: Approve
- 6-7: Approve with notes
- 4-5: Request revision
- 1-3: Reject

Keep response under 4K tokens.""",
}


# ============================================================
# CONTEXT TEMPLATES (Dynamic - Minimal size)
# ============================================================

def build_context(
    agent_name: str,
    task: str,
    step_name: str,
    archetype: Optional[str] = None,
    vibe: Optional[str] = None,
    files: Optional[List[Dict[str, str]]] = None,
    contracts: Optional[str] = None,
    errors: Optional[List[str]] = None,
    memory_hint: Optional[str] = None,
) -> str:
    """
    Build minimal dynamic context for agent calls.
    Only include what's needed for THIS specific task.
    """
    context_parts = [f"TASK: {task}"]
    
    if archetype:
        context_parts.append(f"ARCHETYPE: {archetype}")
    
    if vibe:
        context_parts.append(f"UI_VIBE: {vibe}")
    
    if contracts:
        # Send summary, not full contracts
        contracts_summary = contracts[:500] + "..." if len(contracts) > 500 else contracts
        context_parts.append(f"CONTRACTS:\n{contracts_summary}")
    
    if files:
        # CRITICAL FIX: Send actual file content, not just paths!
        file_content = build_file_context(files, use_summaries=True)
        if file_content:
            context_parts.append(f"PROJECT FILES:\n{file_content}")
    
    if errors:
        # DYNAMIC ERROR FILTERING: Only include actionable CODE issues
        # Code issues reference: file paths, line numbers, specific code patterns
        # Feature requests typically don't reference specific files/code
        
        # Get file paths from context for matching
        file_paths = [f.get("path", "").lower() for f in (files or [])]
        
        actionable_errors = []
        for error in errors[:5]:
            error_lower = error.lower()
            
            # Is this a CODE issue? (references specific code or files)
            is_code_issue = any([
                any(path and path in error_lower for path in file_paths),  # Mentions output file
                "line " in error_lower,  # References line number
                "import" in error_lower,  # Import issues
                "syntax" in error_lower,  # Syntax error
                "async def" in error_lower or "def " in error_lower,  # Function issues
                "class " in error_lower,  # Class issues
                "missing `" in error_lower or "should be `" in error_lower,  # Specific fixes
                ".py" in error_lower or ".jsx" in error_lower,  # File references
            ])
            
            if is_code_issue:
                actionable_errors.append(error)
        
        # Use filtered errors, or fallback to first error if none matched
        errors_to_show = actionable_errors if actionable_errors else errors[:1]
        error_list = "\n".join([f"{i+1}. {e}" for i, e in enumerate(errors_to_show)])
        
        context_parts.append(f"""FIX THESE CODE ISSUES:
{error_list}

⚠️ IMPORTANT: Fix ONLY the issues listed above.
- Do NOT change your overall approach or architecture
- Do NOT add features beyond what's required
- Keep the same file structure
- Just fix the specific code problems mentioned""")
    
    if memory_hint:
        context_parts.append(f"MEMORY_HINT: {memory_hint[:300]}")
    
    return "\n\n".join(context_parts)


# ============================================================
# STEP-AWARE CONTEXT ROUTING
# ============================================================

STEP_CONTEXT_RULES = {
    "analysis": {
        "files": [],  # Only user request
        "include_contracts": False,
        "include_architecture": False,
    },
    "architecture": {
        "files": [],  # Design only
        "include_contracts": False,
        "include_architecture": False,
    },
    "frontend_mock": {
        "files": ["frontend/**/*.jsx", "frontend/**/*.js", "frontend/**/*.css"],
        "include_contracts": False,
        "include_architecture": True,
    },
    "backend_implementation": {
        "files": ["backend/app/models.py", "backend/app/routers/*.py", "backend/app/database.py"],
        "include_contracts": True,
        "include_architecture": True,
    },
    "system_integration": {
        "files": ["backend/app/main.py", "backend/app/routers/*.py"],
        "include_contracts": False,
        "include_architecture": False,
    },
    "frontend_integration": {
        "files": ["frontend/src/**/*.jsx", "frontend/src/lib/api.js"],
        "include_contracts": True,
        "include_architecture": False,
    },
    "testing_backend": {
        "files": ["backend/tests/*.py", "backend/app/**/*.py", "tests/conftest.py"],
        "include_contracts": False,
        "include_architecture": False,
    },
    "testing_frontend": {
        "files": ["frontend/tests/*.js", "frontend/src/**/*.jsx"],
        "include_contracts": False,
        "include_architecture": False,
    },
    # Issue #4 Fix: Add rules for test diagnosis steps
    "backend_test_diagnosis": {
        "files": ["backend/tests/*.py", "backend/app/**/*.py", "tests/conftest.py", "backend/app/models.py", "backend/app/routers/*.py"],
        "include_contracts": False,
        "include_architecture": False,
    },
    "backend_testing_fix": {
        "files": ["backend/tests/*.py", "backend/app/**/*.py", "tests/conftest.py", "backend/app/models.py", "backend/app/routers/*.py"],
        "include_contracts": True,  # May need contracts to understand expected behavior
        "include_architecture": False,
    },
}


def get_relevant_files(step_name: str, all_files: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Filter files to only those relevant for the current step.
    PHASE 2: Context Optimization
    """
    rules = STEP_CONTEXT_RULES.get(step_name, {"files": []})
    patterns = rules.get("files", [])
    
    if not patterns:
        return []
    
    relevant = []
    for file in all_files:
        path = file.get("path", "")
        for pattern in patterns:
            # Simple glob matching
            if pattern.endswith("**/*.*"):
                prefix = pattern.replace("**/*.*", "")
                if path.startswith(prefix):
                    relevant.append(file)
                    break
            elif "*" in pattern:
                # Handle wildcards
                import fnmatch
                if fnmatch.fnmatch(path, pattern):
                    relevant.append(file)
                    break
            elif path == pattern:
                relevant.append(file)
                break
    
    return relevant


# ============================================================
# FILE SUMMARIES (Cache these!)
# ============================================================

_file_summaries: Dict[str, str] = {}


def get_file_summary(path: str, content: str) -> str:
    """
    Generate or retrieve 500-char summary of a file.
    """
    cache_key = f"{path}:{len(content)}"
    
    if cache_key in _file_summaries:
        return _file_summaries[cache_key]
    
    # Generate summary
    lines = content.split('\n')
    summary_lines = []
    char_count = 0
    
    for line in lines[:20]:  # First 20 lines
        if char_count + len(line) > 500:
            break
        summary_lines.append(line)
        char_count += len(line)
    
    summary = '\n'.join(summary_lines)
    if len(content) > 500:
        summary += "\n... (truncated)"
    
    _file_summaries[cache_key] = summary
    return summary


def build_file_context(files: List[Dict[str, str]], use_summaries: bool = True) -> str:
    """
    Build file context - use summaries when possible.
    """
    if not files:
        return ""
    
    context_parts = []
    for file in files:
        path = file.get("path", "")
        content = file.get("content", "")
        
        if use_summaries and len(content) > 1000:
            summary = get_file_summary(path, content)
            context_parts.append(f"FILE: {path}\n{summary}\n")
        else:
            context_parts.append(f"FILE: {path}\n{content}\n")
    
    return "\n---\n".join(context_parts)


# ============================================================
# AUTO-APPROVE RULES (Skip Marcus)
# ============================================================

AUTO_APPROVE_PATTERNS = [
    "*.json",
    "*.md",
    "vite.config.js",
    "tailwind.config.js",
    "postcss.config.js",
    "jsconfig.json",
    "pytest.ini",
    ".dockerignore",
    ".gitignore",
    "frontend/public/*",
    "backend/reference/*",
    "frontend/reference/*",
]


def should_auto_approve(file_path: str) -> bool:
    """
    Check if file should be auto-approved (skip Marcus review).
    PHASE 3: Marcus Optimization
    """
    import fnmatch
    
    for pattern in AUTO_APPROVE_PATTERNS:
        if fnmatch.fnmatch(file_path, pattern):
            return True
    
    return False

