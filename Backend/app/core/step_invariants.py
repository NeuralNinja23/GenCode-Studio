# app/core/step_invariants.py
"""
Unified Step Invariants - Hard Requirements for Step Success

These are NON-NEGOTIABLE conditions for a step to be considered successful.
If any invariant fails, the step MUST fail - no exceptions.

ArborMind correctly exposed these failures by removing masking.
This module enforces the invariants that were previously bypassed.
"""
from typing import Dict, List, Any, Optional
from pathlib import Path
from app.core.logging import log


class StepInvariantError(Exception):
    """Raised when a step invariant is violated."""
    pass


class StepInvariants:
    """
    Unified invariant checker for all workflow steps.
    
    Usage:
        StepInvariants.require_files(parsed, step_name, min_files=1)
        StepInvariants.require_approval(result, step_name)
    """
    
    @staticmethod
    def require_files(
        parsed: Dict[str, Any],
        step_name: str,
        min_files: int = 1,
        required_patterns: Optional[List[str]] = None,
    ) -> int:
        """
        INVARIANT: Step must produce at least min_files files.
        
        Args:
            parsed: The parsed LLM output containing "files" list
            step_name: Name of current step for logging
            min_files: Minimum number of files required (default: 1)
            required_patterns: Optional list of path patterns that MUST be present
            
        Returns:
            Number of files if valid
            
        Raises:
            StepInvariantError if invariant violated
        """
        files = parsed.get("files", [])
        file_count = len(files)
        
        if file_count < min_files:
            error_msg = f"{step_name} invariant violated: Expected at least {min_files} files, got {file_count}"
            log(step_name, f"❌ INVARIANT VIOLATION: {error_msg}")
            raise StepInvariantError(error_msg)
        
        # Check required patterns if specified
        if required_patterns:
            file_paths = [f.get("path", "") for f in files]
            for pattern in required_patterns:
                if not any(pattern in p for p in file_paths):
                    error_msg = f"{step_name} invariant violated: Missing required file pattern '{pattern}'"
                    log(step_name, f"❌ INVARIANT VIOLATION: {error_msg}")
                    raise StepInvariantError(error_msg)
        
        return file_count
    
    @staticmethod
    def require_complete(
        parsed: Dict[str, Any],
        step_name: str,
    ) -> bool:
        """
        INVARIANT: Output must be complete (HDAP - all files have END_FILE).
        
        Args:
            parsed: The parsed HDAP output with "complete" and "incomplete_files"
            step_name: Name of current step for logging
            
        Returns:
            True if complete
            
        Raises:
            StepInvariantError if output was truncated
        """
        is_complete = parsed.get("complete", True)  # Default True for legacy
        incomplete_files = parsed.get("incomplete_files", [])
        
        if not is_complete and incomplete_files:
            error_msg = f"{step_name} invariant violated: Output truncated. Incomplete files: {', '.join(incomplete_files)}"
            log(step_name, f"❌ INVARIANT VIOLATION: {error_msg}")
            raise StepInvariantError(error_msg)
        
        return True
    
    @staticmethod
    def require_non_empty_content(
        parsed: Dict[str, Any],
        step_name: str,
    ) -> bool:
        """
        INVARIANT: All files must have non-empty content.
        
        Raises:
            StepInvariantError if any file has empty content
        """
        files = parsed.get("files", [])
        
        for f in files:
            path = f.get("path", "unknown")
            content = f.get("content", "")
            
            if not content or not content.strip():
                error_msg = f"{step_name} invariant violated: File '{path}' has empty content"
                log(step_name, f"❌ INVARIANT VIOLATION: {error_msg}")
                raise StepInvariantError(error_msg)
        
        return True
    
    @staticmethod
    def require_approval_with_files(
        result: Dict[str, Any],
        parsed: Dict[str, Any],
        step_name: str,
    ) -> bool:
        """
        INVARIANT: Approval is only valid if files were actually produced.
        
        This prevents the "approved with 0 files" bug.
        
        Raises:
            StepInvariantError if approved but no files
        """
        approved = result.get("approved", False)
        files = parsed.get("files", [])
        
        if approved and len(files) == 0:
            error_msg = f"{step_name} invariant violated: Marked 'approved' but produced 0 files"
            log(step_name, f"❌ INVARIANT VIOLATION: {error_msg}")
            raise StepInvariantError(error_msg)
        
        return True
    
    @staticmethod
    def require_router_files(
        project_path: Path,
        min_routers: int = 1,
    ) -> List[str]:
        """
        INVARIANT: Project must have at least min_routers router files.
        
        Used by system_integration to verify backend is ready.
        
        Returns:
            List of router file paths found
            
        Raises:
            StepInvariantError if insufficient routers
        """
        routers_dir = project_path / "backend" / "app" / "routers"
        
        if not routers_dir.exists():
            raise StepInvariantError(
                f"Router directory does not exist: {routers_dir}"
            )
        
        router_files = [
            f.name for f in routers_dir.glob("*.py")
            if f.name != "__init__.py"
        ]
        
        if len(router_files) < min_routers:
            raise StepInvariantError(
                f"Insufficient router files: found {len(router_files)}, need {min_routers}"
            )
        
        return router_files
    
    @staticmethod
    def require_architecture(project_path: Path) -> str:
        """
        INVARIANT: architecture.md must exist.
        
        Returns:
            Contents of architecture.md
            
        Raises:
            StepInvariantError if missing
        """
        arch_path = project_path / "architecture.md"
        
        if not arch_path.exists():
            raise StepInvariantError("architecture.md does not exist")
        
        content = arch_path.read_text(encoding="utf-8")
        
        if len(content.strip()) < 100:
            raise StepInvariantError(
                f"architecture.md is too short ({len(content)} chars) - likely truncated"
            )
        
        return content
    
    @staticmethod
    def require_testids(
        parsed: Dict[str, Any],
        step_name: str,
        required_ids: List[str],
        primary_entity: str = "",
    ) -> bool:
        """
        INVARIANT: JSX files must contain required data-testid attributes.
        
        This is a PREFLIGHT CHECK that runs BEFORE Marcus review.
        Missing testids are caught immediately without wasting LLM tokens.
        
        Args:
            parsed: The parsed LLM output containing "files" list
            step_name: Name of current step for logging
            required_ids: List of required testid patterns (may contain {entity} placeholder)
            primary_entity: Primary entity name for placeholder substitution
            
        Returns:
            True if all required testids are found
            
        Raises:
            StepInvariantError if any required testid is missing
        """
        files = parsed.get("files", [])
        
        # Substitute {entity} placeholder in required_ids
        expanded_ids = []
        for tid in required_ids:
            if "{entity}" in tid:
                expanded_ids.append(tid.replace("{entity}", primary_entity))
            else:
                expanded_ids.append(tid)
        
        # Collect all JSX content
        jsx_content = ""
        jsx_files = []
        for f in files:
            path = f.get("path", "")
            if path.endswith(".jsx") or path.endswith(".tsx"):
                jsx_files.append(path)
                jsx_content += f.get("content", "") + "\n"
        
        if not jsx_files:
            # No JSX files to check
            return True
        
        # Check for missing testids
        missing = []
        for tid in expanded_ids:
            # Check for both exact string and potential variations
            if f'data-testid="{tid}"' not in jsx_content and f"data-testid='{tid}'" not in jsx_content:
                missing.append(tid)
        
        if missing:
            error_msg = f"{step_name} invariant violated: Missing required data-testid(s): {missing}"
            log(step_name, f"❌ INVARIANT VIOLATION: {error_msg}")
            log(step_name, f"   JSX files checked: {jsx_files}")
            raise StepInvariantError(error_msg)
        
        log(step_name, f"✅ All {len(expanded_ids)} required testids found in {len(jsx_files)} JSX files")
        return True


# Convenience function for step handlers
def validate_step_output(
    result: Dict[str, Any],
    parsed: Dict[str, Any],
    step_name: str,
    min_files: int = 1,
) -> int:
    """
    One-call validation for most step handlers.
    
    Checks:
    1. HDAP completeness (no truncated files)
    2. Minimum file count
    3. No empty files
    4. Approval only valid with files
    
    Returns:
        Number of files
        
    Raises:
        StepInvariantError on any violation
    """
    # Check HDAP completeness first (catch truncation early)
    StepInvariants.require_complete(parsed, step_name)
    
    file_count = StepInvariants.require_files(parsed, step_name, min_files)
    StepInvariants.require_non_empty_content(parsed, step_name)
    StepInvariants.require_approval_with_files(result, parsed, step_name)
    
    return file_count
