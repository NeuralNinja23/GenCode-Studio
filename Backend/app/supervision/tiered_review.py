# app/supervision/tiered_review.py
"""
Tiered Review System - Smart quality gates based on file criticality.

Not all code needs the same level of scrutiny:
- Critical code (routers, models) → Full Marcus LLM review
- Test files → Pre-flight only (tests validate themselves)
- Config files → Pre-flight only (syntax check sufficient)
- Static assets → No review needed

This saves 60%+ on review time while maintaining quality where it matters.
"""
from enum import Enum
from typing import Dict, Any, List, Tuple
import re

from app.core.logging import log


class ReviewLevel(Enum):
    """Review levels in order of intensity."""
    NONE = "none"                    # No review needed (static assets)
    PREFLIGHT_ONLY = "preflight"     # Syntax check only (tests, configs)
    LIGHTWEIGHT = "lightweight"       # Quick LLM check (simple files)
    FULL = "full"                    # Full Marcus review (critical code)


# ═══════════════════════════════════════════════════════════════════
# FILE CLASSIFICATION RULES
# ═══════════════════════════════════════════════════════════════════

# Files that need FULL Marcus review (critical business logic)
FULL_REVIEW_PATTERNS = [
    r"backend/app/routers/.*\.py$",      # API endpoints
    r"backend/app/models\.py$",          # Database models
    r"backend/app/main\.py$",            # Main app entry
    r"backend/app/database\.py$",        # Database config
    r"frontend/src/pages/.*\.jsx?$",     # Page components
    r"frontend/src/App\.jsx?$",          # Main app component
    r"frontend/src/api/.*\.js$",         # API client code
]

# Files that only need pre-flight (syntax check)
PREFLIGHT_ONLY_PATTERNS = [
    r".*tests?/.*\.(py|js|jsx|ts|tsx)$", # Test files
    r".*\.spec\.(js|jsx|ts|tsx)$",       # Playwright tests
    r".*\.test\.(js|jsx|ts|tsx)$",       # Jest tests
    r"test_.*\.py$",                     # Python tests
    r"conftest\.py$",                    # Pytest config
    r".*\.config\.(js|ts|json)$",        # Config files
    r"playwright\.config\.js$",          # Playwright config
    r"vite\.config\.js$",                # Vite config
    r"pytest\.ini$",                     # Pytest config
    r"requirements\.txt$",               # Dependencies
    r"package\.json$",                   # NPM config
]

# Files that need NO review
NO_REVIEW_PATTERNS = [
    r".*\.css$",                         # Stylesheets
    r".*\.html$",                        # HTML templates
    r".*\.md$",                          # Markdown docs
    r".*\.svg$",                         # Vector graphics
    r".*\.png$",                         # Images
    r".*\.ico$",                         # Icons
    r"\.gitignore$",                     # Git config
    r"\.dockerignore$",                  # Docker config
    r"Dockerfile$",                      # Docker files
]


def get_review_level(file_path: str) -> ReviewLevel:
    """
    Determine the review level needed for a file.
    
    Args:
        file_path: Relative path to the file
        
    Returns:
        ReviewLevel indicating how thoroughly to review
    """
    # Normalize path
    path = file_path.replace("\\", "/").lower()
    
    # Check no-review patterns first
    for pattern in NO_REVIEW_PATTERNS:
        if re.search(pattern, path, re.IGNORECASE):
            return ReviewLevel.NONE
    
    # Check preflight-only patterns
    for pattern in PREFLIGHT_ONLY_PATTERNS:
        if re.search(pattern, path, re.IGNORECASE):
            return ReviewLevel.PREFLIGHT_ONLY
    
    # Check full-review patterns
    for pattern in FULL_REVIEW_PATTERNS:
        if re.search(pattern, path, re.IGNORECASE):
            return ReviewLevel.FULL
    
    # Default: lightweight review for unknown files
    return ReviewLevel.LIGHTWEIGHT


def classify_files(files: List[Dict[str, Any]]) -> Dict[ReviewLevel, List[Dict[str, Any]]]:
    """
    Classify files by their review level.
    
    Args:
        files: List of file dicts with "path" key
        
    Returns:
        Dict mapping ReviewLevel to list of files
    """
    classified = {level: [] for level in ReviewLevel}
    
    for f in files:
        path = f.get("path", "")
        level = get_review_level(path)
        classified[level].append(f)
    
    return classified


def get_review_summary(files: List[Dict[str, Any]]) -> str:
    """Get a summary of review levels for logging."""
    classified = classify_files(files)
    
    parts = []
    for level in ReviewLevel:
        count = len(classified[level])
        if count > 0:
            parts.append(f"{level.value}: {count}")
    
    return ", ".join(parts)


