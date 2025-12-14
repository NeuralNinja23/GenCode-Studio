# app/handlers/frontend_mock.py
"""
Step 3: Derek creates frontend with MOCK DATA first.

This follows the GenCode Studio pattern:
- Create frontend-first with mock data for immediate "aha moment"
- All mock data goes in src/data/mock.js
- Components are functional but use local state
- Later, contracts.md will be created, then backend, then integration
"""
from pathlib import Path
from typing import Any, List

from app.core.types import ChatMessage, StepResult
from app.core.constants import WorkflowStep
from app.core.exceptions import RateLimitError
from app.handlers.base import broadcast_status
from app.core.logging import log
from app.orchestration.state import WorkflowStateManager
from app.supervision import supervised_agent_call
from app.persistence import persist_agent_output
from app.persistence.validator import validate_file_output
from app.orchestration.utils import pluralize
from app.utils.entity_discovery import discover_primary_entity
from app.handlers.archetype_guidance import get_full_archetype_context, get_archetype_patterns_from_store
from app.utils.component_copier import copy_used_components


# Centralized entity discovery for dynamic fallback



# Constants
MAX_FILES_PER_STEP = 12  # Increased to 12 for components + config
MAX_FILE_LINES = 400






async def step_frontend_mock(
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
    Step 3: Derek generates frontend with MOCK DATA first.
    
    This creates the immediate "aha moment" for users - they see a working
    UI before any backend is built. All data is mocked in mock.js.
    """
    # V3: Track token usage for cost reporting
    step_token_usage = None
    await broadcast_status(
        manager,
        project_id,
        WorkflowStep.FRONTEND_MOCK,
        f"Turn {current_turn}/{max_turns}: Derek creating frontend with mock data (aha moment!)...",
        current_turn,
        max_turns,
    )

    try:
        architecture = (project_path / "architecture.md").read_text(encoding="utf-8")
    except Exception:
        architecture = "No architecture found - use best judgment."

    # Read package.example.json to guide Derek
    package_json_ref = ""
    playwright_config_ref = ""
    try:
        ref_path = project_path / "frontend/reference/package.example.json"
        if ref_path.exists():
            package_json_ref = ref_path.read_text(encoding="utf-8")
            
        pw_path = project_path / "frontend/reference/playwright.config.example.js"
        if pw_path.exists():
            playwright_config_ref = pw_path.read_text(encoding="utf-8")
    except Exception:
        pass

    intent = await WorkflowStateManager.get_intent(project_id) or {}
    entities_list = intent.get("entities", [])
    
    # Use centralized discovery as fallback instead of hardcoded "item"
    if entities_list:
        primary_entity = entities_list[0]
    else:
        entity_name, _ = discover_primary_entity(project_path)
        primary_entity = entity_name if entity_name else "item"  # Last resort only
    
    primary_entity_capitalized = primary_entity.capitalize()
    primary_entity_plural = pluralize(primary_entity)
    domain = intent.get("domain", "general")
    
    # ═══════════════════════════════════════════════════════
    # ARCHETYPE-AWARE GENERATION (Key for diverse UI patterns)
    # ═══════════════════════════════════════════════════════
    archetype_routing = intent.get("archetypeRouting", {})
    detected_archetype = archetype_routing.get("top", "admin_dashboard") if isinstance(archetype_routing, dict) else "admin_dashboard"
    
    # Get archetype-specific UI guidance
    archetype_guidance = get_full_archetype_context(
        archetype=detected_archetype,
        entity=primary_entity,
        domain=domain
    )
    
    # Get learned patterns from Pattern Store (pre-training integration)
    pattern_hints = get_archetype_patterns_from_store(detected_archetype, "frontend_mock")
    
    log("FRONTEND_MOCK", f"🎨 Generating UI for archetype: {detected_archetype}")
    
    # Extract app title from user request
    app_title = user_request.split(".")[0][:50] if "." in user_request else user_request[:50]

    # FRONTEND-FIRST MOCK PROMPT (GenCode Studio Pattern) - CUSTOMIZATION FOCUSED
    frontend_mock_instructions = f"""You are Derek, creating a CUSTOMIZED React frontend for this SPECIFIC project.

═══════════════════════════════════════════════════════
⚠️ CRITICAL: CUSTOMIZE EVERYTHING FOR THIS PROJECT
═══════════════════════════════════════════════════════

Do NOT create generic "Item" pages. Create pages SPECIFIC to:
- **Project**: {app_title}
- **Primary Entity**: {primary_entity_capitalized}
- **All Entities**: {', '.join(entities_list)}
- **Domain**: {domain}
- **Archetype**: {detected_archetype}

USER REQUEST: {user_request}

{archetype_guidance}

{pattern_hints}

ARCHITECTURE REFERENCE:
{architecture[:2000]}

═══════════════════════════════════════════════════════
⚠️ CRITICAL: UI DESIGN SYSTEM COMPLIANCE
═══════════════════════════════════════════════════════

IMPORTANT:
- The architecture.md file includes a section "## UI Design System".
- Before writing any JSX, you MUST:
  1) Read that section.
  2) In your "thinking" field, summarize the key visual rules in 3–5 bullets.
  3) Implement the frontend EXACTLY according to those rules.
