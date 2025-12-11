# app/handlers/frontend_integration.py
"""
Step 10: Derek replaces mock data with real API calls.

Workflow order: ... → Testing Backend (8) → Frontend Integration (9) → Testing Frontend (10)

This is the integration step in the GenCode Studio pattern:
- Frontend already works with mock data
- Backend is now ready with real endpoints
- Replace mock imports with API calls using the centralized api.js client
"""
from pathlib import Path
from typing import Any, Dict, List

from app.core.types import ChatMessage, StepResult
from app.core.constants import WorkflowStep
from app.core.exceptions import RateLimitError
from app.handlers.base import broadcast_status
from app.core.logging import log
from app.orchestration.state import WorkflowStateManager
from app.supervision import supervised_agent_call
from app.persistence import persist_agent_output



MAX_FILES_PER_STEP = 15
MAX_FILE_LINES = 400


from app.persistence.validator import validate_file_output
from app.orchestration.utils import pluralize

# Centralized entity discovery for dynamic fallback
from app.utils.entity_discovery import discover_primary_entity


def _extract_entity_from_request(user_request: str) -> str:
    """
    Dynamically extract a potential entity name from the user request.
    """
    import re
    
    if not user_request:
        return None
    
    request_lower = user_request.lower()
    patterns = [
        r'(?:manage|track|create|build|store|list)\s+(\w+)',
        r'(\w+)\s+(?:app|application|manager|tracker|system)',
        r'(?:a|an)\s+(\w+)\s+(?:management|tracking|listing)',
    ]
    
    skip_words = {'the', 'a', 'an', 'my', 'your', 'web', 'full', 'stack', 'simple', 'basic', 'new'}
    
    def singularize(word: str) -> str:
        """Simple singularization that handles common patterns."""
        word = word.lower().strip()
        if word.endswith('ies') and len(word) > 4:
            return word[:-3] + 'y'
        if word.endswith('sses'):
            return word[:-2]
        if word.endswith('ches') or word.endswith('shes'):
            return word[:-2]
        if word.endswith('xes') or word.endswith('zes'):
            return word[:-2]
        if word.endswith('s') and len(word) > 2 and not word.endswith('ss'):
            return word[:-1]
        return word
    
    for pattern in patterns:
        match = re.search(pattern, request_lower)
        if match:
            candidate = match.group(1)
            if candidate not in skip_words and len(candidate) > 2:
                return singularize(candidate)
    
    return None




def cleanup_unused_components(project_path: Path):
    """
    Remove unused Shadcn UI components to reduce bloat.
    Scans src/pages and src/components for imports and deletes unused files from src/components/ui.
    
    Note: This is a sync function called at the end of step_frontend_integration.
    The os.walk is acceptable here since it's called after async work is done.
    """
    import re
    import os
    
    frontend_dir = project_path / "frontend"
    src_dir = frontend_dir / "src"
    ui_dir = src_dir / "components" / "ui"
    
    if not ui_dir.exists():
        return 0
        
    # 1. identifying used components
    used_components = set()
    
    # Files to scan (pages, layouts, custom components)
    scan_extensions = {".jsx", ".js", ".tsx", ".ts"}
    
    # Regex to find imports like: import { Button } from "@/components/ui/button"
    # or import ... from "../components/ui/button"
    import_pattern = re.compile(r'from\s+["\']@?/?\.*components/ui/([a-z0-9-]+)["\']')
    
    try:
        # FIX ASYNC-001: This function is called synchronously at step end,
        # so blocking os.walk is acceptable here. For true async safety,
        # wrap entire function call in asyncio.to_thread() at call site.
        for root, _, files in os.walk(src_dir):
            for file in files:
                if Path(file).suffix not in scan_extensions:
                    continue
                    
                # Don't scan the UI directory itself (circular)
                if "components\\ui" in root or "components/ui" in root:
                    continue
                    
                file_path = Path(root) / file
                try:
                    content = file_path.read_text(encoding="utf-8")
                    matches = import_pattern.findall(content)
                    for match in matches:
                        used_components.add(match)
                except Exception:
                    pass
                    
        # Always keep basic primitives that might be used dynamically or by other UI components
        # (Though technically we should scan UI components recursively, this is a safe baseline)
        used_components.add("button")
        used_components.add("input")
        used_components.add("label")
        used_components.add("form") # Often used with useForm
        
        # 2. Delete unused components
        deleted_count = 0
        for file in ui_dir.iterdir():
            if file.suffix != ".jsx":
                continue
                
            component_name = file.stem # e.g. "button" from "button.jsx"
            
            if component_name not in used_components:
                try:
                    file.unlink()
                    deleted_count += 1
                except Exception as e:
                    log("CLEANUP", f"Failed to delete {file.name}: {e}")
                    
        if deleted_count > 0:
            log("CLEANUP", f"🗑️ Pruned {deleted_count} unused Shadcn UI components")
            
        return deleted_count
        
    except Exception as e:
        log("CLEANUP", f"Component cleanup failed: {e}")
        return 0


