# GenCode Studio Backend

## 🧠 Complete Architecture & Flow Documentation

This document explains **exactly** how the GenCode Studio backend works - from the moment a user sends a request to the final generated code.

---

## 📋 Table of Contents

1. [Quick Overview](#quick-overview)
2. [System Architecture](#system-architecture)
3. [Entry Point Flow](#entry-point-flow)
4. [The FAST V2 Orchestrator](#the-fast-v2-orchestrator)
5. [Agent System](#agent-system)
6. [Step Handlers](#step-handlers)
7. [Supervision & Quality Gates](#supervision--quality-gates)
8. [Validation & Persistence](#validation--persistence)
9. [LLM Integration](#llm-integration)
10. [Docker Sandbox Testing](#docker-sandbox-testing)
11. [Directory Structure](#directory-structure)
12. [Key Files Reference](#key-files-reference)

---

## Quick Overview

```
User Request → API → Workflow Engine → Agents → LLM → Validation → File Output
     ↓              ↓                    ↓        ↓         ↓           ↓
"Create a     POST /api/       FAST V2      Marcus/   Gemini/   AST      Generated
bug tracker"  /generate    Orchestrator   Derek/    OpenAI   Check     Code
                                          Luna
```

**In 30 seconds:**
1. Frontend sends `POST /api/workspace/{id}/generate/backend` with a description
2. This triggers `run_workflow()` in `engine.py`
3. `FASTOrchestratorV2` executes 12 steps in order
4. Each step calls an **Agent** (Marcus, Derek, Victoria, Luna)
5. Agents call the **LLM** (Gemini/OpenAI) to generate code
6. **Marcus** reviews all generated code for quality
7. Code is **validated** (AST parsing, pre-flight checks)
8. If valid, code is **persisted** to the workspace folder
9. Tests run in **Docker sandboxes**
10. Final preview is generated

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FASTAPI APP                                     │
│                              app/main.py                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐     │
│  │   /api/     │   │   /api/     │   │   /api/     │   │    /ws/     │     │
│  │  workspace  │   │  projects   │   │  sandbox    │   │ {project}   │     │
│  └──────┬──────┘   └─────────────┘   └─────────────┘   └──────┬──────┘     │
│         │                                                      │            │
│         │ POST /generate/backend                               │ WebSocket  │
│         ▼                                                      ▼            │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                       WORKFLOW ENGINE                                 │  │
│  │                       app/workflow/engine.py                          │  │
│  │                              │                                        │  │
│  │                              ▼                                        │  │
│  │  ┌────────────────────────────────────────────────────────────────┐  │  │
│  │  │                   FAST V2 ORCHESTRATOR                          │  │  │
│  │  │                   app/workflow/engine_v2/fast_orchestrator.py   │  │  │
│  │  │                                                                  │  │  │
│  │  │   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ │  │  │
│  │  │   │Analysis │→│  Arch   │→│Frontend │→│Backend  │→│ Testing │ │  │  │
│  │  │   │ (1)     │ │  (2)    │ │  (3-4)  │ │  (5-8)  │ │ (9-11)  │ │  │  │
│  │  │   └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘ │  │  │
│  │  └────────────────────────────────────────────────────────────────┘  │  │
│  │                              │                                        │  │
│  │                              ▼                                        │  │
│  │  ┌────────────────────────────────────────────────────────────────┐  │  │
│  │  │                      STEP HANDLERS                              │  │  │
│  │  │                      app/workflow/handlers/                     │  │  │
│  │  │                                                                  │  │  │
│  │  │   analysis.py │ architecture.py │ backend.py │ testing_*.py    │  │  │
│  │  └────────────────────────────────────────────────────────────────┘  │  │
│  │                              │                                        │  │
│  │                              ▼                                        │  │
│  │  ┌────────────────────────────────────────────────────────────────┐  │  │
│  │  │                    SUPERVISION LAYER                            │  │  │
│  │  │                    app/workflow/supervision/                    │  │  │
│  │  │                                                                  │  │  │
│  │  │   supervisor.py      │     quality_gate.py                      │  │  │
│  │  │   (Marcus reviews)   │     (Score thresholds)                   │  │  │
│  │  └────────────────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                              │                                              │
│                              ▼                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐│
│  │                        LLM LAYER                                        ││
│  │                        app/llm/                                         ││
│  │                                                                          ││
│  │   adapter.py        │    prompts/              │    prompt_management.py ││
│  │   (Gemini/OpenAI)   │    (Agent personas)      │    (Context filtering) ││
│  └────────────────────────────────────────────────────────────────────────┘│
│                              │                                              │
│                              ▼                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐│
│  │                    VALIDATION & PERSISTENCE                             ││
│  │                                                                          ││
│  │   app/validation/           │          app/persistence/                 ││
│  │   preflight.py (AST check)  │          file_writer.py                   ││
│  │   validator.py (syntax)     │          validator.py (path normalization)││
│  └────────────────────────────────────────────────────────────────────────┘│
│                              │                                              │
│                              ▼                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐│
│  │                      DOCKER SANDBOX                                     ││
│  │                      app/sandbox/                                       ││
│  │                                                                          ││
│  │   manager.py              │         executor.py                         ││
│  │   (Container lifecycle)   │         (Run pytest/playwright)             ││
│  └────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Entry Point Flow

### 1. HTTP Request Arrives

```
POST /api/workspace/{project_id}/generate/backend
Body: { "description": "Create a bug tracking system" }
```

**File:** `app/api/workspace.py` → `generate_backend()`

```python
@router.post("/{project_id}/generate/backend")
async def generate_backend(request: Request, project_id: str, data: GenerateRequest):
    # 1. Validate project_id (security check)
    # 2. Check if workflow already running
    # 3. Create project directory
    # 4. Start workflow in background task
    asyncio.create_task(
        run_workflow(
            project_id=project_id,
            description=data.description,
            workspaces_path=settings.paths.workspaces_dir,
            manager=manager,  # WebSocket connection manager
        )
    )
```

### 2. Workflow Engine Starts

**File:** `app/workflow/engine.py` → `run_workflow()`

```python
async def run_workflow(project_id, description, workspaces_path, manager, ...):
    # 1. Set workflow state to "running"
    WorkflowStateManager.set_running(project_id)
    
    # 2. Create project directory structure
    project_path = workspaces_path / project_id
    scaffold_project(project_path)
    
    # 3. Copy template files (shadcn/ui components, Dockerfile, etc.)
    copy_templates(project_path)
    
    # 4. Initialize FAST V2 Orchestrator
    engine = FASTOrchestratorV2(
        project_id=project_id,
        manager=manager,
        project_path=project_path,
        user_request=description,
    )
    
    # 5. Execute the workflow
    await engine.run()
```

---

## The FAST V2 Orchestrator

**File:** `app/workflow/engine_v2/fast_orchestrator.py`

The orchestrator executes 12 steps in order with safety features:

```python
class FASTOrchestratorV2:
    CRITICAL_STEPS = {"backend_routers", "backend_main", "frontend_integration"}
    
    async def run(self):
        for step in self.graph.get_steps():
            # FEATURE 1: Dependency Barrier
            if not self.graph.is_ready(step, self.completed_steps):
                continue  # Wait for dependencies
            
            # FEATURE 2: Budget Check
            if self.budget.allowed_attempts_for_step(step) == 0:
                continue  # Skip if budget exhausted
            
            # FEATURE 3: Pre-step Validation
            if step in ["testing_backend", "testing_frontend"]:
                if not self._validate_critical_files(step):
                    self._attempt_healing(step)  # Try to fix
            
            # EXECUTE STEP
            handler = HANDLERS[step]
            result = await handler(
                project_id=self.project_id,
                user_request=self.user_request,
                manager=self.manager,
                project_path=self.project_path,
                ...
            )
            
            # FEATURE 4: Post-step Validation
            if step in self.CRITICAL_STEPS:
                if not self._validate_step_output(step):
                    self._attempt_healing(step)
            
            # FEATURE 5: Checkpoint
            self._save_checkpoint(step)
            
            # FEATURE 6: Budget Tracking
            self.budget.register_usage(input_tokens, output_tokens)
```

### The 12 Steps

| # | Step | Handler File | Agent | What It Does |
|---|------|--------------|-------|--------------|
| 1 | `analysis` | `handlers/analysis.py` | Marcus | Parse user request, extract entities, classify archetype |
| 2 | `architecture` | `handlers/architecture.py` | Victoria | Create `architecture.md` with system design |
| 3 | `frontend_mock` | `handlers/frontend_mock.py` | Derek | Generate React components with mock data |
| 4 | `screenshot_verify` | `handlers/screenshot_verify.py` | Marcus | Visual QA review of UI |
| 5 | `contracts` | `handlers/contracts.py` | Marcus | Create `contracts.md` with API specifications |
| 6 | `backend_models` | `handlers/backend.py` | Derek | Generate Beanie/MongoDB models |
| 7 | `backend_routers` | `handlers/backend.py` | Derek | Generate FastAPI routers |
| 8 | `backend_main` | `handlers/backend.py` | Derek | Generate `main.py` entry point |
| 9 | `frontend_integration` | `handlers/frontend_integration.py` | Derek | Replace mock data with real API calls |
| 10 | `testing_backend` | `handlers/testing_backend.py` | Derek | Run pytest in Docker |
| 11 | `testing_frontend` | `handlers/testing_frontend.py` | Luna | Run Playwright E2E tests |
| 12 | `preview_final` | `handlers/preview.py` | Marcus | Final review and deployment |

---

## Agent System

### The 4 Agents

| Agent | Role | System Prompt File |
|-------|------|-------------------|
| **Marcus** | Senior Architect & Code Reviewer | `app/llm/prompts/marcus.py` |
| **Derek** | Full-Stack Developer | `app/llm/prompts/derek.py` |
| **Victoria** | System Architect & Planner | `app/llm/prompts/victoria.py` |
| **Luna** | QA & DevOps Engineer | `app/llm/prompts/luna.py` |

### How Agents Are Called

**File:** `app/workflow/agents/sub_agents.py` → `marcus_call_sub_agent()`

```python
async def marcus_call_sub_agent(
    sub_agent: str,           # "Derek", "Victoria", or "Luna"
    instructions: str,        # Task-specific instructions
    project_path: str,
    project_id: str,
    ...
):
    # 1. Get agent's system prompt
    system_prompt = get_agent_prompt(sub_agent)
    
    # 2. Build context (filtered project files)
    context = build_context(project_path, step_name)
    
    # 3. Call LLM
    response = await call_llm(
        prompt=instructions + context,
        system_prompt=system_prompt,
        max_tokens=10000 if not is_retry else 12000,  # More tokens on retry
    )
    
    # 4. Parse JSON response (with salvage for broken JSON)
    parsed = parse_json(response)
    
    return parsed
```

### Agent Prompt Structure

Each agent has a detailed persona:

```python
# app/llm/prompts/derek.py
DEREK_PROMPT = """You are Derek, a senior full-stack developer at GenCode Studio.

YOUR WORKFLOW POSITION:
You work in a pipeline: Marcus (analysis) → Victoria (architecture) → YOU (implementation)

YOUR RESPONSIBILITIES:
- Generate complete, working code files
- Follow the architecture.md exactly
- Match the API contracts.md
- Use proper imports for Docker (from app.xxx, not from backend.app.xxx)

OUTPUT FORMAT:
Always respond with valid JSON:
{
    "thinking": "Your reasoning...",
    "files": [
        {"path": "backend/app/models.py", "content": "..."}
    ]
}
"""
```

---

## Supervision & Quality Gates

### The Supervision Flow

**File:** `app/workflow/supervision/supervisor.py`

Every agent output goes through Marcus's review:

```python
async def supervised_agent_call(
    project_id, manager, agent_name, step_name, base_instructions, ...
):
    for attempt in range(1, max_retries + 1):
        # 1. CALL AGENT
        result = await run_tool("subagentcaller", {
            "sub_agent": agent_name,
            "instructions": current_instructions,
            ...
        })
        
        # 2. LLM OUTPUT INTEGRITY CHECK (V2 Feature)
        if not integrity_checker.validate(result):
            # Truncation detected, retry with larger max_tokens
            continue
        
        # 3. MARCUS REVIEWS
        review = await marcus_supervise(
            agent_name=agent_name,
            agent_output=result,
            contracts=contracts,
        )
        
        if review["approved"]:
            return {"output": result, "approved": True}
        
        # 4. NOT APPROVED - Add feedback for retry
        current_instructions = base_instructions + f"""
        ⚠️ SUPERVISOR REJECTION (Quality: {review['quality_score']}/10)
        Issues: {review['issues']}
        Fix these problems!
        """
    
    # Max retries reached
    return {"output": result, "approved": False}
```

### Marcus's Review Process

```python
async def marcus_supervise(agent_name, agent_output, contracts, ...):
    # LAYER 1: PRE-FLIGHT VALIDATION (Fast, catches 90% of issues)
    cleaned, rejections = preflight_check(agent_output)
    if rejections:
        return {"approved": False, "quality_score": 1, "issues": rejections}
    
    # LAYER 1.5: TIERED REVIEW (Skip LLM review for non-critical files)
    if not needs_full_review(agent_output):
        return {"approved": True, "quality_score": 8}
    
    # LAYER 2: LLM REVIEW (Marcus analyzes code quality)
    review_prompt = f"""
    Review this output from {agent_name}:
    {agent_output}
    
    Check for:
    - Syntax errors
    - Missing imports
    - Broken logic
    - Contract violations
    
    Return JSON: {{"approved": bool, "quality_score": 1-10, "issues": [...]}}
    """
    
    response = await call_llm(review_prompt, system_prompt=MARCUS_PROMPT)
    return parse_json(response)
```

### Quality Gate

**File:** `app/workflow/supervision/quality_gate.py`

```python
async def check_quality_gate(project_id, step_name, quality, approved, attempt, max_attempts):
    # Block if quality < 5 after all retries
    if not approved and attempt >= max_attempts and quality < 5:
        return True, f"Quality gate triggered: {step_name} scored {quality}/10"
    return False, None
```

---

## Validation & Persistence

### Pre-flight Validation

**File:** `app/validation/preflight.py`

Before any file is written, it goes through pre-flight checks:

```python
def preflight_check(agent_output):
    rejections = []
    cleaned_files = []
    
    for file in agent_output.get("files", []):
        path = file["path"]
        content = file["content"]
        
        # CHECK 1: Empty content
        if not content.strip():
            rejections.append(f"{path}: Empty content")
            continue
        
        # CHECK 2: Python syntax (AST validation)
        if path.endswith(".py"):
            try:
                ast.parse(content)
            except SyntaxError as e:
                rejections.append(f"{path}: Python SyntaxError at line {e.lineno}")
                continue
        
        # CHECK 3: JSX bracket balance
        if path.endswith(".jsx"):
            if not validate_jsx_completeness(content):
                rejections.append(f"{path}: Unbalanced brackets")
                continue
        
        cleaned_files.append(file)
    
    return {"files": cleaned_files}, rejections
```

### File Persistence

**File:** `app/persistence/__init__.py` → `persist_agent_output()`

```python
async def persist_agent_output(manager, project_id, project_path, validated_output, step):
    files = validated_output.get("files", [])
    written = 0
    
    for file in files:
        path = file["path"]
        content = file["content"]
        
        # Normalize path for Linux/Docker compatibility
        path = normalize_python_filename(path)
        path = fix_path_prefix(path)
        
        # Write file
        full_path = project_path / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")
        
        written += 1
        log("PERSIST", f"📝 Wrote: {path}")
    
    # Broadcast update to frontend via WebSocket
    await broadcast_to_project(manager, project_id, {
        "type": "FILES_UPDATED",
        "files": [f["path"] for f in files],
    })
    
    return written
```

---

## LLM Integration

### LLM Adapter

**File:** `app/llm/adapter.py`

```python
async def call_llm(
    prompt: str,
    system_prompt: str = "",
    max_tokens: int = 8192,
    temperature: float = 0.7,
) -> str:
    provider = settings.llm.default_provider  # "gemini" or "openai"
    model = settings.llm.default_model
    
    if provider == "gemini":
        return await call_gemini(prompt, system_prompt, max_tokens)
    elif provider == "openai":
        return await call_openai(prompt, system_prompt, max_tokens)
    else:
        raise ValueError(f"Unknown provider: {provider}")

async def call_gemini(prompt, system_prompt, max_tokens):
    import google.generativeai as genai
    
    genai.configure(api_key=settings.llm.gemini_api_key)
    model = genai.GenerativeModel(settings.llm.default_model)
    
    response = model.generate_content(
        [system_prompt, prompt],
        generation_config={"max_output_tokens": max_tokens},
    )
    
    return response.text
```

### Prompt Management

**File:** `app/llm/prompt_management.py`

Context is filtered per step to reduce token usage:

```python
STEP_CONTEXT_RULES = {
    "backend_models": {
        "include": ["contracts.md", "architecture.md"],
        "exclude": ["frontend/", "tests/"],
    },
    "backend_routers": {
        "include": ["contracts.md", "backend/app/models.py"],
        "exclude": ["frontend/"],
    },
    "frontend_integration": {
        "include": ["contracts.md", "frontend/src/"],
        "exclude": ["backend/", "tests/"],
    },
}

def get_relevant_files(step_name, all_files):
    rules = STEP_CONTEXT_RULES.get(step_name, {})
    includes = rules.get("include", [])
    excludes = rules.get("exclude", [])
    
    return [f for f in all_files 
            if any(inc in f["path"] for inc in includes)
            and not any(exc in f["path"] for exc in excludes)]
```

---

## Docker Sandbox Testing

### Sandbox Manager

**File:** `app/sandbox/manager.py`

```python
class SandboxManager:
    def create_sandbox(self, project_id: str):
        # 1. Build docker-compose.yml for project
        compose_content = self._generate_compose(project_id)
        
        # 2. Start containers
        subprocess.run(["docker-compose", "up", "-d"], cwd=project_path)
        
        # 3. Wait for health checks
        self._wait_for_healthy(project_id)
    
    def execute_command(self, project_id: str, service: str, command: str):
        # Run command inside container
        result = subprocess.run(
            ["docker-compose", "exec", service, "sh", "-c", command],
            capture_output=True,
        )
        return result.stdout, result.stderr, result.returncode
```

### Backend Testing Flow

**File:** `app/workflow/handlers/testing_backend.py`

```python
async def step_testing_backend(project_id, project_path, manager, ...):
    # 1. Create sandbox if not exists
    sandbox = SandboxManager()
    sandbox.create_sandbox(project_id)
    
    # 2. Run pytest
    stdout, stderr, code = sandbox.execute_command(
        project_id,
        service="backend",
        command="pytest -q",
    )
    
    # 3. If tests fail, try to fix
    if code != 0:
        for attempt in range(3):
            # Ask Derek to fix based on error
            fix_result = await supervised_agent_call(
                agent_name="Derek",
                step_name="Backend Testing Fix",
                instructions=f"Fix these test failures:\n{stderr}",
                ...
            )
            
            # Apply fixes
            await persist_agent_output(fix_result)
            
            # Re-run tests
            stdout, stderr, code = sandbox.execute_command(...)
            if code == 0:
                break
    
    return StepResult(nextstep=WorkflowStep.FRONTEND_INTEGRATION)
```

---

## Directory Structure

```
Backend/
├── app/
│   ├── main.py                    # FastAPI entry point
│   ├── db.py                      # Database connection
│   │
│   ├── api/                       # REST API Endpoints
│   │   ├── workspace.py           # /api/workspace/* routes
│   │   ├── projects.py            # /api/projects/* routes
│   │   ├── sandbox.py             # /api/sandbox/* routes
│   │   ├── health.py              # /api/health endpoint
│   │   └── ...
│   │
│   ├── core/                      # Core Configuration
│   │   ├── config.py              # Settings from environment
│   │   ├── constants.py           # Enums (WorkflowStep, Agent names)
│   │   ├── logging.py             # Centralized logging
│   │   └── types.py               # Pydantic models (StepResult, etc.)
│   │
│   ├── workflow/                  # 🌟 THE HEART OF THE SYSTEM
│   │   ├── engine.py              # run_workflow() entry point
│   │   │
│   │   ├── engine_v2/             # FAST V2 Orchestrator
│   │   │   ├── fast_orchestrator.py  # Main orchestration loop
│   │   │   ├── budget_manager.py     # Token/cost tracking
│   │   │   ├── task_graph.py         # Step dependencies
│   │   │   ├── llm_output_integrity.py  # Truncation detection
│   │   │   └── ...
│   │   │
│   │   ├── handlers/              # Step Implementations
│   │   │   ├── analysis.py        # Step 1: Marcus analyzes request
│   │   │   ├── architecture.py    # Step 2: Victoria designs system
│   │   │   ├── frontend_mock.py   # Step 3: Derek creates UI
│   │   │   ├── backend.py         # Steps 6-8: Derek creates backend
│   │   │   ├── testing_backend.py # Step 10: Derek runs pytest
│   │   │   ├── testing_frontend.py# Step 11: Luna runs Playwright
│   │   │   └── ...
│   │   │
│   │   ├── supervision/           # Quality Control
│   │   │   ├── supervisor.py      # Marcus reviews all output
│   │   │   └── quality_gate.py    # Score thresholds
│   │   │
│   │   ├── agents/                # Agent Wrappers
│   │   │   └── sub_agents.py      # marcus_call_sub_agent()
│   │   │
│   │   ├── healing_pipeline.py    # Self-healing on failures
│   │   ├── attention_router.py    # Archetype classification
│   │   └── state.py               # Workflow state management
│   │
│   ├── llm/                       # LLM Integration
│   │   ├── adapter.py             # call_llm() - Gemini/OpenAI
│   │   ├── prompt_management.py   # Context filtering
│   │   └── prompts/
│   │       ├── marcus.py          # Marcus system prompt
│   │       ├── derek.py           # Derek system prompt
│   │       ├── victoria.py        # Victoria system prompt
│   │       └── luna.py            # Luna system prompt
│   │
│   ├── validation/                # Pre-write Validation
│   │   ├── preflight.py           # AST parsing, syntax checks
│   │   └── __init__.py
│   │
│   ├── persistence/               # File Writing
│   │   ├── __init__.py            # persist_agent_output()
│   │   └── validator.py           # Path normalization
│   │
│   ├── sandbox/                   # Docker Testing
│   │   ├── manager.py             # Container lifecycle
│   │   └── executor.py            # Command execution
│   │
│   ├── tools/                     # Agent Tools
│   │   ├── registry.py            # Tool definitions
│   │   └── implementations.py     # subagentcaller, etc.
│   │
│   └── lib/                       # Utilities
│       ├── websocket.py           # ConnectionManager
│       └── monitoring.py          # Prometheus metrics
│
├── templates/                     # Project Templates
│   ├── shadcn/                    # UI components
│   ├── Dockerfile.backend         # Backend container
│   ├── Dockerfile.frontend        # Frontend container
│   └── ...
│
├── tests/                         # Backend Tests
│   ├── conftest.py
│   └── test_*.py
│
└── requirements.txt               # Python dependencies
```

---

## Key Files Reference

### Entry Points
| File | Function | Purpose |
|------|----------|---------|
| `app/main.py` | `lifespan()` | App startup/shutdown |
| `app/api/workspace.py` | `generate_backend()` | Starts workflow |
| `app/workflow/engine.py` | `run_workflow()` | Main workflow entry |

### Orchestration
| File | Class/Function | Purpose |
|------|----------------|---------|
| `app/workflow/engine_v2/fast_orchestrator.py` | `FASTOrchestratorV2` | Executes 12 steps |
| `app/workflow/engine_v2/budget_manager.py` | `BudgetManager` | Track token costs |
| `app/workflow/engine_v2/task_graph.py` | `TaskGraph` | Step dependencies |

### Agent System
| File | Function | Purpose |
|------|----------|---------|
| `app/workflow/agents/sub_agents.py` | `marcus_call_sub_agent()` | Call Derek/Luna/Victoria |
| `app/workflow/supervision/supervisor.py` | `marcus_supervise()` | Quality review |
| `app/workflow/supervision/supervisor.py` | `supervised_agent_call()` | Agent + review loop |

### LLM Layer
| File | Function | Purpose |
|------|----------|---------|
| `app/llm/adapter.py` | `call_llm()` | Unified LLM interface |
| `app/llm/prompts/derek.py` | `DEREK_PROMPT` | Derek's persona |
| `app/llm/prompts/marcus.py` | `MARCUS_PROMPT` | Marcus's persona |

### Validation
| File | Function | Purpose |
|------|----------|---------|
| `app/validation/preflight.py` | `preflight_check()` | AST + syntax checks |
| `app/persistence/validator.py` | `validate_file_output()` | Path normalization |
| `app/persistence/validator.py` | `validate_python_syntax()` | Reject invalid Python |

### Persistence
| File | Function | Purpose |
|------|----------|---------|
| `app/persistence/__init__.py` | `persist_agent_output()` | Write files to disk |
| `app/workflow/utils.py` | `broadcast_to_project()` | WebSocket updates |

---

## Quick Debugging Guide

### "Workflow stuck at step X"
1. Check `app/workflow/handlers/<step>.py` for the step logic
2. Look for `log("STEP_NAME", ...)` messages in console
3. Check if `supervised_agent_call()` is returning `approved: False`

### "LLM returning garbage"
1. Check `app/llm/adapter.py` for API key configuration
2. Increase `max_tokens` in the handler
3. Check if context is too large (see `prompt_management.py`)

### "Files not being written"
1. Check `app/validation/preflight.py` for rejection reasons
2. Look for `🚨 REJECTING` in logs
3. Verify AST parsing passes: `python -c "import ast; ast.parse('''<code>''')""`

### "Docker tests failing"
1. Check if sandbox started: `docker ps | grep <project_id>`
2. Look at `app/sandbox/manager.py` for container issues
3. Check Docker logs: `docker logs <container_id>`

---

## Summary

The GenCode Studio backend is a **multi-agent workflow engine** that:

1. **Receives** a natural language description
2. **Routes** through 12 ordered steps
3. **Calls** specialized agents (Marcus, Derek, Victoria, Luna)
4. **Validates** all output (AST, pre-flight, quality gates)
5. **Persists** only valid code to disk
6. **Tests** in isolated Docker containers
7. **Delivers** working full-stack applications

**The key insight:** Every piece of generated code goes through Marcus's review before it's written. This supervision loop is what prevents broken code from reaching the filesystem.