- If anything you were going to do conflicts with the UI Design System, the UI Design System WINS.

DESIGN TOKENS USAGE (CRITICAL):
If `frontend/src/design/theme.ts` exists, you MUST:
- Import `tokens` or `ui` from it and use those className strings instead of inventing new Tailwind class combinations for:
  - page background
  - cards
  - primary/secondary buttons
  - muted text

Example:
```jsx
import {{ ui }} from "../design/theme";

export default function HomePage() {{
  return (
    <main className={{ui.pageRoot}}>
      <section className="max-w-6xl mx-auto px-6 py-10 space-y-8">
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <Card className={{ui.card}}>...</Card>
        <Button className={{ui.primaryButton}}>Create {primary_entity_capitalized}</Button>
      </section>
    </main>
  );
}}
```

Do NOT change the meaning of the tokens; use them consistently across pages.

REFERENCE package.json (Use as template):
{package_json_ref}

REFERENCE playwright.config.js (Use as template):
{playwright_config_ref}

═══════════════════════════════════════════════════════
📁 FILES TO GENERATE (Use ACTUAL entity names!)
═══════════════════════════════════════════════════════

⚠️ IMPORTANT: DO NOT generate package.json or playwright.config.js!
These files are PRE-SEEDED with all required dependencies (Radix UI, Shadcn, etc).
Only generate the SOURCE FILES listed below:

Generate these 5 files with PROJECT-SPECIFIC names:

1. **frontend/src/data/mock.js**
   - Export: `mock{primary_entity_capitalized}s` (not mockItems!)
   - Include 4-5 realistic {primary_entity} objects
   - Add fields relevant to {domain}: title, content, status, etc.

2. **frontend/src/pages/{primary_entity_capitalized}sPage.jsx**
   - This is the MAIN page for managing {primary_entity_plural}
   - Show list of {primary_entity_plural} with CRUD operations
   - Use shadcn Card, Button, Input components

3. **frontend/src/pages/Home.jsx** 
   - Title: "{app_title}" (NOT "My Application"!)
   - Show dashboard with {primary_entity} statistics
   - Recent {primary_entity_plural} list
   - Quick action buttons

4. **frontend/src/components/{primary_entity_capitalized}Card.jsx**
   - Reusable card component for displaying a single {primary_entity}
   - Show relevant fields (title, description, status, etc.)
   - Edit and Delete buttons

5. **frontend/src/App.jsx**
   - Import and render Home page
   - Can add react-router later

❌ DO NOT GENERATE:
- frontend/package.json (ALREADY SEEDED with all deps!)
- frontend/playwright.config.js (ALREADY SEEDED!)
- frontend/vite.config.js (ALREADY SEEDED!)
- frontend/tailwind.config.js (ALREADY SEEDED!)

═══════════════════════════════════════════════════════
📊 MOCK DATA EXAMPLE (src/data/mock.js)
═══════════════════════════════════════════════════════

```javascript
// CORRECT: Use actual entity name "{primary_entity}"
export const mock{primary_entity_capitalized}s = [
  {{
    id: "1",
    title: "Sample {primary_entity_capitalized} 1",
    content: "This is an example {primary_entity}",
    status: "Active",
    created_at: new Date().toISOString(),
  }},
  {{
    id: "2",
    title: "Sample {primary_entity_capitalized} 2", 
    content: "Another {primary_entity} example",
    status: "Draft",
    created_at: new Date().toISOString(),
  }},
  // Add 2-3 more realistic {primary_entity_plural}
];

export const mock{primary_entity_capitalized}Stats = {{
  total: mock{primary_entity_capitalized}s.length,
  active: mock{primary_entity_capitalized}s.filter(x => x.status === "Active").length,
  draft: mock{primary_entity_capitalized}s.filter(x => x.status === "Draft").length,
}};
```

