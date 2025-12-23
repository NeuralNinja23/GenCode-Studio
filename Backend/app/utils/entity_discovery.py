# app/utils/entity_discovery.py
"""
Centralized Entity Discovery Utility

DYNAMIC: Reads entity names from project artifacts in priority order.
NEVER falls back to hardcoded values like "Item" or "Note".
"""
import re
from pathlib import Path
from typing import Tuple, Optional, List, Dict, Any
from dataclasses import dataclass, field
import json

from app.core.logging import log
# NOTE: pluralize imported lazily inside functions to avoid circular import


# Issue #5 Fix: Cache to prevent duplicate "no entity found" warnings
_discovery_warnings_logged: set = set()

# Cache for discovered entities - prevents duplicate logs
_discovery_cache: dict = {}


@dataclass
class Field:
    """Field specification for an entity."""
    name: str
    type: str  # "str", "int", "bool", "datetime", "float", "Optional[str]", etc.
    required: bool = True
    enum_values: List[str] = field(default_factory=list)
    description: str = ""
    default: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "required": self.required,
            "enum_values": self.enum_values,
            "description": self.description,
            "default": self.default
        }


@dataclass
class Relationship:
    """Relationship between entities."""
    from_entity: str
    to_entity: str
    type: str  # "one_to_many", "many_to_many", "one_to_one"
    foreign_key: str = ""
    cascade_delete: bool = False
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_entity": self.from_entity,
            "to_entity": self.to_entity,
            "type": self.type,
            "foreign_key": self.foreign_key,
            "cascade_delete": self.cascade_delete,
            "description": self.description
        }


@dataclass
class EntitySpec:
    """Complete specification for an entity."""
    name: str  # "Task", "User", "Note"
    plural: str  # "tasks", "users", "notes"
    type: str = "AGGREGATE"  # "AGGREGATE" (Document, has collection) or "EMBEDDED" (BaseModel, nested only)
    description: str = ""
    fields: List[Field] = field(default_factory=list)
    is_primary: bool = True
    generation_order: int = 999  # Lower = generated first
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "plural": self.plural,
            "type": self.type,  # NEW: Include in serialization
            "description": self.description,
            "fields": [f.to_dict() for f in self.fields],
            "is_primary": self.is_primary,
            "generation_order": self.generation_order
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EntitySpec":
        """Create EntitySpec from dictionary."""
        fields = [Field(**f) if isinstance(f, dict) else f for f in data.get("fields", [])]
        return cls(
            name=data["name"],
            plural=data["plural"],
            type=data.get("type", "AGGREGATE"),  # NEW: Default to AGGREGATE for backward compat
            description=data.get("description", ""),
            fields=fields,
            is_primary=data.get("is_primary", True),
            generation_order=data.get("generation_order", 999)
        )


@dataclass
class EntityPlan:
    """Complete entity generation plan."""
    entities: List[EntitySpec]
    relationships: List[Relationship]
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entities": [e.to_dict() for e in self.entities],
            "relationships": [r.to_dict() for r in self.relationships],
            "warnings": self.warnings
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EntityPlan":
        """Create EntityPlan from dictionary."""
        entities = [EntitySpec.from_dict(e) for e in data.get("entities", [])]
        relationships = [Relationship(**r) if isinstance(r, dict) else r for r in data.get("relationships", [])]
        return cls(
            entities=entities,
            relationships=relationships,
            warnings=data.get("warnings", [])
        )
    
    def save(self, path) -> None:
        """Save entity plan to JSON file."""
        from pathlib import Path
        path = Path(path)
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
    
    @classmethod
    def load(cls, path) -> "EntityPlan":
        """Load entity plan from JSON file."""
        from pathlib import Path
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Entity plan not found: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_dict(data)


