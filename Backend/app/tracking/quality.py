# app/tracking/quality.py
"""
Quality score tracking.
"""
from typing import Dict, List

# In-memory quality storage
_quality_scores: Dict[str, Dict[str, List[int]]] = {}


def track_quality_score(
    project_id: str,
    agent_name: str,
    quality_score: int,
    approved: bool,
) -> None:
    """Track quality score for an agent."""
    if project_id not in _quality_scores:
        _quality_scores[project_id] = {}
    
    if agent_name not in _quality_scores[project_id]:
        _quality_scores[project_id][agent_name] = []
    
    _quality_scores[project_id][agent_name].append(quality_score)


def get_quality_summary(project_id: str) -> Dict[str, float]:
    """Get average quality scores per agent."""
    scores = _quality_scores.get(project_id, {})
    return {
        agent: sum(s) / len(s) if s else 0
        for agent, s in scores.items()
    }
