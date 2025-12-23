# app/tools/tools.py
"""
═══════════════════════════════════════════════════════════════════════════════
GENCODE TOOL REGISTRY - SINGLE SOURCE OF TRUTH

All 33 tools defined in ONE place:
- ID
- Implementation function
- Capabilities
- Phases (allowed steps)
- Metadata (description, pre/post flags)

NO OTHER FILE should define "what tools exist".
═══════════════════════════════════════════════════════════════════════════════
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable, FrozenSet, Set
from enum import Enum, unique
from functools import wraps
import asyncio


# ═══════════════════════════════════════════════════════════════════════════════
# CAPABILITY TAXONOMY
# ═══════════════════════════════════════════════════════════════════════════════

@unique
class Capability(Enum):
    """What a tool CAN DO."""
    # Generation
    GENERATE_CODE = "generate_code"
    GENERATE_ARCHITECTURE = "generate_architecture"
    GENERATE_TESTS = "generate_tests"
    
    # Validation
    VALIDATE_SYNTAX = "validate_syntax"
    VALIDATE_SCHEMA = "validate_schema"
    LINT_CODE = "lint_code"
    
    # Execution
    EXECUTE_PYTHON = "execute_python"
    EXECUTE_SHELL = "execute_shell"
    EXECUTE_TESTS = "execute_tests"
    
    # File Operations
    READ_FILES = "read_files"
    WRITE_FILES = "write_files"
    DELETE_FILES = "delete_files"
    LIST_FILES = "list_files"
    
    # Patching
    APPLY_PATCH = "apply_patch"
    
    # Environment
    DETECT_ENVIRONMENT = "detect_environment"
    CHECK_DEPENDENCIES = "check_dependencies"
    
    # Database
    READ_SCHEMA = "read_schema"
    EXECUTE_QUERY = "execute_query"
    
    # Testing
    RUN_PYTEST = "run_pytest"
    RUN_PLAYWRIGHT = "run_playwright"
    
    # Deployment
    BUILD_DOCKER = "build_docker"
    DEPLOY_VERCEL = "deploy_vercel"
    CHECK_HEALTH = "check_health"
    
    # Research
    SEARCH_WEB = "search_web"
    TEST_API = "test_api"
    
    # UI
    RENDER_PREVIEW = "render_preview"
    COMPARE_SCREENSHOTS = "compare_screenshots"
    
    # User Interaction
    PROMPT_USER = "prompt_user"
    CONFIRM_USER = "confirm_user"
    
    # Runtime (Phase B - Execution Reality)
    BOOTSTRAP_RUNTIME = "bootstrap_runtime"


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL DEFINITION DATACLASS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ToolDefinition:
    """Complete definition of a tool."""
    id: str
    func: Callable
    capabilities: FrozenSet[Capability]
    phases: FrozenSet[str]
    description: str
    is_pre_step: bool = False
    is_post_step: bool = False
    required_for_phase: bool = False
    writes_files: List[str] = field(default_factory=list)
    allows_execution: Optional[str] = None  # None, "static", "runtime"
    
    # PHASE C1: Argument enforcement
    required_args: List[str] = field(default_factory=list)
    optional_args: List[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL REGISTRY (populated by @tool decorator)
# ═══════════════════════════════════════════════════════════════════════════════

TOOLS: Dict[str, ToolDefinition] = {}


def tool(
    id: str,
    capabilities: List[Capability],
    phases: List[str],
    description: str = "",
    is_pre: bool = False,
    is_post: bool = False,
    required: bool = False,
    writes_files: List[str] = None,
    allows_execution: str = None,
    required_args: List[str] = None,  # PHASE C1
    optional_args: List[str] = None,  # PHASE C1
):
    """
    Decorator to register a tool.
    
    Usage:
        @tool(
            id="subagentcaller",
            capabilities=[Capability.GENERATE_CODE],
            phases=["*"],
            description="Call sub-agents for code generation",
            required_args=["step_name"],
        )
        async def tool_sub_agent_caller(args):
            ...
    """
    def decorator(func):
        TOOLS[id] = ToolDefinition(
            id=id,
            func=func,
            capabilities=frozenset(capabilities),
            phases=frozenset(phases),
            description=description,
            is_pre_step=is_pre,
            is_post_step=is_post,
            required_for_phase=required,
            writes_files=writes_files or [],
            allows_execution=allows_execution,
            required_args=required_args or [],
            optional_args=optional_args or [],
        )
        
        @wraps(func)
        async def wrapper(args: Dict[str, Any] = None):
            return await func(args or {})
        
        return wrapper
    return decorator


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL #1: SUBAGENT CALLER (Core Agent)
# ═══════════════════════════════════════════════════════════════════════════════

@tool(
    id="subagentcaller",
    capabilities=[Capability.GENERATE_CODE, Capability.GENERATE_ARCHITECTURE, Capability.GENERATE_TESTS],
    phases=["*"],
    description="Call sub-agents (Derek, Victoria, Luna) for code generation",
    required=True,
)
async def tool_subagentcaller(args: Dict[str, Any]) -> Dict[str, Any]:
    """Core LLM caller - delegates to Marcus/sub-agents."""
    # Import the full implementation from implementations.py
    from app.tools.implementations import tool_sub_agent_caller as impl
    return await impl(args)


# ═══════════════════════════════════════════════════════════════════════════════
# TOOLS #2-6: FILE OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════════

@tool(
    id="filewriterbatch",
    capabilities=[Capability.WRITE_FILES],
    phases=["*"],
    description="Write multiple files at once",
    writes_files=["*"],
)
async def tool_filewriterbatch(args: Dict[str, Any]) -> Dict[str, Any]:
    from app.tools.implementations import tool_file_writer_batch as impl
    return await impl(args)


@tool(
    id="filereader",
    capabilities=[Capability.READ_FILES],
    phases=["*"],
    description="Read a single file",
    is_pre=True,
)
async def tool_filereader(args: Dict[str, Any]) -> Dict[str, Any]:
    from app.tools.implementations import tool_file_reader as impl
    return await impl(args)


@tool(
    id="filedeleter",
    capabilities=[Capability.DELETE_FILES],
    phases=["healing", "backend_routers"],
    description="Delete files or directories",
)
async def tool_filedeleter(args: Dict[str, Any]) -> Dict[str, Any]:
    from app.tools.implementations import tool_file_deleter as impl
    return await impl(args)


@tool(
    id="filelister",
    capabilities=[Capability.LIST_FILES],
    phases=["*"],
    description="List files in directory",
    is_pre=True,
)
async def tool_filelister(args: Dict[str, Any]) -> Dict[str, Any]:
    from app.tools.implementations import tool_file_lister as impl
    return await impl(args)


@tool(
    id="codeviewer",
    capabilities=[Capability.READ_FILES],
    phases=["*"],
    description="View code with metadata",
    is_pre=True,
)
async def tool_codeviewer(args: Dict[str, Any]) -> Dict[str, Any]:
    from app.tools.implementations import tool_code_viewer as impl
    return await impl(args)


# ═══════════════════════════════════════════════════════════════════════════════
# TOOLS #7-9: EXECUTION
# ═══════════════════════════════════════════════════════════════════════════════

@tool(
    id="bashrunner",
    capabilities=[Capability.EXECUTE_SHELL],
    phases=["testing_backend", "system_integration"],
    description="Run shell commands",
    allows_execution="runtime",
)
async def tool_bashrunner(args: Dict[str, Any]) -> Dict[str, Any]:
    from app.tools.implementations import tool_bash_runner as impl
    return await impl(args)


@tool(
    id="pythonexecutor",
    capabilities=[Capability.EXECUTE_PYTHON],
    phases=["testing_backend", "system_integration"],
    description="Execute Python code",
    allows_execution="runtime",
)
async def tool_pythonexecutor(args: Dict[str, Any]) -> Dict[str, Any]:
    from app.tools.implementations import tool_python_executor as impl
    return await impl(args)


@tool(
    id="npmrunner",
    capabilities=[Capability.EXECUTE_SHELL],
    phases=["frontend_mock", "testing_frontend"],
    description="Run npm commands",
    allows_execution="runtime",
)
async def tool_npmrunner(args: Dict[str, Any]) -> Dict[str, Any]:
    from app.tools.implementations import tool_npm_runner as impl
    return await impl(args)


@tool(
    id="sandboxexec",
    capabilities=[Capability.EXECUTE_SHELL, Capability.EXECUTE_PYTHON],
    phases=["testing_backend", "testing_frontend", "system_integration"],
    description="Execute in Docker sandbox",
    allows_execution="runtime",
)
async def tool_sandboxexec(args: Dict[str, Any]) -> Dict[str, Any]:
    from app.tools.implementations import tool_sandbox_exec as impl
    return await impl(args)


# ═══════════════════════════════════════════════════════════════════════════════
# TOOLS #10-13: TESTING
# ═══════════════════════════════════════════════════════════════════════════════

@tool(
    id="pytestrunner",
    capabilities=[Capability.RUN_PYTEST, Capability.EXECUTE_TESTS],
    phases=["testing_backend"],
    description="Run pytest tests",
    is_post=True,
)
async def tool_pytestrunner(args: Dict[str, Any]) -> Dict[str, Any]:
    from app.tools.implementations import tool_pytest_runner as impl
    return await impl(args)


@tool(
    id="playwrightrunner",
    capabilities=[Capability.RUN_PLAYWRIGHT, Capability.EXECUTE_TESTS],
    phases=["testing_frontend"],
    description="Run Playwright E2E tests",
    is_post=True,
)
async def tool_playwrightrunner(args: Dict[str, Any]) -> Dict[str, Any]:
    from app.tools.implementations import tool_playwright_runner as impl
    return await impl(args)


@tool(
    id="testgenerator",
    capabilities=[Capability.GENERATE_TESTS],
    phases=["testing_backend", "testing_frontend"],
    description="Generate test files",
)
async def tool_testgenerator(args: Dict[str, Any]) -> Dict[str, Any]:
    from app.tools.implementations import tool_test_generator as impl
    return await impl(args)


# ═══════════════════════════════════════════════════════════════════════════════
# TOOLS #14-18: VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

@tool(
    id="syntaxvalidator",
    capabilities=[Capability.VALIDATE_SYNTAX],
    phases=["*"],
    description="Validate syntax (Python/JS)",
    is_post=True,
    allows_execution="static",
)
async def tool_syntaxvalidator(args: Dict[str, Any]) -> Dict[str, Any]:
    from app.tools.implementations import tool_syntax_validator as impl
    return await impl(args)


@tool(
    id="static_code_validator",
    capabilities=[Capability.VALIDATE_SYNTAX, Capability.LINT_CODE],
    phases=["frontend_mock", "backend_models", "backend_routers"],
    description="Static code validation (advisory)",
    is_post=True,
    allows_execution="static",
)
async def tool_static_code_validator(args: Dict[str, Any]) -> Dict[str, Any]:
    from app.tools.implementations import tool_static_code_validator as impl
    return await impl(args)


@tool(
    id="deploymentvalidator",
    capabilities=[Capability.CHECK_HEALTH],
    phases=["system_integration", "preview_final"],
    description="Validate deployment config",
    is_post=True,
)
async def tool_deploymentvalidator(args: Dict[str, Any]) -> Dict[str, Any]:
    from app.tools.implementations import tool_deployment_validator as impl
    return await impl(args)


@tool(
    id="keyvalidator",
    capabilities=[Capability.CHECK_DEPENDENCIES],
    phases=["*"],
    description="Validate API keys and secrets",
    is_pre=True,
)
async def tool_keyvalidator(args: Dict[str, Any]) -> Dict[str, Any]:
    from app.tools.implementations import tool_key_validator as impl
    return await impl(args)


@tool(
    id="crossllmvalidator",
    capabilities=[Capability.VALIDATE_SYNTAX],
    phases=["architecture", "backend_models"],
    description="Cross-validate with another LLM",
)
async def tool_crossllmvalidator(args: Dict[str, Any]) -> Dict[str, Any]:
    from app.tools.implementations import tool_cross_llm_validator as impl
    return await impl(args)


# ═══════════════════════════════════════════════════════════════════════════════
# TOOLS #19-20: ENVIRONMENT
# ═══════════════════════════════════════════════════════════════════════════════

@tool(
    id="environment_guard",
    capabilities=[Capability.DETECT_ENVIRONMENT, Capability.CHECK_DEPENDENCIES],
    phases=["*"],
    description="Check system environment",
    is_pre=True,
)
async def tool_environment_guard(args: Dict[str, Any]) -> Dict[str, Any]:
    from app.tools.implementations import tool_environment_guard as impl
    return await impl(args)


# ═══════════════════════════════════════════════════════════════════════════════
# TOOLS #21-22: DATABASE
# ═══════════════════════════════════════════════════════════════════════════════

@tool(
    id="dbschemareader",
    capabilities=[Capability.READ_SCHEMA],
    phases=["architecture", "backend_models"],
    description="Read database schema",
    is_pre=True,
)
async def tool_dbschemareader(args: Dict[str, Any]) -> Dict[str, Any]:
    from app.tools.implementations import tool_db_schema_reader as impl
    return await impl(args)


@tool(
    id="dbqueryrunner",
    capabilities=[Capability.EXECUTE_QUERY],
    phases=["testing_backend"],
    description="Execute database queries",
)
async def tool_dbqueryrunner(args: Dict[str, Any]) -> Dict[str, Any]:
    from app.tools.implementations import tool_db_query_runner as impl
    return await impl(args)


# ═══════════════════════════════════════════════════════════════════════════════
# TOOLS #23-25: DEPLOYMENT
# ═══════════════════════════════════════════════════════════════════════════════

@tool(
    id="dockerbuilder",
    capabilities=[Capability.BUILD_DOCKER],
    phases=["system_integration", "preview_final"],
    description="Build Docker images",
)
async def tool_dockerbuilder(args: Dict[str, Any]) -> Dict[str, Any]:
    from app.tools.implementations import tool_docker_builder as impl
    return await impl(args)


@tool(
    id="verceldeployer",
    capabilities=[Capability.DEPLOY_VERCEL],
    phases=["preview_final"],
    description="Deploy to Vercel",
)
async def tool_verceldeployer(args: Dict[str, Any]) -> Dict[str, Any]:
    from app.tools.implementations import tool_vercel_deployer as impl
    return await impl(args)


@tool(
    id="healthchecker",
    capabilities=[Capability.CHECK_HEALTH],
    phases=["system_integration", "preview_final"],
    description="Check service health",
    is_post=True,
)
async def tool_healthchecker(args: Dict[str, Any]) -> Dict[str, Any]:
    from app.tools.implementations import tool_health_checker as impl
    return await impl(args)


# ═══════════════════════════════════════════════════════════════════════════════
# TOOLS #26-28: WEB/API
# ═══════════════════════════════════════════════════════════════════════════════

@tool(
    id="webresearcher",
    capabilities=[Capability.SEARCH_WEB],
    phases=["architecture"],
    description="Search the web for information",
    is_pre=True,
)
async def tool_webresearcher(args: Dict[str, Any]) -> Dict[str, Any]:
    from app.tools.implementations import tool_web_researcher as impl
    return await impl(args)


@tool(
    id="apitester",
    capabilities=[Capability.TEST_API],
    phases=["testing_backend", "system_integration"],
    description="Test API endpoints",
    is_post=True,
)
async def tool_apitester(args: Dict[str, Any]) -> Dict[str, Any]:
    from app.tools.implementations import tool_api_tester as impl
    return await impl(args)


# ═══════════════════════════════════════════════════════════════════════════════
# TOOLS #29-30: VISUAL
# ═══════════════════════════════════════════════════════════════════════════════

@tool(
    id="uxvisualizer",
    capabilities=[Capability.RENDER_PREVIEW],
    phases=["frontend_mock"],
    description="Render UI preview",
    is_post=True,
)
async def tool_uxvisualizer(args: Dict[str, Any]) -> Dict[str, Any]:
    from app.tools.implementations import tool_ux_visualizer as impl
    return await impl(args)


@tool(
    id="screenshotcomparer",
    capabilities=[Capability.COMPARE_SCREENSHOTS],
    phases=["testing_frontend"],
    description="Compare screenshots",
    is_post=True,
)
async def tool_screenshotcomparer(args: Dict[str, Any]) -> Dict[str, Any]:
    from app.tools.implementations import tool_screenshot_comparer as impl
    return await impl(args)


# ═══════════════════════════════════════════════════════════════════════════════
# TOOLS #31-32: USER INTERACTION
# ═══════════════════════════════════════════════════════════════════════════════

@tool(
    id="userconfirmer",
    capabilities=[Capability.CONFIRM_USER],
    phases=["*"],
    description="Request user confirmation",
)
async def tool_userconfirmer(args: Dict[str, Any]) -> Dict[str, Any]:
    from app.tools.implementations import tool_user_confirmer as impl
    return await impl(args)


@tool(
    id="userprompter",
    capabilities=[Capability.PROMPT_USER],
    phases=["*"],
    description="Prompt user for input",
)
async def tool_userprompter(args: Dict[str, Any]) -> Dict[str, Any]:
    from app.tools.implementations import tool_user_prompter as impl
    return await impl(args)


# ═══════════════════════════════════════════════════════════════════════════════
# TOOLS #33-36: PATCHING
# ═══════════════════════════════════════════════════════════════════════════════

@tool(
    id="unifiedpatchapplier",
    capabilities=[Capability.APPLY_PATCH],
    phases=["healing", "backend_routers"],
    description="Apply unified diffs",
)
async def tool_unifiedpatchapplier(args: Dict[str, Any]) -> Dict[str, Any]:
    from app.tools.implementations import tool_unified_patch_applier as impl
    return await impl(args)


@tool(
    id="jsonpatchapplier",
    capabilities=[Capability.APPLY_PATCH],
    phases=["healing"],
    description="Apply JSON patches",
)
async def tool_jsonpatchapplier(args: Dict[str, Any]) -> Dict[str, Any]:
    from app.tools.implementations import tool_json_patch_applier as impl
    return await impl(args)


@tool(
    id="code_patch_applier",
    capabilities=[Capability.APPLY_PATCH],
    phases=["healing", "backend_routers"],
    description="Wrapper for patch tools",
)
async def tool_code_patch_applier(args: Dict[str, Any]) -> Dict[str, Any]:
    from app.tools.implementations import tool_code_patch_applier as impl
    return await impl(args)


# ═══════════════════════════════════════════════════════════════════════════════
# TOOLS #37-39: NEW DECLARATIVE TOOLS
# ═══════════════════════════════════════════════════════════════════════════════

@tool(
    id="architecture_writer",
    capabilities=[Capability.GENERATE_ARCHITECTURE],
    phases=["architecture"],
    description="Generate architecture docs only",
    required=True,
)
async def tool_architecture_writer(args: Dict[str, Any]) -> Dict[str, Any]:
    from app.tools.implementations import tool_architecture_writer as impl
    return await impl(args)


@tool(
    id="router_scaffold_generator",
    capabilities=[Capability.GENERATE_CODE],
    phases=["backend_routers"],
    description="Generate router skeletons",
)
async def tool_router_scaffold_generator(args: Dict[str, Any]) -> Dict[str, Any]:
    from app.tools.implementations import tool_router_scaffold_generator as impl
    return await impl(args)


@tool(
    id="router_logic_filler",
    capabilities=[Capability.GENERATE_CODE, Capability.APPLY_PATCH],
    phases=["backend_routers", "healing"],
    description="Fill logic into router scaffolds",
)
async def tool_router_logic_filler(args: Dict[str, Any]) -> Dict[str, Any]:
    from app.tools.implementations import tool_router_logic_filler as impl
    return await impl(args)


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE B: RUNTIME BOOTSTRAP (EXECUTION REALITY)
# ═══════════════════════════════════════════════════════════════════════════════

@tool(
    id="runtime_bootstrap",
    capabilities=[Capability.BOOTSTRAP_RUNTIME, Capability.CHECK_HEALTH],
    phases=["system_integration", "testing_backend", "testing_frontend", "preview_final"],
    description="Start runtime (Docker/local) and block until ready",
    is_pre=True,
    required=True,  # MANDATORY for execution steps
)
async def tool_runtime_bootstrap(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    PHASE B1: Runtime Bootstrap Tool
    
    Runs ONCE after backend_routers, BEFORE any execution step.
    
    Responsibilities:
    - Detect stack (FastAPI + frontend)
    - Start runtime (Docker or local)
    - Block until process started OR failed definitively
    
    Returns:
        {
            "running": bool,
            "mode": "docker" | "local" | "none",
            "ports": {"backend": 8000, "frontend": 3000},
            "container_ids": [...],
            "logs_tail": "..."
        }
    """
    from app.tools.implementations import tool_runtime_bootstrap as impl
    return await impl(args)


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def get_tool(tool_id: str) -> Optional[ToolDefinition]:
    """Get a tool by ID."""
    return TOOLS.get(tool_id)