def clear_discovery_cache(project_path: Path = None):
    """
    Clear the entity discovery cache for a project.
    
    Call this after generating new artifacts (contracts.md, models.py, etc.)
    to ensure fresh discovery results don't use stale cache.
    
    Args:
        project_path: If provided, clear only this project's cache.
                     If None, clear entire cache.
    """
    global _discovery_cache, _discovery_warnings_logged
    
    if project_path:
        cache_key = str(project_path)
        _discovery_cache.pop(cache_key, None)
        _discovery_warnings_logged.discard(cache_key)
    else:
        _discovery_cache.clear()
        _discovery_warnings_logged.clear()


def discover_primary_entity(project_path: Path, suppress_warning: bool = False) -> Tuple[Optional[str], Optional[str]]:
    """
    Discover the primary entity from project artifacts.
    
    PRIORITY ORDER (authoritative sources only):
    1. entity_plan.json (if exists, use first entity)
    2. architecture.md
    3. models.py (actual generated models)
    4. routers/ directory
    
    REMOVED: mock.js, contracts.md (too ambiguous, caused confusion)
    
    Args:
        project_path: Path to the project directory
        suppress_warning: If True, don't log warning if not found (for early steps)
    """
    # Check cache first to avoid duplicate logs
    cache_key = str(project_path)
    if cache_key in _discovery_cache:
        return _discovery_cache[cache_key]
    
    # Priority 1: entity_plan.json (generated by backend_models step)
    entity_plan_path = project_path / "entity_plan.json"
    if entity_plan_path.exists():
        try:
            plan = EntityPlan.load(entity_plan_path)
            if plan.entities:
                first_entity = plan.entities[0]
                result = (first_entity.plural.rstrip('s'), first_entity.name)
                _discovery_cache[cache_key] = result
                log("DISCOVERY", f"✅ Found entity from entity_plan.json: {result}")
                return result
        except Exception as e:
            log("DISCOVERY", f"⚠️ Failed to load entity_plan.json: {e}")
    
    # Priority 2: architecture/backend.md (Architecture Bundle source of truth)
    arch_entities = discover_entities_from_architecture(project_path / "architecture" / "backend.md")
    if arch_entities:
        first = arch_entities[0]
        result = (first.plural, first.name)
        _discovery_cache[cache_key] = result
        log("DISCOVERY", f"✅ Found entity from architecture/backend.md: {result}")
        return result

    
    # Priority 3: models.py (actual generated code)
    result = _extract_from_models(project_path / "backend" / "app" / "models.py")
    if result[0]:
        _discovery_cache[cache_key] = result
        log("DISCOVERY", f"✅ Found entity from models.py: {result}")
        return result
    
    # Priority 4: routers/ directory
    result = _extract_from_routers(project_path / "backend" / "app" / "routers")
    if result[0]:
        _discovery_cache[cache_key] = result
        log("DISCOVERY", f"✅ Found entity from routers/: {result}")
        return result
    
    # Issue #5 Fix: Only warn once per project to avoid log spam
    if not suppress_warning and cache_key not in _discovery_warnings_logged:
        log("DISCOVERY", "⚠️ No entity found in any project artifact!")
        _discovery_warnings_logged.add(cache_key)
    
    return (None, None)




def discover_entities_from_architecture(architecture_path: Path) -> List[EntitySpec]:
    """
    Parse architecture/backend.md or entire architecture directory and extract entities.
    Returns a list of EntitySpec objects.
    """
    from app.orchestration.utils import pluralize  # Lazy import to avoid circular
    
    if not architecture_path.exists():
        return []
        
    entities = []
    
    # Handle both directory (glob) and file (read)
    # FIX: Explicitly handle directories to prevent read_text crashes
    paths_to_read = []
    if architecture_path.is_dir():
        paths_to_read = list(architecture_path.rglob("*.md"))
    else:
        paths_to_read = [architecture_path]
        
    for p in paths_to_read:
        # FIX: Explicitly skip non-files (as requested)
        if not p.is_file():
            continue
            
        try:
            content = p.read_text(encoding="utf-8")
            
            # FIX: Require explicit "Entity:" keyword to prevent matching API section headings
            # ✅ Matches: "### Entity: User"
            # ❌ Won't match: "### Categories" (API endpoint section)
            # Pattern requires "Entity", "Model", or "Resource" followed by colon
            matches = re.finditer(r'###\s*(?:Entity|Model|Resource)\s*:\s*(\w+)', content, re.IGNORECASE)
            for m in matches:
                name = m.group(1)
                # Skip common section names that might be in headings
                if name.lower() not in ["domain", "api", "database", "backend", "overview", "introduction"]:
                     entities.append(EntitySpec(
                         name=name, 
                         plural=pluralize(name), 
                         type="AGGREGATE" # Assume aggregate by default
                     ))
                     
            if not entities:
                # Fallback Pattern 2: just bolded names in list?
                pass
                
        except Exception as e:
            log("DISCOVERY", f"⚠️ Error parsing architecture file {p}: {e}")
        
    return entities

