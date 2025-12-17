# app/tools/registry.py
"""
Tool registry - routes tool calls to implementations.
Matches tools to user intent using Attention (V!=K).
"""
from typing import Any, Dict, List, Optional
from app.core.logging import log
from app.core.config import settings
from app.tools.catalog import ALL_TOOLS
from app.tools.specs import ToolSpec


TOOL_REGISTRY: dict[str, ToolSpec] = {}

def register_tools():
    for tool in ALL_TOOLS:
        TOOL_REGISTRY[tool.id] = tool


def get_tool(tool_id: str) -> ToolSpec:
    return TOOL_REGISTRY[tool_id]


def get_tools_for_step(step: str) -> list[ToolSpec]:
    return [
        tool for tool in TOOL_REGISTRY.values()
        if step in tool.allowed_steps or "*" in tool.allowed_steps
    ]

# ---------------------------------------------------------------------
# CONTEXT MAPPING (Step -> Allowed Categories)
# ---------------------------------------------------------------------
STEP_CONTEXT_MAP = {
    # Analysis & Architecture: Reading, Planning, Thinking
    "analysis": ["planning", "research", "reading"],
    "architecture": ["planning", "research", "reading"],
    
    # Frontend: Coding, UI, Testing
    "frontend_mock": ["planning", "coding", "ui", "testing", "reading"],
    "frontend_integration": ["coding", "ui", "testing", "reading", "file_ops"],
    "screenshot_verify": ["ui", "testing", "reading"],
    
    # Backend: Coding, DB, Testing
    "contracts": ["planning", "reading", "coding"],
    "backend_implementation": ["coding", "database", "reading", "file_ops"],
    "system_integration": ["coding", "database", "reading", "file_ops"],
    
    # Testing: Testing, Execution, Debugging
    "testing_backend": ["testing", "execution", "reading", "file_ops"],
    "testing_frontend": ["testing", "execution", "reading", "ui"],
    
    # Deployment: Deployment, Validation
    "preview_final": ["deployment", "validation", "reading"]
}

