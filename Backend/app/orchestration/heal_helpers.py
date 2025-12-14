# backend/app/orchestration/heal_helpers.py
"""
Healing Validation Utilities

Validates LLM-generated router code to ensure it meets FastAPI requirements.
Auto-falls back to templates when validation fails.
"""
import re
from typing import Dict
from pathlib import Path


# Query annotation patterns to detect
_QUERY_CHECK_PATTERNS = [
    r"\bQuery\s*\(",                      # Query(...) call
    r"from\s+fastapi\s+import\s+.*\bQuery\b",  # from fastapi import Query
    r"fastapi\.Query\s*\(",               # fastapi.Query(...) 
]


def has_query_annotations(code: str) -> bool:
    """
    Check if router code properly uses FastAPI Query() annotations.
    
    Args:
        code: Router code to validate
    
    Returns:
        True if Query annotations are present and imported
    """
    if "Query" not in code:
        return False
    
    for patt in _QUERY_CHECK_PATTERNS:
        if re.search(patt, code):
            return True
    
    return False


def has_pagination_params(code: str, param_names=("page", "limit")) -> bool:
    """
    Check if router code includes expected pagination parameters.
    
    Args:
        code: Router code to validate
        param_names: Expected parameter names (default: page, limit)
    
    Returns:
        True if all expected params are found
    """
    for param in param_names:
        if not re.search(rf"\b{param}\b", code):
            return False
    return True


def has_proper_imports(code: str) -> bool:
    """
    Validate that router has essential FastAPI imports.
    
    Args:
        code: Router code to validate
    
    Returns:
        True if imports look correct
    """
    required_imports = [
        r"from\s+fastapi\s+import\s+.*\bAPIRouter\b",  # Must have APIRouter
        r"from\s+app\.models\s+import",  # Must import models
    ]
    
    for pattern in required_imports:
        if not re.search(pattern, code):
            return False
    
    return True


def has_router_variable(code: str) -> bool:
    """
    Check that router code defines the router variable.
    
    Args:
        code: Router code to validate
    
    Returns:
        True if 'router = APIRouter(...)' is found
    """
    return bool(re.search(r"\brouter\s*=\s*APIRouter\s*\(", code))


def validate_router_code(code: str, entity_name: str = None) -> Dict[str, any]:
    """
    Comprehensive validation of LLM-generated router code.
    
    Args:
        code: Router code to validate
        entity_name: Optional entity name for context
    
    Returns:
        Dict with:
            - valid: bool - Overall validation result
            - checks: dict - Individual check results
            - reasons: list - Failure reasons
    """
    checks = {
        "has_query": has_query_annotations(code),
        "has_pagination": has_pagination_params(code),
        "has_imports": has_proper_imports(code),
        "has_router_var": has_router_variable(code),
    }
    
    reasons = []
    if not checks["has_query"]:
        reasons.append("Missing Query() annotations for pagination params")
    if not checks["has_pagination"]:
        reasons.append("Missing pagination parameters (page/limit)")
    if not checks["has_imports"]:
        reasons.append("Missing required imports (APIRouter, models)")
    if not checks["has_router_var"]:
        reasons.append("Missing 'router = APIRouter(...)' declaration")
    
    valid = all(checks.values())
    
    return {
        "valid": valid,
        "checks": checks,
        "reasons": reasons,
    }


def validate_router_file(file_path: Path, entity_name: str = None) -> Dict[str, any]:
    """
    Validate a router file on disk.
    
    Args:
        file_path: Path to router file
        entity_name: Optional entity name for context
    
    Returns:
        Validation result dict (same as validate_router_code)
    """
    if not file_path.exists():
        return {
            "valid": False,
            "checks": {},
            "reasons": ["File does not exist"],
        }
    
    try:
        code = file_path.read_text(encoding="utf-8")
        return validate_router_code(code, entity_name)
    except Exception as e:
        return {
            "valid": False,
            "checks": {},
            "reasons": [f"Failed to read file: {e}"],
        }
