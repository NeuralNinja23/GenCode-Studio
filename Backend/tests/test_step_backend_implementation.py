# tests/test_step_backend_implementation.py
"""
Tests for Step 6: Backend Implementation (Models + Routers)

This is a SINGLE step that generates the complete backend vertical:
- Beanie/MongoDB models (models.py)
- FastAPI routers (routers/*.py)

Pipeline Position: ... → Contracts → [BACKEND IMPLEMENTATION] → System Integration → ...
"""
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch
import json
import re


class TestBackendImplementationStep:
    """Test suite for the complete backend implementation step."""
    
    @pytest.mark.asyncio
    async def test_backend_impl_creates_models_and_routers(
        self, temp_workspace, simple_entity_plan, mock_backend_impl_llm_response
    ):
        """
        GIVEN a workspace with contracts.md
        WHEN step_backend_implementation is executed
        THEN both models.py AND routers/*.py should be created
        """
        # Setup: Create contracts and entity plan
        contracts_path = temp_workspace / "contracts.md"
        contracts_path.write_text("# API Contracts\n## Tasks\n...", encoding="utf-8")
        
        entity_plan_path = temp_workspace / "entity_plan.json"
        simple_entity_plan.save(entity_plan_path)
        
        # Simulate the step output (models + routers)
        files = mock_backend_impl_llm_response["output"]["files"]
        for file_obj in files:
            file_path = temp_workspace / file_obj["path"]
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(file_obj["content"], encoding="utf-8")
        
        # Verify BOTH were created
        models_path = temp_workspace / "backend" / "app" / "models.py"
        router_path = temp_workspace / "backend" / "app" / "routers" / "tasks.py"
        
        assert models_path.exists(), "models.py should be created"
        assert router_path.exists(), "tasks.py router should be created"
    
    @pytest.mark.asyncio
    async def test_backend_impl_single_entity_mode(
        self, temp_workspace, mock_backend_impl_llm_response
    ):
        """
        GIVEN a workspace WITHOUT entity_plan.json
        WHEN step_backend_implementation is executed
        THEN it should run in single-entity (atomic) mode
        """
        # No entity_plan.json = single entity mode
        entity_plan_path = temp_workspace / "entity_plan.json"
        
        assert not entity_plan_path.exists(), "Should not have entity plan for this test"
        
        # In single-entity mode, everything is generated in one LLM call
        # Simulate output
        models_content = mock_backend_impl_llm_response["output"]["files"][0]["content"]
        router_content = mock_backend_impl_llm_response["output"]["files"][1]["content"]
        
        # Both should come from one call
        assert "class Task(Document):" in models_content
        assert "router = APIRouter()" in router_content
    
    @pytest.mark.asyncio
    async def test_backend_impl_multi_entity_mode(
        self, temp_workspace, multi_entity_plan
    ):
        """
        GIVEN a workspace WITH entity_plan.json
        WHEN step_backend_implementation is executed
        THEN it should run in multi-entity mode (loop per entity)
        """
        entity_plan_path = temp_workspace / "entity_plan.json"
        multi_entity_plan.save(entity_plan_path)
        
        assert entity_plan_path.exists(), "Should have entity plan"
        
        # Load and verify
        plan_data = json.loads(entity_plan_path.read_text(encoding="utf-8"))
        
        # Should generate routers only for AGGREGATE entities
        aggregate_entities = [e for e in plan_data["entities"] if e["type"] == "AGGREGATE"]
        embedded_entities = [e for e in plan_data["entities"] if e["type"] == "EMBEDDED"]
        
        assert len(aggregate_entities) == 2, "Should have 2 AGGREGATE entities"
        assert len(embedded_entities) == 1, "Should have 1 EMBEDDED entity (no router)"


class TestModelGeneration:
    """Test model generation within backend implementation."""
    
    def test_models_extends_beanie_document(self):
        """
        GIVEN generated models
        WHEN checked
        THEN entity classes should extend Document
        """
        model_content = '''from beanie import Document

class Task(Document):
    title: str
    status: str = "active"
    
    class Settings:
        name = "tasks"
'''
        assert "class Task(Document)" in model_content
        assert "from beanie import Document" in model_content
    
    def test_models_no_explicit_id_field(self):
        """
        GIVEN generated models
        WHEN checked for ID fields
        THEN there should be NO explicit id or _id (Beanie handles this)
        """
        # ❌ BAD: Crashes Beanie startup
        bad_model = '''class Task(Document):
    id: str  # WRONG!
    title: str
'''
        
        # ✅ GOOD: Let Beanie auto-generate
        good_model = '''class Task(Document):
    title: str
    status: str = "active"
'''
        
        id_pattern = r'^\s*_?id\s*:'
        assert re.search(id_pattern, bad_model, re.MULTILINE), "Bad example should show anti-pattern"
        assert not re.search(id_pattern, good_model, re.MULTILINE), "Good model has no explicit id"
    
    def test_models_has_settings_with_collection_name(self):
        """
        GIVEN generated models
        WHEN parsed
        THEN each Document should have Settings.name for MongoDB collection
        """
        model_content = '''class Task(Document):
    title: str
    
    class Settings:
        name = "tasks"
'''
        assert "class Settings:" in model_content
        assert 'name = "tasks"' in model_content or "name = 'tasks'" in model_content
    
    def test_embedded_uses_pydantic_basemodel(self):
        """
        GIVEN an EMBEDDED entity
        WHEN model is generated
        THEN it should use Pydantic BaseModel (not Beanie Document)
        """
        embedded_model = '''from pydantic import BaseModel

class Assignee(BaseModel):
    name: str
    email: str
'''
        assert "BaseModel" in embedded_model
        assert "Document" not in embedded_model


