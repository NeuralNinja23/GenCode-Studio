import sys
import os
from datetime import datetime
from typing import Any, Optional, List


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE E4: LOG FILTERING
# ═══════════════════════════════════════════════════════════════════════════════
# Only these 5 log classes are shown at INFO level
# Everything else is gated behind DEBUG

INFO_SCOPES = {
    "FAST-V2",      # Step lifecycle
    "PLANNER",      # Execution intent  
    "TOOL-EXEC",    # Actual execution
    "MARCUS",       # LLM boundary
    "SUPERVISION",  # Review verdict
    "TOKENS",       # Token usage
    "HDAP",         # File protocol
    "LOCKFILE",     # Cache hits
}

# DEBUG-only scopes (hidden by default)
DEBUG_SCOPES = {
    "PREFLIGHT",
    "COMPONENT_COPIER",
    "FILTER",
    "DISCOVERY",
    "OPTIMIZATION",
    "ATTENTION",
    "BOUNDARY",
    "RUNTIME",
}

# Check if DEBUG mode is enabled
DEBUG_MODE = os.getenv("GENCODE_DEBUG", "false").lower() == "true"


def log(scope: str, message: str, data: Any = None, project_id: Optional[str] = None) -> None:
    """
    Unified logging function for GenCode Studio.
    
    PHASE E4: Only INFO_SCOPES are shown by default.
    Set GENCODE_DEBUG=true to see all scopes.
    """
    # Filter non-essential logs unless DEBUG mode
    if not DEBUG_MODE and scope not in INFO_SCOPES:
        return  # Silently skip
    
    timestamp = datetime.now().strftime("%H:%M:%S")
    prefix = f"[{timestamp}] [{scope}]"
    
    if project_id:
        short_id = project_id[:8]
        prefix += f" [{short_id}]"
        
    print(f"{prefix} {message}")
    
    if data:
        print(f"  Data: {data}")
    
    sys.stdout.flush()


def log_section(scope: str, title: str, project_id: Optional[str] = None) -> None:
    """
    Log a section header with visual separator.
    """
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"\n{'='*60}")
    if project_id:
        print(f"[{timestamp}] [{scope}] [{project_id[:8]}] {title}")
    else:
        print(f"[{timestamp}] [{scope}] {title}")
    print(f"{'='*60}")
    sys.stdout.flush()


def log_thinking(scope: str, thinking: str, project_id: Optional[str] = None, max_lines: int = 10) -> None:
    """
    Log agent thinking/reasoning with proper formatting.
    """
    timestamp = datetime.now().strftime("%H:%M:%S")
    prefix = f"[{timestamp}] [{scope}]"
    if project_id:
        prefix += f" [{project_id[:8]}]"
    
    print(f"\n{prefix} 💭 THINKING:")
    lines = str(thinking).split('\n')
    for line in lines[:max_lines]:
        print(f"  {line}")
    if len(lines) > max_lines:
        print(f"  ... ({len(lines) - max_lines} more lines)")
    sys.stdout.flush()


def log_files(scope: str, files: List[dict], project_id: Optional[str] = None) -> None:
    """
    Log file list summary.
    """
    # Silent as requested
    pass


def log_result(scope: str, approved: bool, quality: int, issues: List[str] = None, project_id: Optional[str] = None) -> None:
    """
    Log review result with quality score.
    """
    timestamp = datetime.now().strftime("%H:%M:%S")
    prefix = f"[{timestamp}] [{scope}]"
    if project_id:
        prefix += f" [{project_id[:8]}]"
    
    if approved:
        print(f"\n{prefix} ✅ APPROVED - Quality: {quality}/10")
    else:
        print(f"\n{prefix} ⚠️ REJECTED - Quality: {quality}/10")
        if issues:
            print(f"{prefix} Issues found:")
            for i, issue in enumerate(issues[:5]):
                print(f"  {i+1}. {issue}")
    
    print(f"{'='*60}\n")
    sys.stdout.flush()

