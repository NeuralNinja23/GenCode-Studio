# app/utils/component_copier.py
"""
Just-in-Time Shadcn Component Copier

Instead of copying all 55+ Shadcn components upfront, this utility:
1. Scans generated frontend code for @/components/ui/* imports
2. Copies ONLY the components that are actually used
3. Handles component dependencies (e.g., dialog.jsx needs @radix-ui/react-dialog)

This keeps projects lean and focused.
"""
import re
import shutil
from pathlib import Path
from typing import Set

from app.core.logging import log
from app.core.config import settings


# Component dependency map - some components need other components
COMPONENT_DEPENDENCIES = {
    "alert-dialog": ["button"],
    "command": ["dialog"],
    "drawer": ["dialog"],
    "form": ["label"],
    "sheet": ["dialog"],
    "toast": ["button"],
    "sonner": [],  # Uses external sonner library
}


def get_used_components(project_path: Path) -> Set[str]:
    """
    Scan frontend source files for @/components/ui/* imports.
    
    Returns:
        Set of component names (e.g., {"button", "card", "input"})
    """
    frontend_src = project_path / "frontend" / "src"
    if not frontend_src.exists():
        return set()
    
    used_components = set()
    
    # Regex to match: from '@/components/ui/button' or from "@/components/ui/card"
    import_pattern = re.compile(
        r"""(?:from|import)\s+['"]@/components/ui/([a-z-]+)['"]""",
        re.IGNORECASE
    )
    
    # Scan all JS/JSX/TS/TSX files
    for ext in ["*.js", "*.jsx", "*.ts", "*.tsx"]:
        for file_path in frontend_src.rglob(ext):
            # Skip the ui folder itself
            if "/components/ui/" in str(file_path).replace("\\", "/"):
                continue
                
            try:
                content = file_path.read_text(encoding="utf-8")
                matches = import_pattern.findall(content)
                used_components.update(matches)
            except Exception as e:
                log("COMPONENT_COPIER", f"⚠️ Error reading {file_path}: {e}")
    
    return used_components


def get_all_required_components(components: Set[str]) -> Set[str]:
    """
    Expand component set to include dependencies.
    
    For example, if "alert-dialog" is used, we also need "button".
    """
    all_components = set(components)
    
    for component in components:
        deps = COMPONENT_DEPENDENCIES.get(component, [])
        all_components.update(deps)
    
    return all_components


def copy_used_components(project_path: Path) -> int:
    """
    Copy only the used Shadcn components to the project.
    
    Returns:
        Number of components copied
    """
    # Source: templates folder
    templates_ui = settings.paths.base_dir / "backend" / "templates" / "frontend" / "src" / "components" / "ui"
    
    # Destination: project frontend
    project_ui = project_path / "frontend" / "src" / "components" / "ui"
    
    if not templates_ui.exists():
        log("COMPONENT_COPIER", f"⚠️ Templates UI folder not found: {templates_ui}")
        return 0
    
    # Ensure destination exists
    project_ui.mkdir(parents=True, exist_ok=True)
    
    # Get used components
    used = get_used_components(project_path)
    
    if not used:
        log("COMPONENT_COPIER", "⚠️ No UI components detected in imports")
        # Copy essential components as fallback
        used = {"button", "card", "input", "badge", "label", "skeleton"}
    
    # Expand with dependencies
    required = get_all_required_components(used)
    
    log("COMPONENT_COPIER", f"📦 Detected {len(used)} components, {len(required)} with deps: {sorted(required)}")
    
    # Copy each required component
    copied = 0
    for component in required:
        src_file = templates_ui / f"{component}.jsx"
        dest_file = project_ui / f"{component}.jsx"
        
        if src_file.exists():
            shutil.copy2(src_file, dest_file)
            copied += 1
        else:
            log("COMPONENT_COPIER", f"⚠️ Component not found in templates: {component}")
    
    # Also copy the lib/utils.js if not exists (needed by components)
    lib_src = settings.paths.base_dir / "backend" / "templates" / "frontend" / "src" / "lib"
    lib_dest = project_path / "frontend" / "src" / "lib"
    
    if lib_src.exists() and not (lib_dest / "utils.js").exists():
        lib_dest.mkdir(parents=True, exist_ok=True)
        for lib_file in lib_src.glob("*.js"):
            if not (lib_dest / lib_file.name).exists():
                shutil.copy2(lib_file, lib_dest / lib_file.name)
    
    log("COMPONENT_COPIER", f"✅ Copied {copied}/{len(required)} Shadcn components")
    
    return copied


def copy_component_by_name(project_path: Path, component_name: str) -> bool:
    """
    Copy a single component by name (for on-demand copying).
    
    Args:
        project_path: Path to project
        component_name: Component name (e.g., "dialog")
    
    Returns:
        True if copied successfully
    """
    templates_ui = settings.paths.base_dir / "backend" / "templates" / "frontend" / "src" / "components" / "ui"
    project_ui = project_path / "frontend" / "src" / "components" / "ui"
    
    src_file = templates_ui / f"{component_name}.jsx"
    dest_file = project_ui / f"{component_name}.jsx"
    
    if not src_file.exists():
        return False
    
    project_ui.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_file, dest_file)
    
    return True