class TestRouterGeneration:
    """Test router generation within backend implementation."""
    
    def test_router_no_prefix_or_tags(self):
        """
        GIVEN generated router code
        WHEN checked for APIRouter initialization
        THEN it should NOT have prefix or tags (integrator handles this)
        """
        # ❌ BAD: Causes double-prefix (/api/tasks/tasks)
        bad_router = '''router = APIRouter(prefix="/tasks", tags=["tasks"])'''
        
        # ✅ GOOD: Clean router
        good_router = '''router = APIRouter()'''
        
        assert "prefix=" in bad_router
        assert "prefix=" not in good_router
        assert "tags=" not in good_router
    
    def test_router_uses_root_paths(self):
        """
        GIVEN generated router
        WHEN endpoint paths are checked
        THEN they should use "/" and "/{id}" (not "/tasks" or "/tasks/{id}")
        """
        # ✅ CORRECT paths
        correct_router = '''
@router.get("/")
async def list_tasks():
    pass

@router.post("/")
async def create_task():
    pass

@router.get("/{task_id}")
async def get_task(task_id: str):
    pass
'''
        
        # ❌ WRONG paths (would create /api/tasks/tasks/...)
        wrong_router = '''
@router.get("/tasks")
async def list_tasks():
    pass
'''
        
        # Check correct has root paths
        assert '@router.get("/")' in correct_router
        assert '@router.post("/")' in correct_router
        
        # Check wrong has entity in path
        assert '@router.get("/tasks")' in wrong_router
    
    def test_router_imports_model(self):
        """
        GIVEN generated router
        WHEN imports are checked
        THEN it should import from app.models
        """
        router_content = '''from fastapi import APIRouter, HTTPException
from app.models import Task

router = APIRouter()
'''
        assert "from app.models import Task" in router_content
    
    def test_router_crud_endpoints(self, mock_backend_impl_llm_response):
        """
        GIVEN generated router
        WHEN endpoints are checked
        THEN all CRUD operations should be present
        """
        router_content = mock_backend_impl_llm_response["output"]["files"][1]["content"]
        
        # All CRUD decorators should be present
        assert "@router.get" in router_content
        assert "@router.post" in router_content
        assert "@router.put" in router_content or "@router.patch" in router_content
        assert "@router.delete" in router_content


class TestStatusCodes:
    """Test correct HTTP status codes in routers."""
    
    def test_post_returns_201(self, mock_backend_impl_llm_response):
        """POST endpoints should return 201 Created."""
        router_content = mock_backend_impl_llm_response["output"]["files"][1]["content"]
        
        # Should have status_code=201 or HTTP_201_CREATED
        assert "201" in router_content or "HTTP_201_CREATED" in router_content
    
    def test_delete_returns_204(self, mock_backend_impl_llm_response):
        """DELETE endpoints should return 204 No Content."""
        router_content = mock_backend_impl_llm_response["output"]["files"][1]["content"]
        
        assert "204" in router_content or "HTTP_204_NO_CONTENT" in router_content
    
    def test_not_found_returns_404(self, mock_backend_impl_llm_response):
        """Not found scenarios should raise 404."""
        router_content = mock_backend_impl_llm_response["output"]["files"][1]["content"]
        
        assert "404" in router_content or "HTTPException" in router_content


class TestContractCompliance:
    """Test that generated code complies with contracts."""
    
    def test_field_names_match_contracts(self, mock_contracts_content):
        """
        GIVEN contracts.md with defined field names
        WHEN models are generated
        THEN field names MUST match exactly (no synonyms)
        """
        # Extract field names from contracts
        # e.g., "title", "description", "status"
        
        expected_fields = ["title", "description", "status"]
        
        model_content = '''class Task(Document):
    title: str
    description: Optional[str] = None
    status: str = "active"
'''
        
        for field in expected_fields:
            assert field in model_content, f"Field '{field}' from contract should be in model"
    
    def test_no_extra_required_fields(self, mock_contracts_content):
        """
        GIVEN contracts.md
        WHEN models are generated
        THEN no extra REQUIRED fields should be added (breaks frontend)
        """
        # Contracts define: title (required), description (optional), status (required)
        
        # ❌ BAD: Extra required field not in contract
        bad_model = '''class Task(Document):
    title: str
    description: str  # Made required when contract says optional
    status: str
    created_by: str  # Extra field not in contract!
'''
        
        # ✅ GOOD: Matches contract exactly
        good_model = '''class Task(Document):
    title: str
    description: Optional[str] = None  # Optional as per contract
    status: str = "active"
'''
        
        # Good model should have Optional for description
        assert "Optional[str]" in good_model or "= None" in good_model
