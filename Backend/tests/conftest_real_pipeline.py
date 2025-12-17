# tests/conftest_real_pipeline.py
"""
Pytest configurations specifically for real pipeline integration tests.

This file applies patches BEFORE any app modules are imported.
Import this at the top of test_real_pipeline_integration.py.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
from typing import Any, Dict


# Add backend to path first
_backend_dir = Path(__file__).parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))


class MockWorkflowStateManager:
    """In-memory state manager that replaces the Beanie-backed one."""
    
    _intents: Dict[str, Dict] = {}
    _sessions: Dict[str, Any] = {}
    
    @classmethod
    async def get_intent(cls, project_id: str) -> Dict:
        return cls._intents.get(project_id, {})
    
    @classmethod
    async def set_intent(cls, project_id: str, intent: Dict) -> None:
        cls._intents[project_id] = intent
    
    @classmethod
    async def get_session(cls, project_id: str) -> Any:
        return cls._sessions.get(project_id)
    
    @classmethod
    async def create_session(cls, project_id: str, **kwargs) -> Any:
        session = MagicMock()
        session.project_id = project_id
        session.intent = kwargs
        cls._sessions[project_id] = session
        return session
    
    @classmethod
    def clear(cls):
        """Reset state between tests."""
        cls._intents = {}
        cls._sessions = {}


# Apply critical patches BEFORE importing any app modules
_module_patches = [
    patch("app.orchestration.state.WorkflowStateManager", MockWorkflowStateManager),
    patch("app.utils.entity_classification.classify_project_entities", return_value={"Task": "AGGREGATE"}),
    patch("app.arbormind.metrics_collector.get_successful_classification_examples", return_value=[]),
    patch("app.arbormind.metrics_collector.get_classification_accuracy_stats", return_value={"total": 0, "accuracy": 0}),
    patch("app.arbormind.metrics_collector.store_classification_decision", return_value=None),
]

# Start all patches at module load time
for _p in _module_patches:
    _p.start()

print("[conftest_real_pipeline] Patches applied for mocking MongoDB/Beanie")
