<div align="center">

# 🚀 GenCode Studio

### AI-Powered Full-Stack Code Generation with Multi-Agent Workflow

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18+-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://reactjs.org)
[![MongoDB](https://img.shields.io/badge/MongoDB-47A248?style=for-the-badge&logo=mongodb&logoColor=white)](https://mongodb.com)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)

---

*Transform natural language descriptions into production-ready full-stack applications*

[Features](#-features) • [Architecture](#-architecture) • [Quick Start](#-quick-start) • [How It Works](#-how-it-works) • [API Reference](#-api-reference)

</div>

---

## ✨ Features

<table>
<tr>
<td width="50%">

### 🤖 Multi-Agent System
- **Marcus** - Senior architect & code reviewer
- **Derek** - Full-stack developer (frontend + backend)
- **Victoria** - System architect & planner
- **Luna** - QA & DevOps engineer (Playwright testing)

</td>
<td width="50%">

### 🔄 FAST V2 Workflow Engine
- Dependency-aware step execution
- Budget management (~₹30/run)
- Self-healing on failures
- Quality gates & supervision

</td>
</tr>
<tr>
<td width="50%">

### 🛡️ Production-Grade Reliability
- AST-based syntax validation
- Pre-flight checks before persistence
- Automatic rollback on failures
- Docker sandbox testing

</td>
<td width="50%">

### 🎨 Intelligent UI Generation
- Attention-based archetype routing
- 6 UI vibes (dark_hacker, minimal_light, etc.)
- shadcn/ui component integration
- Responsive design by default

</td>
</tr>
</table>

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        GenCode Studio                           │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐             │
│  │ Marcus  │  │  Derek  │  │Victoria │  │  Luna   │   Agents   │
│  │Supervisor│  │Developer│  │Architect│  │   QA    │             │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘             │
│       │            │            │            │                   │
│       └────────────┴────────────┴────────────┘                   │
│                          ▼                                       │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                  FAST V2 Orchestrator                      │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐          │  │
│  │  │Analysis │→│ Arch    │→│Frontend │→│Backend  │→ ...     │  │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘          │  │
│  └───────────────────────────────────────────────────────────┘  │
│                          ▼                                       │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              Validation & Persistence Layer                │  │
│  │  • AST Syntax Check  • Pre-flight Gates  • Quality Scores │  │
│  └───────────────────────────────────────────────────────────┘  │
│                          ▼                                       │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Docker Sandbox                          │  │
│  │        Backend Tests  │  Frontend Tests  │  Preview        │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker Desktop
- MongoDB (local or Atlas)

### Installation

```bash
# Clone the repository
git clone https://github.com/NeuralNinja23/GenCode-Studio.git
cd GenCode-Studio

# Backend setup
cd Backend
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your API keys (GEMINI_API_KEY, MONGO_URL, etc.)

# Start backend
uvicorn app.main:app --reload

# Frontend setup (new terminal)
cd Frontend
npm install
npm run dev
```

### Environment Variables

```env
# Required
GEMINI_API_KEY=your_gemini_api_key
MONGO_URL=mongodb://localhost:27017/gencode_studio

# Optional
LLM_PROVIDER=gemini          # or openai, anthropic
LLM_MODEL=gemini-2.0-flash   # default model
```

---

## 🔄 How It Works

### The 12-Step Workflow

| Step | Agent | Description |
|------|-------|-------------|
| 1. **Analysis** | Marcus | Understand user request, extract entities |
| 2. **Architecture** | Victoria | Design system architecture, define contracts |
| 3. **Frontend Mock** | Derek | Create UI with mock data |
| 4. **Backend Models** | Derek | Generate MongoDB/Beanie models |
| 5. **Contracts** | Marcus | Finalize API contracts from mock data |
| 6. **Backend Routers** | Derek | Create FastAPI endpoints |
| 7. **Backend Main** | Derek | Configure FastAPI app entry point |
| 8. **Frontend Integration** | Derek | Replace mock data with real API calls |
| 9. **Screenshot Verify** | Marcus | Visual QA review |
| 10. **Testing Backend** | Derek | Run pytest in Docker sandbox |
| 11. **Testing Frontend** | Luna | Run Playwright E2E tests |
| 12. **Preview Final** | Marcus | Final review and deployment |

### Attention-Based Routing

GenCode Studio uses an **attention router** to classify requests:

```python
# Detected archetypes
archetypes = [
    "admin_dashboard",    # Management panels, CRUD systems
    "ecommerce_store",    # Product catalogs, carts, checkout
    "saas_app",           # Multi-tenant applications
    "realtime_collab",    # Chat, collaborative editing
    "portfolio_site",     # Personal/company websites
    "developer_tools",    # APIs, CLIs, utilities
]

# UI vibes
vibes = [
    "dark_hacker",        # Terminal-inspired, green/amber accents
    "minimal_light",      # Clean, whitespace-focused
    "vibrant_modern",     # Bold colors, gradients
    "playful_colorful",   # Fun, animated, rounded
    "corporate_clean",    # Professional, trustworthy
    "glassmorphism",      # Blur effects, transparency
]
```

---

## 📁 Project Structure

```
GenCode-Studio/
├── Backend/
│   ├── app/
│   │   ├── api/              # REST endpoints
│   │   ├── core/             # Config, constants, logging
│   │   ├── llm/              # LLM adapters (Gemini, OpenAI)
│   │   ├── models/           # Pydantic/Beanie models
│   │   ├── persistence/      # File validation & writing
│   │   ├── sandbox/          # Docker container management
│   │   ├── testing/          # Test runners
│   │   ├── workflow/
│   │   │   ├── agents/       # Marcus, Derek, Victoria
│   │   │   ├── engine_v2/    # FAST V2 orchestrator
│   │   │   ├── handlers/     # Step implementations
│   │   │   └── supervision/  # Quality gates, code review
│   │   └── main.py
│   ├── templates/            # shadcn/ui components, boilerplate
│   └── tests/
│
├── Frontend/
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── pages/            # Route pages
│   │   └── lib/              # API client, utilities
│   └── package.json
│
└── workspaces/               # Generated projects (gitignored)
```

---

## 🔌 API Reference

### Generate Application

```http
POST /api/workspace/{project_id}/generate/backend
Content-Type: application/json

{
  "prompt": "Create a bug tracking system with projects, issues, and comments"
}
```

### WebSocket Events

```javascript
// Connect to project WebSocket
const ws = new WebSocket(`ws://localhost:8000/ws/${projectId}`);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch(data.type) {
    case 'WORKFLOW_UPDATE':
      // Step progress updates
      break;
    case 'AGENT_LOG':
      // Agent thinking/output
      break;
    case 'WORKFLOW_COMPLETE':
      // Generation finished
      break;
  }
};
```

---

## 🛡️ Reliability Features

### 1. AST Validation
All Python files are parsed with `ast.parse()` before being written. Syntax errors are rejected automatically.

### 2. Pre-flight Checks
- Empty content detection
- Unbalanced brackets/braces
- Truncation detection (`...`, `<<EOF>`)
- Required file validation

### 3. Quality Gates
- Minimum quality score: 5/10
- Critical issues block workflow
- Warnings are logged but don't block

### 4. Self-Healing
- Missing routers → Fallback template generation
- Missing API client → Auto-generate from contracts
- Failed tests → Targeted fixes with differential context

---

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines before submitting PRs.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Built with ❤️ by [NeuralNinja23](https://github.com/NeuralNinja23)**

⭐ Star this repo if you find it useful!

</div>