def get_all_tools() -> Dict[str, ToolDefinition]:
    """Get all registered tools."""
    return TOOLS


def get_tools_for_phase(phase: str) -> List[ToolDefinition]:
    """Get all tools available for a specific phase."""
    return [
        t for t in TOOLS.values()
        if "*" in t.phases or phase in t.phases
    ]


def get_tools_with_capability(cap: Capability) -> List[ToolDefinition]:
    """Get all tools with a specific capability."""
    return [t for t in TOOLS.values() if cap in t.capabilities]


def get_pre_step_tools(phase: str) -> List[ToolDefinition]:
    """Get pre-step tools for a phase."""
    return [
        t for t in get_tools_for_phase(phase)
        if t.is_pre_step
    ]


def get_post_step_tools(phase: str) -> List[ToolDefinition]:
    """Get post-step tools for a phase."""
    return [
        t for t in get_tools_for_phase(phase)
        if t.is_post_step
    ]


async def run_tool(tool_id: str = None, args: Dict[str, Any] = None, *, name: str = None) -> Dict[str, Any]:
    """
    Run a tool by ID.
    
    Supports both:
    - run_tool("toolname", args)
    - run_tool(name="toolname", args=args)
    """
    # Handle both tool_id and name
    actual_id = tool_id or name
    if not actual_id:
        return {"success": False, "error": "tool_id or name is required"}
    
    tool_def = TOOLS.get(actual_id)
    if not tool_def:
        return {"success": False, "error": f"Unknown tool: {actual_id}"}
    
    try:
        return await tool_def.func(args or {})
    except Exception as e:
        return {"success": False, "error": str(e), "tool": actual_id}


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Core
    "Capability",
    "ToolDefinition",
    "TOOLS",
    "tool",
    # Query functions
    "get_tool",
    "get_all_tools",
    "get_tools_for_phase",
    "get_tools_with_capability",
    "get_pre_step_tools",
    "get_post_step_tools",
    "run_tool",
]


# ═══════════════════════════════════════════════════════════════════════════════
# VERIFICATION (run on import)
# ═══════════════════════════════════════════════════════════════════════════════

def _verify_registry():
    """Verify all tools are registered correctly."""
    count = len(TOOLS)
    if count < 33:
        print(f"⚠️ Warning: Only {count} tools registered, expected 33+")
    else:
        print(f"✅ Tool registry: {count} tools loaded")


# Run verification on import
_verify_registry()
