# app/llm/__init__.py
"""
LLM module - Unified interface for all LLM providers.
"""
from .adapter import LLMAdapter, call_llm

__all__ = ["LLMAdapter", "call_llm"]
