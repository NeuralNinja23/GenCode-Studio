from .specs import ToolSpec


# ═══════════════════════════════════════════════════════════════
# NEW DECLARATIVE TOOLS (7)
# ═══════════════════════════════════════════════════════════════

ARCHITECTURE_WRITER = ToolSpec(
    id="architecture_writer",
    description="Generates architecture.md only",
    output_type="markdown",
    writes_files=["architecture.md"],
    allowed_steps=["architecture"]
)

CONTRACT_WRITER = ToolSpec(
    id="contract_writer",
    description="Generates contracts.md from frontend artifacts",
    output_type="markdown",
    writes_files=["contracts.md"],
    allowed_steps=["contracts"]
)

ROUTER_SCAFFOLD_GENERATOR = ToolSpec(
    id="router_scaffold_generator",
    description="Generates FastAPI router skeletons without logic",
    output_type="code",
    writes_files=["backend/app/routers/*.py"],
    allows_partial=True,
    allowed_steps=["backend_implementation"]
)

ROUTER_LOGIC_FILLER = ToolSpec(
    id="router_logic_filler",
    description="Fills logic inside an existing router file",
    output_type="patch",
    writes_files=["backend/app/routers/*.py"],
    allows_partial=True,
    allowed_steps=["backend_implementation", "healing"]
)

CODE_PATCH_APPLIER = ToolSpec(
    id="code_patch_applier",
    description="Applies unified diffs only (no file rewrites)",
    output_type="patch",
    writes_files=["*"],
    allows_partial=True,
    allowed_steps=["healing", "frontend_integration", "backend_implementation"]
)

STATIC_CODE_VALIDATOR = ToolSpec(
    id="static_code_validator",
    description="Validates syntax/imports without executing code",
    output_type="json",
    writes_files=[],
    allows_execution="static",
    allowed_steps=["frontend_mock", "frontend_integration", "backend_implementation"]
)

ENVIRONMENT_GUARD = ToolSpec(
    id="environment_guard",
    description="Detects OS and capability constraints",
    output_type="json",
    writes_files=[],
    allowed_steps=["*"]
)


# ═══════════════════════════════════════════════════════════════
# EXISTING TOOLS MAPPED TO SPECS (31)
# ═══════════════════════════════════════════════════════════════

# --- CORE AGENT ---
CODE_GENERATOR = ToolSpec(
    id="code_generator",
    description="Generate, refactor, or fix code using specialized AI agents",
    output_type="code",
    writes_files=["*"],
    allows_partial=True,
    allowed_steps=["*"]  # Universal - can be used anywhere
)

SUBAGENT_CALLER = ToolSpec(
    id="subagentcaller",
    description="Directly call a sub-agent (Derek, Luna, Victoria)",
    output_type="code",
    writes_files=["*"],
    allows_partial=True,
    allowed_steps=["*"]
)

# --- FILE OPERATIONS ---
FILEWRITER_BATCH = ToolSpec(
    id="filewriterbatch",
    description="Create or overwrite multiple files at once",
    output_type="code",
    writes_files=["*"],
    allows_partial=False,
    allowed_steps=["*"]
)

FILEREADER = ToolSpec(
    id="filereader",
    description="Read content of existing files",
    output_type="none",
    writes_files=[],
    allowed_steps=["*"]
)

FILEDELETER = ToolSpec(
    id="filedeleter",
    description="Delete files or directories",
    output_type="none",
    writes_files=[],
    allowed_steps=["healing", "backend_implementation", "frontend_integration"]
)

FILELISTER = ToolSpec(
    id="filelister",
    description="List files in directory, explore project structure",
    output_type="json",
    writes_files=[],
    allowed_steps=["*"]
)

CODEVIEWER = ToolSpec(
    id="codeviewer",
    description="View specific symbols (class, function) in a file",
    output_type="none",
    writes_files=[],
    allowed_steps=["*"]
)

