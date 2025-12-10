# GenCode Studio Python - Complete Codebase Architecture

## Overview

GenCode Studio is an AI-powered code generation platform that uses a multi-agent workflow system to generate full-stack applications. The system follows an **Emergent E1-style Frontend-First** pattern, prioritizing UI development with mock data before backend integration.

---

## Directory Structure

```
GenCode Studio Python/
├── Backend/                    # Python FastAPI backend
│   └── app/
│       ├── api/               # REST API routes
│       ├── core/              # Core config, types, constants
│       ├── db/                # MongoDB connection
│       ├── lib/               # Utility libraries
│       ├── llm/               # LLM providers and adapters
│       ├── models/            # Beanie ODM models
│       ├── persistence/       # File persistence layer
│       ├── sandbox/           # Docker sandbox management
│       ├── testing/           # Self-healing test system
│       ├── tools/             # Agent tool implementations
│       ├── tracking/          # Memory, metrics, snapshots
│       ├── utils/             # Utilities (parser, validator)
│       ├── validation/        # Syntax validation
│       └── workflow/          # Workflow engine (core)
│           ├── agents/        # Sub-agent system
│           ├── engine_v2/     # FAST v2 orchestrator
│           ├── handlers/      # Step handlers
│           └── supervision/   # Quality gates
├── Frontend/                  # React TypeScript frontend
│   └── src/
│       ├── components/        # UI components
│       ├── pages/             # Page components
│       ├── services/          # API services
│       └── hooks/             # Custom React hooks
└── templates/                 # Project scaffolding templates
```

---

## Core Workflow (12 Steps)

The workflow follows the **Emergent E1-style Frontend-First** pattern:

| Step | Name | Agent | Description |
|------|------|-------|-------------|
| 1 | Analysis | Marcus | Understand and clarify requirements |
| 2 | Architecture | Victoria | Design system architecture |
| 3 | Frontend Mock | Derek | Create frontend with mock data (aha moment!) |
| 4 | Screenshot Verify | Marcus | Visual QA of frontend |
| 5 | Contracts | Marcus | Define API contracts |
| 6 | Backend Models | Derek | Create database models |
| 7 | Backend Routers | Derek | Create API endpoints |
| 8 | Backend Main | Derek | Wire up main app |
| 9 | Testing Backend | Derek | Run pytest |
| 10 | Frontend Integration | Derek | Replace mock with real API |
| 11 | Testing Frontend | Luna | E2E tests with Playwright |
| 12 | Preview | Marcus | Show running application |

---

## Agent System

### Agent Roles

| Agent | Role | Responsibilities |
|-------|------|------------------|
| **Marcus** | Lead AI Architect & Supervisor | Reviews code quality, orchestrates team, manages quality gates |
| **Victoria** | Senior Solutions Architect | Designs architecture, creates contracts |
| **Derek** | Senior Full-Stack Developer | Implements frontend and backend code |
| **Luna** | QA and DevOps Engineer | Creates and runs Playwright E2E tests |

### Sub-Agent System (`app/workflow/agents/sub_agents.py`)

- `call_sub_agent()` - Main entry point for agent calls
- `call_derek()` - Derek for code implementation
- `call_luna()` - Luna for testing
- `call_victoria()` - Victoria for architecture
- Includes prompt optimization and differential retry logic

---

## Engine Architecture

### Engine Versions

1. **Legacy Engine** (`engine.py`) - Sequential execution
2. **FAST v1 Engine** (`fast_engine.py`) - Parallel batch execution
3. **FAST v2 Engine** (`engine_v2/`) - **Current default** - Dependency barriers + self-healing

### FAST v2 Components

| Component | File | Purpose |
|-----------|------|---------|
| `FASTOrchestratorV2` | `fast_orchestrator.py` | Main orchestrator with dependency barriers |
| `TaskGraph` | `task_graph.py` | Defines step order and dependencies |
| `StepContracts` | `step_contracts.py` | Per-step output contracts |
| `BudgetManager` | `budget_manager.py` | Token/cost tracking and policies |
| `CriticalStepBarriers` | `critical_barriers.py` | Prevents continuation if critical steps fail |
| `LLMOutputIntegrity` | `llm_output_integrity.py` | Structural validation before review |
| `StructuralCompiler` | `structural_compiler.py` | AST/regex validation for completeness |
| `FallbackRouterAgent` | `fallback_router_agent.py` | Template router when LLM fails |
| `FallbackAPIAgent` | `fallback_api_agent.py` | Template API client when LLM fails |
| `CheckpointManagerV2` | `checkpoint_v2.py` | Safe checkpoint saving |
| `ArtifactContracts` | `artifact_contracts.py` | Structural requirements for artifacts |

---

## Key Features

### 1. Self-Healing System

**Location**: `app/workflow/healing_pipeline.py`, `app/workflow/self_healing_manager.py`