async def step_frontend_integration(
    project_id: str,
    user_request: str,
    manager: Any,
    project_path: Path,
    chat_history: List[ChatMessage],
    provider: str,
    model: str,
    current_turn: int,
    max_turns: int,
) -> StepResult:
    """
    Step 9: Derek replaces mock data with real API calls.
    
    The frontend already works with mock data. Now we:
    1. Update lib/api.js to make real fetch calls
    2. Replace mock imports with API calls in each page
    3. Add loading/error states
    """
    await broadcast_status(
        manager,
        project_id,
        WorkflowStep.FRONTEND_INTEGRATION,
        f"Turn {current_turn}/{max_turns}: Derek integrating frontend with real backend API...",
        current_turn,
        max_turns,
    )

    # Read contracts and existing frontend code
    try:
        contracts = (project_path / "contracts.md").read_text(encoding="utf-8")
    except Exception:
        contracts = "No contracts found - assume standard CRUD."

    # Read current frontend files to understand what needs updating
    frontend_files = []
    frontend_src = project_path / "frontend" / "src"
    if frontend_src.exists():
        for pattern in ["*.jsx", "*.js"]:
            for f in frontend_src.rglob(pattern):
                try:
                    content = f.read_text(encoding="utf-8")
                    rel_path = f.relative_to(project_path)
                    frontend_files.append(f"--- {rel_path} ---\n{content[:500]}...")
                except Exception:
                    pass

    existing_frontend = "\n".join(frontend_files[:8])  # First 8 files

    intent = await WorkflowStateManager.get_intent(project_id) or {}
    entities_list = intent.get("entities", [])
    
    # Use centralized discovery as fallback with dynamic last-resort
    if entities_list:
        primary_entity = entities_list[0]
    else:
        entity_name, _ = discover_primary_entity(project_path)
        if entity_name:
            primary_entity = entity_name
        else:
            # Dynamic last resort: extract from user request
            primary_entity = _extract_entity_from_request(user_request) or "entity"
    
    primary_entity_capitalized = primary_entity.capitalize()
    primary_entity_plural = pluralize(primary_entity)

    integration_instructions = f"""You are Derek, integrating the frontend with the real backend API.

GOAL: Replace mock data with REAL API calls. The frontend already works with mock data.
Now the backend is ready - update the frontend to call real endpoints.

USER REQUEST: {user_request}
PRIMARY ENTITY: {primary_entity_capitalized}
ALL ENTITIES: {', '.join(entities_list)}

═══════════════════════════════════════════════════════
📋 API CONTRACTS (Backend is ready with these endpoints)
═══════════════════════════════════════════════════════
{contracts}

═══════════════════════════════════════════════════════
📁 CURRENT FRONTEND CODE
═══════════════════════════════════════════════════════
{existing_frontend}

═══════════════════════════════════════════════════════
🔄 INTEGRATION CHANGES REQUIRED
═══════════════════════════════════════════════════════

1. **UPDATE lib/api.js** - Make real fetch calls:
```javascript
const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8001";

export async function api(path, options = {{}}) {{
  // Smartly handle paths (prevent /api/api/...)
  const endpoint = path.startsWith("/api") ? path : `/api${{path}}`;
  const res = await fetch(`${{API_BASE}}${{endpoint}}`, {{
    headers: {{ "Content-Type": "application/json" }},
    ...options,
  }});
  if (!res.ok) throw new Error(await res.text() || res.statusText);
  return res.json();
}}

export const get = (path) => api(path);
export const post = (path, data) => api(path, {{ method: "POST", body: JSON.stringify(data) }});
export const put = (path, id, data) => api(`${{path}}/${{id}}`, {{ method: "PUT", body: JSON.stringify(data) }});
export const del = (path, id) => api(`${{path}}/${{id}}`, {{ method: "DELETE" }});
```

3. **COMMON PITFALLS - DO NOT DO THIS**:
❌ WRONG: `const data = await get(...); setItems(data.data);`
   - Why: `res.json()` returns the payload directly. If the backend sends `[1,2]`, accessing `.data` gives `undefined`.
✅ RIGHT: `const data = await get(...); setItems(data);` or `setItems(data.data || data);` if backend wraps it.
   - CHECK YOUR BACKEND CONTRACTS! If the backend returns ` {{ "data": [...] }} `, THEN use `.data`. If it returns `[...]`, use it directly.

4. **UPDATE EACH PAGE** - Replace mock imports with API calls:

BEFORE (mock):
```jsx
import {{ mockItems }} from '../data/mock';

function ItemsPage() {{
  const [items, setItems] = useState(mockItems);
  // Local state operations...
}}
```

AFTER (real API):
```jsx
import {{ get, post, del }} from '../lib/api';

function ItemsPage() {{
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  
  const loadItems = async () => {{
    try {{
      setLoading(true);
      setError("");
      const data = await get("/items");
      setItems(Array.isArray(data) ? data : []);
    }} catch (err) {{
      setError(err.message);
    }} finally {{
      setLoading(false);
    }}
  }};
  
  useEffect(() => {{
    loadItems();
  }}, []);
  
  const handleCreate = async (formData) => {{
    try {{
      await post("/items", formData);
      loadItems();  // Refresh list
    }} catch (err) {{
      setError(err.message);
    }}
  }};
  
  const handleDelete = async (id) => {{
    try {{
      await del("/items", id);
      loadItems();  // Refresh list
    }} catch (err) {{
      setError(err.message);
    }}
  }};
  
  if (loading) return <div data-testid="loading-indicator">Loading...</div>;
  if (error) return <div data-testid="error-message" className="text-red-500">{{error}}</div>;
  
  return (...);
}}
```

3. **UPDATE DASHBOARD** - Fetch real stats:
```jsx
const [stats, setStats] = useState({{ total: 0, open: 0 }});

useEffect(() => {{
  async function loadStats() {{
    const items = await get("/items");
    setStats({{
      total: items.length,
      open: items.filter(i => i.status === "Open").length,
      // ...
    }});
  }}
  loadStats();
}}, []);
```

═══════════════════════════════════════════════════════
📤 OUTPUT FORMAT
═══════════════════════════════════════════════════════

Return ONLY valid JSON:
{{
  "thinking": "Explain what mock data you're replacing and how you're connecting to the API...",
  "files": [
    {{ "path": "frontend/src/lib/api.js", "content": "..." }},
    {{ "path": "frontend/src/pages/Home.jsx", "content": "..." }},
    ...
  ]
}}

Generate the updated frontend files with real API calls now!
"""

    try:
        result = await supervised_agent_call(
            project_id=project_id,
            manager=manager,
            agent_name="Derek",
            step_name="Frontend Integration",
            base_instructions=integration_instructions,
            project_path=project_path,
            user_request=user_request,
            contracts=contracts,
            max_retries=2,
        )
        
        parsed = result.get("output", {})
        if "files" in parsed and parsed["files"]:
            validated = validate_file_output(
                parsed, WorkflowStep.FRONTEND_INTEGRATION, max_files=10
            )
            files_written = await persist_agent_output(
                manager,
                project_id,
                project_path,
                validated,
                WorkflowStep.FRONTEND_INTEGRATION,
            )
            
            status = "✅ approved" if result.get("approved") else "⚠️ best effort"
            log(
                "FRONTEND_INTEGRATION",
                f"Derek integrated {files_written} frontend files with API ({status})",
            )
        
        chat_history.append({"role": "assistant", "content": str(parsed)})
        
    except RateLimitError:
        log("FRONTEND_INTEGRATION", "Rate limit exhausted", project_id=project_id)
        raise
        
    except Exception as e:
        log("FRONTEND_INTEGRATION", f"Derek integration failed: {e}")
        raise

    # CLEANUP: Remove unused Shadcn components
    try:
        cleanup_unused_components(project_path)
    except Exception as e:
        log("CLEANUP", f"Warning: Cleanup failed: {e}")

    # Integration complete - proceed to frontend testing
    return StepResult(
        nextstep=WorkflowStep.TESTING_FRONTEND,
        turn=current_turn + 1,
    )
