# app/tracking/metrics.py
"""
Code quality metrics tracking.
"""
from typing import Any, Dict, List

# In-memory metrics storage
_project_metrics: Dict[str, Dict[str, Any]] = {}


def update_code_metrics(
    project_id: str,
    agent_name: str,
    files: List[Dict[str, str]],
) -> Dict[str, Any]:
    """Update code metrics for generated files."""
    if project_id not in _project_metrics:
        _project_metrics[project_id] = {
            "total_files": 0,
            "total_lines": 0,
            "by_agent": {},
        }
    
    metrics = _project_metrics[project_id]
    
    if agent_name not in metrics["by_agent"]:
        metrics["by_agent"][agent_name] = {"files": 0, "lines": 0}
    
    file_count = len(files)
    total_lines = sum(f.get("content", "").count('\n') + 1 for f in files)
    
    metrics["by_agent"][agent_name]["files"] += file_count
    metrics["by_agent"][agent_name]["lines"] += total_lines
    metrics["total_files"] += file_count
    metrics["total_lines"] += total_lines
    
    return {
        "files_generated": file_count,
        "lines_of_code": total_lines,
    }


def get_code_metrics(project_id: str) -> Dict[str, Any]:
    """Get code metrics for a project."""
    return _project_metrics.get(project_id, {
        "total_files": 0,
        "total_lines": 0,
        "by_agent": {},
    })