- Coordinates error attribution, self-healing, and fallback
- Dynamic discovery of entity names from workspace
- Template-based fallback for routers and API clients

### 2. Tiered Review System

**Location**: `app/workflow/tiered_review.py`

| Level | Files | Review Type |
|-------|-------|-------------|
| NONE | CSS, HTML, MD, images | Skip review |
| PREFLIGHT_ONLY | Tests, configs | Syntax check only |
| LIGHTWEIGHT | Components, utils | Quick check |
| FULL | Routers, models, main.py | Full Marcus review |

### 3. Budget Management

**Location**: `app/workflow/engine_v2/budget_manager.py`

- Tracks token usage per step
- Gemini 2.5 Flash pricing (INR-based)
- Per-step budget policies
- Can skip non-critical steps if budget tight

### 4. Syntax Validation

**Location**: `app/validation/syntax_validator.py`

- Pre-flight validation for Python (AST parsing)
- Heuristic checks for JavaScript/JSX/TSX
- Auto-fixing common LLM mistakes:
  - Malformed imports
  - Errant backslashes
  - Duplicate HTML attributes

### 5. Robust LLM Output Parsing

**Location**: `app/utils/parser.py`

- Multi-pass JSON sanitization
- Repair mechanisms for malformed JSON
- Partial file extraction from broken output
- Unterminated string fixing

---

## LLM Integration

### Providers (`app/llm/providers/`)

| Provider | File | Model |
|----------|------|-------|
| Gemini | `gemini.py` | gemini-2.0-flash-exp |
| OpenAI | `openai.py` | gpt-4, gpt-3.5-turbo |
| Anthropic | `anthropic.py` | claude-3 |
| Ollama | `ollama.py` | local models |

### LLM Adapter (`app/llm/adapter.py`)

- Unified interface for all providers
- Retry with exponential backoff
- Stop sequences to prevent truncation
- Step-aware stop sequence selection

### Prompt Management (`app/llm/prompt_management.py`)

- Core prompts (static, cacheable)
- Context templates (dynamic, minimal)
- Step-aware context routing
- Auto-approve patterns for config files

---

## Sandbox System

### Components

| Component | File | Purpose |
|-----------|------|---------|
| `SandboxManager` | `sandbox_manager.py` | Docker compose orchestration |
| `HealthMonitor` | `health_monitor.py` | Container health checks |
| `LogStreamer` | `log_streamer.py` | Container log streaming |
| `SandboxPool` | `pool.py` | Pre-warmed container pool |
| `PreviewManager` | `preview_manager.py` | Traefik preview URLs |
| `SandboxConfig` | `sandbox_config.py` | Configuration dataclass |

### Key Features

- Docker Compose based sandbox environments
- Pre-warming for reduced startup latency
- Health monitoring and log streaming
- Preview URLs via Traefik

---

## API Layer

### Routes (`app/api/`)

| Route | File | Purpose |
|-------|------|---------|
| `/api/projects` | `projects.py` | Project CRUD |
| `/api/workspace` | `workspace.py` | File operations, workflow trigger |
| `/api/sandbox` | `sandbox.py` | Sandbox management |
| `/api/deployment` | `deployment.py` | Deployment operations |
| `/api/providers` | `providers.py` | LLM provider info |
| `/api/agents` | `agents.py` | Agent status |
| `/api/health` | `health.py` | Health check |
| `/api/tracking` | `tracking.py` | Usage tracking |

### WebSocket

- Endpoint: `/ws/{project_id}`
- Handles real-time workflow updates
- Supports USER_INPUT messages for resumption

---

## Workflow Handler Steps

### Handlers (`app/workflow/handlers/`)

| Handler | File | Step |
|---------|------|------|
| `step_analysis` | `analysis.py` | Step 1 |
| `step_architecture` | `architecture.py` | Step 2 |
| `step_frontend_mock` | `frontend_mock.py` | Step 3 |
| `step_screenshot_verify` | `screenshot_verify.py` | Step 4 |
| `step_contracts` | `contracts.py` | Step 5 |
| `step_backend_models` | `backend.py` | Step 6 |
| `step_backend_routers` | `backend.py` | Step 7 |
| `step_backend_main` | `backend.py` | Step 8 |
| `step_testing_backend` | `testing_backend.py` | Step 9 |
| `step_frontend_integration` | `frontend_integration.py` | Step 10 |
| `step_testing_frontend` | `testing_frontend.py` | Step 11 |
| `step_preview_final` | `preview.py` | Step 12 |
| `step_refine` | `refine.py` | Post-workflow |

---

## State Management

### WorkflowStateManager (`app/workflow/state.py`)

- Track running workflows
- Pause/resume workflow state
- Store project intents
- Thread-safe with asyncio locks

### Checkpoint System (`app/workflow/checkpoint.py`)

- Save progress after each step
- JSON serialization to disk
- History tracking
- Recovery from crashes

---

## Testing System

### Self-Healing Tests (`app/testing/self_healing.py`)

