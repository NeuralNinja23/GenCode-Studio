# app/validation/__init__.py
"""
Validation Module - Single Entry Point for All Validation.

This module provides a unified interface for validation across GenCode Studio.
Import from this module instead of individual validator files.

Usage:
    from app.validation import validate_python, validate_syntax, preflight_check
"""
from .syntax_validator import (
    ValidationResult,
    validate_python_syntax,
    validate_javascript_syntax,
    validate_syntax,
    validate_files_batch,
    preflight_check,
    IncompleteCodeError,
    assert_no_empty_defs,
    check_duplicate_attributes,
)

# Re-export with shorter names
validate_python = validate_python_syntax
validate_javascript = validate_javascript_syntax
validate_js = validate_javascript_syntax


__all__ = [
    # Core validation functions
    "validate_python",
    "validate_javascript",
    "validate_js",
    "validate_syntax",
    "validate_files_batch",
    "preflight_check",
    
    # Result and error types
    "ValidationResult",
    "IncompleteCodeError",
    
    # Advanced functions
    "assert_no_empty_defs",
    "check_duplicate_attributes",
    
    # Original names (for compatibility)
    "validate_python_syntax",
    "validate_javascript_syntax",
]