═══════════════════════════════════════════════════════
🎨 SHADCN COMPONENTS (Already Available!)
═══════════════════════════════════════════════════════

Templates include these shadcn components - USE THEM:

```jsx
import {{ Button }} from '@/components/ui/button';
import {{ Card, CardHeader, CardTitle, CardContent }} from '@/components/ui/card';
import {{ Input }} from '@/components/ui/input';
import {{ Textarea }} from '@/components/ui/textarea';
import {{ Badge }} from '@/components/ui/badge';
import {{ Label }} from '@/components/ui/label';
import {{ Skeleton }} from '@/components/ui/skeleton';
```

🚨 ICONS - CRITICAL RULE (WILL BE REJECTED IF VIOLATED):
```jsx
// ✅ CORRECT - Use lucide-react for ALL icons including status:
import {{ Plus, Trash2, Edit, Search, Loader2, CheckCircle, XCircle, Clock, AlertCircle }} from 'lucide-react';

// Status indicators MUST use lucide-react:
<CheckCircle className="text-green-500" />  // For success/active
<XCircle className="text-red-500" />         // For error/failed
<Clock className="text-yellow-500" />        // For pending/waiting
<AlertCircle className="text-orange-500" /> // For warning

// ❌ NEVER USE EMOJIS - These will cause IMMEDIATE REJECTION:
// ❌ ✅ ❌ ⌛ 🔍 ✓ ✗ ⚠️ 🟢 🔴 🟡 ⭐ 📝 🗑️ ➕
// ❌ Any Unicode symbol that looks like an icon
```

═══════════════════════════════════════════════════════
🏠 HOME.JSX REQUIREMENTS
═══════════════════════════════════════════════════════

The Home.jsx page MUST be customized:
- Title: "{app_title}" (NOT generic!)
- Show {primary_entity} statistics from mock data
- Recent {primary_entity_plural} section
- Use shadcn Card components

Example header:
```jsx
<h1 data-testid="page-title" className="text-3xl font-bold">{app_title}</h1>
<p className="text-muted-foreground">
  Manage your {primary_entity_plural} efficiently
</p>
```

═══════════════════════════════════════════════════════
✨ LOCAL STATE FOR CRUD
═══════════════════════════════════════════════════════

```jsx
function {primary_entity_capitalized}sPage() {{
  const [items, setItems] = useState(mock{primary_entity_capitalized}s);
  const [form, setForm] = useState({{ title: '', content: '' }});
  
  const handleCreate = () => {{
    const new{primary_entity_capitalized} = {{
      id: Date.now().toString(),
      ...form,
      status: "Draft",
      created_at: new Date().toISOString(),
    }};
    setItems([...items, new{primary_entity_capitalized}]);
    setForm({{ title: '', content: '' }});
  }};
  
  const handleDelete = (id) => {{
    setItems(items.filter(x => x.id !== id));
  }};
  
  return (...);
}}
```

═══════════════════════════════════════════════════════
📋 TESTING ATTRIBUTES (CRITICAL - MUST MATCH EXACTLY)
═══════════════════════════════════════════════════════

These EXACT testids are REQUIRED for Playwright tests:

1. Main page container: data-testid="page-root"
2. Main page title (h1): data-testid="page-title"
3. Primary create button: data-testid="create-{primary_entity}-button"
4. Delete action button: data-testid="delete-{primary_entity}-button"
5. Main list container: data-testid="{primary_entity}-list"
6. Loading state: data-testid="loading-indicator"
7. Error state: data-testid="error-message"

Example structure:
```jsx
<main data-testid="page-root" className="min-h-screen bg-background">
  <h1 data-testid="page-title">{{title}}</h1>
  <Button data-testid="create-{primary_entity}-button">Create</Button>
  <div data-testid="{primary_entity}-list">...</div>
</main>
```

═══════════════════════════════════════════════════════
📤 OUTPUT FORMAT (5 SOURCE FILES ONLY)
═══════════════════════════════════════════════════════

