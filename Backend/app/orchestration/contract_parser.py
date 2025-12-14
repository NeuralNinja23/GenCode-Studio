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
        Extract expected routes from contracts and tests.
        
        Returns:
            List of RouteContract objects
        """
        routes = []
        
        # Always expect health endpoint
        routes.append(RouteContract(
            method="GET",
            path="/api/health",
            expected_status=200,
            description="Health check endpoint"
        ))
        
        # Parse from contracts.md if it exists
        if self.contracts_file.exists():
            routes.extend(self._parse_contracts_md())
        
        # Parse from test_api.py if it exists
        if self.test_file.exists():
            routes.extend(self._parse_test_file())
        
        # Deduplicate by (method, path)
        seen = set()
        unique_routes = []
        for route in routes:
            key = (route.method, route.path)
            if key not in seen:
                seen.add(key)
                unique_routes.append(route)
        
        return unique_routes
    
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
        
        Uses entity discovery to find primary entity, then filters routes.
        """
        from app.utils.entity_discovery import discover_primary_entity, get_entity_plural
        
        entity_name, model_name = discover_primary_entity(self.project_path)
        if not entity_name:
            return []
        
        entity_plural = get_entity_plural(entity_name)
        
        all_routes = self.get_expected_routes()
        
        # Filter to routes containing the entity plural
        primary_routes = [
            route for route in all_routes 
            if entity_plural in route.path
        ]
        
        return primary_routes
