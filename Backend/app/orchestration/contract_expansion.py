"""
Contract Expansion Manager
Handles the "Contract Expansion Loop" - detecting valid missing endpoints and fixing contracts.md.
"""
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import re

from app.core.logging import log
from app.orchestration.contract_parser import ContractParser
from app.utils.entity_discovery import get_entity_plural

class ContractExpansionManager:
    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.contracts_path = project_path / "contracts.md"
        self.parser = ContractParser(project_path)

    def create_backup(self) -> str:
        """Create a backup of the current contracts.md content."""
        if self.contracts_path.exists():
            return self.contracts_path.read_text(encoding="utf-8")
        return ""

    def rollback_contract(self, backup_content: str):
        """Rollback contracts.md to the backup content."""
        self.contracts_path.write_text(backup_content, encoding="utf-8")
        log("EXPAND", "⏪ Rolled back contracts.md to previous state.")

    def detect_unknown_endpoint(self, failure_output: str) -> Optional[Dict[str, Any]]:
        """
        Detect if failure is due to unknown endpoint (404 on unknown path).
        
        Trigger condition (ALL must be true):
        1. Test failure is in test_capability_api.py (found in log)
        2. HTTP status is 404
        3. Path is not present in contracts.md
        """
        # 1. Verify failure is in capability tests
        if "test_capability_api.py" not in failure_output:
            return None

        # 2. Look for 404s associated with API calls
        # Regex to find: METHOD /api/path ... 404
        # Matches typical pytest/httpx logs: "GET /api/channels" result 404
        # Or assertion: "assert 404 == 200" combined with a path log nearby
        
        candidates = []
        
        lines = failure_output.splitlines()
        for i, line in enumerate(lines):
            # Check for 404 in this line
            if "404" not in line and "Not Found" not in line:
                continue
                
            # Look backwards/forwards nearby lines for the request
            # Search window: 10 lines before (increased window)
            start = max(0, i - 10)
            window = "\n".join(lines[start:i+1])
            
            # Pattern: (GET|POST|PUT|DELETE) <some chars> /api/<path>
            match = re.search(r'(GET|POST|PUT|DELETE)\s+.*(/api/[a-zA-Z0-9\-_/]+)', window)
            if match:
                method = match.group(1).upper()
                path = match.group(2)
                # Normalize path (remove query params)
                path = path.split('?')[0]
                candidates.append((method, path))
        
        if not candidates:
            return None
            
        # Check against contracts.md
        known_routes = self.parser._parse_contracts_md()
        known_paths = {r.path for r in known_routes}
        
        for method, path in candidates:
            # Check strict match (or prefix match if needed, but contracts usually define base or specific paths)
            # Contract parser cleans paths (removes {id}), so we should verify base path mostly.
            
            # Simple check: Is this exact path known?
            # Or is it a dynamic path like /api/channels/123?
            
            # Heuristic: Remove digits/IDs from path to check "base" existence
            # /api/channels/123 -> /api/channels
            base_path_match = re.match(r'(/api/[a-zA-Z0-9\-_]+)', path)
            base_path = base_path_match.group(1) if base_path_match else path
            
            # If base path is known, it's not a "Missing Entity/Endpoint" in the expansion sense,
            # it might be just a missing specific ID route or logic error.
            # Expansion is primarily for NEW entities or sub-resources.
            
            is_known = False
            for kp in known_paths:
                if kp == path or kp == base_path:
                    is_known = True
                    break
                # Also check if known path is a prefix of this path (e.g. /api/channels known, accessing /api/channels/123)
                if path.startswith(kp + "/"):
                    is_known = True
                    break

            if not is_known:
                # Found a candidate!
                log("EXPAND", f"🔍 Detected unknown endpoint: {method} {path}")
                # Infer entity name from path
                # /api/channels -> Channel
                parts = path.strip("/").split("/")
                if len(parts) >= 2 and parts[0] == "api":
                    plural = parts[1]
                    # Simple plural->singular heuristic
                    entity = plural.rstrip("s").capitalize() 
                    return {
                        "entity": entity,
                        "plural": plural,
                        "base_path": f"/api/{plural}",
                        "method": method,
                        "trigger_path": path
                    }

        return None

    def expand_contract(self, delta: Dict[str, Any]) -> bool:
        """
        Expand contracts.md with the new delta.
        Returns check result: Success=True.
        """
        entity = delta["entity"]
        base_path = delta["base_path"]
        method = delta["method"]
        
        # 1. Validate
        if not self._validate_expansion(delta):
            return False
            
        # 2. Append
        log("EXPAND", f"📝 Appending to contracts.md: {entity} {base_path} [{method}]")
        
        new_block = f"""

## {entity}

Base path: {base_path}

Methods:
- {method}
"""
        with open(self.contracts_path, "a", encoding="utf-8") as f:
            f.write(new_block)
            
        return True

    def _validate_expansion(self, delta: Dict[str, Any]) -> bool:
        """
        Validate safeguards.
        ❌ Duplicate base path
        ❌ Non-RESTful path (simple check)
        """
        # Retrieve existing again
        known_routes = self.parser._parse_contracts_md()
        
        # Check duplicate base path
        for r in known_routes:
            if r.path == delta["base_path"]:
                log("EXPAND", f"❌ Validation Failed: Base path {delta['base_path']} already exists.")
                return False
                
        # Check RESTful structure (/api/something)
        if not delta["base_path"].startswith("/api/"):
            log("EXPAND", f"❌ Validation Failed: Path {delta['base_path']} must start with /api/")
            return False
            
        return True

    async def regenerate_backend_for_new_entity(self, delta: Dict[str, Any], manager: Any, project_id: str):
        """
        Regenerate backend components for the new entity.
        Triggered after contract expansion.
        """
        from app.orchestration.self_healing_manager import SelfHealingManager
        
        # We need to ensure models.py and routers are updated.
        # Since this is a NEW entity, we likely need to generate the router and update models.
        
        # But wait, SelfHealingManager focuses on the *primary* entity usually.
        # We might need to trick it or explicitly tell it to generate for THIS entity.
        
        # Actually, self_healing_manager._derek_generate_backend takes entity_name/model_name args!
        # It's flexible!
        
        healer = SelfHealingManager(self.project_path, project_id=project_id)
        
        log("EXPAND", f"🔄 Regenerating backend for new entity: {delta['entity']}")
        
        # Regenerate router/model for this specific entity
        # Note: healing usually generates the 'vertical'.
        # We need to make sure we don't overwrite existing unconnected code?
        # Derek prompt in healing asks for "COMPLETE backend code for {model_name}".
        # This seems safe as it targets the specific vertical.
        
        # We need to calculate tokens.
        tokens = 25000 # Standard amount
        
        success = await healer._derek_generate_backend(
            entity_name=delta["entity"].lower(),
            model_name=delta["entity"],
            entity_plural=delta["plural"],
            max_tokens=tokens,
            temperature=0.1,
            test_context="Implementing new entity from contract expansion."
        )
        
        if success:
            log("EXPAND", "✅ Backend regeneration successful")
        else:
            log("EXPAND", "❌ Backend regeneration failed")
            
        return success
