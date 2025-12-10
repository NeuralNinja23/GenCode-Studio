# app/workflow/agents/__init__.py
"""
Agent calling module - handles calls to sub-agents (Derek, Luna, Victoria).
"""
from .sub_agents import marcus_call_sub_agent, run_sub_agent

__all__ = ["marcus_call_sub_agent", "run_sub_agent"]
