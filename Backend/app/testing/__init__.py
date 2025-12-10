# app/testing/__init__.py
"""
Testing module - test runners and self-healing.
"""
from .self_healing import SelfHealingTests, create_robust_smoke_test

__all__ = ["SelfHealingTests", "create_robust_smoke_test"]
