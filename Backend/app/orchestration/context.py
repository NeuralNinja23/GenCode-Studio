# app/orchestration/context.py
"""
Context selection for agents - only provide relevant files per step.
Reduces token usage and improves LLM output quality.
"""
from pathlib import Path
from typing import List, Dict, Any, Optional
import glob

from app.core.logging import log

# Centralized entity discovery for dynamic fallback
from app.utils.entity_discovery import discover_primary_entity


# Define which files are relevant for each step
# Define which files are relevant for each step
STEP_CONTEXT_RULES = {
    "ARCHITECTURE": {
        "include": [],  # Only architecture.md (which doesn't exist yet)
        "max_files": 0,
    },
    "FRONTEND_MOCK": {
        "include": ["architecture.md"],
        "max_files": 1,
    },
    "SCREENSHOT_VERIFY": {
        "include": ["frontend/src/pages/*.jsx", "frontend/src/components/*.jsx"],
        "max_files": 5,
    },
    "CONTRACTS": {
        "include": [
            "frontend/src/data/mock.js",
            "frontend/src/pages/*.jsx",
        ],
        "max_files": 5,
    },
    "BACKEND_IMPLEMENTATION": {
        "include": ["contracts.md", "architecture.md", "backend/app/models.py", "backend/app/routers/*.py"],
        "max_files": 5,
    },
    "SYSTEM_INTEGRATION": {
        "include": ["backend/app/main.py", "backend/app/routers/*.py"],
        "max_files": 3,
    },
    "TESTING_BACKEND": {
        "include": [
            "contracts.md",
            "backend/app/routers/*.py",
            "backend/app/models.py",
            "backend/app/main.py",
            "backend/tests/*.py",
        ],
        "max_files": 5,
    },
    "FRONTEND_INTEGRATION": {
        "include": [
            "contracts.md",
            "frontend/src/lib/api.js",
            "frontend/src/pages/*.jsx",
            "frontend/src/data/mock.js",
        ],
        "max_files": 6,
    },
    "TESTING_FRONTEND": {
        "include": [
            "frontend/src/pages/*.jsx",
            "frontend/src/components/*.jsx",
            "frontend/tests/*.spec.js",
        ],
        "max_files": 8,
    },
}


def get_relevant_files(
    project_path: Path,
    step_name: str,
    max_content_size: int = 50000,  # Max total characters
) -> str:
    """
    Get only the files relevant to the current step.
    Returns a formatted string of file contents.
    """
    rules = STEP_CONTEXT_RULES.get(step_name, {"include": [], "max_files": 5})
    include_patterns = rules.get("include", [])
    max_files = rules.get("max_files", 5)
    
    if not include_patterns:
        log("CONTEXT", f"No context rules for step {step_name}, returning empty")
        return ""
    
    files_content = []
    total_size = 0
    files_added = 0
    
    for pattern in include_patterns:
        # Handle glob patterns
        if "*" in pattern:
            matches = list(project_path.glob(pattern))
        else:
            file_path = project_path / pattern
            matches = [file_path] if file_path.exists() else []
        
        for file_path in matches:
            if files_added >= max_files:
                break
            
            if not file_path.is_file():
                continue
            
            try:
                content = file_path.read_text(encoding="utf-8")
                
                # Check size limit
                if total_size + len(content) > max_content_size:
                    # Truncate this file
                    remaining = max_content_size - total_size
                    if remaining > 500:  # Only include if meaningful size left
                        content = content[:remaining] + "\n... (truncated)"
                    else:
                        continue
                
                relative_path = file_path.relative_to(project_path)
                files_content.append(f"=== {relative_path} ===\n{content}")
                total_size += len(content)
                files_added += 1
                
            except Exception as e:
                log("CONTEXT", f"Could not read {file_path}: {e}")
                continue
    
    if files_content:
        log("CONTEXT", f"Selected {files_added} files ({total_size} chars) for {step_name}")
        return "\n\n".join(files_content)
    
    log("CONTEXT", f"No matching files found for {step_name}")
    return ""


def get_entity_context(project_id: str, user_request: str = "", project_path: Path = None) -> str:
    """
    Get entity-specific context for agents.
    Tells them what the primary entity is and where to find/create related files.
    """
    from app.orchestration.state import WorkflowStateManager
    
    intent = WorkflowStateManager.get_intent(project_id) or {}
    entities = intent.get("entities", [])
    
    # Use centralized discovery as fallback instead of hardcoded "item"
    if entities:
        primary_entity = entities[0]
    elif project_path:
        entity_name, _ = discover_primary_entity(project_path)
        primary_entity = entity_name if entity_name else "item"  # Last resort
    else:
        primary_entity = "item"  # No project path available
    
    # Smart pluralization
    if primary_entity.endswith("s"):
        primary_entity_plural = primary_entity
        primary_entity_singular = primary_entity[:-1]
    else:
        primary_entity_singular = primary_entity
        primary_entity_plural = primary_entity + "s"
    
    primary_entity_capitalized = primary_entity_singular.capitalize()
    
    return f"""
═══════════════════════════════════════════════════════
PROJECT ENTITY CONTEXT
═══════════════════════════════════════════════════════

PRIMARY ENTITY: {primary_entity_singular}

File Locations:
- Model: backend/app/models.py (class {primary_entity_capitalized})
- Router: backend/app/routers/{primary_entity_plural}.py
- Frontend Page: frontend/src/pages/{primary_entity_capitalized}sPage.jsx
- Frontend Card: frontend/src/components/{primary_entity_capitalized}Card.jsx

API Endpoints (per contracts.md):
- GET /api/{primary_entity_plural}
- POST /api/{primary_entity_plural}
- GET /api/{primary_entity_plural}/{{id}}
- PUT /api/{primary_entity_plural}/{{id}}
- DELETE /api/{primary_entity_plural}/{{id}}

⚠️ IMPORTANT:
- Focus on {primary_entity_singular} entity
- Do NOT create other entities (users, products, etc.) unless explicitly in the request
- Use the exact paths shown above
"""


