# app/workflow/integration_example.py
"""
Example of how to integrate Phase 1 outcome aggregation.

This shows how workflow engine and orchestrators should use the new types.
"""
from typing import List
from pathlib import Path

from app.core.step_outcome import StepOutcome, StepExecutionResult
from app.workflow.outcome_aggregator import (
    aggregate_workflow_outcome,
    format_degradation_summary
)


def example_workflow_completion():
    """
    Example: How to use outcome aggregation at end of workflow.
    """
    
    # Simulate step results from a workflow run
    step_results = [
        StepExecutionResult(
            outcome=StepOutcome.SUCCESS,
            step_name="analysis",
            artifacts=[]
        ),
        StepExecutionResult(
            outcome=StepOutcome.SUCCESS,
            step_name="architecture",
            artifacts=[]
        ),
        StepExecutionResult(
            outcome=StepOutcome.SUCCESS,
            step_name="backend_implementation",
            artifacts=[]
        ),
        StepExecutionResult(
            outcome=StepOutcome.ENVIRONMENT_FAILURE,
            step_name="testing_backend",
            isolated=True,  # This step was isolated
            artifacts=[Path("backend/tests/test_api.py")],
            error_details="Playwright not available on Windows"
        ),
        StepExecutionResult(
            outcome=StepOutcome.SUCCESS,
            step_name="system_integration",
            artifacts=[]
        ),
    ]
    
    # Alternative evidence from static validation
    evidence = {
        "testing_backend": {
            "type": "static",
            "result": {
                "syntax_errors": 0,
                "routes_found": 12,
                "models_found": 3
            }
        }
    }
    
    # Aggregate outcomes
    status, report = aggregate_workflow_outcome(step_results, evidence)
    
    print(f"Workflow Status: {status.value}")
    
    if report:
        print("\nDegradation Report:")
        print(format_degradation_summary(report))
    
    # Output:
    # Workflow Status: success_with_degradation
    # 
    # Degradation Report:
    # ⚠️ Workflow completed with degradation:
    #   • 1 step(s) isolated
    #     - testing_backend (1 artifact(s) quarantined)
    #   • Alternative validation provided:
    #     - testing_backend: static validation


def example_hard_failure_precedence():
    """
    Example: HARD_FAILURE in isolated step still fails workflow.
    
    This demonstrates ADJUSTMENT 1.
    """
    
    step_results = [
        StepExecutionResult(
            outcome=StepOutcome.SUCCESS,
            step_name="analysis",
            artifacts=[]
        ),
        StepExecutionResult(
            outcome=StepOutcome.HARD_FAILURE,
            step_name="contracts",
            isolated=True,  # Even though isolated...
            error_details="Contract violation detected",
            artifacts=[]
        ),
        StepExecutionResult(
            outcome=StepOutcome.SUCCESS,
            step_name="backend_implementation",
            artifacts=[]
        ),
    ]
    
    status, report = aggregate_workflow_outcome(step_results)
    
    print(f"Workflow Status: {status.value}")  # FAILED
    print(f"Report: {report}")  # None
    
    # Output:
    # Workflow Status: failed
    # Report: None
    #
    # Why: HARD_FAILURE is a global truth that ignores isolation


if __name__ == '__main__':
    print("=== Example 1: Degraded Success ===")
    example_workflow_completion()
    
    print("\n\n=== Example 2: Hard Failure Precedence ===")
    example_hard_failure_precedence()