# ---------------------------------------------------------------------
# TOOL DEFINITIONS (With Categories)
# ---------------------------------------------------------------------
TOOL_DEFINITIONS = [
    # --- CORE AGENT ---
    {
        "id": "code_generator", # Alias for subagentcaller
        "description": "Generate, refactor, or fix code using specialized AI agents (Derek/Luna).",
        "value": {"temperature": 0.3, "max_tokens": 8000, "mode": "creative"},
        "categories": ["coding", "planning", "testing"]
    },
    {
        "id": "subagentcaller",
        "description": "Directly call a sub-agent (Derek, Luna, Victoria) for a specific task.",
        "value": {"temperature": 0.3},
        "categories": ["planning", "coding"]
    },
    
    # --- FILE OPERATIONS ---
    {
        "id": "filewriterbatch",
        "description": "Create or overwrite multiple files (code, config, docs) at once.",
        "value": {"verify_syntax": True},
        "categories": ["file_ops", "coding", "planning"]
    },
    {
        "id": "filereader",
        "description": "Read content of existing files.",
        "value": {"max_size_kb": 100},
        "categories": ["reading", "planning", "coding", "testing"]
    },
    {
        "id": "filedeleter",
        "description": "Delete files or directories.",
        "value": {"force": False},
        "categories": ["file_ops"]
    },
    {
        "id": "filelister",
        "description": "List files in directory, explore project structure/tree.",
        "value": {"depth": 2, "ignore_git": True},
        "categories": ["reading", "planning"]
    },
    {
        "id": "codeviewer",
        "description": "View specific symbols (class, function) logic in a file without reading the whole file.",
        "value": {"context_lines": 5},
        "categories": ["reading", "coding", "testing"]
    },

    # --- EXECUTION ---
    {
        "id": "sandboxexec",
        "description": "Execute shell commands, run scripts, install packages in Docker container.",
        "value": {"timeout": 30, "allow_network": True},
        "categories": ["execution", "coding", "testing"]
    },
    {
        "id": "bashrunner",
        "description": "Run advanced bash scripts or complex commands.",
        "value": {"timeout": 60},
        "categories": ["execution"]
    },
    {
        "id": "pythonexecutor",
        "description": "Execute Python scripts or snippets directly.",
        "value": {"timeout": 30},
        "categories": ["execution", "testing"]
    },
    {
        "id": "npmrunner",
        "description": "Run npm/bun/yarn commands (install, build, test).",
        "value": {"timeout": 300},
        "categories": ["execution", "coding"]
    },

    # --- TESTING & QUALITY ---
    {
        "id": "pytestrunner",
        "description": "Run backend python unit tests using pytest.",
        "value": {"timeout": 60, "collect_only": False},
        "categories": ["testing"]
    },
    {
        "id": "playwrightrunner",
        "description": "Run frontend E2E browser tests using playwright.",
        "value": {"timeout": 120, "headless": True},
        "categories": ["testing", "ui"]
    },
    {
        "id": "testgenerator",
        "description": "Generate new test files based on code.",
        "value": {"framework": "pytest"},
        "categories": ["testing", "coding"]
    },
    {
        "id": "syntaxvalidator",
        "description": "Check syntax of code files without running them.",
        "value": {"strict": True},
        "categories": ["testing", "coding"]
    },

    # --- PATCHING ---
    {
        "id": "unifiedpatchapplier",
        "description": "Apply strict diffs (unified format) with minimal edits.",
        "value": {"temperature": 0.0, "max_tokens": 4000, "mode": "strict"},
        "categories": ["coding", "file_ops"]
    },
    {
        "id": "jsonpatchapplier",
        "description": "Apply JSON patches to data files.",
        "value": {"safe_mode": True},
        "categories": ["coding", "file_ops"]
    },

    # --- DATABASE ---
    {
        "id": "dbschemareader",
        "description": "Introspect database schema/collections.",
        "value": {"depth": 1},
        "categories": ["database", "planning", "reading"]
    },
    {
        "id": "dbqueryrunner",
        "description": "Run specific queries against the database.",
        "value": {"read_only": False, "timeout": 10},
        "categories": ["database", "execution"]
    },

    # --- DEPLOYMENT & DEVOPS ---
    {
        "id": "dockerbuilder",
        "description": "Build Docker images.",
        "value": {"cache": True},
        "categories": ["deployment", "execution"]
    },
    {
        "id": "verceldeployer",
        "description": "Deploy frontend to Vercel.",
        "value": {"prod": False},
        "categories": ["deployment"]
    },
    {
        "id": "deploymentvalidator",
        "description": "Validate health of a deployed application.",
        "value": {"check_endpoints": ["/health"]},
        "categories": ["validation", "deployment"]
    },
    {
        "id": "keyvalidator",
        "description": "Validate API keys and environment secrets.",
        "value": {"check_provider": True},
        "categories": ["validation", "security"]
    },

    # --- VISUAL & UX ---
    {
        "id": "uxvisualizer",
        "description": "Render UI component preview or wireframe.",
        "value": {"format": "image"},
        "categories": ["ui", "planning"]
    },
    {
        "id": "screenshotcomparer",
        "description": "Compare UI screenshots for regression.",
        "value": {"threshold": 0.1},
        "categories": ["ui", "testing"]
    },

    # --- WEB & RESEARCH ---
    {
        "id": "webresearcher",
        "description": "Search the web for documentation or solutions.",
        "value": {"depth": 1},
        "categories": ["research", "planning"]
    },
    {
        "id": "apitester",
        "description": "Test external API endpoints.",
        "value": {"method": "GET"},
        "categories": ["testing", "validation"]
    },
    {
        "id": "healthchecker",
        "description": "Check system health status.",
        "value": {},
        "categories": ["validation"]
    },

    # --- USER ---
    {
        "id": "userconfirmer",
        "description": "Ask user for explicit confirmation.",
        "value": {"timeout": 300},
        "categories": ["planning", "validation"]
    },
    {
        "id": "userprompter",
        "description": "Prompt user for input.",
        "value": {"timeout": 300},
        "categories": ["planning"]
    }
]


def get_available_tools() -> List[str]:
    """Return list of available tool names dynamically."""
    return [t["id"] for t in TOOL_DEFINITIONS]