def get_previous_files_summary(project_path: Path, max_files: int = 10) -> str:
    """
    Get a brief summary of what files exist in the project.
    Useful for agents to understand what's already been created.
    """
    summary = []
    
    # Key directories to summarize
    dirs_to_check = [
        ("frontend/src/pages", "Frontend Pages"),
        ("frontend/src/components", "Frontend Components"),
        ("backend/app/routers", "Backend Routers"),
        ("backend/app", "Backend Core"),
    ]
    
    for dir_path, label in dirs_to_check:
        full_path = project_path / dir_path
        if full_path.exists():
            files = [f.name for f in full_path.iterdir() if f.is_file()]
            if files:
                summary.append(f"{label}: {', '.join(files[:5])}")
    
    if summary:
        return "Existing Files:\n" + "\n".join(summary)
    
    return ""


# ════════════════════════════════════════════════════════════════════
# V2: CROSS-STEP CONTEXT MANAGER
# ════════════════════════════════════════════════════════════════════

class CrossStepContext:
    """
    V2 Feature: Maintains context summaries across workflow steps.
    
    This helps later steps understand what earlier steps produced,
    reducing errors and improving coherence.
    
    Usage:
        ctx = CrossStepContext(project_id)
        ctx.record_step_completion("backend_models", {"entity": "product", "fields": ["name", "price"]})
        
        # Later step can get summary:
        summary = ctx.get_summary_for_step("backend_routers")
    """
    
    # Class-level storage (persists across calls for same project)
    _contexts: Dict[str, Dict[str, Any]] = {}
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        if project_id not in self._contexts:
            self._contexts[project_id] = {
                "completed_steps": [],
                "step_summaries": {},
                "entities": [],
                "architecture": "",
            }
    
    @property
    def _ctx(self) -> Dict[str, Any]:
        return self._contexts[self.project_id]
    
    def record_step_completion(self, step: str, summary: Dict[str, Any] = None):
        """Record that a step completed with optional summary data."""
        if step not in self._ctx["completed_steps"]:
            self._ctx["completed_steps"].append(step)
        if summary:
            self._ctx["step_summaries"][step] = summary
    
    def set_entities(self, entities: List[str]):
        """Set the primary entities from analysis step."""
        self._ctx["entities"] = entities
    
    def set_architecture(self, arch_summary: str):
        """Set architecture summary from architecture step."""
        self._ctx["architecture"] = arch_summary
    
    def get_summary_for_step(self, current_step: str) -> str:
        """
        Get a context summary tailored for the current step.
        
        Returns a formatted string with relevant context from previous steps.
        """
        lines = []
        
        # Always include entities
        if self._ctx["entities"]:
            lines.append(f"ENTITIES: {', '.join(self._ctx['entities'])}")
        
        # Include architecture summary for backend steps
        if current_step in ["backend_implementation", "system_integration"]:
            if self._ctx["architecture"]:
                lines.append(f"ARCHITECTURE: {self._ctx['architecture'][:200]}...")
        
        # Include relevant previous step summaries
        summaries = self._ctx["step_summaries"]
        
        # Step-specific context
        if current_step == "frontend_integration":
            if "backend_implementation" in summaries:
                lines.append(f"BACKEND VERTICAL: {summaries['backend_implementation']}")
            if "contracts" in summaries:
                lines.append(f"CONTRACTS: {summaries['contracts']}")
        
        if current_step in ["testing_backend", "testing_frontend"]:
            lines.append(f"COMPLETED STEPS: {', '.join(self._ctx['completed_steps'])}")
        
        if lines:
            return "═══ PREVIOUS STEP CONTEXT ═══\n" + "\n".join(lines) + "\n═══════════════════════════\n"
        
        return ""
    
    def get_completed_steps(self) -> List[str]:
        """Get list of completed steps."""
        return self._ctx["completed_steps"].copy()
    
    def reset(self):
        """Reset context for a new workflow run."""
        self._contexts[self.project_id] = {
            "completed_steps": [],
            "step_summaries": {},
            "entities": [],
            "architecture": "",
        }
    
    @classmethod
    def get_or_create(cls, project_id: str) -> "CrossStepContext":
        """Factory method to get or create context for a project."""
        return cls(project_id)

