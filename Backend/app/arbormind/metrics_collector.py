"""
ArborMind Metrics Collector

Centralized collection and reporting of system performance metrics.
Tracks:
1. Pipeline run statistics (success/failure rates across 100+ runs)
2. Per-step latency and success rates
3. Routing decision outcomes (for T-AM reinforcement learning)
4. Resource usage (tokens, cost)

IMPORTANT: This module should be imported early in app/main.py to ensure
metrics DB is initialized before any traffic.
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from app.core.config import settings
from app.core.logging import log

# Path to the SQLite DB for persistent metrics
# Using Backend/data/arbormind/arbormind_metrics.db
DATA_DIR = settings.paths.base_dir / "Backend" / "data" / "arbormind"
METRICS_DB_PATH = DATA_DIR / "arbormind_metrics.db"
PIPELINE_DB_PATH = DATA_DIR / "pipeline_metrics.db"

def init_metrics_db():
    """Initialize the metrics database tables if they don't exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. Routing Metrics DB (for T-AM reinforcement learning)
    try:
        conn = sqlite3.connect(METRICS_DB_PATH)
        c = conn.cursor()
        
        # Table: routing_metrics
        # Tracks individual routing decisions (e.g., standard vs E-AM vs T-AM)
        c.execute('''
            CREATE TABLE IF NOT EXISTS routing_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                decision_id TEXT,
                archetype TEXT,
                context_type TEXT,
                selected_strategy TEXT,
                used_tam BOOLEAN DEFAULT 0,
                success BOOLEAN,
                quality_score FLOAT,
                details TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        # log("METRICS", f"✅ Initialized Routing Metrics DB at {METRICS_DB_PATH}")
        
    except Exception as e:
        log("METRICS", f"⚠️ Failed to init Routing Metrics DB: {e}")

    # 2. Pipeline Metrics DB (for system reliability tracking)
    try:
        conn = sqlite3.connect(PIPELINE_DB_PATH)
        c = conn.cursor()
        
        # Table: pipeline_runs
        # Tracks overall success/failure of user requests
        c.execute('''
            CREATE TABLE IF NOT EXISTS pipeline_runs (
                run_id TEXT PRIMARY KEY,
                started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                completed_at DATETIME,
                project_id TEXT,
                archetype TEXT,
                status TEXT, -- 'running', 'success', 'failure'
                final_step TEXT,
                total_steps_succeeded INTEGER DEFAULT 0,
                duration_seconds FLOAT,
                error_message TEXT
            )
        ''')
        
        # Table: step_outcomes
        # Tracks individual step performance within a run
        c.execute('''
            CREATE TABLE IF NOT EXISTS step_outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT,
                step_name TEXT,
                status TEXT, -- 'success', 'failure'
                duration_seconds FLOAT,
                attempts INTEGER DEFAULT 1,
                healed BOOLEAN DEFAULT 0,
                error_type TEXT,
                error_message TEXT,
                FOREIGN KEY(run_id) REFERENCES pipeline_runs(run_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        # log("METRICS", f"✅ Initialized Pipeline Metrics DB at {PIPELINE_DB_PATH}")
        
    except Exception as e:
        log("METRICS", f"⚠️ Failed to init Pipeline Metrics DB: {e}")

def get_db_connection(db_path: Path):
    return sqlite3.connect(db_path)

# ----------------------------------------------------------------------------
# PIPELINE METRICS (High-level system reliability)
# ----------------------------------------------------------------------------

def start_pipeline_run(project_id: str, archetype: str = "unknown", user_request: str = "") -> str:
    """Start tracking a new pipeline run. Returns run_id."""
    import uuid
    run_id = str(uuid.uuid4())
    
    try:
        conn = get_db_connection(PIPELINE_DB_PATH)
        c = conn.cursor()
        c.execute('''
            INSERT INTO pipeline_runs (run_id, project_id, archetype, status)
            VALUES (?, ?, ?, 'running')
        ''', (run_id, project_id, archetype))
        conn.commit()
        conn.close()
    except Exception as e:
        log("METRICS", f"⚠️ Failed to start pipeline run: {e}")
        
    return run_id

def complete_pipeline_run(run_id: str, success: bool, final_step: str, error_message: str = ""):
    """Mark a pipeline run as complete."""
    status = "success" if success else "failure"
    
    try:
        conn = get_db_connection(PIPELINE_DB_PATH)
        c = conn.cursor()
        
        # Calculate duration
        c.execute('SELECT started_at FROM pipeline_runs WHERE run_id = ?', (run_id,))
        row = c.fetchone()
        if row:
            start_time = datetime.fromisoformat(row[0]) if row[0] else datetime.now()
            duration = (datetime.now() - start_time).total_seconds()
        else:
            duration = 0
            
        c.execute('''
            UPDATE pipeline_runs 
            SET status = ?, completed_at = ?, final_step = ?, duration_seconds = ?, error_message = ?
            WHERE run_id = ?
        ''', (status, datetime.now(), final_step, duration, error_message, run_id))
        conn.commit()
        conn.close()
    except Exception as e:
        log("METRICS", f"⚠️ Failed to complete pipeline run: {e}")

def start_step(run_id: str, step_name: str, step_order: int):
    """(Optional) Log step start - mainly for real-time dashboards."""
    pass

def complete_step(run_id: str, step_name: str, success: bool, attempts: int = 1, healed: bool = False, 
                 duration: float = 0.0, error_type: str = "", error_message: str = "", 
                 llm_calls: int = 0):
    """Record the outcome of a single step."""
    status = "success" if success else "failure"
    
    try:
        conn = get_db_connection(PIPELINE_DB_PATH)
        c = conn.cursor()
        
        # Record step outcome
        c.execute('''
            INSERT INTO step_outcomes (run_id, step_name, status, attempts, healed, duration_seconds, error_type, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (run_id, step_name, status, attempts, healed, duration, error_type, error_message))
        
        # Update running total in parent run if success
        if success:
            c.execute('''
                UPDATE pipeline_runs 
                SET total_steps_succeeded = total_steps_succeeded + 1 
                WHERE run_id = ?
            ''', (run_id,))
            
        conn.commit()
        conn.close()
    except Exception as e:
        log("METRICS", f"⚠️ Failed to record step outcome: {e}")

# ----------------------------------------------------------------------------
# ROUTING METRICS (Low-level decision reinforcement)
# ----------------------------------------------------------------------------

def record_routing_decision(decision_id: str, archetype: str, context: str, strategy: str, tam_used: bool):
    """Record a routing decision made by ArborMind."""
    try:
        conn = get_db_connection(METRICS_DB_PATH)
        c = conn.cursor()
        c.execute('''
            INSERT INTO routing_metrics (decision_id, archetype, context_type, selected_strategy, used_tam)
            VALUES (?, ?, ?, ?, ?)
        ''', (decision_id, archetype, context, strategy, tam_used))
        conn.commit()
        conn.close()
    except Exception as e:
        log("METRICS", f"⚠️ Failed to record routing decision: {e}")

def report_routing_outcome_db(decision_id: str, success: bool, quality_score: float, details: str):
    """Update a routing decision with its outcome."""
    try:
        conn = get_db_connection(METRICS_DB_PATH)
        c = conn.cursor()
        c.execute('''
            UPDATE routing_metrics 
            SET success = ?, quality_score = ?, details = ?
            WHERE decision_id = ?
        ''', (success, quality_score, details, decision_id))
        conn.commit()
        conn.close()
    except Exception as e:
        log("METRICS", f"⚠️ Failed to report routing outcome: {e}")