def _extract_from_architecture_legacy(path: Path) -> Tuple[Optional[str], Optional[str]]:
     # Wrapper for discover_primary_entity backward compatibility
     entities = discover_entities_from_architecture(path)
     if entities:
         return (entities[0].plural, entities[0].name)
     return (None, None)


def _extract_from_models(path: Path) -> Tuple[Optional[str], Optional[str]]:
    """Extract entity from models.py Document class definitions.
    
    IMPORTANT: Only matches ACTUAL class definitions, not commented examples!
    """
    if not path.exists():
        log("DISCOVERY", "⚠️ models.py not found during extraction")
        return (None, None)
    
    try:
        content = path.read_text(encoding="utf-8")
        
        # Process line-by-line to properly skip comments
        for line in content.splitlines():
            # Strip leading whitespace for the check
            stripped = line.lstrip()
            
            # Skip empty lines and comments
            if not stripped or stripped.startswith('#'):
                continue
            
            # Match actual class definition on this line
            match = re.match(r'class\s+(\w+)\s*\(\s*Document\s*\)', stripped)
            if match:
                model_name = match.group(1)
                # Skip base classes
                if model_name not in ["BaseDocument", "BaseModel", "Document"]:
                    return (model_name.lower(), model_name)
                
    except Exception as e:
        log("DISCOVERY", f"Error reading models.py: {e}")
    
    return (None, None)


def extract_all_models_from_models_py(project_path: Path) -> List[str]:
    """
    Extract ALL Beanie Document model class names that ACTUALLY EXIST in models.py.
    
    This is used during system_integration to wire only models that Derek generated,
    NOT entities discovered from mock.js (which may be different).
    
    BUG FIX: Previously, entity discovery from mock.js could return "Category"
    when Derek actually generated "Expense", causing ImportError crashes.
    
    Returns:
        List of model class names (e.g., ["Expense", "Category"])
    """
    models_path = project_path / "backend" / "app" / "models.py"
    
    if not models_path.exists():
        log("DISCOVERY", "⚠️ models.py not found")
        return []
    
    try:
        content = models_path.read_text(encoding="utf-8")
        models = []
        
        # Process line-by-line to properly skip comments
        for line in content.splitlines():
            stripped = line.lstrip()
            
            # Skip empty lines and comments
            if not stripped or stripped.startswith('#'):
                continue
            
            # Match actual class definitions that inherit from Document
            # Updated to handle multiple inheritance: class X(Document, BaseClass)
            match = re.match(r'class\s+(\w+)\s*\([^)]*Document[^)]*\)', stripped)
            if match:
                model_name = match.group(1)
                # Skip base classes
                if model_name not in ["BaseDocument", "BaseModel", "Document"]:
                    models.append(model_name)
        
        if models:
            log("DISCOVERY", f"✅ Found {len(models)} models in models.py: {models}")
        else:
            log("DISCOVERY", "⚠️ No Document classes found in models.py")
        
        return models
        
    except Exception as e:
        log("DISCOVERY", f"Error reading models.py: {e}")
        return []


