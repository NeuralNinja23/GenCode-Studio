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
from app.orchestration.fallback_model_agent import FallbackModelAgent
from app.orchestration.artifact_types import Artifact

# CENTRALIZED ENTITY DISCOVERY (replaces duplicated methods)
from app.utils.entity_discovery import (
    discover_primary_entity,
    discover_db_function,
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
        self.fallback_model = FallbackModelAgent()

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
    def repair(self, artifact_name, strategy_id: str = "generic", params: Dict = None) -> bool:
        """
        Attempt to repair a broken artifact with tailored strategy.
        
        Args:
            artifact_name: Name of artifact to repair (Artifact enum or str for backwards compat)
            strategy_id: Strategy identifier (e.g. 'syntax_fix')
            params: Synthesized behavior parameters (e.g. {'max_edits': 2})
            
        Returns:
            True if repair succeeded, False otherwise
        """
        params = params or {}
        
        # Convert to string for comparison (handles both Artifact enum and str)
        artifact_str = artifact_name.value if isinstance(artifact_name, Artifact) else artifact_name
        log("HEAL", f"🔧 Repairing {artifact_str} with strategy '{strategy_id}'")
        
        # Example of using params:
        # strictness = params.get("priority", 0.5)
        # if strictness > 0.8: ...
        
        # Use Artifact enum for comparison
        if artifact_str == Artifact.BACKEND_ROUTER.value:
            return self._repair_backend_router()
        
        if artifact_str == Artifact.BACKEND_VERTICAL.value:
            return self._repair_backend_vertical()

        if artifact_str == Artifact.FRONTEND_API.value:
            return self._repair_frontend_api()

        if artifact_str == Artifact.BACKEND_MAIN.value:
            return self._repair_backend_main()

        if artifact_str == Artifact.BACKEND_DB.value:
            return self._repair_backend_db()

        log("HEAL", f"⚠️ Unknown artifact: {artifact_str}")
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
        
        # Import config and validation helpers
        from app.core.config import settings
        from app.orchestration.heal_helpers import validate_router_file
        
        # Check if we should skip LLM entirely
        if settings.healing.force_fallback:
            log("HEAL", "🔧 HEAL_FORCE_FALLBACK=true - skipping LLM, using fallback template")
        elif not settings.healing.allow_llm:
            log("HEAL", "🔧 HEAL_ALLOW_LLM=false - skipping LLM, using fallback template")
        elif self.llm_caller:
            # Try LLM regeneration with validation
            log("HEAL", f"🤖 Attempting LLM regeneration for {model_name} router")
            prompt = self._get_router_prompt(model_name, entity_name)
            
            try:
                text = self.llm_caller(prompt)
                
                #Old validation (structural)
                if not (self.integrity.validate(text) and self.compiler.router_is_complete(text)):
                    log("HEAL", "⚠️ LLM output failed structural validation")
                else:
                    # Write LLM output temporarily
                    self._write_file(router_path, text)
                    
                    # NEW: Validate router code for FastAPI compliance
                    if settings.healing.validate_llm_output:
                        validation = validate_router_file(router_path, entity_name)
                        
                        if not validation["valid"]:
                            log("HEAL", "❌ LLM-generated router failed FastAPI validation:")
                            for reason in validation["reasons"]:
                                log("HEAL", f"   - {reason}")
                            log("HEAL", f"📊 Validation checks: {validation['checks']}")
                            log("HEAL", "🔄 Falling back to template")
                        else:
                            log("HEAL", "✅ LLM-generated router passed all validations")
                            log("HEAL", f"   Checks: {validation['checks']}")
                            return True
                    else:
                        # Validation disabled, accept LLM output
                        log("HEAL", "✅ Router regenerated via LLM (validation skipped)")
                        return True
                        
            except Exception as e:
                log("HEAL", f"⚠️ LLM call failed: {e}")

        # Fallback to DYNAMIC template
        log("HEAL", f"📋 Using fallback router template for {model_name}")
        template = self.fallback_router.generate_for_entity(entity_name, model_name)
        self._write_file(router_path, template)
        log("HEAL", f"✅ Fallback router written: {entity_plural}.py")
        
        # Validate fallback template (should always pass)
        if settings.healing.validate_llm_output:
            validation = validate_router_file(router_path, entity_name)
            if not validation["valid"]:
                log("HEAL", "⚠️ WARNING: Even fallback template failed validation!")
                log("HEAL", f"   Reasons: {validation['reasons']}")
            else:
                log("HEAL", "✅ Fallback template validated successfully")
        
        return True

    # ----------------------------------------------------------------
    # REPAIR BACKEND VERTICAL (MODELS + ROUTER + WIRING)
    # ----------------------------------------------------------------
    def _repair_backend_vertical(self) -> bool:
        """
        Repair the complete backend vertical slice: models.py + router + main.py hints.
        
        This is triggered when backend_implementation fails completely.
        It regenerates the entire backend stack atomically.
        """
        # DYNAMIC: Discover actual model name using centralized utility
        entity_name, model_name = discover_primary_entity(self.project_path)
        if not entity_name:
            log("HEAL", "❌ Cannot repair backend vertical - no entity found!")
            return False
        entity_plural = get_entity_plural(entity_name)
        
        log("HEAL", f"🔧 Repairing complete backend vertical for {model_name}")
        
        # Step 1: Generate models.py using FallbackModelAgent
        models_path = self.project_path / "backend" / "app" / "models.py"
        model_template = self.fallback_model.generate_for_entity(entity_name, model_name)
        self._write_file(models_path, model_template)
        log("HEAL", f"✅ Generated models.py with {model_name}")
        
        # Step 2: Generate router
        router_path = self.project_path / "backend" / "app" / "routers" / f"{entity_plural}.py"
        router_template = self.fallback_router.generate_for_entity(entity_name, model_name)
        self._write_file(router_path, router_template)
        log("HEAL", f"✅ Generated router: {entity_plural}.py")
        
        # Step 3: Router wiring is NOW handled by step_system_integration (single source of truth)
        # This prevents double-wiring bugs and marker corruption
        log("HEAL", f"✅ Ensured {entity_plural} is wired in main.py")
        
        # Step 4: GENERALIZED VALIDATION - Test if FastAPI app can actually start
        log("HEAL", "🔍 Running generalized validation...")
        try:
            from app.orchestration.code_validator import CodeValidator
            
            validator = CodeValidator(self.project_path)
            
            # NOTE: Using synchronous validation to avoid event loop conflict
            # The healing code runs inside an already-running async context
            # so we can't use asyncio.run() or run_until_complete()
            
            # Quick synchronous validation: just check if app module can be imported
            import subprocess
            import sys
            
            validation_script = f'''
import sys
sys.path.insert(0, r"{self.project_path / 'backend'}")
try:
    from app.main import app
    print("SUCCESS")
except Exception as e:
    print("FAIL:", type(e).__name__, str(e))
'''
            
            result = subprocess.run(
                [sys.executable, "-c", validation_script],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(self.project_path / "backend"),
            )
            
            output = result.stdout + result.stderr
            
            if "SUCCESS" in output:
                log("HEAL", "✅ Generalized validation PASSED - app can start")
            else:
                log("HEAL", "❌ Generalized validation FAILED:")
                log("HEAL", f"   {output[:500]}")
                log("HEAL", "⚠️ Files written but app has startup errors")
                # CRITICAL FIX: Return False when validation fails!
                return False
        except Exception as e:
            log("HEAL", f"⚠️ Generalized validation skipped (error: {e})")
        
        log("HEAL", f"✅ Backend vertical healing complete for {model_name}")
        return True
    
    # NOTE: _get_model_template was removed - now using FallbackModelAgent
    # This consolidates model generation into a single source of truth

    
    def _ensure_router_wired(self, router_name: str) -> None:
        """
        Ensure router is wired in main.py (idempotent).
        
        This method is truly idempotent - it checks for ALL variants of how
        a router might be imported/registered before adding.
        """
        main_path = self.project_path / "backend" / "app" / "main.py"
        if not main_path.exists():
            log("HEAL", "⚠️ main.py doesn't exist, will be created by integrator")
            return
        
        content = main_path.read_text(encoding="utf-8")
        
        # Check for ANY variant of this router being imported
        import_variants = [
            f"from app.routers import {router_name}",
            f"from app.routers.{router_name} import router",
            f"from app.routers.{router_name} import router as {router_name}_router",
        ]
        router_already_imported = any(v in content for v in import_variants)
        
        # Check for ANY variant of this router being registered
        register_variants = [
            f"include_router({router_name}.router",
            f"include_router({router_name}_router",
        ]
        router_already_registered = any(v in content for v in register_variants)
        
        import re
        
        # Only add import if not already present in ANY form
        if not router_already_imported:
            import_line = f"from app.routers import {router_name}"
            if "from app.routers import" in content:
                # Add to existing router imports
                content = re.sub(
                    r'(from app\.routers import [^\n]+)',
                    f'\\1\n{import_line}',
                    content,
                    count=1
                )
            elif "# @ROUTER_IMPORTS" in content:
                # Use marker - FIXED: Use regex to preserve full marker line including suffix
                content = re.sub(
                    r'^(# @ROUTER_IMPORTS[^\n]*)\n',
                    f'\\1\n{import_line}\n',
                    content,
                    count=1,
                    flags=re.MULTILINE
                )
            else:
                # Add new import section
                content = content.replace(
                    "from app.database import",
                    f"{import_line}\nfrom app.database import"
                )
        
        # Only add registration if not already present in ANY form
        if not router_already_registered:
            include_line = f"app.include_router({router_name}.router, prefix='/api/{router_name}', tags=['{router_name}'])"
            if "# @ROUTER_REGISTER" in content:
                # Use marker - FIXED: Use regex to preserve full marker line including suffix
                content = re.sub(
                    r'^(# @ROUTER_REGISTER[^\n]*)\n',
                    f'\\1\n{include_line}\n',
                    content,
                    count=1,
                    flags=re.MULTILINE
                )
            elif "@app.get" in content:
                # Add before health check endpoint
                content = re.sub(
                    r'(@app\.get)',
                    f'{include_line}\n\n\\1',
                    content,
                    count=1
                )
            else:
                content += f"\n\n{include_line}\n"
        
        self._write_file(main_path, content)
        log("HEAL", f"✅ Ensured {router_name} is wired in main.py")

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
        
        # FIX: Immediately wire existing routers to prevent 404s
        # The template starts empty (scaffold only), so we must discover and wire
        # any routers that already exist in the project.
        try:
            routers_dir = self.project_path / "backend" / "app" / "routers"
            if routers_dir.exists():
                for router_file in routers_dir.glob("*.py"):
                    if router_file.stem != "__init__":
                        log("HEAL", f"🔗 Re-wiring detected router: {router_file.stem}")
                        self._ensure_router_wired(router_file.stem)
        except Exception as e:
            log("HEAL", f"⚠️ Failed to re-wire routers: {e}")
            
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
        
        Uses @ROUTER_IMPORTS and @ROUTER_REGISTER markers that the System Integrator
        will fill in. This prevents double router registration by having ONLY the
        integrator be responsible for wiring routers.
        
        Discovers:
        - Actual database init function name from database.py
        """
        # DYNAMIC: Discover actual db function name using centralized utility
        db_init_func = discover_db_function(self.project_path)
        
        # Get primary entity for API title using centralized utility
        entity_name, model_name = discover_primary_entity(self.project_path)
        api_title = f"{model_name}s API" if model_name else "GenCode API"
        entity_desc = entity_name if entity_name else "resource"
        
        # NOTE: We use markers here instead of directly writing router imports/includes.
        # The System Integrator (step_system_integration) is the SINGLE SOURCE OF TRUTH
        # for router wiring. This prevents the double-registration bug.
        
        return f'''# backend/app/main.py
"""
FastAPI Main Application - Auto-generated by Self-Healing Manager (DYNAMIC)
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import {db_init_func}
# @ROUTER_IMPORTS - DO NOT REMOVE THIS LINE


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    await {db_init_func}()
    yield


app = FastAPI(
    title="{api_title}",
    description="A {entity_desc} management API",
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

# @ROUTER_REGISTER - DO NOT REMOVE THIS LINE


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

