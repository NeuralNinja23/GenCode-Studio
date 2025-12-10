# app/utils/integration_playbooks.py

import json
from pathlib import Path


INTEGRATION_PLAYBOOKS = {
    "react_vite_frontend": {
        "package.json": {
            "dependencies": {
                "react": "^18.2.0",
                "react-dom": "^18.2.0"
            },
            "devDependencies": {
                "@vitejs/plugin-react": "^4.0.0",
                "vite": "^4.4.0",
                "@playwright/test": "^1.40.0"
            },
            "scripts": {
                "dev": "vite",
                "build": "vite build",
                "test:e2e": "playwright test"
            }
        },
        "vite.config.js": "...",
        "playwright.config.js": "..."
    },
    "fastapi_backend": {
        "requirements.txt": [
            "fastapi==0.104.0",
            "uvicorn[standard]==0.24.0",
            "sqlalchemy==2.0.23",
            "pydantic==2.5.0",
            "pytest==7.4.3",
            "httpx==0.25.0"
        ],
        "pytest.ini": "...",
        "main.py_health_endpoint": """
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}
"""
    }
}

def apply_playbook(playbook_name: str, project_path: Path):
    """Apply integration playbook to project"""
    playbook = INTEGRATION_PLAYBOOKS.get(playbook_name)
    if not playbook:
        return
    
    # Write all playbook files to project
    for file_path, content in playbook.items():
        full_path = project_path / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, dict):
            content = json.dumps(content, indent=2)
        full_path.write_text(content)