- Analyzes Playwright test failures
- Auto-fixes common issues:
  - Relative URL to absolute
  - Add timeouts
  - Remove flaky assertions
  - Add retry logic
  - Make selectors more specific

### Robust Smoke Test Generation

- Dynamic test generation based on `data-testid` attributes
- Archetype-aware test patterns

---

## Configuration

### Settings (`app/core/config.py`)

```python
@dataclass
class Settings:
    llm: LLMSettings          # Provider config
    workflow: WorkflowSettings # Workflow limits
    sandbox: SandboxSettings   # Docker timeouts
    paths: PathSettings        # Directory paths
    port: int                  # Server port
    debug: bool                # Debug mode
```

### Constants (`app/core/constants.py`)

- WorkflowStep enum
- AgentName constants
- Protected files set
- Default templates (requirements.txt, package.json)

---

## Exception Hierarchy

```
GenCodeError (base)
├── WorkflowError
├── QualityGateError
├── AgentError
├── LLMError
│   └── RateLimitError
├── SandboxError
├── PersistenceError
├── ValidationError
└── ParseError
```

---

## Frontend Architecture

### Tech Stack

- React 18 + TypeScript
- Vite build system
- TailwindCSS + shadcn/ui
- React Router (HashRouter)

### Key Components

| Component | Purpose |
|-----------|---------|
| `HomePage` | Project listing and creation |
| `WorkspacePage` | Code editor and preview |
| `Header` | Navigation header |
| `MatrixBackground` | Visual background effect |
| `ErrorBoundary` | Error handling |

### Services

| Service | Purpose |
|---------|---------|
| `agentService.ts` | Agent API calls |
| `deploymentService.ts` | Deployment operations |
| `autoApplyClient.ts` | Auto-apply changes |

---

## Tool System

### Registry (`app/tools/registry.py`)

- `run_tool()` - Execute a tool by name
- `get_available_tools()` - List available tools

### Implementations (`app/tools/implementations.py`)

| Tool | Purpose |
|------|---------|
| `sandboxexec` | Execute commands in sandbox |
| `filewriterbatch` | Write multiple files |
| `filereader` | Read file contents |
| `pytestrunner` | Run pytest tests |
| `playwrightrunner` | Run Playwright tests |
| `unifiedpatchapplier` | Apply unified diffs |
| `jsonpatchapplier` | Apply JSON patches |
| `healthchecker` | Check service health |
| `deploymentvalidator` | Validate deployment |

---

## Tracking & Memory

### Memory Store (`app/tracking/memory.py`)

- SQLite-backed persistent memory
- Stores successful patterns
- Provides memory hints for agents

### Metrics (`app/tracking/metrics.py`)

- Total files/lines generated
- Per-agent metrics
- Quality scores

### Snapshots (`app/tracking/snapshots.py`)

- Project state snapshots
- Rollback capability
- Step completion tracking

---

## Attention Router (`app/workflow/attention_router.py`)

Uses transformer-style scaled dot-product attention for:
- Project archetype classification
- UI vibe selection

Supports embeddings from:
- Gemini (text-embedding-004)
- OpenAI (text-embedding-3-small)
- Fallback hash-based embeddings

---

## Key Design Patterns

1. **Singleton Pattern** - BudgetManager, SandboxManager, CheckpointManager
2. **Factory Pattern** - Engine selection (v1/v2/legacy)
3. **Strategy Pattern** - LLM provider selection
4. **Observer Pattern** - WebSocket broadcasts
5. **Template Method** - Step handlers
6. **Chain of Responsibility** - Validation pipeline

---

## Environment Variables

```env
# LLM Configuration
GEMINI_API_KEY=xxx
OPENAI_API_KEY=xxx
ANTHROPIC_API_KEY=xxx
DEFAULT_LLM_PROVIDER=gemini
DEFAULT_LLM_MODEL=gemini-2.0-flash-exp

# Database
MONGODB_URL=mongodb://localhost:27017

# Paths
WORKSPACES_DIR=./workspaces
FRONTEND_DIST_PATH=../Frontend/dist

# Server
PORT=8000
DEBUG=false
CORS_ORIGINS=*
```

---

## Known TODOs/Placeholders

1. **`app/sandbox/pool.py`**: `_is_healthy` and `_stop_sandbox` are placeholders
2. **`app/tools/implementations.py`**: `tool_web_researcher` and DB tools are stubs
3. **`app/utils/parser.py`**: FIX #8 (ContextVar for async), FIX #10 (return empty dict)
4. **`app/workflow/agents/sub_agents.py`**: `_broadcast_agent_thinking` import fix needed
5. **`app/workflow/engine.py`**: Various FIX markers for atomic operations

---

## Running the Application

```bash
# Backend
cd Backend
pip install -r requirements.txt
python -m app.main

# Frontend
cd Frontend
npm install
npm run dev
```

---

*Document generated by codebase review on 2025-12-10*