async def tiered_review(
    files: List[Dict[str, Any]],
    project_id: str,
    manager: Any,
    agent_name: str,
    step_name: str,
    contracts: str = "",
    user_request: str = "",
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Apply tiered review to a list of files.
    
    Returns:
        Tuple of (approved_files, review_summary)
    """
    from app.validation import preflight_check, validate_file
    
    classified = classify_files(files)
    approved_files = []
    review_results = {
        "full_reviewed": 0,
        "preflight_only": 0,
        "skipped": 0,
        "rejected": 0,
        "total_files": len(files),
    }
    
    log("TIERED", f"📊 Review allocation: {get_review_summary(files)}")
    
    # ═══════════════════════════════════════════════════════════════════
    # Level 1: NO REVIEW (static assets) - Just pass through
    # ═══════════════════════════════════════════════════════════════════
    for f in classified[ReviewLevel.NONE]:
        approved_files.append(f)
        review_results["skipped"] += 1
        log("TIERED", f"⏭️ Skipping review for static: {f.get('path')}")
    
    # ═══════════════════════════════════════════════════════════════════
    # Level 2: PREFLIGHT ONLY (tests, configs) - Syntax check only
    # ═══════════════════════════════════════════════════════════════════
    preflight_files = classified[ReviewLevel.PREFLIGHT_ONLY]
    if preflight_files:
        log("TIERED", f"🔍 Pre-flight checking {len(preflight_files)} files...")
        
        for f in preflight_files:
            path = f.get("path", "")
            content = f.get("content", "")
            
            result = validate_file(path, content)
            if result.valid:
                approved_files.append(f)
                review_results["preflight_only"] += 1
                log("TIERED", f"✅ Pre-flight passed: {path}")
            else:
                review_results["rejected"] += 1
                log("TIERED", f"❌ Pre-flight failed: {path} - {result.errors[0]}")
    
    # ═══════════════════════════════════════════════════════════════════
    # Level 3: LIGHTWEIGHT (quick check) - Brief LLM review
    # ═══════════════════════════════════════════════════════════════════
    lightweight_files = classified[ReviewLevel.LIGHTWEIGHT]
    if lightweight_files:
        # For now, treat lightweight same as preflight
        # In future, could use a faster/cheaper LLM
        for f in lightweight_files:
            path = f.get("path", "")
            content = f.get("content", "")
            
            result = validate_file(path, content)
            if result.valid:
                approved_files.append(f)
                review_results["preflight_only"] += 1
            else:
                review_results["rejected"] += 1
    
    # ═══════════════════════════════════════════════════════════════════
    # Level 4: FULL REVIEW (critical code) - Marcus review
    # ═══════════════════════════════════════════════════════════════════
    critical_files = classified[ReviewLevel.FULL]
    if critical_files:
        log("TIERED", f"🔬 Full Marcus review for {len(critical_files)} critical files...")
        
        # Run Marcus review only on critical files
        from app.supervision import marcus_supervise
        
        critical_output = {"files": critical_files}
        review = await marcus_supervise(
            project_id=project_id,
            manager=manager,
            agent_name=agent_name,
            step_name=step_name,
            agent_output=critical_output,
            contracts=contracts,
            user_request=user_request,
        )
        
        if review.get("approved"):
            for f in critical_files:
                approved_files.append(f)
                review_results["full_reviewed"] += 1
        else:
            review_results["rejected"] += len(critical_files)
            review_results["rejection_reason"] = review.get("feedback", "")
    
    # Build summary
    review_results["approved_count"] = len(approved_files)
    review_results["approval_rate"] = len(approved_files) / len(files) if files else 0
    
    log("TIERED", f"📋 Review complete: {review_results['approved_count']}/{len(files)} approved")
    
    return approved_files, review_results


# ═══════════════════════════════════════════════════════════════════
# PARALLEL REVIEW HELPERS
# ═══════════════════════════════════════════════════════════════════

async def parallel_tiered_review(
    outputs: List[Dict[str, Any]],  # List of {"agent": ..., "files": [...], ...}
    project_id: str,
    manager: Any,
    user_request: str = "",
) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
    """
    Run tiered reviews in parallel for multiple agent outputs.
    
    This is the key speed optimization - review frontend and backend
    simultaneously instead of sequentially.
    """
    import asyncio
    
    log("PARALLEL", f"🚀 Starting parallel review of {len(outputs)} outputs")
    
    async def review_one(output: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        files = output.get("files", [])
        agent = output.get("agent", "Unknown")
        step = output.get("step", "Unknown")
        
        approved, summary = await tiered_review(
            files=files,
            project_id=project_id,
            manager=manager,
            agent_name=agent,
            step_name=step,
            user_request=user_request,
        )
        
        return {"files": approved, "agent": agent, "step": step}, summary
    
    # Run all reviews in parallel
    results = await asyncio.gather(*[review_one(o) for o in outputs])
    
    return list(results)
