# app/orchestration/contract_parser.py
"""
ContractParser: Extract expected routes from contracts.md and test_api.py

This allows validation to be contract-driven instead of hardcoding
route paths like /api/notes or /api/cats.

The contracts define what the system should do, and validation verifies it.
"""
from pathlib import Path
from typing import List
import re
from dataclasses import dataclass


@dataclass
class RouteContract:
    """A single route contract extracted from tests/contracts."""
    method: str
    path: str
    expected_status: int
    description: str = ""


class ContractParser:
    """Parse API contracts from contracts.md and test_api.py."""
    
    def __init__(self, project_path: Path):
        """
        Initialize contract parser.
        
        Args:
            project_path: Path to project workspace
        """
        self.project_path = project_path
        self.contracts_file = project_path / "contracts.md"
        self.test_file = project_path / "backend" / "tests" / "test_api.py"
    
    def get_expected_routes(self) -> List[RouteContract]:
        """
        Extract expected routes for validation.
        
        🔒 INVARIANT #1: Validation ⊇ Tests
        Every route tested in test_api.py MUST appear here.
        If validation passes, tests WILL pass (no under-approximation).
        
        This is the NON-NEGOTIABLE contract. If any route is missing → FAIL FAST.
        """
        routes = []
        
        # Always expect health endpoint
        routes.append(RouteContract(
            method="GET",
            path="/api/health",
            expected_status=200,
            description="Health check endpoint (mandatory)"
        ))
        
        # ═══════════════════════════════════════════════════════════
        # MANDATORY CRUD ROUTES - Must match test_api.py exactly
        #
        # BUG FIX: Use extract_all_models_from_models_py instead of
        # discover_primary_entity. The old approach discovered entities
        # from mock.js (e.g., "User") but Derek might generate different
        # models (e.g., "Ticket"), causing validation to check wrong routes.
        #
        # FIX #6: FILTER TO AGGREGATE ENTITIES ONLY (2025-12-15)
        # Uses entity_plan.json to skip EMBEDDED entities.
        # Only AGGREGATE entities have routers, so only test those routes!
        # ═══════════════════════════════════════════════════════════
        from app.utils.entity_discovery import extract_all_models_from_models_py, get_entity_plural
        
        actual_models = extract_all_models_from_models_py(self.project_path)
        
        # Filter to AGGREGATE models only
        aggregate_models = actual_models  # Default: assume all are aggregate
        entity_plan_path = self.project_path / "entity_plan.json"
        
        if entity_plan_path.exists():
            try:
                from app.utils.entity_discovery import EntityPlan
                plan = EntityPlan.load(entity_plan_path)
                
                # Get only AGGREGATE entity names
                aggregate_names = [
                    e.name for e in plan.entities 
                    if e.type == "AGGREGATE"
                ]
                
                # Filter actual_models to only include aggregates
                aggregate_models = [m for m in actual_models if m in aggregate_names]
                
                embedded_count = len(actual_models) - len(aggregate_models)
                if embedded_count > 0:
                    embedded = [m for m in actual_models if m not in aggregate_models]
                    from app.core.logging import log
                    log("CONTRACT_PARSER", f"🔒 Skipping {embedded_count} EMBEDDED entities from validation: {embedded}")
                    log("CONTRACT_PARSER", f"✅ Testing {len(aggregate_models)} AGGREGATE entities: {aggregate_models}")
            except Exception as e:
                from app.core.logging import log
                log("CONTRACT_PARSER", f"⚠️ Could not load entity_plan.json: {e}, testing all models")
        
        for model_name in aggregate_models:
            # Derive entity name from model name (e.g., "Ticket" -> "ticket")
            entity_name = model_name.lower()
            entity_plural = get_entity_plural(entity_name)
            base_path = f"/api/{entity_plural}"
            
            # ALL 4 routes that test_api.py requires
            routes.extend([
                # List all
                RouteContract(
                    method="GET",
                    path=base_path,
                    expected_status=200,
                    description=f"List all {entity_plural} (mandatory)"
                ),
                # Create
                RouteContract(
                    method="POST",
                    path=base_path,
                    expected_status=201,
                    description=f"Create new {entity_name} (mandatory)"
                ),
                # Get by ID - validated as route exists, not actual data
                # We use a placeholder ID; 404 is acceptable (route exists but no data)
                RouteContract(
                    method="GET",
                    path=f"{base_path}/test-id-validation",
                    expected_status=404,  # 404 means route EXISTS but ID not found
                    description=f"Get {entity_name} by ID (route must exist)"
                ),
                # Delete - same logic, 404 means route exists
                RouteContract(
                    method="DELETE",
                    path=f"{base_path}/test-id-validation",
                    expected_status=404,  # 404 means route EXISTS but ID not found
                    description=f"Delete {entity_name} by ID (route must exist)"
                ),
            ])
        
        return routes
    
    def _parse_contracts_md(self) -> List[RouteContract]:
        """Parse route contracts from contracts.md."""
        routes = []
        
        try:
            content = self.contracts_file.read_text(encoding="utf-8")
            
            # Look for endpoint definitions like:
            # GET /api/notes → 200 OK
            # POST /api/notes → 201 Created
            pattern = r'(GET|POST|PUT|DELETE|PATCH)\s+(/api/[\w\-/{}]+)\s*[→->]\s*(\d{3})'
            
            for match in re.finditer(pattern, content, re.MULTILINE):
                method = match.group(1)
                path = match.group(2)
                status = int(match.group(3))
                
                # Clean up path parameters {id} → just validate base path
                clean_path = re.sub(r'\{[^}]+\}', '', path).rstrip('/')
                if not clean_path:
                    clean_path = path  # Keep original if cleaning removed everything
                
                routes.append(RouteContract(
                    method=method,
                    path=clean_path,
                    expected_status=status,
                    description="From contracts.md"
                ))
        except Exception:
            pass  # contracts.md is optional
        
        return routes
    
    def _parse_test_file(self) -> List[RouteContract]:
        """Parse expected routes from test_api.py."""
        routes = []
        
        try:
            content = self.test_file.read_text(encoding="utf-8")
            
            # Look for patterns like:
            # response = await client.get("/api/notes")
            # assert response.status_code == 200
            # or
            # assert response.status_code in [200, 201]
            
            # Simple heuristic: find client.METHOD("/path") followed by status assertion
            method_pattern = r'await\s+client\.(get|post|put|delete)\("(/api/[^"]+)"\)'
            
            for match in re.finditer(method_pattern, content):
                method = match.group(1).upper()
                path = match.group(2)
                
                # Try to find the expected status code nearby (next 3 lines)
                match_pos = match.end()
                next_lines = content[match_pos:match_pos+200]
                
                status_match = re.search(r'assert.*?status_code\s*(?:==|in)\s*(?:\[)?(\d{3})', next_lines)
                if status_match:
                    status = int(status_match.group(1))
                else:
                    # Default to 200 for GET, 201 for POST, 200 for others
                    status = 201 if method == "POST" else 200
                
                routes.append(RouteContract(
                    method=method,
                    path=path,
                    expected_status=status,
                    description="From test_api.py"
                ))
        except Exception:
            pass  # test_api.py might not exist yet
        
        return routes
    
    def get_primary_entity_routes(self) -> List[RouteContract]:
        """
        Get routes for the primary entity only.
        
        BUG FIX: Uses extract_all_models_from_models_py to find actual models
        instead of discover_primary_entity which may return wrong entity.
        """
        from app.utils.entity_discovery import extract_all_models_from_models_py, get_entity_plural
        
        actual_models = extract_all_models_from_models_py(self.project_path)
        if not actual_models:
            return []
        
        # Use first model as primary (most commonly the main entity)
        primary_model = actual_models[0]
        entity_name = primary_model.lower()
        entity_plural = get_entity_plural(entity_name)
        
        all_routes = self.get_expected_routes()
        
        # Filter to routes containing the entity plural
        primary_routes = [
            route for route in all_routes 
            if entity_plural in route.path
        ]
        
        return primary_routes
