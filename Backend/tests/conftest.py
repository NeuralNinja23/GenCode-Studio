# tests/conftest.py
"""
Shared pytest fixtures for GenCode Studio pipeline tests.

Provides:
- Mock project paths and directories
- Mock manager for broadcasting
- Mock LLM responses
- Entity plan fixtures
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass, field


# ═══════════════════════════════════════════════════════
# MOCK TYPES
# ═══════════════════════════════════════════════════════

@dataclass
class MockChatMessage:
    """Mock chat message for testing."""
    role: str
    content: str


@dataclass
class MockEntitySpec:
    """Mock entity specification."""
    name: str
    plural: str
    type: str = "AGGREGATE"  # AGGREGATE or EMBEDDED
    generation_order: int = 0
    fields: Dict[str, str] = field(default_factory=dict)


@dataclass
class MockEntityPlan:
    """Mock entity plan for multi-entity testing."""
    entities: List[MockEntitySpec] = field(default_factory=list)
    relationships: List[Dict] = field(default_factory=list)
    
    def save(self, path: Path) -> None:
        """Save entity plan to JSON file."""
        import json
        data = {
            "entities": [
                {
                    "name": e.name,
                    "plural": e.plural,
                    "type": e.type,
                    "generation_order": e.generation_order,
                    "fields": e.fields,
                }
                for e in self.entities
            ],
            "relationships": self.relationships,
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ═══════════════════════════════════════════════════════
# FIXTURES - Project Setup
# ═══════════════════════════════════════════════════════

@pytest.fixture
def temp_workspace():
    """Create a temporary workspace directory with proper structure."""
    temp_dir = tempfile.mkdtemp(prefix="gencode_test_")
    workspace = Path(temp_dir)
    
    # Create standard project structure
    (workspace / "backend" / "app" / "routers").mkdir(parents=True)
    (workspace / "backend" / "tests").mkdir(parents=True)
    (workspace / "frontend" / "src" / "pages").mkdir(parents=True)
    (workspace / "frontend" / "src" / "components").mkdir(parents=True)
    (workspace / "frontend" / "src" / "data").mkdir(parents=True)
    (workspace / "frontend" / "src" / "lib").mkdir(parents=True)
    
    # Create minimal main.py (Golden Seed)
    main_py = workspace / "backend" / "app" / "main.py"
    main_py.write_text('''# backend/app/main.py
"""FastAPI Application - Golden Seed"""
from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
async def health_check():
    return {"status": "ok"}
''', encoding="utf-8")
    
    # Create __init__.py for package
    (workspace / "backend" / "app" / "__init__.py").write_text(
        "# Auto-generated for package imports\n",
        encoding="utf-8"
    )
    
    yield workspace
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def project_id():
    """Generate a test project ID."""
    return "test_project_123"


@pytest.fixture
def user_request():
    """Sample user request for testing."""
    return "Create a task management application with tasks, projects, and user assignments"


@pytest.fixture
def chat_history():
    """Empty chat history for testing."""
    return []


# ═══════════════════════════════════════════════════════
# FIXTURES - Mock Manager
# ═══════════════════════════════════════════════════════

@pytest.fixture
def mock_manager():
    """Create a mock manager for WebSocket broadcasting."""
    manager = AsyncMock()
    manager.broadcast = AsyncMock()
    return manager


# ═══════════════════════════════════════════════════════
# FIXTURES - Mock Entity Plans
# ═══════════════════════════════════════════════════════

@pytest.fixture
def simple_entity_plan():
    """Simple single-entity plan for basic tests."""
    return MockEntityPlan(
        entities=[
            MockEntitySpec(
                name="Task",
                plural="tasks",
                type="AGGREGATE",
                generation_order=0,
                fields={"title": "str", "description": "str", "status": "str"}
            )
        ],
        relationships=[]
    )


@pytest.fixture
def multi_entity_plan():
    """Multi-entity plan for complex tests."""
    return MockEntityPlan(
        entities=[
            MockEntitySpec(
                name="Project",
                plural="projects",
                type="AGGREGATE",
                generation_order=0,
                fields={"name": "str", "description": "str"}
            ),
            MockEntitySpec(
                name="Task",
                plural="tasks",
                type="AGGREGATE",
                generation_order=1,
                fields={"title": "str", "status": "str", "project_id": "str"}
            ),
            MockEntitySpec(
                name="Assignee",
                plural="assignees",
                type="EMBEDDED",
                generation_order=2,
                fields={"name": "str", "email": "str"}
            ),
        ],
        relationships=[
            {"from": "Task", "to": "Project", "type": "belongs_to"},
            {"from": "Task", "to": "Assignee", "type": "embeds"},
        ]
    )


# ═══════════════════════════════════════════════════════
# FIXTURES - Mock Contracts
# ═══════════════════════════════════════════════════════

@pytest.fixture
def mock_contracts_content():
    """Sample contracts.md content for testing."""
    return '''# API Contracts

## Overview
This document defines the API contracts for the Task Management application.

## Tasks

### List Tasks
- **Endpoint:** GET /api/tasks
- **Query Params:** status (optional), page (default: 1), limit (default: 20)
- **Response:** { "data": [...], "total": int, "page": int, "limit": int }

### Create Task
- **Endpoint:** POST /api/tasks
- **Body:** { "title": string, "description": string, "status": string }
- **Response:** { "id": string, "title": string, "description": string, "status": string }
- **Status:** 201 Created

### Get Task
- **Endpoint:** GET /api/tasks/{id}
- **Response:** { "id": string, "title": string, "description": string, "status": string }

### Update Task
- **Endpoint:** PUT /api/tasks/{id}
- **Body:** { "title"?: string, "description"?: string, "status"?: string }
- **Response:** Updated task object

### Delete Task
- **Endpoint:** DELETE /api/tasks/{id}
- **Response:** 204 No Content
'''


# ═══════════════════════════════════════════════════════
# FIXTURES - Mock LLM Responses  
# ═══════════════════════════════════════════════════════

@pytest.fixture
def mock_contracts_llm_response():
    """Mock LLM response for contracts step."""
    return {
        "output": {
            "thinking": "I will generate API contracts based on the frontend mock...",
            "files": [
                {
                    "path": "contracts.md",
                    "content": '''# API Contracts

## Tasks Endpoints

### GET /api/tasks
List all tasks with pagination.

### POST /api/tasks  
Create a new task.

### GET /api/tasks/{id}
Get a specific task.

### PUT /api/tasks/{id}
Update a task.

### DELETE /api/tasks/{id}
Delete a task.
'''
                }
            ]
        },
        "approved": True,
        "token_usage": {"input": 1000, "output": 500}
    }


@pytest.fixture
def mock_models_llm_response():
    """Mock LLM response for backend models step."""
    return {
        "spec": {
            "models": [
                {
                    "name": "Task",
                    "fields": [
                        {"name": "title", "type": "str"},
                        {"name": "description", "type": "Optional[str]", "default": "None"},
                        {"name": "status", "type": "str", "default": '"active"'}
                    ]
                }
            ]
        },
        "token_usage": {"input": 800, "output": 400}
    }


@pytest.fixture
def mock_backend_impl_llm_response():
    """Mock LLM response for backend implementation step."""
    return {
        "output": {
            "thinking": "I will implement the Task model and router...",
            "manifest": {
                "dependencies": [],
                "backend_routers": ["tasks"],
            },
            "files": [
                {
                    "path": "backend/app/models.py",
                    "content": '''from beanie import Document
from typing import Optional


class Task(Document):
    """Task model for the task management app."""
    title: str
    description: Optional[str] = None
    status: str = "active"
    
    class Settings:
        name = "tasks"
'''
                },
                {
                    "path": "backend/app/routers/tasks.py", 
                    "content": '''from fastapi import APIRouter, HTTPException, Query, status
from typing import List, Optional
from app.models import Task

router = APIRouter()


@router.get("/")
async def list_tasks(
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """List all tasks with optional filtering."""
    query = Task.find_all()
    if status_filter:
        query = Task.find(Task.status == status_filter)
    
    total = await query.count()
    tasks = await query.skip((page - 1) * limit).limit(limit).to_list()
    
    return {
        "data": tasks,
        "total": total,
        "page": page,
        "limit": limit
    }


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_task(task_data: dict):
    """Create a new task."""
    task = Task(**task_data)
    await task.insert()
    return task


@router.get("/{task_id}")
async def get_task(task_id: str):
    """Get a specific task by ID."""
    task = await Task.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.put("/{task_id}")
async def update_task(task_id: str, updates: dict):
    """Update a task."""
    task = await Task.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    for key, value in updates.items():
        setattr(task, key, value)
    await task.save()
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)  
async def delete_task(task_id: str):
    """Delete a task."""
    task = await Task.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await task.delete()
'''
                }
            ]
        },
        "approved": True,
        "token_usage": {"input": 1500, "output": 800}
    }


@pytest.fixture
def mock_tests_llm_response():
    """Mock LLM response for testing backend step."""
    return {
        "output": {
            "thinking": "I will generate comprehensive tests for the Task API...",
            "files": [
                {
                    "path": "backend/tests/test_api.py",
                    "content": '''# backend/tests/test_api.py
"""API Tests for Task Management"""
import pytest
from faker import Faker

fake = Faker()

TASKS_BASE = "/api/tasks"


@pytest.mark.anyio
async def test_health_check(client):
    """Test the health endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.anyio
