# app/tools/handler_example.py
"""
Example: How Handlers Work Under the New Architecture

=== THE OLD WAY (What you had) ===

async def handle_backend_models(branch):
    return await run_tool("subagentcaller", {
        "sub_agent": "Derek",
        "instructions": "Generate models...",
        ...
    })

PROBLEMS:
- Handler knows about tools (tight coupling)
- Tool selection is hardcoded
- No observation of tool sequence
- 36 tools exist but only 1 is used


=== THE NEW WAY (This file) ===

async def handle_backend_models(branch):
    plan = await build_tool_plan(
        step="backend_models",
        branch=branch,
        goal="Generate Beanie models for CRM entities"
    )
    result = await execute_tool_plan(plan, branch)
    return result.final_output

BENEFITS:
- Handler describes INTENT, not tools
- Tool sequence is explicit and observable
- Multiple tools can be composed
- All 36 tools are now usable
"""

from typing import Any, Dict

from app.tools.planning import ToolPlanExecutionResult, StepFailure
from app.tools.planner import build_tool_plan
from app.tools.executor import execute_tool_plan
from app.core.logging import log


# ═══════════════════════════════════════════════════════════════════════════════
# EXAMPLE: NEW-STYLE HANDLER
# ═══════════════════════════════════════════════════════════════════════════════

async def handle_backend_models_v2(branch: Any) -> Dict[str, Any]:
    """
    NEW-STYLE HANDLER: Describes intent, doesn't select tools.
    
    The handler's job is now:
    1. Describe the GOAL
    2. Call build_tool_plan() 
    3. Call execute_tool_plan()
    4. Return the result
    
    The handler does NOT:
    - Name specific tools
    - Call subagentcaller directly
    - Know which tool sequence runs
    """
    # Step 1: Build the plan
    plan = await build_tool_plan(
        step="backend_models",
        branch=branch,
        goal="Generate Beanie Document models for all entities in architecture.md"
    )
    
    log("HANDLER", f"Built plan with {plan.tool_count} tools: {plan.tool_names}")
    
    # Step 2: Execute the plan
    try:
        result = await execute_tool_plan(plan, branch)
        
        log("HANDLER", f"Plan completed: {result.completed_count} succeeded, {result.failed_count} failed")
        
        return result.final_output or {}
        
    except StepFailure as e:
        log("HANDLER", f"Step failed: {e}")
        raise


async def handle_architecture_v2(branch: Any) -> Dict[str, Any]:
    """
    Architecture step - Victoria generates the architecture.md
    """
    plan = await build_tool_plan(
        step="architecture",
        branch=branch,
        goal="Generate architecture.md with entities, relationships, and tech stack"
    )
    
    result = await execute_tool_plan(plan, branch)
    return result.final_output or {}


async def handle_testing_backend_v2(branch: Any) -> Dict[str, Any]:
    """
    Testing step - Derek generates tests, then pytest runs them.
    """
    plan = await build_tool_plan(
        step="testing_backend",
        branch=branch,
        goal="Generate pytest tests for all routers and run them"
    )
    
    result = await execute_tool_plan(plan, branch)
    return result.final_output or {}


# ═══════════════════════════════════════════════════════════════════════════════
# MIGRATION PATH
# ═══════════════════════════════════════════════════════════════════════════════

def migrate_handler_to_v2(old_handler_name: str) -> str:
    """
    Shows how to migrate an old handler to the new style.
    
    OLD:
        async def handle_foo(branch):
            return await run_tool("subagentcaller", {...})
    
    NEW:
        async def handle_foo(branch):
            plan = await build_tool_plan(step="foo", branch=branch, goal="...")
            result = await execute_tool_plan(plan, branch)
            return result.final_output
    """
    return f"""
# OLD ({old_handler_name}):
async def {old_handler_name}(branch):
    return await run_tool("subagentcaller", {{...}})

# NEW ({old_handler_name}_v2):
async def {old_handler_name}_v2(branch):
    plan = await build_tool_plan(
        step="{old_handler_name.replace('handle_', '')}",
        branch=branch,
        goal="Describe what this step should accomplish"
    )
    result = await execute_tool_plan(plan, branch)
    return result.final_output or {{}}
"""
