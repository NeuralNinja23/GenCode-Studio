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


def has_optional_list_params(code: str) -> tuple[bool, list]:
    """
    ═══════════════════════════════════════════════════════════════════
    CRITICAL: Validate list endpoint query params are Optional with defaults.
    ═══════════════════════════════════════════════════════════════════
    
    Problem: LLM generates list endpoints with REQUIRED query params:
        async def get_all(status: str, channel: str):  # ❌ WRONG - tests fail!
    
    Solution: List endpoints MUST have Optional params with defaults:
        async def get_all(status: Optional[str] = None):  # ✅ CORRECT
    
    This check prevents:
    - Test failures (tests don't provide query params)
    - Healing loop exhaustion trying to fix it
    - Wasted tokens/money
    
    Returns:
        (is_valid, list_of_issues)
    """
    import ast
    
    issues = []
    
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return True, []  # Let syntax validator handle this
    
    # Find all GET list endpoints (decorated with @router.get("/") or similar)
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        
        # Check if this is a list endpoint (get_all, list_*, etc.)
        func_name = node.name.lower()
        is_list_endpoint = any([
            func_name.startswith('get_all'),
            func_name.startswith('list_'),
            func_name == 'get_all',
            func_name.endswith('_list'),
            'list' in func_name,
        ])
        
        # Also check decorator for @router.get("/")
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Attribute):
                    if decorator.func.attr == 'get' and decorator.args:
                        # Check if path is "/" (list endpoint)
                        if isinstance(decorator.args[0], ast.Constant):
                            if decorator.args[0].value in ('/', ''):
                                is_list_endpoint = True
        
        if not is_list_endpoint:
            continue
        
        # Check function parameters (skip 'self' if present)
        for arg in node.args.args:
            param_name = arg.arg
            
            # Skip common non-query params
            if param_name in ('self', 'db', 'session', 'request', 'response'):
                continue
            
            # Check if this param has a default
            # In AST, defaults are at the END of args list
            # args.defaults[i] corresponds to args.args[len(args)-len(defaults)+i]
            num_defaults = len(node.args.defaults)
            num_args = len(node.args.args)
            args_without_defaults = num_args - num_defaults
            
            arg_index = node.args.args.index(arg)
            has_default = arg_index >= args_without_defaults
            
            if not has_default:
                issues.append(
                    f"List endpoint '{node.name}' has required query param '{param_name}'. "
                    f"Must be Optional[...] with default=None for tests to pass."
                )
    
    return len(issues) == 0, issues


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
    # Check list endpoint query params (CRITICAL for preventing test failures)
    list_params_ok, list_param_issues = has_optional_list_params(code)
    
    checks = {
        "has_query": has_query_annotations(code),
        "has_pagination": has_pagination_params(code),
        "has_imports": has_proper_imports(code),
        "has_router_var": has_router_variable(code),
        "list_params_optional": list_params_ok,  # NEW: Critical check
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
    if not checks["list_params_optional"]:
        reasons.extend(list_param_issues)  # Add specific issues
    
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
