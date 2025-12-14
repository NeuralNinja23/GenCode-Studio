# app/orchestration/healing_policy.py
"""
HealingPolicy: Stateful policy engine for determining healing actions.

Instead of ad-hoc decisions scattered across testing_backend.py and healing code,
this engine centralizes the logic:
    Input: {step, error_type, http_statuses, recent_repairs}
    Output: ordered list of (artifact, requires_restart) tuples

This makes healing deterministic, testable, and easy to evolve.
"""
from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path
from enum import Enum


class ErrorType(Enum):
    """Classification of failure types."""
    ROUTING_404 = "routing_404"              # 404s on expected routes
    IMPORT_ERROR = "import_error"            # Python import failures
    SYNTAX_ERROR = "syntax_error"            # Code syntax errors
    LOGIC_ERROR = "logic_error"              # Wrong business logic (500s, wrong data)
    DATABASE_ERROR = "database_error"        # DB connection/query failures
    VALIDATION_ERROR = "validation_error"    # Schema/Pydantic validation failures
    
    # GENERALIZED: New error types from CodeValidator
    FASTAPI_PARAMETER_ERROR = "fastapi_parameter_error"  # Query/Path/Body annotation issues
    FASTAPI_ROUTE_ERROR = "fastapi_route_error"          # Route registration errors
    MODULE_NOT_FOUND = "module_not_found"                # Missing module/file
    TYPE_ERROR = "type_error"                            # Type mismatch errors
    
    UNKNOWN = "unknown"                      # Unclassified failure


@dataclass
class HealingAction:
    """A single healing action to perform."""
    artifact: str                    # "backend_vertical", "system_integration", etc.
    requires_restart: bool           # Does this need service restart?
    priority: int                    # Lower = higher priority (0 = highest)
    reason: str                      # Why this action was chosen


