import sys
from datetime import datetime
from typing import Any, Optional, List

def log(scope: str, message: str, data: Any = None, project_id: Optional[str] = None) -> None:
    """
    Unified logging function for GenCode Studio.
    Prints to stdout with timestamp and scope.
    """
    timestamp = datetime.now().strftime("%H:%M:%S")
    prefix = f"[{timestamp}] [{scope}]"
    
    if project_id:
        # Keep just the first 8 chars of project_id for cleaner logs
        short_id = project_id[:8]
        prefix += f" [{short_id}]"
        
    print(f"{prefix} {message}")
    
    if data:
        # Avoid dumping huge data blobs unless necessary
        # For now, we print it as requested
        print(f"  Data: {data}")
    
    # Ensure flush to see logs immediately in some environments
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

