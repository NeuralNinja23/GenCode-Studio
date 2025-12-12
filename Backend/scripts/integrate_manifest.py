
"""
Script to apply the Agent's Manifest to the project.
This replaces the "Agent Editing main.py" step.

Usage:
  python integrate_manifest.py --project_path <path> --manifest <json_string_or_path>
"""
import sys
import os
import json
from pathlib import Path

def integrate_manifest(project_path_str: str, manifest_data: dict):
    project_path = Path(project_path_str)
    backend_app_path = project_path / "backend" / "app"
    main_py_path = backend_app_path / "main.py"
    
    print(f"Integrating manifest into {project_path} ...")
    
    # 1. Update Dependencies (requirements.txt)
    reqs = manifest_data.get("dependencies", [])
    if reqs:
        req_path = project_path / "backend" / "requirements.txt"
        if req_path.exists():
            current_reqs = req_path.read_text().splitlines()
            new_reqs = [r for r in reqs if r not in current_reqs]
            if new_reqs:
                print(f"Adding requirements: {new_reqs}")
                with open(req_path, "a") as f:
                    f.write("\n" + "\n".join(new_reqs))
    
    # 2. Wire New Routers into main.py (The Glue)
    new_routers = manifest_data.get("new_routers", []) # List of module names e.g. ["orders", "blog"]
    if new_routers and main_py_path.exists():
        content = main_py_path.read_text(encoding="utf-8")
        lines = content.splitlines()
        
        # A. Inject Imports
        # Find # @ROUTER_IMPORTS
        import_marker_idx = -1
        for i, line in enumerate(lines):
            if "# @ROUTER_IMPORTS" in line:
                import_marker_idx = i
                break
        
        if import_marker_idx != -1:
            for router in new_routers:
                import_line = f"from app.routers import {router}"
                if import_line not in content:
                    lines.insert(import_marker_idx + 1, import_line)
                    print(f"Injected: {import_line}")
        
        # B. Inject Router Registration
        # Find # @ROUTER_REGISTER
        reg_marker_idx = -1
        # Re-scan lines as they shifted
        for i, line in enumerate(lines):
            if "# @ROUTER_REGISTER" in line:
                reg_marker_idx = i
                break
                
        if reg_marker_idx != -1:
            for router in new_routers:
                # Default convention: prefix = /api/{router_name}
                reg_line = f'app.include_router({router}.router, prefix="/api/{router}", tags=["{router}"])'
                if reg_line not in content:
                    lines.insert(reg_marker_idx + 1, reg_line)
                    print(f"Injected: {reg_line}")
        
        main_py_path.write_text("\n".join(lines), encoding="utf-8")
        
    print("Integration complete.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: integrate_manifest.py <project_path> <manifest_json>")
        sys.exit(1)
        
    p_path = sys.argv[1]
    m_data_raw = sys.argv[2]
    
    try:
        if m_data_raw.endswith(".json") and os.path.exists(m_data_raw):
            m_data = json.load(open(m_data_raw))
        else:
            m_data = json.loads(m_data_raw)
            
        integrate_manifest(p_path, m_data)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
