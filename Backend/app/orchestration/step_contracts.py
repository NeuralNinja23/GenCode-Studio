# app/workflow/engine_v2/step_contracts.py
"""
FAST v2 Step Contracts

Defines structural & semantic requirements for each FAST v2 step.
If a step violates its contract, self-healing is invoked.

Contracts enforced at:
- LLM output layer
- structural compiler layer
- file system layer
"""
from typing import Dict, List


class StepContracts:
    """
    Defines structural & semantic requirements for each FAST v2 step.
    If a step violates its contract, self-healing is invoked.
    """

    CONTRACTS: Dict[str, Dict] = {
        "analysis": {
            "must_contain": ["domain", "goal", "features"],
            "files_required": []
        },
        "architecture": {
            "must_contain": ["architecture", "components"],
            "files_required": ["architecture.md"]
        },
        "frontend_mock": {
            "must_contain": [],
            "files_required": [
                "frontend/src/pages/",
                "frontend/src/components/",
                "frontend/src/data/"
            ]
        },
        "backend_implementation": {
            "must_contain": ["Document", "class", "router", "async def"],
            "files_required": [
                "backend/app/models.py",
                "backend/app/routers/"
            ]
        },
        "contracts": {
            "must_contain": ["endpoint", "API"],
            "files_required": ["contracts.md"]
        },
        "system_integration": {
            "must_contain": ["FastAPI", "include_router"],
            "files_required": ["backend/app/main.py"]
        },
        "frontend_integration": {
            "must_contain": ["export", "fetch"],
            "files_required": [
                "frontend/src/lib/api.js",
                "frontend/src/pages/"
            ]
        },
        "screenshot_verify": {
            "must_contain": [],
            "files_required": []  # Visual QA may not produce files
        },
        "testing_backend": {
            "must_contain": ["pytest", "test_"],
            "files_required": []
        },
        "testing_frontend": {
            "must_contain": ["test", "expect"],
            "files_required": []
        },
        "preview_final": {
            "must_contain": [],
            "files_required": []
        }
    }

    def requires_files(self, step: str) -> List[str]:
        """Get required file paths/directories for a step."""
        return self.CONTRACTS.get(step, {}).get("files_required", [])

    def requires_content(self, step: str) -> List[str]:
        """Get required content patterns for a step."""
        return self.CONTRACTS.get(step, {}).get("must_contain", [])

    def check_content(self, step: str, text: str) -> bool:
        """Check if text contains all required patterns for a step."""
        for phrase in self.requires_content(step):
            if phrase.lower() not in text.lower():
                return False
        return True

    def get_missing_content(self, step: str, text: str) -> List[str]:
        """Get list of missing content patterns."""
        missing = []
        for phrase in self.requires_content(step):
            if phrase.lower() not in text.lower():
                missing.append(phrase)
        return missing
