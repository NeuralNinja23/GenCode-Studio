
"""
Orchestration Guard - The Permanent Safety Lock.

Prevents re-introduction of "cognitive decision" logic in the execution layer.
"""

class OrchestrationGuard:
    """
    Safety lock to prevent accidental re-introduction of cognitive decisions
    (retries, escalation, healing) into the orchestration layer.
    """
    def __getattr__(self, name):
        raise RuntimeError(
            f"Orchestration attempted cognitive decision: {name}. "
            "COGNITIVE LOGIC BELONGS IN ARBORMIND BRANCHES ONLY."
        )
