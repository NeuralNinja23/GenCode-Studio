# app/handlers/system_integration.py
"""
Step 5: System Integration (Script).

Deterministic wiring of agent-generated modules (models and routers) into the Golden Seed.
This ensures that the FastAPI application correctly includes all routers and initializes Beanie with all models.
"""
from pathlib import Path
from app.core.types import StepResult
from app.core.constants import WorkflowStep
from app.handlers.base import broadcast_status
from app.core.logging import log
from app.core.failure_boundary import FailureBoundary

@FailureBoundary.enforce
async def step_system_integration(branch) -> StepResult:
    """
    Step 5: System Integration (Pure Python).
    
    Deterministic wiring of ALL generated modules:
    - Backend: Wire routers and models into main.py
    - Frontend: Generate API helpers and replace mock→API
    - Cross-system: Ensure consistent configuration
    """
    from app.arbormind.cognition.branch import Branch
    assert isinstance(branch, Branch)
    
    # Extract context from branch
    project_id = branch.intent["project_id"]
    manager = branch.intent["manager"]
    project_path = branch.intent["project_path"]
    
    await broadcast_status(
        manager, project_id, WorkflowStep.SYSTEM_INTEGRATION,
        f"System Integrator wiring backend + frontend...",
        5, 9
    )
    
    # ═══════════════════════════════════════════════════════════════════
    # BACKEND INTEGRATION (existing logic)
    # ═══════════════════════════════════════════════════════════════════
    
    # Detect routers
    routers_dir = project_path / "backend/app/routers"
    existing_routers = []
    if routers_dir.exists():
        existing_routers = [f.stem.lower() for f in routers_dir.glob("*.py") if f.stem != "__init__"]
        
    log("INTEGRATION", f"🔗 Found {len(existing_routers)} backend routers to wire")
    
    main_py_path = project_path / "backend/app/main.py"
    if main_py_path.exists() and existing_routers:
        # Architecture Bundle: Check system.md for special wiring instructions (future-proofing)
        try:
            system_md = (project_path / "architecture" / "system.md").read_text(encoding="utf-8")
        except Exception:
            pass

        from app.orchestration.wiring_utils import wire_router, wire_model
        from app.utils.entity_discovery import extract_document_models_only
        
        for router in existing_routers:
            wire_router(project_path, router)
        
        all_models = extract_document_models_only(project_path)
        
        for model_name in all_models:
            wire_model(project_path, model_name)
        
        content = main_py_path.read_text(encoding="utf-8")
        
        # Inject Route Audit Log
        audit_marker = 'print("📊 [Route Audit] Registered Routes:")'
        if audit_marker not in content:
            content += "\n\n" + """# ---------------------------------------------------------------------------
# ROUTE AUDIT LOG
# ---------------------------------------------------------------------------
print("📊 [Route Audit] Registered Routes:")
for route in app.routes:
    if hasattr(route, "path") and hasattr(route, "methods"):
        methods = ", ".join(route.methods)
        print(f"   - {methods} {route.path}")
"""
            main_py_path.write_text(content, encoding="utf-8")
            
        log("INTEGRATION", "✅ Backend wiring complete")
        
    # Ensure __init__.py exists
    app_dir = project_path / "backend" / "app"
    app_dir.mkdir(parents=True, exist_ok=True)
    init_file = app_dir / "__init__.py"
    if not init_file.exists():
        init_file.write_text("# Auto-created init\n", encoding="utf-8")
    
    # ═══════════════════════════════════════════════════════════════════
    # FRONTEND INTEGRATION (new Python-based logic)
    # ═══════════════════════════════════════════════════════════════════
    
    frontend_src = project_path / "frontend" / "src"
    if frontend_src.exists() and existing_routers:
        log("INTEGRATION", f"🔗 Generating frontend API helpers for {len(existing_routers)} entities...")
        
        # Generate API helper functions
        _generate_api_helpers(project_path, existing_routers)
        
        # Replace mock imports with API calls in pages
        pages_dir = frontend_src / "pages"
        if pages_dir.exists():
            for page_file in pages_dir.glob("*.jsx"):
                _replace_mock_with_api(page_file, existing_routers)
        
        log("INTEGRATION", "✅ Frontend integration complete")
    
    return StepResult(
        nextstep=WorkflowStep.TESTING_BACKEND,
        turn=6,  # System integration is step 5
    )


