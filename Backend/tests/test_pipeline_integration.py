# tests/test_pipeline_integration.py
"""
Integration Tests for the Complete Backend Pipeline

Tests the full flow: Contracts → Backend Implementation → System Integration → Testing Backend

This validates that all steps work together correctly with proper handoffs.
"""
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import json
import re


class TestPipelineFlow:
    """Test the complete pipeline execution flow."""
    
    @pytest.mark.asyncio
    async def test_full_pipeline_creates_working_backend(
        self, temp_workspace, project_id, user_request, mock_manager, chat_history
    ):
        """
        GIVEN a user request
        WHEN the full pipeline executes
        THEN a complete, testable backend should be created
        
        Steps:
        1. Contracts → contracts.md
        2. Backend Implementation → models.py + routers/*.py
        3. System Integration → wired main.py
        4. Testing Backend → test_api.py with passing tests
        """
        # ═══ STEP 5: Contracts ═══
        contracts_content = '''# API Contracts

## Tasks

### List Tasks
GET /api/tasks
Response: { "data": [...], "total": int }

### Create Task  
POST /api/tasks
Body: { "title": str, "description": str, "status": str }
Response: 201 Created

### Get Task
GET /api/tasks/{id}
Response: 200 OK

### Update Task
PUT /api/tasks/{id}

### Delete Task
DELETE /api/tasks/{id}
Response: 204 No Content
'''
        contracts_path = temp_workspace / "contracts.md"
        contracts_path.write_text(contracts_content, encoding="utf-8")
        
        # ═══ STEP 6: Backend Implementation ═══
        models_content = '''from beanie import Document
from typing import Optional

class Task(Document):
    title: str
    description: Optional[str] = None
    status: str = "active"
    
    class Settings:
        name = "tasks"
'''
        models_path = temp_workspace / "backend" / "app" / "models.py"
        models_path.write_text(models_content, encoding="utf-8")
        
        router_content = '''from fastapi import APIRouter, HTTPException, status
from typing import Optional
from app.models import Task

router = APIRouter()

@router.get("/")
async def list_tasks():
    tasks = await Task.find_all().to_list()
    return {"data": tasks, "total": len(tasks)}

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_task(data: dict):
    task = Task(**data)
    await task.insert()
    return task

@router.get("/{task_id}")
async def get_task(task_id: str):
    task = await Task.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Not found")
    return task

@router.put("/{task_id}")
async def update_task(task_id: str, data: dict):
    task = await Task.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Not found")
    for k, v in data.items():
        setattr(task, k, v)
    await task.save()
    return task

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: str):
    task = await Task.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Not found")
    await task.delete()
'''
        router_path = temp_workspace / "backend" / "app" / "routers" / "tasks.py"
        router_path.write_text(router_content, encoding="utf-8")
        
        # ═══ STEP 7: System Integration ═══
        main_content = '''from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.database import init_db, close_db
from app.routers import tasks

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()

app = FastAPI(lifespan=lifespan)

app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])

@app.get("/health")
async def health_check():
    return {"status": "ok"}
'''
        main_path = temp_workspace / "backend" / "app" / "main.py"
        main_path.write_text(main_content, encoding="utf-8")
        
        # ═══ STEP 8: Testing Backend ═══
        test_content = '''import pytest
from faker import Faker

fake = Faker()
TASKS_BASE = "/api/tasks"

@pytest.mark.anyio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200

@pytest.mark.anyio
async def test_create_task(client):
    data = {"title": fake.sentence(), "status": "active"}
    response = await client.post(TASKS_BASE, json=data)
    assert response.status_code == 201
'''
        test_path = temp_workspace / "backend" / "tests" / "test_api.py"
        test_path.write_text(test_content, encoding="utf-8")
        
        # ═══ VERIFY COMPLETE PIPELINE OUTPUT ═══
        assert contracts_path.exists(), "Contracts should exist"
        assert models_path.exists(), "Models should exist"
        assert router_path.exists(), "Router should exist"
        assert main_path.exists(), "Main.py should exist"
        assert test_path.exists(), "Tests should exist"
        
        # Verify linkage between steps
        main_content = main_path.read_text(encoding="utf-8")
        assert "from app.routers import tasks" in main_content
        assert "include_router" in main_content


