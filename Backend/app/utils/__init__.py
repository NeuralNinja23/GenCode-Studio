# app/utils/__init__.py
"""
Utility modules for GenCode Studio.
"""
from .parser import (
    normalize_llm_output,
    parse_hdap,
    parse_json,
    parse_json_metadata,
    sanitize_marcus_output,
    is_output_complete,
    get_incomplete_files,
    has_hdap_markers,
)
from .ui_beautifier import beautify_frontend_files
from .dependency_fixer import (
    auto_fix_backend_dependencies,
    detect_missing_dependencies,
    add_dependencies_to_requirements,
)
from .entity_discovery import (
    discover_primary_entity,
    discover_db_function,
    discover_routers,
    get_entity_plural,
    singularize,
    extract_entity_from_request,
    ENTITY_PATTERNS,
)
from .path_utils import (
    get_project_path,
    get_backend_path,
    get_frontend_path,
    get_backend_app_path,
    get_routers_path,
    get_models_path,
    get_main_py_path,
    get_architecture_path,
    get_tests_path,
    is_valid_project_path,
    ensure_project_directories,
)

__all__ = [
    "normalize_llm_output",
    "parse_hdap",
    "parse_json",
    "parse_json_metadata",
    "sanitize_marcus_output",
    "is_output_complete",
    "get_incomplete_files",
    "has_hdap_markers",
    "beautify_frontend_files",
    "auto_fix_backend_dependencies",
    "detect_missing_dependencies",
    "add_dependencies_to_requirements",
    # Entity Discovery
    "discover_primary_entity",
    "discover_db_function",
    "discover_routers",
    "get_entity_plural",
    "singularize",
    "extract_entity_from_request",
    "ENTITY_PATTERNS",
    # Path Utilities
    "get_project_path",
    "get_backend_path",
    "get_frontend_path",
    "get_backend_app_path",
    "get_routers_path",
    "get_models_path",
    "get_main_py_path",
    "get_architecture_path",
    "get_tests_path",
    "is_valid_project_path",
    "ensure_project_directories",
]
