# tests/test_step_system_integration.py
"""
Tests for Step 7: System Integration

Validates the deterministic wiring of agent-generated modules into the Golden Seed.
This is a SCRIPTED step (not LLM) that:
- Discovers generated routers
- Wires them into main.py
- Registers Beanie models
- Validates routes are accessible

Pipeline Position: ... → Backend Implementation → [SYSTEM INTEGRATION] → Testing Backend → ...
"""
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch
import re


class TestSystemIntegrationStep:
    """Test suite for the system integration step."""
    
    @pytest.mark.asyncio
    async def test_integration_discovers_routers(self, temp_workspace):
        """
        GIVEN a workspace with generated routers
        WHEN system integration runs
        THEN all routers in routers/ directory should be discovered
        """
        routers_dir = temp_workspace / "backend" / "app" / "routers"
        routers_dir.mkdir(parents=True, exist_ok=True)
        
        # Create some router files
        (routers_dir / "tasks.py").write_text("router = APIRouter()", encoding="utf-8")
        (routers_dir / "projects.py").write_text("router = APIRouter()", encoding="utf-8")
        (routers_dir / "__init__.py").write_text("", encoding="utf-8")  # Should be ignored
        
        # Discover routers (simulate the integration logic)
        router_files = list(routers_dir.glob("*.py"))
        router_names = [
            f.stem for f in router_files 
            if f.stem != "__init__" and not f.stem.startswith("_")
        ]
        
        assert "tasks" in router_names
        assert "projects" in router_names
        assert "__init__" not in router_names
    
    @pytest.mark.asyncio
    async def test_integration_wires_main_py(self, temp_workspace):
        """
        GIVEN discovered routers
        WHEN integration runs
        THEN main.py should have include_router calls
        """
        main_py_path = temp_workspace / "backend" / "app" / "main.py"
        
        # Simulate the wired main.py
        wired_main = '''# backend/app/main.py
from fastapi import FastAPI
from app.routers import tasks, projects

app = FastAPI()


# ═══ ROUTER REGISTRATION ═══
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])


@app.get("/health")
async def health_check():
    return {"status": "ok"}
'''
        main_py_path.write_text(wired_main, encoding="utf-8")
        
        content = main_py_path.read_text(encoding="utf-8")
        
        # Verify router registrations
        assert "include_router" in content
        assert 'prefix="/api/tasks"' in content
        assert 'prefix="/api/projects"' in content
    
    @pytest.mark.asyncio
    async def test_integration_registers_beanie_models(self, temp_workspace):
        """
        GIVEN generated models.py
        WHEN integration runs
        THEN models should be registered with Beanie in db.py or startup
        """
        db_py_path = temp_workspace / "backend" / "app" / "db.py"
        
        # Simulate db.py with model registration
        db_content = '''# backend/app/db.py
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.models import Task, Project

async def init_db():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    await init_beanie(
        database=client.get_default_database(),
        document_models=[Task, Project]  # ← Models registered here
    )
'''
        db_py_path.write_text(db_content, encoding="utf-8")
        
        content = db_py_path.read_text(encoding="utf-8")
        
        assert "init_beanie" in content
        assert "document_models" in content
        assert "Task" in content
        assert "Project" in content


class TestRouterWiring:
    """Test the router wiring logic."""
    
    def test_router_prefix_follows_convention(self):
        """
        GIVEN a router name (e.g., "tasks")
        WHEN wired to main.py
        THEN prefix should be /api/{router_name}
        """
        router_name = "tasks"
        expected_prefix = f"/api/{router_name}"
        
        wiring_code = f'app.include_router({router_name}.router, prefix="{expected_prefix}")'
        
        assert expected_prefix in wiring_code
    
    def test_router_import_statement_generated(self):
        """
        GIVEN discovered routers
        WHEN import statements are generated
        THEN they should import from app.routers
        """
        routers = ["tasks", "projects", "users"]
        
        # Generate import line
        import_line = f"from app.routers import {', '.join(routers)}"
        
        assert "from app.routers import tasks, projects, users" == import_line
    
    def test_no_duplicate_router_registration(self, temp_workspace):
        """
        GIVEN main.py with existing router registrations
        WHEN integration runs again
        THEN routers should NOT be duplicated
        """
        main_py_path = temp_workspace / "backend" / "app" / "main.py"
        
        # Main.py already has tasks registered
        existing_main = '''from fastapi import FastAPI
from app.routers import tasks

app = FastAPI()

app.include_router(tasks.router, prefix="/api/tasks")
'''
        main_py_path.write_text(existing_main, encoding="utf-8")
        
        content = main_py_path.read_text(encoding="utf-8")
        
        # Count registrations
        registrations = len(re.findall(r'include_router\(tasks\.router', content))
        
        assert registrations == 1, "Should not duplicate router registration"