async def test_list_tasks(client):
    """Test listing all tasks."""
    response = await client.get(TASKS_BASE)
    assert response.status_code == 200
    data = response.json()
    assert "data" in data or isinstance(data, list)


@pytest.mark.anyio
async def test_create_task(client):
    """Test creating a task."""
    task_data = {
        "title": fake.sentence(nb_words=4),
        "description": fake.paragraph(nb_sentences=2),
        "status": "active"
    }
    response = await client.post(TASKS_BASE, json=task_data)
    assert response.status_code == 201
    created = response.json()
    assert "id" in created
    assert created["title"] == task_data["title"]


@pytest.mark.anyio  
async def test_get_task_not_found(client):
    """Test getting a non-existent task returns 404."""
    fake_id = "507f1f77bcf86cd799439011"
    response = await client.get(f"{TASKS_BASE}/{fake_id}")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_delete_task(client):
    """Test deleting a task."""
    # First create a task
    task_data = {
        "title": fake.sentence(nb_words=4),
        "description": fake.paragraph(nb_sentences=2),
        "status": "active"
    }
    create_response = await client.post(TASKS_BASE, json=task_data)
    assert create_response.status_code == 201
    task_id = create_response.json()["id"]
    
    # Then delete it
    delete_response = await client.delete(f"{TASKS_BASE}/{task_id}")
    assert delete_response.status_code == 204
'''
                }
            ]
        },
        "approved": True,
        "token_usage": {"input": 1200, "output": 600}
    }
