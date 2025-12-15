# app/orchestration/wiring_utils.py
"""
Wiring Utilities - Handles injection of content into main.py.

This is the SINGLE SOURCE OF TRUTH for:
- Registering Routers (imports + include_router)
- Registering Models (imports + document_models)

Used by:
- handlers/backend.py (System Integration)
- orchestration/self_healing_manager.py (Healing)
"""
from pathlib import Path
import re
from app.core.logging import log


def wire_router(project_path: Path, router_name: str) -> bool:
    """
    Ensure router is wired in main.py (idempotent).
    
    Args:
        project_path: Path to the workspace
        router_name: Name of the router (e.g. "tasks")
        
    Returns:
        True if changes were made, False if already present
    """
    main_path = project_path / "backend" / "app" / "main.py"
    if not main_path.exists():
        log("WIRING", f"⚠️ main.py not found at {main_path}")
        return False
    
    content = main_path.read_text(encoding="utf-8")
    original_content = content
    
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
    
    # Add import if not present
    if not router_already_imported:
        import_line = f"from app.routers import {router_name}"
        if "# @ROUTER_IMPORTS" in content:
            content = re.sub(
                r'^(# @ROUTER_IMPORTS[^\n]*)\n',
                f'\\1\n{import_line}\n',
                content,
                count=1,
                flags=re.MULTILINE
            )
        else:
            # Fallback: add before lifespan
            content = content.replace(
                "from app.core.config import settings",
                f"from app.core.config import settings\n{import_line}"
            )
    
    # Add registration if not present
    if not router_already_registered:
        include_line = f"app.include_router({router_name}.router, prefix='/api/{router_name}', tags=['{router_name}'])"
        if "# @ROUTER_REGISTER" in content:
            content = re.sub(
                r'^(# @ROUTER_REGISTER[^\n]*)\n',
                f'\\1\n{include_line}\n',
                content,
                count=1,
                flags=re.MULTILINE
            )
        elif "@app.get" in content:
            content = re.sub(
                r'(@app\.get)',
                f'{include_line}\n\n\\1',
                content,
                count=1
            )
        else:
            content += f"\n\n{include_line}\n"
    
    if content != original_content:
        main_path.write_text(content, encoding="utf-8")
        log("WIRING", f"✅ Wired router: {router_name}")
        return True
    return False


def wire_model(project_path: Path, model_name: str) -> bool:
    """
    Ensure model is imported AND registered in document_models list in main.py.
    
    THIS IS CRITICAL FOR BEANIE ODM TO WORK.
    Without this, all collection operations return 500 Server Error.
    
    Args:
        project_path: Path to the workspace
        model_name: Name of the model class (e.g. "Task")
        
    Returns:
        True if changes were made
    """
    main_path = project_path / "backend" / "app" / "main.py"
    if not main_path.exists():
        log("WIRING", f"⚠️ main.py not found at {main_path}")
        return False
    
    content = main_path.read_text(encoding="utf-8")
    original_content = content
    
    # ═══════════════════════════════════════════════════════════
    # 1. ENSURE MODEL IMPORT
    # ═══════════════════════════════════════════════════════════
    import_line = f"from app.models import {model_name}"
    if import_line not in content:
        if "# @MODEL_IMPORTS" in content:
            content = re.sub(
                r'^(# @MODEL_IMPORTS[^\n]*)\n',
                f'\\1\n{import_line}\n',
                content,
                count=1,
                flags=re.MULTILINE
            )
        elif "from app.core.config import settings" in content:
            content = content.replace(
                "from app.core.config import settings",
                f"from app.core.config import settings\n{import_line}"
            )
        else:
            # Absolute fallback: prepend after other imports
            content = import_line + "\n" + content
        log("WIRING", f"✅ Added import: {import_line}")
    
    # ═══════════════════════════════════════════════════════════
    # 2. ENSURE MODEL REGISTRATION IN document_models
    # ═══════════════════════════════════════════════════════════
    # Find: document_models = [] or document_models = [SomeModel]
    # Replace with: document_models = [SomeModel, NewModel]
    # 
    # BUG FIX: Use ^(\s*) with MULTILINE to match only actual code lines,
    # not comments like "# Example: document_models = [User, Post]"
    
    match = re.search(r'^(\s*)document_models\s*=\s*\[(.*?)\]', content, re.MULTILINE)
    if match:
        indent = match.group(1)  # Preserve indentation
        current_list = match.group(2).strip()
        
        # Check if model already in list
        if model_name not in current_list:
            if current_list:
                new_list = f"{current_list}, {model_name}"
            else:
                new_list = model_name
            
            old_str = match.group(0)
            new_str = f"{indent}document_models = [{new_list}]"
            content = content.replace(old_str, new_str)
            log("WIRING", f"✅ Added {model_name} to document_models")
    else:
        log("WIRING", f"⚠️ Could not find document_models list in main.py")
    
    if content != original_content:
        main_path.write_text(content, encoding="utf-8")
        
        # ═══════════════════════════════════════════════════════════
        # HARDENING: Post-write verification (NON-NEGOTIABLE)
        # ═══════════════════════════════════════════════════════════
        # Re-read and verify document_models is not empty
        written_content = main_path.read_text(encoding="utf-8")
        if re.search(r'^\s*document_models\s*=\s*\[\s*\]', written_content, re.MULTILINE):
            raise RuntimeError(
                f"WIRING FAILURE: document_models is still empty after wiring {model_name}. "
                f"This is a critical bug - Beanie ODM will fail to initialize."
            )
        log("WIRING", f"✅ Verified document_models is not empty")
        
        return True
    return False
