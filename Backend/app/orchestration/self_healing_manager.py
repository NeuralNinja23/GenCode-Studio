# app/orchestration/self_healing_manager.py
"""
Self-Healing Workflow Manager (DYNAMIC VERSION)

Self-healing layer that regenerates critical artifacts when:
- An LLM step produces broken code
- A contract validation fails
- A dependency barrier stops execution

CRITICAL: This manager is DYNAMIC - it reads actual entity names, 
function names, and router files from the workspace instead of 
hardcoding Note/notes.py/init_db.

Uses:
1. LLM regeneration with strict prompts (first attempt)
2. Template-based fallback (last resort)
"""
from pathlib import Path
from typing import Optional, Callable, Tuple, Dict


from app.core.logging import log
from app.orchestration.structural_compiler import StructuralCompiler
from app.orchestration.llm_output_integrity import LLMOutputIntegrity
from app.orchestration.fallback_router_agent import FallbackRouterAgent
from app.orchestration.fallback_api_agent import FallbackAPIAgent

# CENTRALIZED ENTITY DISCOVERY (replaces duplicated methods)
from app.utils.entity_discovery import (
    discover_primary_entity,
    discover_db_function,
    discover_routers,
    get_entity_plural,
)


class SelfHealingManager:
    """
    Self-healing layer that regenerates critical artifacts when:
    - An LLM step produces broken code
    - A contract validation fails
    - A dependency barrier stops execution
    
    DYNAMIC: Reads actual model/entity names from workspace files.
    """
    
    def __init__(
        self, 
        project_path: Path,
        llm_caller: Optional[Callable[[str], str]] = None,
    ):
        """
        Args:
            project_path: Path to the project workspace
            llm_caller: Optional function that takes a prompt and returns LLM response
        """
        self.project_path = project_path
        self.llm_caller = llm_caller

        self.compiler = StructuralCompiler()
        self.integrity = LLMOutputIntegrity()
        
        # Fallback agents (will be used with dynamic entity names)
        self.fallback_router = FallbackRouterAgent()
        self.fallback_api = FallbackAPIAgent()

    # ----------------------------------------------------------------
    # DYNAMIC DISCOVERY METHODS (now using centralized utility)
    # ----------------------------------------------------------------
    # NOTE: Removed duplicated _discover_primary_model, _discover_db_init_function,
    # and _discover_routers methods. Now using app.utils.entity_discovery instead.
    # This ensures consistent discovery logic across the entire codebase.
    
    def _get_entity(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Get the primary entity using centralized discovery.
        
        Returns:
            Tuple of (entity_name, model_name) e.g. ("product", "Product")
            Returns (None, None) if no entity found.
        """
        entity_name, model_name = discover_primary_entity(self.project_path)
        if not entity_name:
            log("HEAL", "⚠️ No entity found in project artifacts")
        return (entity_name, model_name)

    # ----------------------------------------------------------------
    # HIGH-LEVEL REPAIR ENTRY POINT
    # ----------------------------------------------------------------
    # ----------------------------------------------------------------
    # HIGH-LEVEL REPAIR ENTRY POINT
    # ----------------------------------------------------------------
    def repair(self, artifact_name: str, strategy_id: str = "generic", params: Dict = None) -> bool:
        """
        Attempt to repair a broken artifact with tailored strategy.
        
        Args:
            artifact_name: Name of artifact to repair
            strategy_id: Strategy identifier (e.g. 'syntax_fix')
            params: Synthesized behavior parameters (e.g. {'max_edits': 2})
            
        Returns:
            True if repair succeeded, False otherwise
        """
        params = params or {}
        log("HEAL", f"🔧 Repairing {artifact_name} with strategy '{strategy_id}'")
        
        # Example of using params:
        # strictness = params.get("priority", 0.5)
        # if strictness > 0.8: ...
        
        if artifact_name == "backend_router":
            return self._repair_backend_router()

        if artifact_name == "frontend_api":
            return self._repair_frontend_api()

        if artifact_name == "backend_main":
            return self._repair_backend_main()

        if artifact_name == "backend_db":
            return self._repair_backend_db()

        log("HEAL", f"⚠️ Unknown artifact: {artifact_name}")
        return False


    # ----------------------------------------------------------------
    # REPAIR BACKEND ROUTER (DYNAMIC)
    # ----------------------------------------------------------------
    def _repair_backend_router(self) -> bool:
        """Repair the backend router using LLM or fallback template."""
        
        # DYNAMIC: Discover actual model name using centralized utility
        entity_name, model_name = discover_primary_entity(self.project_path)
        if not entity_name:
            log("HEAL", "❌ Cannot repair router - no entity found!")
            return False
        entity_plural = get_entity_plural(entity_name)
        
        # Use entity-specific router path
        router_path = self.project_path / "backend" / "app" / "routers" / f"{entity_plural}.py"
        
        # Try LLM regeneration first (if caller available)
        if self.llm_caller:
            prompt = self._get_router_prompt(model_name, entity_name)
            try:
                text = self.llm_caller(prompt)
                
                if self.integrity.validate(text) and self.compiler.router_is_complete(text):
                    self._write_file(router_path, text)
                    log("HEAL", f"✅ Router regenerated via LLM for {model_name}")
                    return True
                else:
                    log("HEAL", "⚠️ LLM-generated router failed validation")
            except Exception as e:
                log("HEAL", f"⚠️ LLM call failed: {e}")

        # Fallback to DYNAMIC template
        log("HEAL", f"📋 Using fallback router template for {model_name}")
        template = self.fallback_router.generate_for_entity(entity_name, model_name)
        self._write_file(router_path, template)
        log("HEAL", f"✅ Fallback router written: {entity_plural}.py")
        return True

    # ----------------------------------------------------------------
    # REPAIR FRONTEND API CLIENT
    # ----------------------------------------------------------------
    def _repair_frontend_api(self) -> bool:
        """Repair the frontend API client using LLM or fallback template."""
        api_path = self.project_path / "frontend" / "src" / "lib" / "api.js"
        
        # DYNAMIC: Get entity name using centralized utility
        entity_name, model_name = discover_primary_entity(self.project_path)
        if not entity_name:
            log("HEAL", "❌ Cannot repair API client - no entity found!")
            return False
        entity_plural = get_entity_plural(entity_name)
        
        # Try LLM regeneration first
        if self.llm_caller:
            prompt = self._get_api_prompt(entity_name, entity_plural)
            try:
                text = self.llm_caller(prompt)
                
                if self.integrity.validate(text) and self.compiler.api_is_complete(text, entity_name=entity_name):
                    self._write_file(api_path, text)
                    log("HEAL", f"✅ API client regenerated via LLM for {entity_plural}")
                    return True
                else:
                    log("HEAL", "⚠️ LLM-generated API client failed validation")
            except Exception as e:
                log("HEAL", f"⚠️ LLM call failed: {e}")

        # Fallback to DYNAMIC template
        log("HEAL", f"📋 Using fallback API client template for {entity_plural}")
        template = self.fallback_api.generate_for_entity(entity_name, entity_plural)
        self._write_file(api_path, template)
        log("HEAL", "✅ Fallback API client written")
        return True

    # ----------------------------------------------------------------
    # REPAIR BACKEND MAIN (DYNAMIC)
    # ----------------------------------------------------------------
    def _repair_backend_main(self) -> bool:
        """Repair backend main.py - reads actual routers and db function."""
        main_path = self.project_path / "backend" / "app" / "main.py"
        
        # DYNAMIC: Generate template based on actual workspace contents
        template = self._get_main_template()
        self._write_file(main_path, template)
        log("HEAL", "✅ Backend main.py written from DYNAMIC template")
        return True

    # ----------------------------------------------------------------
    # REPAIR BACKEND DB (Test Wrapper)
    # ----------------------------------------------------------------
    def _repair_backend_db(self) -> bool:
        """
        Repair backend/app/db.py - optional wrapper for legacy compatibility.
        
        NOTE: The standardized pattern now uses app.database directly:
        - conftest.py imports: from app.database import init_db, close_db
        - This wrapper is for legacy support only.
        """
        db_path = self.project_path / "backend" / "app" / "db.py"
        
        # DYNAMIC: Discover actual db init function using centralized utility
        db_init_func = discover_db_function(self.project_path)
        
        template = f'''# backend/app/db.py
"""
Database connection wrapper (legacy compatibility).

PREFERRED: Import directly from app.database:
  from app.database import init_db, close_db

This file exists for backwards compatibility only.
"""
from app.database import {db_init_func}


async def connect_db():
    """Connect to database (wrapper for {db_init_func})."""
    await {db_init_func}()


async def disconnect_db():
    """Disconnect from database."""
    pass  # Motor handles connection cleanup automatically


# Re-export for compatibility
__all__ = ["connect_db", "disconnect_db"]
'''
        
        self._write_file(db_path, template)
        log("HEAL", "✅ Backend db.py written (legacy wrapper)")
        return True

    # ----------------------------------------------------------------
    # PROMPTS FOR LLM REGENERATION (DYNAMIC)
    # ----------------------------------------------------------------
    def _get_router_prompt(self, model_name: str, entity_name: str) -> str:
        """Generate a dynamic router prompt based on actual entity."""
        entity_plural = entity_name + "s" if not entity_name.endswith("s") else entity_name
        
        return f"""Generate a complete FastAPI router named {entity_plural}.py with CRUD operations.

ENTITY: {model_name} (plural: {entity_plural})

REQUIRED async def functions:
- create (POST /)
- get_all (GET /)
- get_one (GET /{{id}})
- update (PUT /{{id}})
- delete (DELETE /{{id}})

REQUIREMENTS:
- Use Beanie ODM models
- Use PydanticObjectId for IDs (from beanie import PydanticObjectId)
- Import {model_name} from app.models
- Use APIRouter with prefix="/api/{entity_plural}" and tags=["{entity_plural}"]
- Return JSON response format
- Include proper error handling with HTTPException

Do NOT truncate output. Generate the COMPLETE file."""

    def _get_api_prompt(self, entity_name: str, entity_plural: str) -> str:
        """Generate a dynamic API client prompt based on actual entity."""
        entity_cap = entity_name.capitalize()
        
        return f"""Generate a JavaScript API client for {entity_plural}.

ENTITY: {entity_cap} (plural: {entity_plural})

REQUIRED exported async functions:
- get{entity_cap}s(skip, limit)
- get{entity_cap}ById(id)
- create{entity_cap}(data)
- update{entity_cap}(id, data)
- delete{entity_cap}(id)

REQUIREMENTS:
- Base URL should use import.meta.env.VITE_API_URL || "http://localhost:8001/api"
- API endpoint: /api/{entity_plural}
- Include proper error handling
- Use fetch() API
- Return parsed JSON responses

Do NOT truncate output. Generate the COMPLETE file."""

    def _get_main_template(self) -> str:
        """
        Generate a DYNAMIC main.py template based on actual workspace contents.
        
        Discovers:
        - Actual database init function name from database.py
        - Actual router files from routers/ directory
        """
        # DYNAMIC: Discover actual db function name using centralized utility
        db_init_func = discover_db_function(self.project_path)
        
        # DYNAMIC: Discover actual routers using centralized utility
        routers = discover_routers(self.project_path)
        
        # Build router imports
        if routers:
            router_imports = "\n".join([
                f"from app.routers.{name} import router as {name}_router"
                for name, _ in routers
            ])
            router_includes = "\n".join([
                f"app.include_router({name}_router, prefix=\"/api/{name}\", tags=[\"{name}\"])"
                for name, _ in routers
            ])
        else:
            # Fallback: discover primary model and create router reference
            entity_name, model_name = discover_primary_entity(self.project_path)
            if entity_name:
                entity_plural = get_entity_plural(entity_name)
                router_imports = f"from app.routers.{entity_plural} import router as {entity_plural}_router"
                router_includes = f"app.include_router({entity_plural}_router, prefix=\"/api/{entity_plural}\", tags=[\"{entity_plural}\"])"
            else:
                router_imports = "# No routers found"
                router_includes = "# No routers to include"
        
        # Get primary entity for API title using centralized utility
        entity_name, model_name = discover_primary_entity(self.project_path)
        api_title = f"{model_name}s API" if model_name else "GenCode API"
        
        return f'''# backend/app/main.py
"""
FastAPI Main Application - Auto-generated by Self-Healing Manager (DYNAMIC)
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import {db_init_func}
{router_imports}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    await {db_init_func}()
    yield


app = FastAPI(
    title="{api_title}",
    description="A {entity_name} management API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
{router_includes}


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {{"status": "healthy"}}
'''

    # ----------------------------------------------------------------
    # FILE UTILITIES
    # ----------------------------------------------------------------
    def _write_file(self, path: Path, content: str):
        """Write content to file, creating directories as needed."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def _read_file(self, path: Path) -> Optional[str]:
        """Read file content, return None if not found."""
        if path.exists():
            return path.read_text(encoding="utf-8")
        return None