async def run_tool(name: str, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Execute a tool by name."""
    from app.tools.implementations import _run_tool_impl
    return await _run_tool_impl(name, args)


async def get_relevant_tools_for_query(query: str, top_k: int = 5, **kwargs) -> Dict[str, Any]:
    """
    Select tools using V!=K Attention with strict Context constraints.
    
    Returns:
        Dict with:
            - tools: List of selected tools
            - decision_id: ID for tracking routing outcome (for learning)
    """
    try:
        from app.arbormind import arbormind_route
        
        # 1. Filter candidates based on step_name
        step_name = kwargs.get("step_name", "")
        allowed_categories = STEP_CONTEXT_MAP.get(step_name)
        
        if allowed_categories:
            candidates = [
                t for t in TOOL_DEFINITIONS 
                if any(cat in allowed_categories for cat in t.get("categories", []))
            ]
            # Ensure essentials are always available regardless of category
            essential_ids = {"code_generator", "filewriterbatch", "filereader"}
            for t in TOOL_DEFINITIONS:
                if t["id"] in essential_ids and t not in candidates:
                    candidates.append(t)
        else:
            candidates = TOOL_DEFINITIONS

        if not candidates:
            log("REGISTRY", f"⚠️ No allowed tools for step '{step_name}', using full set.")
            candidates = TOOL_DEFINITIONS
        
        # 1.5: TOOL POLICY ENFORCEMENT - Filter by declarative constraints
        # ONLY if specs exist; otherwise allow all tools (gradual rollout)
        from app.tools.tool_policy import allowed_tools_for_step
        from app.tools.registry import TOOL_REGISTRY
        
        # Only filter if we have registered tool specs for this step
        if TOOL_REGISTRY and step_name:
            allowed = allowed_tools_for_step(step_name)
            if allowed:  # If policy exists for this step, enforce it
                candidates = [c for c in candidates if c["id"] in allowed]
                if not candidates:
                    log("REGISTRY", f"⚠️ Tool policy filtered all tools for '{step_name}', falling back to standard tools")
                    candidates = [t for t in TOOL_DEFINITIONS if t["id"] in {"code_generator", "filewriterbatch", "filereader"}]
            else:
                # No policy for this step - allow all candidates through
                log("REGISTRY", f"📋 No tool policy for '{step_name}', allowing all candidates")


        # 2. Add 'No-Op' option (Standard Tools Only)
        candidates_with_noop = candidates.copy()
        candidates_with_noop.append({
            "id": "standard_tools_only",
            "description": "No special tools needed. Use ONLY standard code generation and file operations.",
            "value": {}
        })

        if settings.debug:
            log("REGISTRY", f"🔍 Routing query '{query[:50]}...' across {len(candidates)} candidates for step '{step_name}'")

        # 3. Route Query
        result = await arbormind_route(
            f"Select tools for: {query}", 
            candidates_with_noop, 
            top_k=top_k, 
            context_type=kwargs.get("context_type", "tool_selection"),
            archetype=kwargs.get("archetype", "unknown")
        )
        
        # SELF-EVOLUTION: Extract decision_id for outcome tracking
        decision_id = result.get("decision_id", "")
        
        # 4. Analyze Decision (Score Thresholding)
        top_match = result["selected"]
        top_score = result["ranked"][0]["score"] if result["ranked"] else 0.0
        
        # Threshold: if < 0.15, confidence is too low → default to standard
        if top_score < 0.15:
            if settings.debug:
                log("REGISTRY", f"📉 Low confidence ({top_score:.3f}). Defaulting to standard tools.")
            return {"tools": _get_standard_tools(), "decision_id": decision_id}

        # If explicit no-op wins
        if top_match == "standard_tools_only":
            if settings.debug:
                log("REGISTRY", f"✅ Selected 'standard_tools_only' (Score: {top_score:.3f})")
            return {"tools": _get_standard_tools(), "decision_id": decision_id}
        
        # 5. Build Result
        # Determine global configuration override (V parameter)
        global_config = result.get("value", {})
        
        selected_tools = []
        for r in result["ranked"]:
             if r["id"] == "standard_tools_only":
                 continue
                 
             # Use description from definition
             desc = r.get("description", "")
             
             selected_tools.append({
                 "id": r["id"],
                 "config": global_config,
                 "description": desc
             })
        
        # Enforce essentials for Robustness
        tools = _ensure_essentials(selected_tools, global_config)
        
        return {"tools": tools, "decision_id": decision_id}
        
    except Exception as e:
        log("REGISTRY", f"⚠️ Tool selection failed: {e}. using fallback")
        return {"tools": _get_standard_tools(), "decision_id": ""}

def _get_standard_tools() -> List[Dict[str, Any]]:
    """Return only the essential tools."""
    essentials = {"code_generator", "filewriterbatch", "filereader"}
    return [
        {"id": t["id"], "config": {}, "description": t["description"]} 
        for t in TOOL_DEFINITIONS if t["id"] in essentials
    ]

def _ensure_essentials(selected_tools: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Ensure essential tools are present in the list."""
    essentials = {"code_generator", "filewriterbatch", "filereader"}
    current_ids = {t["id"] for t in selected_tools}
    
    def_map = {t["id"]: t for t in TOOL_DEFINITIONS}
    
    result = selected_tools.copy()
    for ess in essentials:
        if ess not in current_ids:
            tool_def = def_map.get(ess, {})
            result.append({
                "id": ess, 
                "config": config,
                "description": tool_def.get("description", "")
            })
    return result

