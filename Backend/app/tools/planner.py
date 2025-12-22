# app/tools/planner.py
"""
Tool Plan Builder

THE SHIFT:
- Router output is BINDING, not advisory
- Router builds EXPLICIT plans from the consolidated tools.py
- Plans include reason for each tool

The Flow:
  Step → Tools for Phase → Ordered ToolPlan

NO LLM INVOLVED. DETERMINISTIC. OBSERVABLE.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path

from app.tools.planning import ToolPlan, ToolInvocationPlan
from app.tools.tools import (
    TOOLS,
    Capability,
    ToolDefinition,
    get_tool,
    get_tools_for_phase,
    get_pre_step_tools,
    get_post_step_tools,
)
from app.core.logging import log


# Agent mapping
STEP_AGENTS = {
    "architecture": "Victoria",
    "frontend_mock": "Derek",
    "backend_models": "Derek",
    "backend_routers": "Derek",
    "system_integration": "Derek",
    "testing_backend": "Derek",
    "testing_frontend": "Luna",
    "preview_final": "System",
}


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL PLAN BUILDER
# ═══════════════════════════════════════════════════════════════════════════════

class ToolPlanBuilder:
    """
    Builds binding tool plans for steps.
    
    The Flow:
    1. Step name → Get tools for phase
    2. Order by: pre-step → core → post-step
    3. Build ToolPlan
    
    NO LLM INVOLVED. DETERMINISTIC. OBSERVABLE.
    """
    
    def __init__(self):
        pass
    
    async def build_tool_plan(
        self,
        step: str,
        branch: Any,
        goal: str,
        override_args: Optional[Dict[str, Any]] = None,
    ) -> ToolPlan:
        """
        Build a tool plan for a step.
        """
        log("PLANNER", f"📐 Building plan for step '{step}'")
        
        # Get all tools for this phase
        phase_tools = get_tools_for_phase(step)
        
        # Separate into pre, core, post
        pre_tools = [t for t in phase_tools if t.is_pre_step]
        post_tools = [t for t in phase_tools if t.is_post_step]
        core_tools = [t for t in phase_tools if not t.is_pre_step and not t.is_post_step]
        
        # Build ordered sequence: pre → core (just subagentcaller) → post
        sequence = []
        
        # Add pre-step tools (only if their context exists)
        project_path = self._get_project_path(branch)
        for tool_def in pre_tools:
            # Skip pre-tools if their required context doesn't exist yet
            if self._should_skip_pre_tool(tool_def.id, step, project_path):
                continue
                
            args = self._build_tool_args(tool_def.id, step, branch, goal, override_args)
            invocation = ToolInvocationPlan(
                tool_name=tool_def.id,
                args=args,
                reason=f"[PRE] {tool_def.description}",
                required=tool_def.required_for_phase,
            )
            sequence.append(invocation)
            log("PLANNER", f"   + {tool_def.id} (optional)")
        
        # Add core tool (subagentcaller)
        subagent = get_tool("subagentcaller")
        if subagent:
            args = self._build_tool_args("subagentcaller", step, branch, goal, override_args)
            invocation = ToolInvocationPlan(
                tool_name="subagentcaller",
                args=args,
                reason="Core LLM call",
                required=True,
            )
            sequence.append(invocation)
            log("PLANNER", f"   + subagentcaller (REQUIRED)")
        
        # Add post-step tools
        for tool_def in post_tools:
            args = self._build_tool_args(tool_def.id, step, branch, goal, override_args)
            invocation = ToolInvocationPlan(
                tool_name=tool_def.id,
                args=args,
                reason=f"[POST] {tool_def.description}",
                required=tool_def.required_for_phase,
            )
            sequence.append(invocation)
            log("PLANNER", f"   + {tool_def.id} (optional)")
        
        # Get agent for this step
        agent = STEP_AGENTS.get(step, "System")
        
        plan = ToolPlan(
            step=step,
            agent=agent,
            goal=goal,
            sequence=sequence,
        )
        
        log("PLANNER", f"   ✅ Plan built: {plan.tool_count} tools")
        
        return plan
    
    def _build_tool_args(
        self,
        tool_id: str,
        step: str,
        branch: Any,
        goal: str,
        override_args: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Build args for a specific tool."""
        args = {}
        
        # Extract context from branch
        project_path = self._get_project_path(branch)
        
        # Tool-specific args
        if tool_id == "subagentcaller":
            args = self._build_subagent_args(step, branch, goal)
            
        elif tool_id == "environment_guard":
            args = {"check": "system_info", "project_path": project_path}
            
        elif tool_id == "filereader":
            args = {"file_path": self._get_architecture_file(step, project_path)}
            
        elif tool_id == "codeviewer":
            args = {"file_path": self._get_context_file(step, project_path)}
            
        elif tool_id == "filelister":
            args = {"directory": project_path, "recursive": True}
            
        elif tool_id == "dbschemareader":
            args = {"project_path": project_path}
            
        elif tool_id == "keyvalidator":
            args = {"project_path": project_path}
            
        elif tool_id == "webresearcher":
            args = {"query": goal[:100]}
            
        elif tool_id in ("syntaxvalidator", "static_code_validator"):
            args = {"language": "python" if "backend" in step else "javascript", "project_path": project_path}
            
        elif tool_id == "pytestrunner":
            args = {"test_path": "backend/tests", "cwd": project_path}
            
        elif tool_id == "playwrightrunner":
            args = {"test_file": "tests/e2e.spec.js", "cwd": project_path}
            
        elif tool_id == "deploymentvalidator":
            args = {"project_path": project_path}
            
        elif tool_id == "healthchecker":
            args = {"url": "http://localhost:8000/health"}
            
        elif tool_id == "apitester":
            args = {"base_url": "http://localhost:8000", "project_path": project_path}
            
        elif tool_id in ("screenshotcomparer", "uxvisualizer"):
            args = {"project_path": project_path}
        
        # Merge with override args
        if override_args:
            args.update(override_args)
        
        return args
    
    def _get_project_path(self, branch: Any) -> str:
        """Extract project_path from branch."""
        if hasattr(branch, "project_path"):
            return str(branch.project_path)
        if hasattr(branch, "intent") and branch.intent:
            return str(branch.intent.get("project_path", "."))
        if isinstance(branch, dict):
            return str(branch.get("project_path", branch.get("intent", {}).get("project_path", ".")))
        return "."
    
    def _get_architecture_file(self, step: str, project_path: str) -> str:
        """Get the relevant architecture file for a step."""
        base = Path(project_path) / "architecture"
        if "frontend" in step:
            return str(base / "frontend.md")
        elif "backend" in step or "models" in step or "routers" in step:
            return str(base / "backend.md")
        return str(base / "system.md")
    
    def _get_context_file(self, step: str, project_path: str) -> str:
        """Get the relevant code file for context."""
        base = Path(project_path)
        if "models" in step:
            return str(base / "backend" / "app" / "models.py")
        elif "routers" in step:
            return str(base / "backend" / "app" / "routers" / "__init__.py")
        elif "frontend" in step:
            return str(base / "frontend" / "src" / "App.jsx")
        return str(base / "README.md")
    
    def _should_skip_pre_tool(self, tool_id: str, step: str, project_path: str) -> bool:
        """
        Check if a pre-tool should be skipped because its required context doesn't exist.
        
        This prevents unnecessary failures for tools that read files that haven't been
        created yet (e.g., filereader trying to read architecture/ during architecture step).
        """
        base = Path(project_path)
        
        # filereader - needs architecture files to exist
        if tool_id == "filereader":
            target_file = Path(self._get_architecture_file(step, project_path))
            if not target_file.exists():
                return True
        
        # codeviewer - needs code files to exist
        elif tool_id == "codeviewer":
            target_file = Path(self._get_context_file(step, project_path))
            if not target_file.exists():
                return True
        
        # dbschemareader - needs models.py to exist
        elif tool_id == "dbschemareader":
            models_py = base / "backend" / "app" / "models.py"
            models_py_alt = base / "app" / "models.py"
            if not models_py.exists() and not models_py_alt.exists():
                return True
        
        # webresearcher - always run (no file dependency)
        # keyvalidator - always run (checks .env)
        # environment_guard - always run (checks system)
        # filelister - always run (just lists directory)
        
        return False
    
    def _build_subagent_args(self, step: str, branch: Any, goal: str) -> Dict[str, Any]:
        """Build args for subagentcaller."""
        args = {
            "step_name": step,
            "sub_agent": STEP_AGENTS.get(step, "Derek"),
        }
        
        if hasattr(branch, 'intent') and branch.intent:
            intent = branch.intent
            args["user_request"] = intent.get("user_request", "")
            args["project_path"] = str(intent.get("project_path", ""))
            args["project_id"] = intent.get("project_id", "")
        
        args["instructions"] = f"Execute step: {step}. Goal: {goal}"
        
        return args


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON BUILDER
# ═══════════════════════════════════════════════════════════════════════════════

_builder_instance: Optional[ToolPlanBuilder] = None


def get_plan_builder() -> ToolPlanBuilder:
    """Get the singleton plan builder."""
    global _builder_instance
    if _builder_instance is None:
        _builder_instance = ToolPlanBuilder()
    return _builder_instance


async def build_tool_plan(
    step: str,
    branch: Any,
    goal: str,
    override_args: Optional[Dict[str, Any]] = None,
) -> ToolPlan:
    """Convenience function to build a tool plan."""
    builder = get_plan_builder()
    return await builder.build_tool_plan(step, branch, goal, override_args)
