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
6. [Supervision & Quality Gates](#supervision--quality-gates)
7. [Validation & Persistence](#validation--persistence)
8. [Tracking & Learning](#tracking--learning)
9. [LLM Integration](#llm-integration)
10. [Docker Sandbox Testing](#docker-sandbox-testing)
11. [Directory Structure](#directory-structure)
12. [Configuration](#configuration)
13. [Running the Application](#running-the-application)

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
1. Frontend sends `POST /api/workspace/{id}/generate/backend` with a description.
2. This triggers `run_workflow()` in `app/workflow/engine.py`.
3. `FASTOrchestratorV2` executes 11 atomic steps in order.
4. Each step calls an **Agent** (Marcus, Derek, Victoria, Luna).
5. Agents call the **LLM** (Gemini/OpenAI) to generate code.
6. **Marcus** reviews all generated code for quality.
7. Code is **validated** (AST parsing, pre-flight checks).
8. If valid, code is **persisted** to the workspace folder.
9. Tests run in **Docker sandboxes**.
10. Final preview is generated.

---

## System Architecture

The backend follows a **Clean Architecture** pattern with a powerful orchestration layer.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FASTAPI APP                                     │
│                              app/main.py                                     │
│                    (Rate Limiting, CORS, Monitoring)                         │
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
│  │  │                   app/orchestration/fast_orchestrator.py        │  │  │
│  │  │                                                                  │  │  │
│  │  │   • Dependency Barriers   • Budget Management                    │  │  │
│  │  │   • Self-Healing          • Cross-Step Context                   │  │  │
│  │  │                                                                  │  │  │
│  │  │   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ │  │  │
│  │  │   │Analysis │→│  Arch   │→│Frontend │→│Atomic   │→│ Testing │ │  │  │
│  │  │   │ (1)     │ │  (2)    │ │  (3-5)  │ │Backend  │→│ & Integ │ │  │  │
│  │  │   └─────────┘ └─────────┘ └─────────┘ │  (6-7)  │ └ (8-11)  ┘ │  │  │
│  │  │                                       └─────────┘             │  │  │
│  │  └────────────────────────────────────────────────────────────────┘  │  │
│  │                              │                                        │  │
│  │                              ▼                                        │  │
│  │  ┌────────────────────────────────────────────────────────────────┐  │  │
│  │  │                      STEP HANDLERS                              │  │  │
│  │  │                      app/handlers/                              │  │  │
│  │  │                                                                  │  │  │
│  │  │   analysis.py │ architecture.py │ backend.py │ testing_*.py    │  │  │
│  │  └────────────────────────────────────────────────────────────────┘  │  │
│  │                              │                                        │  │
│  │                              ▼                                        │  │
│  │  ┌────────────────────────────────────────────────────────────────┐  │  │
│  │  │                    SUPERVISION LAYER                            │  │  │
│  │  │                    app/supervision/                             │  │  │
│  │  │   supervisor.py (Marcus)  │  quality_gate.py  │  tiered_review  │  │  │
│  │  └────────────────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                              │                                              │
│                              ▼                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐│
│  │                        LLM LAYER                                        ││
│  │                  app/llm/ (Gemini / OpenAI)                             ││
│  └────────────────────────────────────────────────────────────────────────┘│
│                              │                                              │
│                              ▼                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐│
│  │                   PERSISTENCE & VALIDATION                              ││
│  │   app/validation/ (AST)   │   app/persistence/ (File Writer)           ││
│  │   app/tracking/ (Metrics) │   app/learning/ (Pattern Store)            ││
│  └────────────────────────────────────────────────────────────────────────┘│
│                              │                                              │
│                              ▼                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐│
│  │                      INFRASTRUCTURE                                    ││
│  │   app/sandbox/ (Docker)   │   app/db/ (MongoDB + Beanie)               ││
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

1. Validates `project_id`.
2. Checks if workflow is already running.
3. Creates project directory.
4. Starts `run_workflow` in a background task.

### 2. Workflow Engine Starts

**File:** `app/workflow/engine.py` → `run_workflow()`

1. Sets workflow state to "running".
2. Scaffolds project directory structure.
3. Copies template files (shadcn/ui, Dockerfiles).
4. Initializes `FASTOrchestratorV2`.
5. Executes `engine.run()`.

---

## The FAST V2 Orchestrator

**File:** `app/orchestration/fast_orchestrator.py`

The V2 orchestrator is a robust engine that executes steps with built-in safety mechanisms:

### Key V2 Features
1.  **Dependency Barriers:** Steps only run when their dependencies (e.g., previous steps) are successfully completed.
2.  **Budget Management:** Tracks token usage and costs (INR) per project/step. Stops execution if budget is exceeded.
3.  **Self-Healing Pipeline:** Automatically attempts to repair failed steps or missing/broken files using `HealingPipeline`.
4.  **Pre-Step Validation:** Checks for critical files (e.g., `main.py`, `models.py`) before running expensive testing steps.
5.  **Checkpointing:** Saves progress after every successful step to `projects/.fast_checkpoints`, allowing resumption.
6.  **Cross-Step Context:** Passes intelligent context (entities, architecture decisions) between steps.

### The 11 Steps (Atomic Backend Upgrade)

| # | Step | Handler File | Agent | What It Does |
|---|------|--------------|-------|--------------|
| 1 | `analysis` | `handlers/analysis.py` | Marcus | Parse request, extract entities, classify archetype |
| 2 | `architecture` | `handlers/architecture.py` | Victoria | Create `architecture.md` (MongoDB/Beanie design) |
| 3 | `frontend_mock` | `handlers/frontend_mock.py` | Derek | Generate React components with mock data |
| 4 | `screenshot_verify` | `handlers/screenshot_verify.py` | Marcus | Visual QA review of UI |
| 5 | `contracts` | `handlers/contracts.py` | Marcus | Create `contracts.md` with API specifications |
| 6 | `backend_implementation` | `handlers/backend.py` | Derek | **Atomic Vertical**: Models + Routers + Deps |
| 7 | `system_integration` | `handlers/backend.py` | **Script** | **Deterministic Wiring**: Wires `main.py` + `requirements.txt` |
| 8 | `testing_backend` | `handlers/testing_backend.py` | Derek | Run pytest in Docker |
| 9 | `frontend_integration` | `handlers/frontend_integration.py` | Derek | Replace mock data with real API calls |
| 10 | `testing_frontend` | `handlers/testing_frontend.py` | Luna | Run Playwright E2E tests |
| 11 | `preview_final` | `handlers/preview.py` | Marcus | Final review and dynamic preview deployment |

---

## Agent System

The system uses specialized agents tailored to specific phases of software development:

| Agent | Role | System Prompt File |
|-------|------|-------------------|
| **Marcus** | Senior Architect & Code Reviewer | `app/llm/prompts/marcus.py` |
| **Derek** | Full-Stack Developer | `app/llm/prompts/derek.py` |
| **Victoria** | System Architect & Planner | `app/llm/prompts/victoria.py` |
| **Luna** | QA & DevOps Engineer | `app/llm/prompts/luna.py` |

The `supervised_agent_call` function wraps every agent interaction, ensuring that Marcus reviews the output before it is accepted.

---

## Supervision & Quality Gates

**File:** `app/supervision/supervisor.py` & `quality_gate.py`

Every piece of generated code must pass strict quality checks:

1.  **Pre-flight Check:** AST parsing to ensure valid Python/JS syntax.
2.  **Tiered Review:** Marcus reviews complex code; simple files get automated checks.
3.  **Approve/Reject Loop:** If quality score < 8/10, the agent is asked to retry with specific feedback.
4.  **Quality Gate:** If quality remains low after retries, the step fails (self-healing may trigger).

---

## Validation & Persistence

**File:** `app/validation/preflight.py` & `app/persistence/__init__.py`

*   **Pre-flight:** Checks for empty content, syntax errors (AST), and unbalanced JSX.
*   **Persistence:** Writes validated code to the project directory, normalizing paths for cross-platform compatibility.

---

## Tracking & Learning

Two new modules enhance the system's intelligence and observability:

### Tracking (`app/tracking/`)
*   **Metrics:** Collects performance data (step duration, token usage).
*   **Snapshots:** Captures state of the codebase at various points.
*   **Quality:** Tracks quality scores over time.

### Learning (`app/learning/`)
*   **Pattern Store:** Stores and retrieves successful coding patterns to improve future generations (`pattern_store.py`).
*   **Memory:** Manages long-term memory of project context.

---

## LLM Integration

**File:** `app/llm/adapter.py`

Supports multiple providers with a unified interface:
*   **Google Gemini:** (Default) High speed and large context window.
*   **OpenAI:** (Option) GPT-4o support.

Context management (`app/llm/prompt_management.py`) ensures only relevant files are sent to the LLM to save tokens and improve focus.

---

## Docker Sandbox Testing

**File:** `app/sandbox/manager.py`

*   **Isolation:** Each project runs in its own Docker container set (Frontend + Backend + MongoDB).
*   **Execution:** `pytest` and `playwright` tests run inside the containers.
*   **Feedback:** Test results (stdout/stderr) are fed back to agents for fixing bugs.

---

## Directory Structure

```
Backend/
├── app/
│   ├── main.py                    # FastAPI entry point
│   ├── db.py                      # MongoDB connection (Motor/Beanie)
│   ├── api/                       # REST API Endpoints
│   ├── core/                      # Configuration & Logging
│   ├── workflow/                  # Workflow Entry Point
│   ├── orchestration/             # 🌟 FAST V2 ORCHESTRATOR
│   ├── handlers/                  # Step Implementations
│   ├── supervision/               # Quality Control (Marcus)
│   ├── agents/                    # Agent Wrappers
│   ├── llm/                       # LLM Adapter & Prompts
│   ├── validation/                # Pre-write Validation (AST)
│   ├── persistence/               # File Writing
│   ├── sandbox/                   # Docker Management
│   ├── tracking/                  # 📊 Telemetry & Snapshots
│   ├── learning/                  # 🧠 Pattern Store & Memory
│   ├── tools/                     # Agent Tools
│   └── lib/                       # Utilities (Websockets, Monitor)
│
├── templates/                     # Project Templates (shadcn, Dockerfiles)
├── tests/                         # Backend Unit Tests
└── requirements.txt               # Dependencies
```

---

## Configuration

The application is configured via environment variables (cleanly managed in `.env`):

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Key for Google Gemini API | Required |
| `OPENAI_API_KEY` | Key for OpenAI API | Optional |
| `RATE_LIMIT` | API rate limit string | "100/minute" |
| `CORS_ORIGINS` | Comma-separated allowed origins | "*" |
| `MONGODB_URL` | MongoDB connection string | "mongodb://localhost:27017" |
| `LOG_LEVEL` | Logging verbosity | "INFO" |

---

## Running the Application

### Prerequisites
*   Python 3.10+
*   Docker & Docker Compose
*   MongoDB (local or remote)

### Setup

1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Configure Environment:**
    Copy `.env.example` to `.env` and add your API keys.

3.  **Run Dev Server:**
    ```bash
    uvicorn app.main:app --reload
    ```
    *   API: `http://localhost:8000`
    *   Docs: `http://localhost:8000/docs`

4.  **Run Tests:**
    ```bash
    pytest
    ```
