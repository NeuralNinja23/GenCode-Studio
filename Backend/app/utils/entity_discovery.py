# app/utils/entity_discovery.py
"""
Centralized Entity Discovery Utility

DYNAMIC: Reads entity names from project artifacts in priority order.
NEVER falls back to hardcoded values like "Item" or "Note".
"""
import re
from pathlib import Path
from typing import Tuple, Optional, List

from app.core.logging import log


# Issue #5 Fix: Cache to prevent duplicate "no entity found" warnings
_discovery_warnings_logged: set = set()


def discover_primary_entity(project_path: Path, suppress_warning: bool = False) -> Tuple[Optional[str], Optional[str]]:
    """
    Discover the primary entity from project artifacts.
    
    Args:
        project_path: Path to the project directory
        suppress_warning: If True, don't log warning if not found (for early steps)
    """
    
    # Priority 1: contracts.md
    result = _extract_from_contracts(project_path / "contracts.md")
    if result[0]:
        log("DISCOVERY", f"✅ Found entity from contracts.md: {result}")
        return result
    
    # Priority 2: architecture.md
    result = _extract_from_architecture(project_path / "architecture.md")
    if result[0]:
        log("DISCOVERY", f"✅ Found entity from architecture.md: {result}")
        return result
    
    # Priority 3: models.py
    result = _extract_from_models(project_path / "backend" / "app" / "models.py")
    if result[0]:
        log("DISCOVERY", f"✅ Found entity from models.py: {result}")
        return result
    
    # Priority 4: mock.js
    result = _extract_from_mock(project_path / "frontend" / "src" / "data" / "mock.js")
    if result[0]:
        log("DISCOVERY", f"✅ Found entity from mock.js: {result}")
        return result
    
    # Priority 5: routers/ directory
    result = _extract_from_routers(project_path / "backend" / "app" / "routers")
    if result[0]:
        log("DISCOVERY", f"✅ Found entity from routers/: {result}")
        return result
    
    # Priority 6: User Request
    result = _extract_from_user_request(project_path / "user_request.txt")
    if result[0]:
        log("DISCOVERY", f"✅ Found entity from user_request.txt: {result}")
        return result
    
    # Issue #5 Fix: Only warn once per project to avoid log spam
    project_key = str(project_path)
    if not suppress_warning and project_key not in _discovery_warnings_logged:
        log("DISCOVERY", "⚠️ No entity found in any project artifact!")
        _discovery_warnings_logged.add(project_key)
    
    return (None, None)


def _extract_from_contracts(path: Path) -> Tuple[Optional[str], Optional[str]]:
    if not path.exists(): return (None, None)
    try:
        content = path.read_text(encoding="utf-8")
        match = re.search(r'(?:GET|POST|PUT|DELETE|PATCH)\s+/api/(\w+)', content, re.IGNORECASE)
        if match:
            plural = match.group(1).lower()
            return (_singularize(plural), _singularize(plural).capitalize())
    except Exception: pass
    return (None, None)


def _extract_from_architecture(path: Path) -> Tuple[Optional[str], Optional[str]]:
    if not path.exists(): return (None, None)
    try:
        content = path.read_text(encoding="utf-8")
        match = re.search(r'(?:Primary\s+)?(?:Entity|Model|Resource):\s*["\']?(\w+)["\']?', content, re.IGNORECASE)
        if match:
            name = match.group(1)
            return (name.lower(), name.capitalize())
    except Exception: pass
    return (None, None)


def _extract_from_models(path: Path) -> Tuple[Optional[str], Optional[str]]:
    """Extract entity from models.py Document class definitions.
    
    IMPORTANT: Only matches ACTUAL class definitions, not commented examples!
    """
    if not path.exists(): return (None, None)
    
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


def _extract_from_mock(path: Path) -> Tuple[Optional[str], Optional[str]]:
    if not path.exists(): return (None, None)
    try:
        content = path.read_text(encoding="utf-8")
        match = re.search(r'export\s+(?:const|let|var)\s+(?:mock)?(\w+)\s*=\s*\[', content, re.IGNORECASE)
        if match:
            name = match.group(1).lower()
            name = re.sub(r'(?:data|list|items|array)$', '', name, flags=re.IGNORECASE)
            return (_singularize(name), _singularize(name).capitalize())
    except Exception: pass
    return (None, None)


def _extract_from_routers(routers_dir: Path) -> Tuple[Optional[str], Optional[str]]:
    if not routers_dir.exists(): return (None, None)
    try:
        for f in routers_dir.glob("*.py"):
            if f.stem not in ["__init__", "base", "utils", "health"]:
                plural = f.stem.lower()
                return (_singularize(plural), _singularize(plural).capitalize())
    except Exception: pass
    return (None, None)


def _extract_from_user_request(path: Path) -> Tuple[Optional[str], Optional[str]]:
    if not path.exists(): return (None, None)
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
                    return (_singularize(name), _singularize(name).capitalize())
    except Exception: pass
    return (None, None)


def _singularize(word: str) -> str:
    word = word.lower().strip()
    if word.endswith("ies") and len(word) > 3: return word[:-3] + "y"
    if word.endswith("es") and len(word) > 2: return word[:-1]
    if word.endswith("s") and len(word) > 1: return word[:-1]
    return word

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
    if not entity_name: return ""
    entity = entity_name.lower()
    if entity.endswith("y"): return entity[:-1] + "ies"
    if entity.endswith("s"): return entity + "es"
    return entity + "s"