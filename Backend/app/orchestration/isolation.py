# app/orchestration/isolation.py
"""
Isolation manager with runtime enforcement.

CRITICAL: Isolated = dead branch (cannot be used downstream).

Phase 3: Implements step isolation and artifact quarantine.
When a step ends in ENVIRONMENT_FAILURE, it is isolated and its outputs
are quarantined to prevent contamination.
"""
import shutil
from typing import Set, Dict, List, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class IsolationViolation(Exception):
    """
    Raised when code tries to use quarantined artifacts.
    
    This is a hard error - isolated steps are dead branches and their
    outputs must not be consumed by downstream steps.
    """
    pass


class IsolationManager:
    """
    Enforces isolation semantics for steps that encounter ENVIRONMENT_FAILURE.
    
    Phase 8: Adds PHYSICAL QUARANTINE (I/O Enforcement).
    Artifacts from isolated steps are moved to a hidden directory to strictly
    prevent downstream steps from "accidentally" consuming them.
    """
    
    # Map of steps to their potential artifacts (relative to project root)
    # This list allows us to infer artifacts even if the step result doesn't explicitly list them.
    STEP_ARTIFACTS_MAP = {
        "testing_frontend": [
            "frontend/playwright-report",
            "frontend/test-results",
            "frontend/e2e-report.json"
        ],
        "testing_backend": [
            "backend/htmlcov",
            "backend/.coverage",
            "backend/test-reports"
        ],
        "backend_implementation": [
            # Be careful not to quarantine source code unless we are sure.
            # Usually we don't quarantine source code, just execution artifacts.
        ],
        "frontend_integration": [
            "frontend/integration_report.json"
        ]
    }
    
    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.isolated_steps: Set[str] = set()
        self.quarantined_artifacts: Dict[str, List[Path]] = {}
        self.isolation_reasons: Dict[str, str] = {}
        
        # Ensure quarantine root exists
        self.quarantine_root = self.project_path / ".gencode" / "quarantine"
        if not self.quarantine_root.exists():
            self.quarantine_root.mkdir(parents=True, exist_ok=True)
    
    def isolate_step(
        self,
        step_name: str,
        artifacts: List[Path],
        reason: str
    ) -> None:
        """
        Quarantine a step and its outputs.
        
        Phase 8 Enhancement:
        - Physically moves artifacts to .gencode/quarantine/<step_name>/
        - Ensures downstream tools CANNOT access them (I/O enforcement)
        
        Args:
            step_name: Name of the step to isolate
            artifacts: List of file paths produced by this step
            reason: Human-readable explanation
        """
        self.isolated_steps.add(step_name)
        self.isolation_reasons[step_name] = reason
        
        # 1. Identify all artifacts (Explicit + Inferred)
        all_artifacts = set()
        
        # Add explicit artifacts
        for art in artifacts:
            all_artifacts.add(Path(art))
            
        # Add inferred artifacts from map
        inferred = self.STEP_ARTIFACTS_MAP.get(step_name, [])
        for rel_path in inferred:
            full_path = self.project_path / rel_path
            all_artifacts.add(full_path)
            
        # 2. Physically move them to quarantine
        quarantine_dir = self.quarantine_root / step_name
        quarantine_dir.mkdir(parents=True, exist_ok=True)
        
        moved_artifacts = []
        
        for art_path in all_artifacts:
            if art_path.exists():
                try:
                    # Calculate destination path to preserve structure or just flatten?
                    # Flattening is simpler for quarantine storage.
                    dest_name = f"{art_path.name}"
                    dest_path = quarantine_dir / dest_name
                    
                    if art_path.is_dir():
                        if dest_path.exists():
                            shutil.rmtree(dest_path)
                        shutil.move(str(art_path), str(dest_path))
                    else:
                        shutil.move(str(art_path), str(dest_path))
                        
                    moved_artifacts.append(art_path)
                    logger.info(f"    moved artifact {art_path.name} -> {dest_path}")
                    
                except Exception as e:
                    logger.warning(f"Failed to move artifact {art_path}: {e}")
        
        # Store what we actually moved
        self.quarantined_artifacts[step_name] = moved_artifacts
        
        logger.warning(
            f"🔒 ISOLATED: {step_name}",
            extra={
                "step": step_name,
                "reason": reason,
                "artifacts_moved": len(moved_artifacts),
                "quarantine_location": str(quarantine_dir)
            }
        )
    
    def is_isolated(self, step_name: str) -> bool:
        """Check if a step has been isolated."""
        return step_name in self.isolated_steps
    
    def get_isolated_steps(self) -> List[str]:
        """Get list of all isolated steps."""
        return list(self.isolated_steps)
    
    def can_use_artifact(
        self,
        artifact_path: Path,
        requesting_step: str
    ) -> bool:
        """
        Check if an artifact is safe to use.
        
        Args:
            artifact_path: Path to artifact being accessed
            requesting_step: Name of step trying to access it
            
        Returns:
            True if artifact is safe to use
            
        Raises:
            IsolationViolation: If artifact is quarantined
        """
        # Normalize path for comparison
        artifact_path = Path(artifact_path).resolve()
        
        for step_name, artifacts in self.quarantined_artifacts.items():
            for quarantined in artifacts:
                quarantined = Path(quarantined).resolve()
                
                # Check if artifact is quarantined
                if artifact_path == quarantined or artifact_path in quarantined.parents:
                    raise IsolationViolation(
                        f"Step '{requesting_step}' cannot use quarantined "
                        f"artifact from isolated step '{step_name}': {artifact_path}\n"
                        f"Reason for isolation: {self.isolation_reasons.get(step_name, 'unknown')}"
                    )
        
        return True
    
    def depends_on_step(
        self,
        current_step: str,
        dependency_step: str
    ) -> None:
        """
        Check if a step can depend on another step.
        
        Args:
            current_step: Name of current step
            dependency_step: Name of step being depended on
            
        Raises:
            IsolationViolation: If dependency is isolated (dead branch)
        """
        if dependency_step in self.isolated_steps:
            raise IsolationViolation(
                f"Step '{current_step}' cannot depend on isolated step '{dependency_step}'\n"
                f"Reason: {self.isolation_reasons.get(dependency_step, 'unknown')}\n"
                f"Isolated steps are dead branches and cannot be used as dependencies."
            )
    
    def get_quarantine_report(self) -> Dict[str, any]:
        """
        Generate a quarantine report for debugging/logging.
        
        Returns:
            Dictionary with isolation statistics and details
        """
        return {
            "isolated_count": len(self.isolated_steps),
            "isolated_steps": list(self.isolated_steps),
            "quarantined_artifacts": {
                step: [str(a) for a in artifacts]
                for step, artifacts in self.quarantined_artifacts.items()
            },
            "reasons": self.isolation_reasons
        }
    
    def clear(self) -> None:
        """Clear all isolation data (for testing or workflow restart)."""
        self.isolated_steps.clear()
        self.quarantined_artifacts.clear()
        self.isolation_reasons.clear()
        logger.info("🔓 Isolation manager cleared")