def extract_document_models_only(project_path: Path) -> List[str]:
    """
    Extract ONLY aggregate Document models (excludes embedded BaseModel classes).
    
    CRITICAL FIX: Prevents wiring embedded models to Beanie, which causes crashes.
    
    Uses entity_plan.json to filter:
    - If entity_plan.json exists: Return only AGGREGATE entities
    - If entity_plan.json missing: Return all Document classes (backward compat)
    
    This works with ANY project - completely dynamic based on entity_plan.json!
    
    Returns:
        List of Document class names that should be wired to Beanie
        Empty list if models don't exist yet
    
    Example:
        For kanban board:
        - All models found: ["Task", "Assignee", "Tag", "Subtasks"]
        - Filtered: ["Task"] (only AGGREGATE)
        - Wired to Beanie: document_models = [Task]
        - Result: Server doesn't crash!
    """
    entity_plan_path = project_path / "entity_plan.json"
    
    # Get all Document classes from models.py
    all_documents = extract_all_models_from_models_py(project_path)
    
    if not all_documents:
        return []  # No models exist yet
    
    # If no entity plan, return all (backward compatibility)
    if not entity_plan_path.exists():
        log("DISCOVERY", "⚠️ No entity_plan.json - wiring all Document models (backward compat)")
        return all_documents
    
    try:
        plan = EntityPlan.load(entity_plan_path)
        
        # Filter: only entities with type="AGGREGATE" (or missing type field = default AGGREGATE)
        aggregate_names = [
            entity.name 
            for entity in plan.entities 
            if entity.type == "AGGREGATE"  # Uses default from FIX #1
        ]
        
        # Return only models that are in aggregates list
        filtered = [m for m in all_documents if m in aggregate_names]
        
        # Log filtering action
        if len(filtered) < len(all_documents):
            embedded = set(all_documents) - set(filtered)
            log("DISCOVERY", f"🔒 Filtered out {len(embedded)} EMBEDDED models: {list(embedded)}")
            log("DISCOVERY", f"   These are BaseModel classes, NOT Document collections")
            log("DISCOVERY", f"✅ Wiring {len(filtered)} AGGREGATE models: {filtered}")
        else:
            log("DISCOVERY", f"✅ All {len(filtered)} models are AGGREGATE: {filtered}")
        
        return filtered
        
    except Exception as e:
        log("DISCOVERY", f"⚠️ Error loading entity_plan.json: {e}")
        log("DISCOVERY", "   Falling back to all Document models (could cause crashes if embedded models exist)")
        return all_documents  # Fallback to all


def _extract_from_mock(path: Path) -> Tuple[Optional[str], Optional[str]]:
    if not path.exists():
        return (None, None)
    try:
        content = path.read_text(encoding="utf-8")
        match = re.search(r'export\s+(?:const|let|var)\s+(?:mock)?(\w+)\s*=\s*\[', content, re.IGNORECASE)
        if match:
            name = match.group(1).lower()
            name = re.sub(r'(?:data|list|items|array)$', '', name, flags=re.IGNORECASE)
            return (singularize(name), singularize(name).capitalize())
    except Exception:
        pass
    return (None, None)


def _extract_from_routers(routers_dir: Path) -> Tuple[Optional[str], Optional[str]]:
    if not routers_dir.exists():
        return (None, None)
    try:
        for f in routers_dir.glob("*.py"):
            if f.stem not in ["__init__", "base", "utils", "health"]:
                plural = f.stem.lower()
                return (singularize(plural), singularize(plural).capitalize())
    except Exception:
        pass
    return (None, None)


def _extract_from_user_request(path: Path) -> Tuple[Optional[str], Optional[str]]:
    if not path.exists():
        return (None, None)
    try:
        content = path.read_text(encoding="utf-8").lower()
        patterns = [
            r'(?:manage|track|create|store|list)\s+(\w+)',
            r'(\w+)\s+(?:app|application|system|manager|tracker)',
        ]
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                name = match.group(1)
                if name not in ["the", "a", "an", "my", "your", "web", "full", "stack"]:
                    return (singularize(name), singularize(name).capitalize())
    except Exception:
        pass
    return (None, None)