Return ONLY valid JSON with these 5 files (NO package.json!):
{{
  "thinking": "Explain your design for {app_title} and how you're customizing for {primary_entity_plural}...",
  "files": [
    {{ "path": "frontend/src/data/mock.js", "content": "..." }},
    {{ "path": "frontend/src/pages/{primary_entity_capitalized}sPage.jsx", "content": "..." }},
    {{ "path": "frontend/src/pages/Home.jsx", "content": "..." }},
    {{ "path": "frontend/src/components/{primary_entity_capitalized}Card.jsx", "content": "..." }},
    {{ "path": "frontend/src/App.jsx", "content": "..." }}
  ]
}}

Generate the CUSTOMIZED frontend for "{app_title}" now!
"""

    try:
        # Use supervised call with auto-retry
        result = await supervised_agent_call(
            project_id=project_id,
            manager=manager,
            agent_name="Derek",
            step_name="Frontend (Mock Data)",
            base_instructions=frontend_mock_instructions,
            project_path=project_path,
            user_request=user_request,
            contracts="",  # No contracts yet - this is frontend-first
            max_retries=2,
        )
        
        # V3: Extract token usage for cost tracking
        step_token_usage = result.get("token_usage")
        
        parsed = result.get("output", {})
        if "files" in parsed and parsed["files"]:
            validated = validate_file_output(
                parsed, WorkflowStep.FRONTEND_MOCK, max_files=10
            )
            files_written = await persist_agent_output(
                manager,
                project_id,
                project_path,
                validated,
                WorkflowStep.FRONTEND_MOCK,
            )
            
            status = "✅ approved" if result.get("approved") else "⚠️ best effort"
            log(
                "FRONTEND_MOCK",
                f"Derek generated {files_written} frontend files with mock data ({status})",
            )
            
            # =========================================================================
            # 📦 JUST-IN-TIME COMPONENT COPYING (Only copy what's needed)
            # =========================================================================
            try:
                copied_count = copy_used_components(project_path)
                log("FRONTEND_MOCK", f"📦 Copied {copied_count} Shadcn components based on imports")
            except Exception as e:
                log("FRONTEND_MOCK", f"⚠️ Component copying failed (non-fatal): {e}")
        
        chat_history.append({"role": "assistant", "content": str(parsed)})

        # =========================================================================
        # 🔗 FRONTEND INTEGRATOR (Deterministic Wiring)
        # =========================================================================
        log("FRONTEND", "🔗 Running Frontend Integrator to wire pages...")
        
        app_jsx_path = project_path / "frontend/src/App.jsx"
        pages_dir = project_path / "frontend/src/pages"
        
        if app_jsx_path.exists() and pages_dir.exists():
            content = app_jsx_path.read_text(encoding="utf-8")
            
            # Find all page components
            page_files = [f for f in pages_dir.glob("*.jsx")]
            import_lines = []
            route_lines = []
            
            for page in page_files:
                component_name = page.stem # e.g. "HomePage"
                # Import
                import_lines.append(f"import {component_name} from './pages/{component_name}';")
                
                # Route
                if "Home" in component_name:
                     route_lines.append(f'<Route path="/dashboard" element={{<{component_name} />}} />')
                else:
                    # Generic route generation strategy
                    # e.g. ProjectsPage -> /projects
                    route_slug = component_name.lower().replace("page", "")
                    route_lines.append(f'<Route path="/{route_slug}" element={{<{component_name} />}} />')

            # Inject
            imports_block = "\n".join(import_lines)
            routes_block = "\n            ".join(route_lines) # Indentation for JSX
            
            if "// @ROUTE_IMPORTS" in content:
                content = content.replace("// @ROUTE_IMPORTS", f"// @ROUTE_IMPORTS\n{imports_block}")
            
            if "{/* @ROUTE_REGISTER" in content:
                 content = content.replace(
                     "{/* @ROUTE_REGISTER - Integrator injects new routes here */}", 
                     f"{{/* @ROUTE_REGISTER */}}\n            {routes_block}"
                 )
            
            app_jsx_path.write_text(content, encoding="utf-8")
            log("FRONTEND", f"✅ Integrator wired {len(page_files)} pages into App.jsx")
        
    except RateLimitError:
        log("FRONTEND_MOCK", "Rate limit exhausted - stopping workflow", project_id=project_id)
        raise
        
    except Exception as e:
        log("FRONTEND_MOCK", f"Derek failed: {e}")

    # Frontend mock is complete - now do visual QA
    return StepResult(
        nextstep=WorkflowStep.SCREENSHOT_VERIFY,  # Visual QA before contracts
        turn=current_turn + 1,
        token_usage=step_token_usage,  # V3
    )

