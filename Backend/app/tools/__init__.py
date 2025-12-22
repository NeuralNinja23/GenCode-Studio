# app/tools/__init__.py
"""
Tools Module - The SINGLE SOURCE OF TRUTH

Architecture:
- tools.py: 36 tool definitions (ID, function, capabilities, phases)
- planner.py: Builds tool plans for steps
- executor.py: Executes tool plans linearly
- registry.py: Simple lookup/run interface

NO OTHER FILE should define "what tools exist".
"""

# The consolidated tool registry
from .tools import (
    TOOLS,
    Capability,
    ToolDefinition,
    get_tool,
    get_all_tools,
    get_tools_for_phase,
    get_pre_step_tools,
    get_post_step_tools,
    run_tool,
)

# Legacy-compatible imports
from .registry import get_available_tools

# Planning primitives
from .planning import (
    ToolPlan,
    ToolInvocationPlan,
    ToolInvocationResult,
    ToolPlanExecutionResult,
    StepFailure,
)

# Plan building
from .planner import build_tool_plan, get_plan_builder

# Plan execution
from .executor import execute_tool_plan

__all__ = [
    # Tools registry (NEW - single source of truth)
    "TOOLS",
    "Capability",
    "ToolDefinition",
    "get_tool",
    "get_all_tools",
    "get_tools_for_phase",
    "get_pre_step_tools",
    "get_post_step_tools",
    "run_tool",
    # Legacy
    "get_available_tools",
    # Planning
    "ToolPlan",
    "ToolInvocationPlan",
    "ToolInvocationResult",
    "ToolPlanExecutionResult",
    "StepFailure",
    # Building
    "build_tool_plan",
    "get_plan_builder",
    # Execution
    "execute_tool_plan",
]