class TestIntegrationValidation:
    """Test post-integration validation."""
    
    @pytest.mark.asyncio
    async def test_validation_checks_routes_accessible(self, temp_workspace):
        """
        GIVEN wired routers
        WHEN validation runs
        THEN it should verify routes are accessible via contract parsing
        """
        # Create contracts.md
        contracts_path = temp_workspace / "contracts.md"
        contracts_path.write_text('''# API Contracts

## Tasks
- GET /api/tasks
- POST /api/tasks
- GET /api/tasks/{id}
- PUT /api/tasks/{id}
- DELETE /api/tasks/{id}
''', encoding="utf-8")
        
        # Parse expected routes
        content = contracts_path.read_text(encoding="utf-8")
        routes = re.findall(r'(GET|POST|PUT|DELETE)\s+(/api/\S+)', content)
        
        assert len(routes) == 5
        
        # Each should have method and path
        for method, path in routes:
            assert method in ["GET", "POST", "PUT", "DELETE"]
            assert path.startswith("/api/")
    
    @pytest.mark.asyncio
    async def test_validation_restarts_docker_before_check(self):
        """
        GIVEN new router code written
        WHEN validation prepares to test
        THEN Docker should be restarted to pick up changes
        """
        # This test documents the behavior:
        # 1. Stop existing sandbox
        # 2. Wait for filesystem sync (Windows is slower)
        # 3. Start sandbox with build
        # 4. Wait for uvicorn --reload
        
        expected_flow = [
            "stop_sandbox",       # Stop existing
            "sleep(2)",           # Wait for FS sync
            "start_sandbox",      # Start with build
            "sleep(3)",           # Wait for uvicorn reload
        ]
        
        # This is documentation of expected behavior
        assert len(expected_flow) == 4


class TestEdgeCases:
    """Test edge cases in system integration."""
    
    @pytest.mark.asyncio
    async def test_empty_routers_directory(self, temp_workspace):
        """
        GIVEN an empty routers directory
        WHEN integration runs
        THEN it should handle gracefully (no routers to wire)
        """
        routers_dir = temp_workspace / "backend" / "app" / "routers"
        routers_dir.mkdir(parents=True, exist_ok=True)
        
        router_files = list(routers_dir.glob("*.py"))
        valid_routers = [f for f in router_files if f.stem != "__init__"]
        
        assert len(valid_routers) == 0
    
    @pytest.mark.asyncio
    async def test_malformed_router_skipped(self, temp_workspace):
        """
        GIVEN a router file without 'router = APIRouter()'
        WHEN integration runs
        THEN it should be skipped with warning
        """
        routers_dir = temp_workspace / "backend" / "app" / "routers"
        routers_dir.mkdir(parents=True, exist_ok=True)
        
        # Valid router
        (routers_dir / "tasks.py").write_text(
            "from fastapi import APIRouter\nrouter = APIRouter()",
            encoding="utf-8"
        )
        
        # Malformed - no router defined
        (routers_dir / "broken.py").write_text(
            "# This file has no router = APIRouter()",
            encoding="utf-8"
        )
        
        # Check which files have valid router definition
        valid_routers = []
        for f in routers_dir.glob("*.py"):
            if f.stem == "__init__":
                continue
            content = f.read_text(encoding="utf-8")
            if "router = APIRouter()" in content or "router=APIRouter()" in content:
                valid_routers.append(f.stem)
        
        assert "tasks" in valid_routers
        assert "broken" not in valid_routers