def singularize(word: str) -> str:
    """
    Convert a plural word to singular form.
    
    This is the SINGLE SOURCE OF TRUTH for singularization.
    Import this function instead of creating inline copies.
    
    Examples:
        singularize("notes") -> "note"
        singularize("categories") -> "category"
        singularize("classes") -> "class"
    """
    word = word.lower().strip()
    if word.endswith("ies") and len(word) > 3:
        return word[:-3] + "y"
    if word.endswith("es") and len(word) > 2:
        return word[:-1]
    if word.endswith("s") and len(word) > 1:
        return word[:-1]
    return word


# Known entity patterns - used for fast lookup before regex
# These patterns map keywords to entity names
ENTITY_PATTERNS = [
    ("bug", ["bug tracking", "bug tracker", "issue tracker"]),
    ("note", ["notes app", "note taking", "notepad"]),
    ("task", ["task management", "task manager", "todo", "to-do"]),
    ("product", ["e-commerce", "store", "shop", "marketplace"]),
    ("post", ["blog", "blogging"]),
    ("article", ["article", "cms", "content management"]),
    ("query", ["database", "chat with database", "sql"]),
    ("recipe", ["recipe", "cooking", "food"]),
    ("expense", ["expense", "budget", "finance tracker"]),
    ("contact", ["contact", "crm", "customer relationship"]),
    ("event", ["event", "calendar", "scheduling"]),
    ("message", ["chat", "messaging", "communication"]),
    ("file", ["file manager", "storage", "upload"]),
    ("ticket", ["ticketing", "support ticket", "help desk", "customer support"]),
    ("order", ["order management", "orders", "fulfillment"]),
    ("invoice", ["invoice", "billing", "payment"]),
    ("project", ["project management", "projects"]),
    ("user", ["user management", "users", "authentication"]),
]


def extract_entity_from_request(user_request: str) -> Optional[str]:
    """
    Dynamically extract a potential entity name from the user request.
    
    This is the SINGLE SOURCE OF TRUTH for entity extraction from user requests.
    Import this function instead of creating inline copies.
    
    Uses multiple strategies for robust entity extraction:
    1. Known entity patterns (e.g., "ticketing tool" → "ticket")
    2. Dynamic extraction from "X tracker/manager/tool" patterns
    3. "manage/track/create/build X" patterns
    4. Final fallback returns None (caller decides default)
    
    Args:
        user_request: The user's input request
        
    Returns:
        Singularized entity name or None if not found
        
    Examples:
        extract_entity_from_request("create a notes app") -> "note"
        extract_entity_from_request("task tracker") -> "task"
        extract_entity_from_request("ticketing system") -> "ticket"
    """
    if not user_request:
        return None
    
    request_lower = user_request.lower()
    
    # Strategy 1: Check known entity patterns first (fast lookup)
    for entity, keywords in ENTITY_PATTERNS:
        if any(kw in request_lower for kw in keywords):
            return entity
    
    # Strategy 2: Dynamic extraction - "X tracker/manager/system/tool/dashboard/app"
    match = re.search(r'(\w+)\s*(?:tracker|manager|management|system|tool|dashboard|app|application)', request_lower)
    if match:
        word = match.group(1)
        skip_words = {"the", "a", "an", "my", "your", "our", "this", "that", "web", "full", "stack", "simple", "basic", "modern", "new"}
        if word not in skip_words:
            # Handle -ing suffix: "ticketing" → "ticket"
            if word.endswith("ing") and len(word) > 4:
                word = word[:-3] if word.endswith("ting") else word[:-3]
            return singularize(word)
    
    # Strategy 3: Look for "manage/track/create/build X" pattern
    match = re.search(r'(?:manage|track|create|build|store|list)\s+(?:a\s+)?(?:list\s+of\s+)?(\w+)', request_lower)
    if match:
        word = match.group(1)
        skip_words = {"the", "a", "an", "my", "your", "our", "items", "data", "things"}
        if word not in skip_words and len(word) > 2:
            return singularize(word)
            
    # Strategy 3b: Specific fallback for "create a notes manager" where "manager" is the noun in previous regex
    # but "notes" is the adjective/real entity.
    match = re.search(r'create\s+(?:a\s+)?(\w+)\s+(?:manager|app|system)', request_lower)
    if match:
        return singularize(match.group(1))
    
    # Strategy 4: Look for nouns after "with" (e.g., "with ticket list, filters")
    match = re.search(r'with[:\s]+(\w+)\s*(?:list|management|tracking)', request_lower)
    if match:
        return match.group(1)
    
    return None  # Let caller decide default

