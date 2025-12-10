# app/utils/__init__.py
"""
Utility modules for GenCode Studio.
"""
from .parser import (
    normalize_llm_output,
    parse_json,
    sanitize_marcus_output,
    extract_files_from_pseudo_json,
)
from .ui_beautifier import beautify_frontend_files
from .dependency_fixer import (
    auto_fix_backend_dependencies,
    detect_missing_dependencies,
    add_dependencies_to_requirements,
)

__all__ = [
    "normalize_llm_output",
    "parse_json",
    "sanitize_marcus_output",
    "extract_files_from_pseudo_json",
    "beautify_frontend_files",
    "auto_fix_backend_dependencies",
    "detect_missing_dependencies",
    "add_dependencies_to_requirements",
]
