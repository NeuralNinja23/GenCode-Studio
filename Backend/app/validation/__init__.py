# app/validation/__init__.py
"""
Validation module - Multi-layer quality gates.

Layer 1: Pre-flight (0.5s) - AST/syntax checks, catches 90% of issues
Layer 2: Lightweight review (10s) - Gemini Flash (future)
Layer 3: Deep review (60s) - Marcus full review (existing)
"""
from .syntax_validator import (
    validate_file,
    validate_files_batch,
    validate_python_syntax,
    validate_javascript_syntax,
    preflight_check,
    ValidationResult,
)

__all__ = [
    "validate_file",
    "validate_files_batch", 
    "validate_python_syntax",
    "validate_javascript_syntax",
    "preflight_check",
    "ValidationResult",
]