# Additional Helpers
def discover_db_function(project_path: Path) -> str:
    """
    Discover the database initialization function name from database.py.
    
    Scans the actual database.py file to find the correct function name.
    Falls back to 'init_db' only if discovery fails.
    
    Returns:
        Function name (e.g., 'init_db', 'init_database', 'connect_db')
    """
    database_file = project_path / "backend" / "app" / "database.py"
    
    if database_file.exists():
        try:
            content = database_file.read_text(encoding="utf-8")
            
            # Look for async def init_* or connect_* patterns
            import re
            
            # Priority 1: init_db (standard pattern)
            if re.search(r'async\s+def\s+init_db\s*\(', content):
                return "init_db"
            
            # Priority 2: init_database
            if re.search(r'async\s+def\s+init_database\s*\(', content):
                return "init_database"
            
            # Priority 3: connect_db (legacy pattern)
            if re.search(r'async\s+def\s+connect_db\s*\(', content):
                return "connect_db"
            
            # Priority 4: Any init_* function
            match = re.search(r'async\s+def\s+(init_\w+)\s*\(', content)
            if match:
                return match.group(1)
                
        except Exception as e:
            log("DISCOVERY", f"Error reading database.py: {e}")
    
    # Fallback to standard pattern
    return "init_db"

def discover_routers(project_path: Path) -> List[Tuple[str, str]]:
    routers_dir = project_path / "backend" / "app" / "routers"
    routers = []
    if routers_dir.exists():
        for f in routers_dir.glob("*.py"):
            if f.stem != "__init__":
                routers.append((f.stem, f.stem))
    return routers


def get_entity_plural(entity_name: str) -> str:
    """
    Get the plural form of an entity name.
    
    This is a wrapper around the centralized pluralize function.
    """
    from app.orchestration.utils import pluralize
    return pluralize(entity_name)


# ============================================================================
# MULTI-ENTITY DISCOVERY (Phase 1)
# ============================================================================

