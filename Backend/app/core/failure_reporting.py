# app/core/failure_reporting.py
"""
STEP 11: Accept Failure as a Feature

════════════════════════════════════════════════════════════════════════════════
ARCHITECTURAL INVARIANT: Honest Failure Reporting
════════════════════════════════════════════════════════════════════════════════

Old mindset: "Fix it until it works."
New mindset: "If it fails, stop — and tell the truth."

WHY THIS IS BETTER:
- Cheaper (no wasted tokens on healing attempts)
- Faster (fail fast, inform immediately)  
- Honest (no hidden corruption)
- Debuggable (clear failure points)
- Scalable (predictable behavior)

This module provides utilities for reporting failures clearly and honestly.
════════════════════════════════════════════════════════════════════════════════
"""
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path
from app.core.logging import log


# ═══════════════════════════════════════════════════════
# FAILURE TYPES
# ═══════════════════════════════════════════════════════

class FailureType:
    """Canonical failure types for honest reporting."""
    
    # Causal step failures (workflow stops)
    CAUSAL_GENERATION = "causal_generation"      # LLM failed to generate valid code
    CAUSAL_VALIDATION = "causal_validation"      # Generated code failed validation
    CAUSAL_TRUNCATION = "causal_truncation"      # Output was truncated (incomplete)
    CAUSAL_MALFORMED = "causal_malformed"        # Output was malformed (parse failed)
    
    # Evidence step failures (can retry on infra issues)
    EVIDENCE_TIMEOUT = "evidence_timeout"        # Test/validation timed out
    EVIDENCE_INFRA = "evidence_infra"            # Infrastructure failure (sandbox, etc.)
    EVIDENCE_ASSERTION = "evidence_assertion"    # Test assertion failed
    
    # System failures (not the LLM's fault)
    SYSTEM_BUDGET = "system_budget"              # Token budget exhausted
    SYSTEM_API = "system_api"                    # API error (rate limit, network, etc.)
    SYSTEM_CONFIG = "system_config"              # Configuration error


# ═══════════════════════════════════════════════════════
# FAILURE REPORT
# ═══════════════════════════════════════════════════════

def report_failure(
    step_name: str,
    failure_type: str,
    reason: str,
    details: Optional[Dict[str, Any]] = None,
    is_causal: bool = True,
) -> Dict[str, Any]:
    """
    Report a failure honestly and clearly.
    
    This is the SINGLE SOURCE OF TRUTH for failure reporting.
    
    Args:
        step_name: The workflow step that failed
        failure_type: One of FailureType constants
        reason: Human-readable explanation of what went wrong
        details: Additional context (file paths, error messages, etc.)
        is_causal: If True, this is a causal step failure (workflow stops)
        
    Returns:
        Failure report dict (for logging, WebSocket, etc.)
    """
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "step": step_name,
        "failure_type": failure_type,
        "is_causal": is_causal,
        "reason": reason,
        "details": details or {},
        "action_taken": "WORKFLOW_STOPPED" if is_causal else "WILL_RETRY",
    }
    
    # Log with appropriate severity
    emoji = "🛑" if is_causal else "⚠️"
    step_type = "CAUSAL" if is_causal else "EVIDENCE"
    
    log("FAILURE", f"{emoji} {step_type} failure in {step_name}")
    log("FAILURE", f"   Type: {failure_type}")
    log("FAILURE", f"   Reason: {reason}")
    
    if is_causal:
        log("FAILURE", "   Action: Workflow STOPPED - no healing, no retry")
        log("FAILURE", "   This is correct behavior. Causal failures are deterministic.")
    else:
        log("FAILURE", "   Action: May retry if infrastructure issue")
    
    if details:
        for key, value in details.items():
            log("FAILURE", f"   {key}: {value}")
    
    return report


def report_truncation(
    step_name: str,
    file_path: str,
    expected_sentinel: str = "# === END OF FILE ===",
) -> Dict[str, Any]:
    """
    Report a truncation failure (output cut off).
    
    This is a CHEAP check that saves thousands of tokens.
    """
    return report_failure(
        step_name=step_name,
        failure_type=FailureType.CAUSAL_TRUNCATION,
        reason=f"Output truncated - missing END OF FILE sentinel",
        details={
            "file_path": file_path,
            "expected_sentinel": expected_sentinel,
            "fix_suggestion": "Reduce output complexity or split into multiple files",
        },
        is_causal=True,
    )


def report_malformed_output(
    step_name: str,
    parse_error: str,
) -> Dict[str, Any]:
    """
    Report a malformed output failure (JSON parse failed, etc.)
    """
    return report_failure(
        step_name=step_name,
        failure_type=FailureType.CAUSAL_MALFORMED,
        reason=f"Output malformed - could not parse",
        details={
            "parse_error": parse_error,
            "salvage_attempted": False,  # STEP 4: No salvage for causal steps
        },
        is_causal=True,
    )


def report_validation_failure(
    step_name: str,
    validation_errors: list,
) -> Dict[str, Any]:
    """
    Report a validation failure (syntax error, empty file, etc.)
    """
    return report_failure(
        step_name=step_name,
        failure_type=FailureType.CAUSAL_VALIDATION,
        reason=f"Generated code failed validation",
        details={
            "validation_errors": validation_errors[:5],  # Limit to first 5
            "healing_attempted": False,  # STEP 6: No healing for causal steps
        },
        is_causal=True,
    )


# ═══════════════════════════════════════════════════════
# SUMMARY GENERATOR
# ═══════════════════════════════════════════════════════

def generate_failure_summary(failures: list) -> str:
    """
    Generate a human-readable failure summary.
    
    This is the message shown to the user when the workflow fails.
    """
    if not failures:
        return "No failures recorded."
    
    lines = [
        "════════════════════════════════════════════════════",
        "WORKFLOW FAILED - HONEST FAILURE REPORT",
        "════════════════════════════════════════════════════",
        "",
    ]
    
    for i, f in enumerate(failures, 1):
        step = f.get("step", "unknown")
        failure_type = f.get("failure_type", "unknown")
        reason = f.get("reason", "No reason provided")
        is_causal = f.get("is_causal", True)
        
        lines.append(f"{i}. Step: {step}")
        lines.append(f"   Type: {failure_type}")
        lines.append(f"   Reason: {reason}")
        
        if is_causal:
            lines.append("   → This was a CAUSAL failure. The workflow stopped correctly.")
        lines.append("")
    
    lines.extend([
        "════════════════════════════════════════════════════",
        "This is NOT a bug in the system.",
        "LLMs sometimes fail. Honest failure is better than hidden corruption.",
        "════════════════════════════════════════════════════",
    ])
    
    return "\n".join(lines)