class HealingPolicy:
    """
    Policy engine that decides what to heal based on failure patterns.
    
    This is stateful - tracks recent repairs to avoid infinite loops.
    """
    
    def __init__(self, project_path: Path):
        """
        Initialize healing policy.
        
        Args:
            project_path: Path to project workspace
        """
        self.project_path = project_path
        self.repair_history: List[str] = []  # Track recent repairs
        self.max_history = 10
    
    @staticmethod
    def from_code_validator_error(cv_error_type) -> 'ErrorType':
        """
        Map CodeValidator.ErrorType to HealingPolicy.ErrorType.
        
        This bridges the generalized validator with the policy engine.
        
        Args:
            cv_error_type: ErrorType from code_validator module
        
        Returns:
            Corresponding HealingPolicy.ErrorType
        """
        # Import here to avoid circular import
        from app.orchestration.code_validator import ErrorType as CVErrorType
        
        mapping = {
            CVErrorType.SYNTAX_ERROR: ErrorType.SYNTAX_ERROR,
            CVErrorType.INDENTATION_ERROR: ErrorType.SYNTAX_ERROR,
            CVErrorType.IMPORT_ERROR: ErrorType.IMPORT_ERROR,
            CVErrorType.MODULE_NOT_FOUND: ErrorType.MODULE_NOT_FOUND,
            CVErrorType.CIRCULAR_IMPORT: ErrorType.IMPORT_ERROR,
            CVErrorType.FASTAPI_PARAMETER_ERROR: ErrorType.FASTAPI_PARAMETER_ERROR,
            CVErrorType.FASTAPI_ROUTE_ERROR: ErrorType.FASTAPI_ROUTE_ERROR,
            CVErrorType.FASTAPI_DEPENDENCY_ERROR: ErrorType.FASTAPI_ROUTE_ERROR,
            CVErrorType.ATTRIBUTE_ERROR: ErrorType.LOGIC_ERROR,
            CVErrorType.TYPE_ERROR: ErrorType.TYPE_ERROR,
            CVErrorType.VALUE_ERROR: ErrorType.VALIDATION_ERROR,
            CVErrorType.BEANIE_ERROR: ErrorType.DATABASE_ERROR,
            CVErrorType.MONGODB_ERROR: ErrorType.DATABASE_ERROR,
            CVErrorType.UNKNOWN: ErrorType.UNKNOWN,
        }
        
        return mapping.get(cv_error_type, ErrorType.UNKNOWN)
    
    def classify_error(
        self, 
        step: str, 
        error_message: str, 
        http_statuses: Optional[List[int]] = None
    ) -> ErrorType:
        """
        Classify the type of error based on context.
        
        Args:
            step: Workflow step that failed
            error_message: Error message/output
            http_statuses: List of HTTP status codes seen in failures
        
        Returns:
            ErrorType classification
        """
        error_lower = error_message.lower()
        
        # Check HTTP status patterns
        if http_statuses:
            if 404 in http_statuses:
                return ErrorType.ROUTING_404
            if any(s >= 500 for s in http_statuses):
                return ErrorType.LOGIC_ERROR
        
        # GENERALIZED: Check for FastAPI parameter errors (like missing Query())
        if "assertionerror: non-body parameters must be in" in error_lower:
            return ErrorType.FASTAPI_PARAMETER_ERROR
        
        if "assertionerror" in error_lower and ("path" in error_lower or "query" in error_lower):
            return ErrorType.FASTAPI_PARAMETER_ERROR
        
        # Check error message patterns
        if "404" in error_lower or "not found" in error_lower:
            return ErrorType.ROUTING_404
        
        if "modulenotfounderror" in error_lower:
            return ErrorType.MODULE_NOT_FOUND
        
        if "import" in error_lower and "error" in error_lower:
            return ErrorType.IMPORT_ERROR
        
        if "syntax" in error_lower or "invalid syntax" in error_lower:
            return ErrorType.SYNTAX_ERROR
        
        if "database" in error_lower or "mongodb" in error_lower:
            return ErrorType.DATABASE_ERROR
        
        if "validation" in error_lower or "pydantic" in error_lower:
            return ErrorType.VALIDATION_ERROR
        
        if "typeerror" in error_lower:
            return ErrorType.TYPE_ERROR
        
        return ErrorType.UNKNOWN
    
    def get_healing_actions(
        self,
        step: str,
        error_type: ErrorType,
        entity_plural: Optional[str] = None,
        http_statuses: Optional[List[int]] = None
    ) -> List[HealingAction]:
        """
        Determine healing actions based on error type.
        
        Args:
            step: Workflow step that failed
            error_type: Classified error type
            entity_plural: Plural form of primary entity (for context)
            http_statuses: HTTP status codes from failures
        
        Returns:
            Ordered list of HealingAction objects (highest priority first)
        """
        actions = []
        
        # Routing 404s: routes don't exist or aren't wired
        if error_type == ErrorType.ROUTING_404:
            # Check if this is a repeated repair (avoid loops)
            if "backend_vertical" not in self.repair_history[-3:]:
                actions.append(HealingAction(
                    artifact="backend_vertical",
                    requires_restart=True,
                    priority=0,
                    reason=f"404s on /api/{entity_plural or 'entity'} - regenerating router + models"
                ))
            
            if "system_integration" not in self.repair_history[-3:]:
                actions.append(HealingAction(
                    artifact="system_integration",
                    requires_restart=True,
                    priority=1,
                    reason="404s may be due to unwired routes in main.py"
                ))
        
        # Import errors: main.py or router has broken imports
        elif error_type == ErrorType.IMPORT_ERROR:
            actions.append(HealingAction(
                artifact="backend_main",
                requires_restart=True,
                priority=0,
                reason="Import error - regenerating main.py with correct imports"
            ))
            
            actions.append(HealingAction(
                artifact="backend_vertical",
                requires_restart=True,
                priority=1,
                reason="Import error may be in router - regenerating"
            ))
        
        # Syntax errors: code has syntax issues
        elif error_type == ErrorType.SYNTAX_ERROR:
            actions.append(HealingAction(
                artifact="backend_vertical",
                requires_restart=True,
                priority=0,
                reason="Syntax error in backend code - regenerating"
            ))
        
        # GENERALIZED: FastAPI parameter errors (e.g., missing Query() annotations)
        elif error_type == ErrorType.FASTAPI_PARAMETER_ERROR:
            actions.append(HealingAction(
                artifact="backend_vertical",
                requires_restart=True,
                priority=0,
                reason="FastAPI parameter annotation error - regenerating router with proper Query()/Path() annotations"
            ))
        
        # GENERALIZED: FastAPI route registration errors
        elif error_type == ErrorType.FASTAPI_ROUTE_ERROR:
            actions.append(HealingAction(
                artifact="backend_vertical",
                requires_restart=True,
                priority=0,
                reason="FastAPI route registration error - regenerating router"
            ))
            
            actions.append(HealingAction(
                artifact="system_integration",
                requires_restart=True,
                priority=1,
                reason="Route error may be in main.py wiring - regenerating"
            ))
        
        # GENERALIZED: Module not found errors
        elif error_type == ErrorType.MODULE_NOT_FOUND:
            actions.append(HealingAction(
                artifact="backend_vertical",
                requires_restart=True,
                priority=0,
                reason="Module not found - regenerating backend files"
            ))
            
            actions.append(HealingAction(
                artifact="backend_main",
                requires_restart=True,
                priority=1,
                reason="Module not found may be in main.py imports - regenerating"
            ))
        
        # GENERALIZED: Type errors
        elif error_type == ErrorType.TYPE_ERROR:
            actions.append(HealingAction(
                artifact="backend_vertical",
                requires_restart=True,
                priority=0,
                reason="Type error - regenerating router with correct types"
            ))
        
        # Database errors: DB connection or query issues
        elif error_type == ErrorType.DATABASE_ERROR:
            actions.append(HealingAction(
                artifact="backend_db",
                requires_restart=True,
                priority=0,
                reason="Database connection error - regenerating db wrapper"
            ))
            
            actions.append(HealingAction(
                artifact="backend_vertical",
                requires_restart=True,
                priority=1,
                reason="Database error may be in router queries - regenerating"
            ))
        
        # Unknown errors: try most common fixes
        else:
            actions.append(HealingAction(
                artifact="backend_vertical",
                requires_restart=True,
                priority=0,
                reason="Unknown error - regenerating backend vertical as catch-all"
            ))
        
        # Sort by priority
        actions.sort(key=lambda a: a.priority)
        
        return actions
    
    def record_repair(self, artifact: str):
        """
        Record that a repair was attempted.
        
        Args:
            artifact: Artifact that was repaired
        """
        self.repair_history.append(artifact)
        
        # Keep only recent history
        if len(self.repair_history) > self.max_history:
            self.repair_history = self.repair_history[-self.max_history:]
    
    def should_stop_healing(self, artifact: str, max_attempts: int = 3) -> bool:
        """
        Check if we should stop healing to avoid infinite loops.
        
        Args:
            artifact: Artifact being considered for repair
            max_attempts: Maximum attempts for same artifact
        
        Returns:
            True if we should stop healing this artifact
        """
        # Count recent attempts for this artifact
        recent_attempts = self.repair_history[-max_attempts:].count(artifact)
        return recent_attempts >= max_attempts
    
    def reset(self):
        """Reset repair history (e.g., for new workflow run)."""
        self.repair_history.clear()