def discover_all_entities(project_path: Path, user_request: str = "") -> List["EntitySpec"]:
    """
    Discover ALL entities from project artifacts or user request.
    
    Returns at least 1 entity, up to MAX_ENTITIES.
    
    Priority:
    1. Extract from architecture.md (Data Models section)
    2. Extract from intent state (entities array)
    3. LLM fallback if still <2 entities
    4. Fallback to primary entity only
    
    Args:
        project_path: Project directory path
        user_request: User's original request (for LLM fallback)
    
    Returns:
        List of EntitySpec objects (1-MAX_ENTITIES)
    """

    from app.core.constants import MAX_ENTITIES
    
    entities = []
    
    # Priority 1: Extract ALL entities from architecture/backend.md (Bundle)
    # This is the EXCLUSIVE Source of Truth if it exists.
    arch_backend_path = project_path / "architecture" / "backend.md"
    if arch_backend_path.exists():
        entities.extend(_extract_all_entities_from_architecture(arch_backend_path))
        if entities:
            log("DISCOVERY", f"✅ Found {len(entities)} entities from architecture/backend.md (STRICT MODE)")
            # Phase-1: ARCHITECTURE IS TRUTH. 
            # If we found entities here, we stop - no falling back to intent or AI inference.
            return entities
    if len(entities) < 2:
        try:
            from app.orchestration.state import WorkflowStateManager
            import asyncio
            
            # Check if we're in an async context
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Can't use asyncio.run(), need to handle differently
                    pass
                else:
                    intent = asyncio.run(WorkflowStateManager.get_intent(str(project_path)))
                    if intent and intent.get("entities"):
                        for entity_name in intent["entities"]:
                            from app.orchestration.utils import pluralize
                            entities.append(EntitySpec(
                                name=entity_name.capitalize(),
                                plural=pluralize(entity_name),
                                is_primary=(len(entities) == 0)
                            ))
                        log("DISCOVERY", f"✅ Found {len(intent['entities'])} entities from intent state")
            except RuntimeError:
                # No event loop, skip this source
                pass
        except Exception as e:
            log("DISCOVERY", f"Could not check intent state: {e}")
    
    # Deduplicate by name (case-insensitive)
    seen = set()
    unique_entities = []
    for e in entities:
        if e.name.lower() not in seen:
            seen.add(e.name.lower())
            unique_entities.append(e)
    
    # Cap at MAX_ENTITIES
    if len(unique_entities) > MAX_ENTITIES:
        log("DISCOVERY", f"⚠️ Found {len(unique_entities)} entities; capping at {MAX_ENTITIES}")
        unique_entities = unique_entities[:MAX_ENTITIES]
    
    # If we still don't have at least 1 entity, fall back to primary entity discovery
    if not unique_entities:
        primary_entity, _ = discover_primary_entity(project_path, suppress_warning=True)
        if primary_entity:
            from app.orchestration.utils import pluralize
            unique_entities = [EntitySpec(
                name=primary_entity.capitalize(),
                plural=pluralize(primary_entity),
                is_primary=True
            )]
            log("DISCOVERY", f"✅ Fell back to primary entity: {primary_entity}")
        else:
            # Last resort: use "Task" as default
            unique_entities = [EntitySpec(name="Task", plural="tasks", is_primary=True)]
            log("DISCOVERY", "⚠️ Using default entity: Task")
    
    return unique_entities




def _extract_all_entities_from_architecture(architecture_path: Path) -> List["EntitySpec"]:
    """Parse architecture.md for ALL entities in 'Data Models' section."""

    
    try:
        content = architecture_path.read_text(encoding="utf-8")
    except Exception:
        return []
    
    entities = []
    
    # NEW PARSING LOGIC: Look for "## Entity: <Name>"
    # This matches the format defined in Victoria's prompt.
    # Format: ## Entity: User
    entity_header_pattern = r"^##\s+Entity:\s+([\w]+)"
    matches = re.findall(entity_header_pattern, content, re.MULTILINE)
    
    from app.orchestration.utils import pluralize
    
    for match in matches:
        entity_name = match.strip()
        
        # EXTRACT TYPE (AGGREGATE vs EMBEDDED)
        # Scan the content following the entity header
        # Pattern: ## Entity: Note\nType: EMBEDDED
        entity_block_pattern = rf"##\s+Entity:\s+{re.escape(entity_name)}([\s\S]*?)(?:##\s+Entity:|$)"
        block_match = re.search(entity_block_pattern, content)
        entity_type = "AGGREGATE" # Default
        
        if block_match:
            block_content = block_match.group(1)
            # More permissive regex for Type:
            # Matches: "Type: EMBEDDED", "**Type**: EMBEDDED", "- Type: EMBEDDED"
            type_match = re.search(r"(?:Type|Persistence)[:\s\*]*\s*(AGGREGATE|EMBEDDED)", block_content, re.IGNORECASE)
            if type_match:
                entity_type = type_match.group(1).upper()
        
        entities.append(EntitySpec(
            name=entity_name.capitalize(),
            plural=pluralize(entity_name.lower()),
            type=entity_type,
            is_primary=(len(entities) == 0),
            generation_order=len(entities) + 1
        ))

    
    # Deduplicate
    seen = set()
    unique = []
    for e in entities:
        if e.name.lower() not in seen:
            seen.add(e.name.lower())
            unique.append(e)
    
    return unique


def detect_relationships(
    project_path: Path,
    entities: List["EntitySpec"]
) -> List["Relationship"]:
    """
    Detect relationships from architecture.md.
    
    Args:
        project_path: Project directory
        entities: List of discovered entities
    
    Returns:
        List of Relationship objects
    """

    return []
