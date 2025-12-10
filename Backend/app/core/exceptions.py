# app/core/exceptions.py
"""
Custom exceptions for the application.
"""
from typing import Optional, Dict, Any


class GenCodeError(Exception):
    """Base exception for all GenCode errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class WorkflowError(GenCodeError):
    """Workflow execution error."""
    pass


class QualityGateError(GenCodeError):
    """Quality gate blocked the workflow."""
    def __init__(self, step: str, quality_score: int, threshold: int):
        super().__init__(
            f"Quality gate blocked: {step} scored {quality_score}/{10} (min: {threshold})",
            {"step": step, "quality_score": quality_score, "threshold": threshold}
        )
        self.step = step
        self.quality_score = quality_score
        self.threshold = threshold


class AgentError(GenCodeError):
    """Agent execution error."""
    def __init__(self, agent_name: str, message: str, attempt: int = 0):
        super().__init__(
            f"{agent_name} error: {message}",
            {"agent": agent_name, "attempt": attempt}
        )
        self.agent_name = agent_name
        self.attempt = attempt


class LLMError(GenCodeError):
    """LLM provider error."""
    def __init__(self, provider: str, message: str):
        super().__init__(
            f"LLM error ({provider}): {message}",
            {"provider": provider}
        )
        self.provider = provider


class RateLimitError(LLMError):
    """Rate limit exhausted - workflow should STOP immediately."""
    def __init__(self, provider: str, retries: int = 3):
        super().__init__(
            provider,
            f"Rate limited after {retries} retries. Workflow cannot continue."
        )
        self.retries = retries



class SandboxError(GenCodeError):
    """Docker sandbox error."""
    def __init__(self, project_id: str, message: str):
        super().__init__(
            f"Sandbox error for {project_id}: {message}",
            {"project_id": project_id}
        )
        self.project_id = project_id


class PersistenceError(GenCodeError):
    """File persistence error."""
    def __init__(self, path: str, message: str):
        super().__init__(
            f"Cannot write to {path}: {message}",
            {"path": path}
        )
        self.path = path


class ValidationError(GenCodeError):
    """Output validation error."""
    pass


class ParseError(GenCodeError):
    """JSON/output parsing error."""
    pass