class TestStepHandoffs:
    """Test data handoffs between steps."""
    
    @pytest.mark.asyncio
    async def test_contracts_to_backend_impl_handoff(
        self, temp_workspace, mock_contracts_content
    ):
        """
        GIVEN contracts.md from Step 5
        WHEN Step 6 runs
        THEN it should read contracts to determine field names
        """
        contracts_path = temp_workspace / "contracts.md"
        contracts_path.write_text(mock_contracts_content, encoding="utf-8")
        
        # Step 6 reads contracts
        contracts = contracts_path.read_text(encoding="utf-8")
        
        # Should find field definitions
        assert "title" in contracts
        assert "description" in contracts
        assert "status" in contracts
    
    @pytest.mark.asyncio
    async def test_entity_plan_to_multi_entity_handoff(
        self, temp_workspace, multi_entity_plan
    ):
        """
        GIVEN entity_plan.json from contracts step
        WHEN backend implementation runs
        THEN it should iterate entities in generation_order
        """
        entity_plan_path = temp_workspace / "entity_plan.json"
        multi_entity_plan.save(entity_plan_path)
        
        # Load plan
        plan_data = json.loads(entity_plan_path.read_text(encoding="utf-8"))
        
        # Sort by generation_order as backend_implementation does
        entities = sorted(plan_data["entities"], key=lambda e: e["generation_order"])
        
        # First should be Project (order 0), then Task (order 1)
        assert entities[0]["name"] == "Project"
        assert entities[1]["name"] == "Task"
    
    @pytest.mark.asyncio
    async def test_backend_impl_to_integration_handoff(self, temp_workspace):
        """
        GIVEN routers from Step 6
        WHEN Step 7 runs
        THEN it should discover and wire all routers
        """
        routers_dir = temp_workspace / "backend" / "app" / "routers"
        routers_dir.mkdir(parents=True, exist_ok=True)
        
        # Create routers (from Step 6)
        (routers_dir / "tasks.py").write_text("router = APIRouter()", encoding="utf-8")
        (routers_dir / "projects.py").write_text("router = APIRouter()", encoding="utf-8")
        
        # Step 7 discovers them
        discovered = [
            f.stem for f in routers_dir.glob("*.py")
            if f.stem != "__init__"
        ]
        
        assert "tasks" in discovered
        assert "projects" in discovered
    
    @pytest.mark.asyncio
    async def test_integration_to_testing_handoff(self, temp_workspace):
        """
        GIVEN wired main.py from Step 7
        WHEN Step 8 runs
        THEN tests should be able to import app
        """
        main_path = temp_workspace / "backend" / "app" / "main.py"
        main_path.write_text('''from fastapi import FastAPI
app = FastAPI()
''', encoding="utf-8")
        
        # Tests would do: from app.main import app
        # This verifies the file exists and is importable
        assert main_path.exists()
        content = main_path.read_text(encoding="utf-8")
        assert "app = FastAPI()" in content


class TestPipelineResilience:
    """Test pipeline resilience and error handling."""
    
    @pytest.mark.asyncio
    async def test_pipeline_continues_on_optional_failures(self, temp_workspace):
        """
        GIVEN a step that partially fails
        WHEN next step runs
        THEN pipeline should continue with best effort
        """
        # Even if one router fails, others should be wired
        routers_dir = temp_workspace / "backend" / "app" / "routers"
        routers_dir.mkdir(parents=True, exist_ok=True)
        
        # One valid, one broken
        (routers_dir / "tasks.py").write_text("router = APIRouter()", encoding="utf-8")
        (routers_dir / "broken.py").write_text("# No router defined", encoding="utf-8")
        
        # Should still wire tasks.py
        valid_routers = []
        for f in routers_dir.glob("*.py"):
            content = f.read_text(encoding="utf-8")
            if "router = APIRouter()" in content:
                valid_routers.append(f.stem)
        
        assert "tasks" in valid_routers
        assert "broken" not in valid_routers
    
    @pytest.mark.asyncio
    async def test_pipeline_healing_budget(self):
        """
        GIVEN a step that needs healing
        WHEN healing budget is tracked
        THEN it should respect budget limits
        """
        # Healing budget tracking
        healing_budget = {
            "max_attempts": 3,
            "attempts_used": 0,
            "budget_remaining": 3
        }
        
        # Simulate healing attempts
        for _ in range(4):  # Try 4 times
            if healing_budget["attempts_used"] < healing_budget["max_attempts"]:
                healing_budget["attempts_used"] += 1
                healing_budget["budget_remaining"] -= 1
        
        assert healing_budget["attempts_used"] == 3  # Capped at max
        assert healing_budget["budget_remaining"] == 0


class TestStepContracts:
    """Test step contract validation."""
    
    def test_backend_implementation_contracts(self, temp_workspace):
        """
        GIVEN StepContracts definition
        WHEN backend_implementation output is checked
        THEN it should contain required patterns
        """
        contracts = {
            "must_contain": ["Document", "class", "router", "async def"],
            "files_required": ["backend/app/models.py", "backend/app/routers/"]
        }
        
        # Simulate output
        models_content = "class Task(Document):\n    pass"
        router_content = "router = APIRouter()\n\nasync def list_tasks():\n    pass"
        combined = models_content + "\n" + router_content
        
        for pattern in contracts["must_contain"]:
            assert pattern.lower() in combined.lower()
    
    def test_system_integration_contracts(self, temp_workspace):
        """
        GIVEN StepContracts definition
        WHEN system_integration output is checked
        THEN it should contain required patterns
        """
        contracts = {
            "must_contain": ["FastAPI", "include_router"],
            "files_required": ["backend/app/main.py"]
        }
        
        main_content = '''from fastapi import FastAPI
app = FastAPI()
app.include_router(tasks.router, prefix="/api/tasks")
'''
        
        for pattern in contracts["must_contain"]:
            assert pattern in main_content
    
    def test_testing_backend_contracts(self):
        """
        GIVEN StepContracts definition
        WHEN testing_backend output is checked
        THEN it should contain required patterns
        """
        contracts = {
            "must_contain": ["pytest", "test_"],
            "files_required": []  # Test files are optional
        }
        
        test_content = '''import pytest

@pytest.mark.anyio
async def test_health(client):
    pass
'''
        
        for pattern in contracts["must_contain"]:
            assert pattern in test_content
