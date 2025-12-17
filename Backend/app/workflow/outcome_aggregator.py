# app/workflow/outcome_aggregator.py
"""
Aggregates step outcomes into workflow status.

CRITICAL: Degradation is an AGGREGATE property, not step-level.

Phase 1: Implementation with ADJUSTMENT 1 applied:
🔧 HARD_FAILURE anywhere (even in isolated steps) → FAILED
Logical impossibilities are global truths.
"""
from typing import List, Optional, Tuple, Dict, Any

from app.core.types import WorkflowStatus, DegradationReport
from app.core.step_outcome import StepExecutionResult, StepOutcome


def aggregate_workflow_outcome(
    step_results: List[StepExecutionResult],
    evidence: Optional[Dict[str, Any]] = None
) -> Tuple[WorkflowStatus, Optional[DegradationReport]]:
    """
    Aggregate step outcomes into workflow status.
    
    Rules (with ADJUSTMENT 1 applied):
    1. 🔧 Any HARD_FAILURE ANYWHERE → FAILED (ignores isolation)
    2. All non-isolated steps SUCCESS → check for degradation
    3. Mix of SUCCESS + isolated ENVIRONMENT → SUCCESS_WITH_DEGRADATION
    4. COGNITIVE_FAILURE with healing → depends on healing result
    
    Args:
        step_results: List of step execution results
        evidence: Optional evidence dictionary (for static validation proofs)
        
    Returns:
        Tuple of (WorkflowStatus, Optional[DegradationReport])
    """
    if evidence is None:
        evidence = {}
    
    # 🔧 ADJUSTMENT 1: Check HARD_FAILURE in ALL steps (including isolated)
    # Logical impossibilities are global - isolation doesn't protect from them
    hard_failures = [
        r for r in step_results 
        if r.outcome == StepOutcome.HARD_FAILURE
    ]
    
    if hard_failures:
        # Hard failure is absolute - workflow must fail
        return WorkflowStatus.FAILED, None
    
    # Filter out isolated steps for remaining checks
    active_results = [r for r in step_results if not r.isolated]
    isolated_results = [r for r in step_results if r.isolated]
    
    # Check if all active steps succeeded
    all_active_succeeded = all(
        r.outcome == StepOutcome.SUCCESS 
        for r in active_results
    )
    
    if all_active_succeeded:
        # Check for isolated branches
        if isolated_results:
            # Degraded success - some steps were isolated
            report = DegradationReport(
                isolated_steps=[r.step_name for r in isolated_results],
                quarantined_artifacts={
                    r.step_name: [str(a) for a in r.artifacts]
                    for r in isolated_results
                },
                alternative_evidence=evidence,
                message=f"Workflow succeeded with {len(isolated_results)} isolated step(s): {', '.join(r.step_name for r in isolated_results)}"
            )
            return WorkflowStatus.SUCCESS_WITH_DEGRADATION, report
        else:
            # Clean success - all steps passed
            return WorkflowStatus.SUCCESS, None
    
    # Active steps have cognitive failures or are still running
    # Check for any cognitive failures that weren't healed
    cognitive_failures = [
        r for r in active_results 
        if r.outcome == StepOutcome.COGNITIVE_FAILURE
    ]
    
    if cognitive_failures:
        # Cognitive failures that weren't resolved
        return WorkflowStatus.FAILED, None
    
    # If we get here, workflow is probably still running
    return WorkflowStatus.RUNNING, None


def should_continue_workflow(
    current_status: WorkflowStatus,
    degradation_report: Optional[DegradationReport]
) -> bool:
    """
    Determine if workflow should continue to next step.
    
    Args:
        current_status: Current workflow status
        degradation_report: Optional degradation report
        
    Returns:
        True if workflow can continue
    """
    # Can continue on success or degraded success
    if current_status in (WorkflowStatus.SUCCESS, WorkflowStatus.SUCCESS_WITH_DEGRADATION):
        return True
    
    # Can continue if still running
    if current_status == WorkflowStatus.RUNNING:
        return True
    
    # Cannot continue on failure or pause
    return False


def format_degradation_summary(report: DegradationReport) -> str:
    """
    Format degradation report for user-facing display.
    
    Args:
        report: DegradationReport to format
        
    Returns:
        Human-readable summary
    """
    lines = ["⚠️ Workflow completed with degradation:"]
    lines.append(f"  • {len(report.isolated_steps)} step(s) isolated")
    
    for step_name in report.isolated_steps:
        artifacts = report.quarantined_artifacts.get(step_name, [])
        lines.append(f"    - {step_name} ({len(artifacts)} artifact(s) quarantined)")
    
    # Check for alternative evidence
    if report.alternative_evidence:
        lines.append("  • Alternative validation provided:")
        for step, evidence_data in report.alternative_evidence.items():
            evidence_type = evidence_data.get('type', 'unknown')
            lines.append(f"    - {step}: {evidence_type} validation")
    
    return "\n".join(lines)
