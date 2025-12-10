# app/workflow/engine_v2/artifact_contracts.py
"""
Defines Required Artifacts + Validation Rules for FAST v2

This module defines the structural requirements for backend/frontend components.
FAST v2 uses this to verify a project before moving to testing.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
import re


@dataclass
class ArtifactContract:
    """
    Defines the structural requirements for backend/frontend components.
    FAST v2 uses this to verify a project before moving to testing.
    """
    name: str
    required_paths: List[str]
    required_patterns: Dict[str, str] = field(default_factory=dict)
    is_critical: bool = True


class ArtifactContractsRegistry:
    """
    Contains all project-level contracts.
    FAST v2 checks these BEFORE running tests or docker build.
    """
    
    def __init__(self):
        self.contracts: Dict[str, ArtifactContract] = {}

    # ------------------------------------------------------------
    # Register new artifact contract
    # ------------------------------------------------------------
    def register(self, contract: ArtifactContract):
        self.contracts[contract.name] = contract

    # ------------------------------------------------------------
    # Validate artifacts exist + meet patterns
    # ------------------------------------------------------------
    def validate(self, file_reader: Callable[[str], Optional[str]]) -> Dict[str, bool]:
        """
        file_reader(path) -> returns file contents or None
        """
        results = {}

        for name, contract in self.contracts.items():
            contract_ok = True

            for path in contract.required_paths:
                contents = file_reader(path)
                if contents is None:
                    contract_ok = False
                    break

                # Check required patterns
                for label, pattern in contract.required_patterns.items():
                    if re.search(pattern, contents) is None:
                        contract_ok = False
                        break
                
                if not contract_ok:
                    break

            results[name] = contract_ok

        return results

    def get_failures(self, file_reader: Callable[[str], Optional[str]]) -> Dict[str, List[str]]:
        """Get detailed failure information for each contract."""
        failures = {}

        for name, contract in self.contracts.items():
            issues = []

            for path in contract.required_paths:
                contents = file_reader(path)
                if contents is None:
                    issues.append(f"Missing file: {path}")
                    continue

                # Check required patterns
                for label, pattern in contract.required_patterns.items():
                    if re.search(pattern, contents) is None:
                        issues.append(f"Missing pattern '{label}' in {path}")

            if issues:
                failures[name] = issues

        return failures


# ------------------------------------------------------------
# DEFAULT CONTRACT SET FOR BACKEND + FRONTEND (STATIC)
# Only used when no project path is available
# ------------------------------------------------------------
def default_contracts() -> ArtifactContractsRegistry:
    """
    Creates default contracts with flexible patterns.
    NOTE: For dynamic contracts that discover actual files, use dynamic_contracts().
    """
    registry = ArtifactContractsRegistry()
    
    # Backend router contract - FLEXIBLE patterns (not tied to specific entity)
    registry.register(ArtifactContract(
        name="backend_router",
        required_paths=[],  # Will be populated dynamically
        required_patterns={
            # Flexible patterns that match any CRUD router
            "crud_endpoint": r"@router\.(get|post|put|patch|delete)\s*\(",
            "async_handler": r"async\s+def\s+\w+",
        },
        is_critical=True
    ))

    # Backend main app contract
    registry.register(ArtifactContract(
        name="backend_main",
        required_paths=["backend/app/main.py"],
        required_patterns={
            "include_router": r"include_router",
            "lifespan_or_startup": r"(@app\.on_event|lifespan|@asynccontextmanager)",
        },
        is_critical=True
    ))

    # Frontend API client contract
    registry.register(ArtifactContract(
        name="frontend_api",
        required_paths=["frontend/src/lib/api.js"],
        required_patterns={
            "getAll": r"export\s+(async\s+)?function\s+get",
            "create": r"export\s+(async\s+)?function\s+create",
            "update": r"export\s+(async\s+)?function\s+update",
            "delete": r"export\s+(async\s+)?function\s+delete",
        },
        is_critical=True
    ))

    # Backend models contract
    registry.register(ArtifactContract(
        name="backend_models",
        required_paths=["backend/app/models.py"],
        required_patterns={
            "document_class": r"class\s+\w+\(Document\)",
        },
        is_critical=True
    ))

    # Backend database contract - FLEXIBLE pattern for init function
    registry.register(ArtifactContract(
        name="backend_database",
        required_paths=["backend/app/database.py"],
        required_patterns={
            "mongo_client": r"(AsyncIOMotorClient|motor)",
            "init_function": r"async\s+def\s+(init_|initiate_|setup_|connect_)\w+\s*\(",
        },
        is_critical=False  # Not as critical, has defaults
    ))

    return registry


# ------------------------------------------------------------
# DYNAMIC CONTRACT SET - DISCOVERS ACTUAL FILES FROM WORKSPACE
# ------------------------------------------------------------
def dynamic_contracts(project_path) -> ArtifactContractsRegistry:
    """
    Creates contracts based on actual files discovered in the workspace.
    
    This is the preferred method - it reads what the LLM actually generated
    instead of assuming hardcoded file names like notes.py.
    
    Args:
        project_path: Path to the project workspace
    """
    from pathlib import Path
    
    registry = ArtifactContractsRegistry()
    project_path = Path(project_path)
    
    # DYNAMIC: Discover actual router files
    routers_dir = project_path / "backend" / "app" / "routers"
    router_files = []
    
    if routers_dir.exists():
        for f in routers_dir.glob("*.py"):
            if f.stem != "__init__":
                router_files.append(f"backend/app/routers/{f.name}")
    
    # Backend router contract - uses discovered files
    if router_files:
        registry.register(ArtifactContract(
            name="backend_router",
            required_paths=router_files,  # DYNAMIC!
            required_patterns={
                # Flexible patterns that match any CRUD router
                "crud_endpoint": r"@router\.(get|post|put|patch|delete)\s*\(",
                "async_handler": r"async\s+def\s+\w+",
            },
            is_critical=True
        ))
    else:
        # No routers found yet - use placeholder
        registry.register(ArtifactContract(
            name="backend_router",
            required_paths=[],
            required_patterns={},
            is_critical=False  # Can't enforce if no routers exist
        ))

    # Backend main app contract
    registry.register(ArtifactContract(
        name="backend_main",
        required_paths=["backend/app/main.py"],
        required_patterns={
            "include_router": r"include_router",
            "lifespan_or_startup": r"(@app\.on_event|lifespan|@asynccontextmanager)",
        },
        is_critical=True
    ))

    # Frontend API client contract
    registry.register(ArtifactContract(
        name="frontend_api",
        required_paths=["frontend/src/lib/api.js"],
        required_patterns={
            "fetch_usage": r"(fetch|axios|api)",
            "export_function": r"export\s+(async\s+)?function",
        },
        is_critical=True
    ))

    # Backend models contract
    registry.register(ArtifactContract(
        name="backend_models",
        required_paths=["backend/app/models.py"],
        required_patterns={
            "document_class": r"class\s+\w+\(Document\)",
        },
        is_critical=True
    ))

    # Backend database contract - FLEXIBLE pattern
    registry.register(ArtifactContract(
        name="backend_database",
        required_paths=["backend/app/database.py"],
        required_patterns={
            "mongo_client": r"(AsyncIOMotorClient|motor)",
            "init_function": r"async\s+def\s+\w+\s*\(",  # Any async function
        },
        is_critical=False
    ))

    return registry

