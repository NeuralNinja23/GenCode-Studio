# app/orchestration/failure_classifier.py
"""
Strict failure classifier with explicit rules.

PHILOSOPHY: When in doubt, classify as COGNITIVE.
Over-healing is better than under-healing.

Part of Phase 2 - Failure Classification with Strict Rules
"""
import re
import platform
from typing import Dict, Any, Union, List
from app.core.step_outcome import StepOutcome


class FailureClassifier:
    """
    Classifies errors into outcomes.
    
    DECISION TREE:
    1. Check ALWAYS_COGNITIVE patterns → COGNITIVE_FAILURE
    2. Check HARD_FAILURE (invariants) → HARD_FAILURE
    3. Check ENVIRONMENT patterns + "could reasoning fix?" → maybe ENVIRONMENT
    4. Default → COGNITIVE_FAILURE (safe fallback)
    """
    
    # Exhaustive allow-list for ENVIRONMENT_FAILURE
    ENVIRONMENT_PATTERNS = [
        r"playwright.*executable not found",
        r"chromium.*not installed",
        r"cannot find module.*playwright",
        r"permission denied.*(?:root|admin)",
        r"port \d+ already in use",
        r"network unreachable",
        r"npm err! 404.*registry\.npmjs\.org",
        r"pypi.*connection timeout",
        r"out of memory",
        r"disk quota exceeded",
        r"enospc.*no space left",
    ]
    
    # Patterns that are NEVER environment failures
    ALWAYS_COGNITIVE = [
        r"syntaxerror",
        r"indentationerror",
        r"typeerror",
        r"attributeerror",
        r"importerror: cannot import name",
        r"404.*localhost",
        r"422.*validation",
        r"500.*internal server error",
        r"modulenotfounderror.*app\.",  # Our own missing modules
        r"nameerror",
        r"valueerror",
    ]
    
    # Hard failure patterns (invariant violations - GLOBAL)
    HARD_FAILURE_PATTERNS = [
        r"invariant violation",
        r"contract violated",
        r"structural impossibility",
        r"critical.*missing.*cannot proceed",
    ]
    
    @classmethod
    def classify(
        cls,
        error: Union[Exception, str],
        context: Dict[str, Any]
    ) -> StepOutcome:
        """
        Classify error with strict rules.
        
        Args:
            error: Exception or error string
            context: Additional context (generated_files, platform, etc.)
            
        Returns:
            StepOutcome classification
        """
        error_str = str(error).lower()
        
        # STEP 1: Explicit cognitive patterns (highest priority)
        for pattern in cls.ALWAYS_COGNITIVE:
            if re.search(pattern, error_str, re.IGNORECASE):
                return StepOutcome.COGNITIVE_FAILURE
        
        # STEP 2: Hard failures (global truths)
        for pattern in cls.HARD_FAILURE_PATTERNS:
            if re.search(pattern, error_str, re.IGNORECASE):
                return StepOutcome.HARD_FAILURE
        
        # STEP 3: Environment patterns + reasoning test
        for pattern in cls.ENVIRONMENT_PATTERNS:
            if re.search(pattern, error_str, re.IGNORECASE):
                # Double-check: Could reasoning fix this?
                if cls._could_reasoning_fix(error_str, context):
                    return StepOutcome.COGNITIVE_FAILURE
                return StepOutcome.ENVIRONMENT_FAILURE
        
        # STEP 4: Default to cognitive (safe fallback)
        return StepOutcome.COGNITIVE_FAILURE
    
    @staticmethod
    def _could_reasoning_fix(error: str, context: Dict[str, Any]) -> bool:
        """
        Ultimate test: Could regenerating code fix this?
        
        Philosophy: If healing/regeneration could fix it → COGNITIVE
        
        Args:
            error: Error message (lowercase)
            context: Context dictionary
            
        Returns:
            True if reasoning could fix it (making it COGNITIVE)
        """
        
        # If error mentions a file we generated, it's fixable
        generated_files = context.get("generated_files", [])
        for file_path in generated_files:
            if str(file_path) in error:
                return True
        
        # If it's about our own missing code, it's fixable
        if re.search(r'cannot import.*app\.', error):
            return True
        
        # Platform constraints on Windows
        current_platform = context.get("platform", platform.system().lower())
        if current_platform in ["windows", "win32"]:
            if "playwright" in error or "chromium" in error:
                return False  # Can't fix platform limitation with code
        
        # If it's a missing package that we control (in requirements.txt)
        if "modulenotfounderror" in error:
            # Check if it's our app code (fixable) vs external package (not fixable)
            if "app." in error:
                return True
        
        # Default: assume not fixable (environment constraint)
        return False
