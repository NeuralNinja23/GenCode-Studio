# app/core/arbormind_paths.py
"""
Centralized ArborMind Storage Paths

This module defines canonical storage paths for all ArborMind components.
Ensures V-Vector store, metrics collector, and all visualization tools
use the same database paths.

Usage:
    from app.core.arbormind_paths import ARBORMIND_STORAGE_DIR, V_VECTOR_DB_PATH
    
    store = VVectorStore(ARBORMIND_STORAGE_DIR)
    # Both will use backend/data/arbormind/v_vector_history.db
"""
from pathlib import Path


# Root directory (backend/)
BACKEND_ROOT = Path(__file__).parent.parent.parent

# ArborMind storage directory
ARBORMIND_STORAGE_DIR = BACKEND_ROOT / "data" / "arbormind"

# Database file names
V_VECTOR_DB_NAME = "v_vector_history.db"
METRICS_DB_NAME = "arbormind_metrics.db"

# Full database paths
V_VECTOR_DB_PATH = ARBORMIND_STORAGE_DIR / V_VECTOR_DB_NAME
METRICS_DB_PATH = ARBORMIND_STORAGE_DIR / METRICS_DB_NAME

# Ensure storage directory exists
ARBORMIND_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def get_arbormind_storage_dir() -> Path:
    """Get the ArborMind storage directory."""
    return ARBORMIND_STORAGE_DIR


def get_v_vector_db_path() -> Path:
    """Get the V-Vector database path."""
    return V_VECTOR_DB_PATH


def get_metrics_db_path() -> Path:
    """Get the metrics database path."""
    return METRICS_DB_PATH
