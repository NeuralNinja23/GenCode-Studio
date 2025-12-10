# app/workflow/engine_v2/critical_step_barriers.py
"""
Hard Barriers: Prevent FAST from Continuing if Critical Steps Fail

A step cannot continue if it is critical and its artifacts fail validation.
This prevents cascade failures like:
  - Router fails → Main succeeds with broken import → Tests fail
"""
from typing import Callable, Optional

from .artifact_contracts import ArtifactContractsRegistry


class CriticalStepBarriers:
    """
    Implements blocking rules for FAST v2.
    A step cannot continue if it is critical and its artifacts fail validation.
    """
    
    def __init__(self, contracts_registry: ArtifactContractsRegistry, self_healer):
        self.contracts = contracts_registry
        self.self_healer = self_healer

    # ------------------------------------------------------------
    # Enforce contract before running dependent steps
    # ------------------------------------------------------------
    def enforce(self, file_reader: Callable[[str], Optional[str]], current_step: str) -> bool:
        """
        Returns True if allowed to continue.
        Otherwise triggers self-repair and revalidates.
        """

        validation = self.contracts.validate(file_reader)

        for name, ok in validation.items():
            # Ignore non-critical artifacts
            contract = self.contracts.contracts[name]
            if not contract.is_critical:
                continue

            # If missing → block
            if not ok:
                print(f"[CRITICAL BARRIER] Artifact '{name}' failed validation. Initiating repair...")
                repaired = self.self_healer.repair(name)

                if not repaired:
                    print(f"[CRITICAL BARRIER] Repair FAILED for '{name}'. Cannot continue FAST pipeline.")
                    return False

                # After repair, revalidate
                validation = self.contracts.validate(file_reader)
                if not validation.get(name, False):
                    print(f"[CRITICAL BARRIER] Artifact '{name}' still invalid after repair.")
                    return False

        return True

    # ------------------------------------------------------------
    # Check single artifact
    # ------------------------------------------------------------
    def check_artifact(self, artifact_name: str, file_reader: Callable[[str], Optional[str]]) -> bool:
        """Check if a specific artifact passes validation."""
        validation = self.contracts.validate(file_reader)
        return validation.get(artifact_name, False)

    # ------------------------------------------------------------
    # Get failure details
    # ------------------------------------------------------------
    def get_all_failures(self, file_reader: Callable[[str], Optional[str]]) -> dict:
        """Get detailed failure information for all artifacts."""
        return self.contracts.get_failures(file_reader)