# --- EXECUTION ---
SANDBOX_EXEC = ToolSpec(
    id="sandboxexec",
    description="Execute shell commands in Docker container",
    output_type="none",
    writes_files=[],
    allows_execution="runtime",
    allows_network=True,
    allows_shell=True,
    allowed_steps=["testing_backend", "testing_frontend", "system_integration"]
)

BASH_RUNNER = ToolSpec(
    id="bashrunner",
    description="Run advanced bash scripts or complex commands",
    output_type="none",
    writes_files=[],
    allows_execution="runtime",
    allows_shell=True,
    allowed_steps=["testing_backend", "system_integration"]
)

PYTHON_EXECUTOR = ToolSpec(
    id="pythonexecutor",
    description="Execute Python scripts or snippets directly",
    output_type="none",
    writes_files=[],
    allows_execution="runtime",
    allowed_steps=["testing_backend", "backend_implementation"]
)

NPM_RUNNER = ToolSpec(
    id="npmrunner",
    description="Run npm/bun/yarn commands (install, build, test)",
    output_type="none",
    writes_files=[],
    allows_execution="runtime",
    allows_shell=True,
    allowed_steps=["testing_frontend", "frontend_integration"]
)

# --- TESTING & QUALITY ---
PYTEST_RUNNER = ToolSpec(
    id="pytestrunner",
    description="Run backend python unit tests using pytest",
    output_type="json",
    writes_files=[],
    allows_execution="runtime",
    allowed_steps=["testing_backend"]
)

PLAYWRIGHT_RUNNER = ToolSpec(
    id="playwrightrunner",
    description="Run frontend E2E browser tests using playwright",
    output_type="json",
    writes_files=[],
    allows_execution="runtime",
    allows_network=True,
    allowed_steps=["testing_frontend"],
    # Phase 2: Prevent Playwright from being selected on Windows
    environment_constraints={"os": ["linux", "darwin"]}  # NOT Windows
)

TEST_GENERATOR = ToolSpec(
    id="testgenerator",
    description="Generate new test files based on code",
    output_type="code",
    writes_files=["backend/tests/*.py", "frontend/tests/*.spec.js"],
    allowed_steps=["testing_backend", "testing_frontend"]
)

SYNTAX_VALIDATOR = ToolSpec(
    id="syntaxvalidator",
    description="Check syntax of code files without running them",
    output_type="json",
    writes_files=[],
    allows_execution="static",
    allowed_steps=["*"]
)

# --- PATCHING ---
UNIFIED_PATCH_APPLIER = ToolSpec(
    id="unifiedpatchapplier",
    description="Apply strict diffs (unified format) with minimal edits",
    output_type="patch",
    writes_files=["*"],
    allows_partial=True,
    allowed_steps=["healing", "backend_implementation", "frontend_integration"]
)

JSON_PATCH_APPLIER = ToolSpec(
    id="jsonpatchapplier",
    description="Apply JSON patches to data files",
    output_type="patch",
    writes_files=["*.json"],
    allows_partial=True,
    allowed_steps=["healing", "contracts"]
)

# --- DATABASE ---
DB_SCHEMA_READER = ToolSpec(
    id="dbschemareader",
    description="Introspect database schema/collections",
    output_type="json",
    writes_files=[],
    allowed_steps=["analysis", "architecture", "backend_implementation"]
)

DB_QUERY_RUNNER = ToolSpec(
    id="dbqueryrunner",
    description="Run specific queries against the database",
    output_type="json",
    writes_files=[],
    allows_execution="runtime",
    allowed_steps=["testing_backend", "backend_implementation"]
)

# --- DEPLOYMENT & DEVOPS ---
DOCKER_BUILDER = ToolSpec(
    id="dockerbuilder",
    description="Build Docker images",
    output_type="none",
    writes_files=[],
    allows_execution="runtime",
    allows_shell=True,
    allowed_steps=["preview_final"]
)

VERCEL_DEPLOYER = ToolSpec(
    id="verceldeployer",
    description="Deploy frontend to Vercel",
    output_type="json",
    writes_files=[],
    allows_execution="runtime",
    allows_network=True,
    allowed_steps=["preview_final"]
)