def _generate_api_helpers(project_path: Path, routers: list):
    """Generate frontend/src/lib/api.js with API helper functions."""
    
    api_file = project_path / "frontend" / "src" / "lib" / "api.js"
    
    code = """// Auto-generated API helpers
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

"""
    
    for router_name in routers:
        # Convert router filename to entity name
        # tasks.py -> Tasks, bugs.py -> Bugs
        entity_plural = router_name  # tasks
        entity_singular = _singularize(entity_plural)  # task
        entity_title = entity_plural.title()  # Tasks
        singular_title = entity_singular.title()  # Task
        
        code += f"""
// {entity_title} API
export async function fetch{entity_title}() {{
    const res = await fetch(`${{API_BASE}}/api/{entity_plural}`);
    if (!res.ok) throw new Error('Failed to fetch {entity_plural}');
    return await res.json();
}}

export async function create{singular_title}(data) {{
    const res = await fetch(`${{API_BASE}}/api/{entity_plural}`, {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify(data),
    }});
    if (!res.ok) throw new Error('Failed to create {entity_singular}');
    return await res.json();
}}

export async function update{singular_title}(id, data) {{
    const res = await fetch(`${{API_BASE}}/api/{entity_plural}/${{id}}`, {{
        method: 'PUT',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify(data),
    }});
    if (!res.ok) throw new Error('Failed to update {entity_singular}');
    return await res.json();
}}

export async function delete{singular_title}(id) {{
    const res = await fetch(`${{API_BASE}}/api/{entity_plural}/${{id}}`, {{
        method: 'DELETE',
    }});
    if (!res.ok) throw new Error('Failed to delete {entity_singular}');
    return await res.json();
}}
"""
    
    api_file.write_text(code, encoding="utf-8")
    log("INTEGRATION", f"   📝 Generated {api_file.relative_to(project_path)}")


def _replace_mock_with_api(page_file: Path, routers: list):
    """Replace mock data imports with API calls in a JSX page."""
    import re
    
    content = page_file.read_text(encoding="utf-8")
    original = content
    
    # Find which entity this page uses
    for router_name in routers:
        entity_plural = router_name
        entity_title = entity_plural.title()
        
        # Pattern: import { mockTasks } from '@/data/mock'
        mock_import_pattern = rf"import\s+{{\s*mock{entity_title}\s*}}\s+from\s+['\"]@/data/mock['\"]"
        
        if re.search(mock_import_pattern, content):
            # Replace import
            new_import = f"import {{ fetch{entity_title} }} from '@/lib/api'"
            content = re.sub(mock_import_pattern, new_import, content)
            
            # Pattern: const tasks = mockTasks
            # Replace with: const { data: tasks } = use<truncated>

            # Pattern: const tasks = mockTasks
            # Simple text replacement (not full AST - requires manual async handling)
            mock_usage_pattern = rf"const\s+{entity_plural}\s*=\s*mock{entity_title}"
            
            if re.search(mock_usage_pattern, content):
                log("INTEGRATION", f"    Updated {page_file.name} (entity: {entity_plural})")
    
    # Write back if changed
    if content != original:
        page_file.write_text(content, encoding="utf-8")


def _singularize(plural: str) -> str:
    """Simple pluralization remover for common cases."""
    if plural.endswith("ies"):
        return plural[:-3] + "y"  # categories -> category
    elif plural.endswith("ses"):
        return plural[:-2]  # classes -> class
    elif plural.endswith("s"):
        return plural[:-1]  # tasks -> task
    return plural
