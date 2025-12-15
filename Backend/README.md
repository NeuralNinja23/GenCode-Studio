<div align="center">

# ⚙️ GenCode Studio Backend

### **The Brain Behind AI-Powered Code Generation**

<br />

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![MongoDB](https://img.shields.io/badge/MongoDB-Beanie_ODM-47A248?style=for-the-badge&logo=mongodb&logoColor=white)](https://mongodb.com)
[![Docker](https://img.shields.io/badge/Docker-Sandbox-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)

<br />

---

</div>

<br />

## 📋 Table of Contents

- [Quick Overview](#-quick-overview)
- [System Architecture](#-system-architecture)
- [The FAST V2 Orchestrator](#-the-fast-v2-orchestrator)
- [ArborMind Intelligence](#-arbormind-intelligence-core)
- [Agent System](#-agent-system)
- [Step Handlers](#-step-handlers)
- [Self-Healing Pipeline](#-self-healing-pipeline)
- [Validation & Persistence](#-validation--persistence)
- [Docker Sandbox](#-docker-sandbox-testing)
- [API Endpoints](#-api-endpoints)
- [Directory Structure](#-directory-structure)
- [Configuration](#-configuration)
- [Running the Backend](#-running-the-backend)

<br />

---

<br />

## 🚀 Quick Overview

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   User       │───▶│   FastAPI    │───▶│   FAST V2    │───▶│   AI Agents  │───▶│  Generated   │
│   Request    │    │   + WebSocket│    │ Orchestrator │    │ + ArborMind  │    │    Code      │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
                           │                   │                   │                   │
                           ▼                   ▼                   ▼                   ▼
                      Rate Limit          12-Step              Gemini/            AST Valid
                      CORS                Pipeline             OpenAI             Tested
                      Auth                Self-Healing         Multi-Agent        Production
```

**The Request Lifecycle:**

| Step | What Happens |
|:-----|:-------------|
| 1️⃣ | `POST /api/workspace/{id}/generate` arrives |
| 2️⃣ | Workflow engine initializes FAST V2 Orchestrator |
| 3️⃣ | 12 atomic steps execute with dependency barriers |
| 4️⃣ | AI agents (Marcus, Derek, Victoria, Luna) generate code |
| 5️⃣ | ArborMind routes decisions via attention mechanism |
| 6️⃣ | Code validated (AST + pre-flight checks) |
| 7️⃣ | Tests run in Docker sandbox |
| 8️⃣ | Final code persisted to workspace |

<br />

---

<br />

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                    FASTAPI APPLICATION                                   │
│                                      app/main.py                                         │
│                         (Rate Limiting • CORS • WebSocket • Monitoring)                  │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐        │
│  │  /api/workspace│  │  /api/projects │  │  /api/sandbox  │  │  /ws/{project} │        │
│  │    Generate    │  │    CRUD        │  │   Docker Mgmt  │  │   Real-time    │        │
│  └───────┬────────┘  └────────────────┘  └────────────────┘  └───────┬────────┘        │
│          │                                                            │                 │
│          ▼                                                            ▼                 │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │                            WORKFLOW ENGINE                                        │  │
│  │                          app/workflow/engine.py                                   │  │
│  │                                   │                                               │  │
│  │                                   ▼                                               │  │
│  │  ┌────────────────────────────────────────────────────────────────────────────┐  │  │
│  │  │                        🌟 FAST V2 ORCHESTRATOR 🌟                           │  │  │
│  │  │                    app/orchestration/fast_orchestrator.py                   │  │  │
│  │  │                                                                              │  │  │
│  │  │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │  │  │
│  │  │   │ Dependency  │  │   Budget    │  │ Self-Healing│  │ Checkpoints │       │  │  │
│  │  │   │  Barriers   │  │  Manager    │  │  Pipeline   │  │   & Resume  │       │  │  │
│  │  │   └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘       │  │  │
│  │  └────────────────────────────────────────────────────────────────────────────┘  │  │
│  │                                   │                                               │  │
│  │                                   ▼                                               │  │
│  │  ┌────────────────────────────────────────────────────────────────────────────┐  │  │
│  │  │                          STEP HANDLERS                                      │  │  │
│  │  │                          app/handlers/                                      │  │  │
│  │  │                                                                              │  │  │
│  │  │   analysis │ architecture │ contracts │ backend │ frontend │ testing       │  │  │
│  │  └────────────────────────────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────────────────┘  │
│                                   │                                                     │
│          ┌───────────────────────┬┴───────────────────────┐                            │
│          ▼                       ▼                        ▼                            │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐                     │
│  │  🌳 ARBORMIND    │  │    AI AGENTS     │  │   SUPERVISION    │                     │
│  │  Intelligence    │  │                  │  │   Quality Gates  │                     │
│  │                  │  │  Marcus (Review) │  │                  │                     │
│  │  • Router        │  │  Derek (Code)    │  │  • Pre-flight    │                     │
│  │  • Evolution     │  │  Victoria (Arch) │  │  • Tiered Review │                     │
│  │  • Explorer      │  │  Luna (Test)     │  │  • Score Check   │                     │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘                     │
│          │                       │                        │                            │
│          └───────────────────────┴────────────────────────┘                            │
│                                   │                                                     │
│                                   ▼                                                     │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │                              LLM INTEGRATION                                      │  │
│  │                           app/llm/adapter.py                                      │  │
│  │                                                                                    │  │
│  │   ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌─────────────────────────┐    │  │
│  │   │  Gemini    │  │   OpenAI   │  │  Anthropic │  │  Prompt Management      │    │  │
│  │   │ (Default)  │  │   GPT-4o   │  │   Claude   │  │  Context Optimization   │    │  │
│  │   └────────────┘  └────────────┘  └────────────┘  └─────────────────────────┘    │  │
│  └──────────────────────────────────────────────────────────────────────────────────┘  │
│                                   │                                                     │
│                                   ▼                                                     │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │                         VALIDATION & PERSISTENCE                                  │  │
│  │                                                                                    │  │
│  │   ┌────────────────┐  ┌────────────────┐  ┌────────────────┐                      │  │
│  │   │ AST Validator  │  │  Pre-flight    │  │ File Persister │                      │  │
│  │   │ Syntax Check   │  │  Safety Checks │  │ Cross-Platform │                      │  │
│  │   └────────────────┘  └────────────────┘  └────────────────┘                      │  │
│  └──────────────────────────────────────────────────────────────────────────────────┘  │
│                                   │                                                     │
│                                   ▼                                                     │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │                            INFRASTRUCTURE                                         │  │
│  │                                                                                    │  │
│  │   ┌────────────────┐  ┌────────────────┐  ┌────────────────┐                      │  │
│  │   │ 🐳 Docker      │  │  MongoDB       │  │  Pattern &     │                      │  │
│  │   │ Sandbox        │  │  Beanie ODM    │  │  Learning Store│                      │  │
│  │   └────────────────┘  └────────────────┘  └────────────────┘                      │  │
│  └──────────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

<br />

---

<br />

## ⚡ The FAST V2 Orchestrator

The heart of the backend — a robust 12-step pipeline with enterprise-grade reliability.

**File:** `app/orchestration/fast_orchestrator.py` (841 lines)

### Core Features

<table>
<tr>
<td width="50%">

**🔗 Dependency Barriers**
- Steps only run when prerequisites complete
- Prevents cascade failures
- Enables parallel execution where possible

**💰 Budget Management**
- Tracks token usage per step
- Cost monitoring (INR/USD)
- Auto-stops on budget exceeded

</td>
<td width="50%">

**🩹 Self-Healing Pipeline**
- Automatic error recovery
- LLM regeneration + fallback templates
- Semantic error classification

**📍 Checkpointing**
- Saves progress after each step
- Resume from failure point
- `.fast_checkpoints` directory

</td>
</tr>
</table>

### The 12 Steps

| # | Step | Handler | Agent | Description |
|:-:|:-----|:--------|:------|:------------|
| 1 | `analysis` | `analysis.py` | Marcus | Parse request, extract entities, classify archetype |
| 2 | `architecture` | `architecture.py` | Victoria | Design system architecture, create `architecture.md` |
| 3 | `frontend_mock` | `frontend_mock.py` | Derek | Generate React UI with mock data |
| 4 | `screenshot_verify` | `screenshot_verify.py` | Marcus | Visual QA review of generated UI |
| 5 | `contracts` | `contracts.py` | Marcus | Create `contracts.md` with OpenAPI specs |
| 6 | `backend_models` | `backend_models.py` | Derek | Generate MongoDB/Beanie models |
| 7 | `backend_implementation` | `backend.py` | Derek | Atomic: Models + Routers + Dependencies |
| 8 | `system_integration` | `backend.py` | Script | Deterministic wiring: `main.py` + `requirements.txt` |
| 9 | `testing_backend` | `testing_backend.py` | Derek | Run pytest in Docker sandbox |
| 10 | `frontend_integration` | `frontend_integration.py` | Derek | Replace mock data with real API calls |
| 11 | `testing_frontend` | `testing_frontend.py` | Luna | Run Playwright E2E tests |
| 12 | `preview_final` | `preview.py` | Marcus | Final review, dynamic preview deployment |

<br />

---

<br />

## 🌳 ArborMind Intelligence Core

**Location:** `app/arbormind/`

ArborMind is the neural orchestration engine that powers intelligent decision-making.

### Components

| File | Purpose |
|:-----|:--------|
| `router.py` | **V≠K Attention Router** — Semantic routing using separate Key/Value vectors |
| `evolution.py` | **Self-Evolution** — EMA-adjusted V-vectors learn from outcomes |
| `explorer.py` | **E-AM Explorer** — Foreign pattern injection for creative solutions |
| `metrics_collector.py` | **Pipeline Metrics** — Tracks step durations, success rates |

### The V≠K Architecture

Unlike traditional RAG where `V = K`, ArborMind uses separate vectors:

```python
# Query (Q): User request or error log
# Key (K): Semantic description of options
# Value (V): Behavior configuration (JSON)

# Example: Smart tool selection
result = await arbormind_route(
    query="Fix broken React imports",
    options=[
        {"key": "syntax fixer", "value": {"mode": "strict"}},
        {"key": "import resolver", "value": {"mode": "smart"}},
    ]
)
# → Returns: {"mode": "smart"} with confidence score
```

<br />

---

<br />

## 🤖 Agent System

**Location:** `app/agents/` and `app/llm/prompts/`

Four specialized AI agents work together:

<table>
<tr>
<td width="25%" align="center">

### 🔵 Marcus
**Senior Architect**

Code review, quality gates, final approval. Uses `tiered_review` for efficiency.

</td>
<td width="25%" align="center">

### 🟣 Victoria
**System Architect**

Designs system architecture, API contracts, database schemas.

</td>
<td width="25%" align="center">

### 🟢 Derek
**Full-Stack Developer**

Implements React frontends, FastAPI backends, integrations.

</td>
<td width="25%" align="center">

### 🟡 Luna
**QA Engineer**

Writes Playwright E2E tests, validates flows, catches bugs.

</td>
</tr>
</table>

**Supervised Agent Calls:**
```python
# Every agent call passes through supervision
result = await supervised_agent_call(
    agent="derek",
    task="Generate user router",
    context={"entities": [...], "contracts": "..."}
)
# Marcus reviews automatically if quality < threshold
```

<br />

---

<br />

## 📂 Step Handlers

**Location:** `app/handlers/` (20 files)

| Handler | Lines | Purpose |
|:--------|------:|:--------|
| `analysis.py` | 10,338 | Entity extraction, archetype detection |
| `architecture.py` | 19,010 | System design, data modeling |
| `archetype_guidance.py` | 57,738 | UI patterns for 6 app types |
| `backend.py` | 38,098 | Router generation, CRUD logic |
| `backend_models.py` | 17,869 | Beanie model generation |
| `contracts.py` | 34,186 | OpenAPI contract creation |
| `frontend_mock.py` | 20,918 | React component scaffolding |
| `frontend_integration.py` | 14,915 | API integration for frontend |
| `testing_backend.py` | 59,563 | Pytest generation & execution |
| `testing_frontend.py` | 42,134 | Playwright E2E test generation |
| `screenshot_verify.py` | 16,740 | Visual QA verification |
| `preview.py` | 7,442 | Final preview deployment |

<br />

---

<br />

## 🩹 Self-Healing Pipeline

**Location:** `app/orchestration/`

When steps fail, the system automatically attempts recovery:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Step Fails  │────▶│ Error Router│────▶│ Healing     │────▶│ Retry Step  │
│             │     │ Classify    │     │ Strategy    │     │             │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                           │                   │
                           ▼                   ▼
                    ┌─────────────┐     ┌─────────────┐
                    │ Syntax      │     │ Fallback    │
                    │ Import      │     │ Template    │
                    │ Logic       │     │ Generation  │
                    └─────────────┘     └─────────────┘
```

| File | Purpose |
|:-----|:--------|
| `healing_pipeline.py` | Main healing orchestration |
| `error_router.py` | Semantic error classification |
| `healing_policy.py` | Retry limits & strategies |
| `self_healing_manager.py` | 48KB of repair logic |
| `fallback_*_agent.py` | Fallback generators for models, routers, APIs |

<br />

---

<br />

## ✅ Validation & Persistence

### Pre-flight Validation

**Location:** `app/validation/`

| Check | Description |
|:------|:------------|
| **AST Parsing** | Python files parsed with `ast.parse()` |
| **Empty Content** | Rejects blank files |
| **Bracket Balance** | Detects `{`, `[`, `(` mismatches |
| **Truncation** | Catches `...`, `<<EOF>`, incomplete code |
| **Undefined Names** | Validates all referenced names exist |

### File Persistence

**Location:** `app/persistence/`

- Cross-platform path normalization
- Atomic writes (temp file → rename)
- Backup before overwrite
- Directory creation on demand

<br />

---

<br />

## 🐳 Docker Sandbox Testing

**Location:** `app/sandbox/` (7 files)

Tests run in isolated Docker containers:

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Network                        │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Backend    │  │   Frontend   │  │   MongoDB    │  │
│  │   Container  │◄─┤   Container  │  │   Container  │  │
│  │   pytest     │  │   playwright │  │              │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

| File | Purpose |
|:-----|:--------|
| `manager.py` | Container lifecycle management |
| `executor.py` | Command execution in containers |
| `builder.py` | Image building from project templates |

<br />

---

<br />

## 🌐 API Endpoints

**Location:** `app/api/` (9 files)

### Workspace API
| Method | Endpoint | Description |
|:-------|:---------|:------------|
| `POST` | `/api/workspace/{id}/generate` | Start code generation |
| `GET` | `/api/workspace/{id}` | Get workspace details |
| `GET` | `/api/workspace/{id}/files` | List generated files |
| `DELETE` | `/api/workspace/{id}` | Delete workspace |

### Projects API
| Method | Endpoint | Description |
|:-------|:---------|:------------|
| `GET` | `/api/projects` | List all projects |
| `POST` | `/api/projects` | Create new project |
| `GET` | `/api/projects/{id}` | Get project details |

### Sandbox API
| Method | Endpoint | Description |
|:-------|:---------|:------------|
| `POST` | `/api/sandbox/{id}/start` | Start preview containers |
| `POST` | `/api/sandbox/{id}/stop` | Stop containers |

### WebSocket
| Endpoint | Description |
|:---------|:------------|
| `/ws/{project_id}` | Real-time workflow updates |

<br />

---

<br />

## 📁 Directory Structure

```
Backend/
├── app/
│   ├── main.py                     # FastAPI entry point
│   │
│   ├── api/                        # REST API Endpoints (9 files)
│   │   ├── workspace.py            # Generation endpoints
│   │   ├── projects.py             # Project CRUD
│   │   ├── sandbox.py              # Docker management
│   │   └── ...
│   │
│   ├── orchestration/              # 🌟 FAST V2 Core (31 files)
│   │   ├── fast_orchestrator.py    # Main orchestrator (841 lines)
│   │   ├── healing_pipeline.py     # Self-healing
│   │   ├── error_router.py         # Error classification
│   │   ├── budget_manager.py       # Cost tracking
│   │   ├── checkpoint.py           # Progress saving
│   │   └── ...
│   │
│   ├── handlers/                   # Step Implementations (20 files)
│   │   ├── analysis.py             # Entity extraction
│   │   ├── architecture.py         # System design
│   │   ├── backend.py              # Router generation
│   │   ├── testing_backend.py      # Pytest (59K lines)
│   │   └── ...
│   │
│   ├── arbormind/                  # 🌳 Intelligence Core (7 files)
│   │   ├── router.py               # V≠K attention routing
│   │   ├── evolution.py            # Self-evolution
│   │   ├── explorer.py             # Pattern discovery
│   │   └── metrics_collector.py    # Pipeline metrics
│   │
│   ├── agents/                     # Agent Wrappers
│   ├── llm/                        # LLM Integration (13 files)
│   │   ├── adapter.py              # Multi-provider adapter
│   │   ├── prompt_management.py    # Context optimization
│   │   └── prompts/                # Agent system prompts
│   │
│   ├── supervision/                # Quality Control (4 files)
│   │   ├── supervisor.py           # Marcus supervision
│   │   ├── quality_gate.py         # Score thresholds
│   │   └── tiered_review.py        # Efficiency routing
│   │
│   ├── validation/                 # Pre-write Validation
│   ├── persistence/                # File Writing
│   ├── sandbox/                    # Docker Management (7 files)
│   ├── learning/                   # Pattern Store (4 files)
│   ├── tracking/                   # Telemetry (4 files)
│   ├── tools/                      # Agent Tools (4 files)
│   ├── models/                     # Pydantic Models (5 files)
│   ├── core/                       # Config & Logging (8 files)
│   ├── utils/                      # Utilities (11 files)
│   ├── db/                         # Database Connection
│   └── lib/                        # Shared Libraries
│
├── templates/                      # Project Templates (85 files)
│   ├── shadcn/                     # UI components
│   ├── docker/                     # Dockerfiles
│   └── base/                       # Boilerplate code
│
├── tests/                          # Backend Unit Tests
├── data/                           # Static Data Files
├── scripts/                        # Utility Scripts
│
├── requirements.txt                # Dependencies
├── requirements.lock               # Locked versions
└── .env.example                    # Environment template
```

<br />

---

<br />

## ⚙️ Configuration

### Environment Variables

```env
# ═══════════════════════════════════════════════════════════════
# 🔑 REQUIRED
# ═══════════════════════════════════════════════════════════════
GEMINI_API_KEY=your_gemini_api_key_here
MONGO_URL=mongodb://localhost:27017/gencode_studio

# ═══════════════════════════════════════════════════════════════
# 🤖 LLM CONFIGURATION
# ═══════════════════════════════════════════════════════════════
LLM_PROVIDER=gemini                # gemini | openai | anthropic
LLM_MODEL=gemini-2.0-flash-exp     # Default model for generation
OPENAI_API_KEY=                    # Optional: for GPT-4o
ANTHROPIC_API_KEY=                 # Optional: for Claude

# ═══════════════════════════════════════════════════════════════
# 🌐 SERVER CONFIGURATION
# ═══════════════════════════════════════════════════════════════
RATE_LIMIT=100/minute              # API rate limiting
CORS_ORIGINS=*                     # Allowed origins
LOG_LEVEL=INFO                     # DEBUG | INFO | WARNING | ERROR

# ═══════════════════════════════════════════════════════════════
# 🐳 DOCKER CONFIGURATION
# ═══════════════════════════════════════════════════════════════
DOCKER_HOST=npipe:////./pipe/docker_engine    # Windows
# DOCKER_HOST=unix:///var/run/docker.sock     # Linux/Mac

# ═══════════════════════════════════════════════════════════════
# 📁 PATHS
# ═══════════════════════════════════════════════════════════════
WORKSPACE_ROOT=./workspaces        # Generated projects location
TEMPLATE_ROOT=./templates          # Project templates
```

### Core Constants

**File:** `app/core/constants.py`

```python
WORKFLOW_CONFIG = {
    "max_retries_per_step": 3,
    "quality_threshold": 5.0,
    "budget_limit_inr": 30,
    "sandbox_timeout_seconds": 120,
    "enable_self_healing": True,
    "enable_attention_routing": True,
}
```

<br />

---

<br />

## 🚀 Running the Backend

### Prerequisites

| Requirement | Version | Purpose |
|:------------|:--------|:--------|
| Python | 3.11+ | Runtime |
| Docker | Latest | Sandbox testing |
| MongoDB | 6.0+ | Database |

### Setup

```bash
# 1. Navigate to backend
cd Backend

# 2. Create virtual environment
python -m venv .venv

# 3. Activate
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux/Mac

# 4. Install dependencies
pip install -r requirements.txt

# 5. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 6. Start MongoDB (if local)
docker run -d -p 27017:27017 --name mongodb mongo:6

# 7. Run development server
uvicorn app.main:app --reload --port 8000
```

### Access Points

| URL | Description |
|:----|:------------|
| `http://localhost:8000` | API root |
| `http://localhost:8000/docs` | Swagger UI |
| `http://localhost:8000/redoc` | ReDoc |
| `ws://localhost:8000/ws/{id}` | WebSocket |

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_orchestrator.py -v
```

<br />

---

<br />

<div align="center">

### Part of [GenCode Studio](../README.md)

**Built with ❤️ using FastAPI, MongoDB, and Google Gemini**

</div>