DEPLOYMENT_VALIDATOR = ToolSpec(
    id="deploymentvalidator",
    description="Validate health of a deployed application",
    output_type="json",
    writes_files=[],
    allows_network=True,
    allowed_steps=["preview_final", "system_integration"]
)

KEY_VALIDATOR = ToolSpec(
    id="keyvalidator",
    description="Validate API keys and environment secrets",
    output_type="json",
    writes_files=[],
    allowed_steps=["analysis", "architecture"]
)

# --- VISUAL & UX ---
UX_VISUALIZER = ToolSpec(
    id="uxvisualizer",
    description="Render UI component preview or wireframe",
    output_type="json",
    writes_files=[],
    allows_network=True,  # May call external rendering APIs
    allowed_steps=["frontend_mock", "screenshot_verify"]
)

SCREENSHOT_COMPARER = ToolSpec(
    id="screenshotcomparer",
    description="Compare UI screenshots for regression",
    output_type="json",
    writes_files=[],
    allowed_steps=["screenshot_verify", "testing_frontend"]
)

# --- WEB & RESEARCH ---
WEB_RESEARCHER = ToolSpec(
    id="webresearcher",
    description="Search the web for documentation or solutions",
    output_type="markdown",
    writes_files=[],
    allows_network=True,
    allowed_steps=["analysis", "architecture"]
)

API_TESTER = ToolSpec(
    id="apitester",
    description="Test external API endpoints",
    output_type="json",
    writes_files=[],
    allows_network=True,
    allowed_steps=["testing_backend", "system_integration"]
)

HEALTH_CHECKER = ToolSpec(
    id="healthchecker",
    description="Check system health status",
    output_type="json",
    writes_files=[],
    allows_network=True,
    allowed_steps=["system_integration", "preview_final"]
)

# --- USER INTERACTION ---
USER_CONFIRMER = ToolSpec(
    id="userconfirmer",
    description="Ask user for explicit confirmation",
    output_type="none",
    writes_files=[],
    allowed_steps=["*"]
)

USER_PROMPTER = ToolSpec(
    id="userprompter",
    description="Prompt user for input",
    output_type="none",
    writes_files=[],
    allowed_steps=["*"]
)


# ═══════════════════════════════════════════════════════════════
# COMBINED REGISTRY
# ═══════════════════════════════════════════════════════════════

ALL_TOOLS = [
    # New declarative tools (7)
    ARCHITECTURE_WRITER,
    CONTRACT_WRITER,
    ROUTER_SCAFFOLD_GENERATOR,
    ROUTER_LOGIC_FILLER,
    CODE_PATCH_APPLIER,
    STATIC_CODE_VALIDATOR,
    ENVIRONMENT_GUARD,
    
    # Existing tools mapped to specs (31)
    CODE_GENERATOR,
    SUBAGENT_CALLER,
    FILEWRITER_BATCH,
    FILEREADER,
    FILEDELETER,
    FILELISTER,
    CODEVIEWER,
    SANDBOX_EXEC,
    BASH_RUNNER,
    PYTHON_EXECUTOR,
    NPM_RUNNER,
    PYTEST_RUNNER,
    PLAYWRIGHT_RUNNER,
    TEST_GENERATOR,
    SYNTAX_VALIDATOR,
    UNIFIED_PATCH_APPLIER,
    JSON_PATCH_APPLIER,
    DB_SCHEMA_READER,
    DB_QUERY_RUNNER,
    DOCKER_BUILDER,
    VERCEL_DEPLOYER,
    DEPLOYMENT_VALIDATOR,
    KEY_VALIDATOR,
    UX_VISUALIZER,
    SCREENSHOT_COMPARER,
    WEB_RESEARCHER,
    API_TESTER,
    HEALTH_CHECKER,
    USER_CONFIRMER,
    USER_PROMPTER,
]

# Deprecated - use ALL_TOOLS
ALL_NEW_TOOLS = ALL_TOOLS
