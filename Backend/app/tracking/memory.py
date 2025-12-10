import json
import sqlite3
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pathlib import Path
from app.core.config import settings

# ================================================================
# PERSISTENT MEMORY STORE (SQLite)
# ================================================================

class PersistentMemoryStore:
    """SQLite-backed persistent memory for architectural decisions"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        # Ensure directory exists
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id TEXT NOT NULL,
                category TEXT,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                timestamp REAL NOT NULL,
                metadata TEXT
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_workflow_category 
            ON memories(workflow_id, category)
        """)

        conn.commit()
        conn.close()

    def save_memory(
        self, 
        workflow_id: str, 
        category: str, 
        key: str, 
        value: Any, 
        metadata: Optional[Dict] = None
    ):
        """Save a memory entry"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO memories (workflow_id, category, key, value, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                workflow_id,
                category,
                key,
                json.dumps(value),
                datetime.now(timezone.utc).timestamp(),
                json.dumps(metadata or {})
            ))

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[MEMORY] Failed to save memory: {e}")

    def recall_patterns(self, agent_name: str, step_name: str) -> List[Dict[str, Any]]:
        """Recall successful patterns for an agent/step"""
        category = f"{agent_name}:{step_name}"
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get memories where quality_score >= 7 (stored in metadata/value)
        # For simplicity, we filter in python
        cursor.execute("""
            SELECT value FROM memories
            WHERE category = ?
            ORDER BY timestamp DESC
            LIMIT 50
        """, (category,))
        
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for row in rows:
            try:
                data = json.loads(row[0])
                if data.get("quality_score", 0) >= 7:
                    results.append(data)
            except Exception:
                continue
                
        return sorted(results, key=lambda x: x.get("quality_score", 0), reverse=True)[:10]

# Global instance
_store = None

def get_store() -> PersistentMemoryStore:
    global _store
    if _store is None:
        db_path = str(settings.paths.base_dir / "backend" / "data" / "memory.sqlite")
        _store = PersistentMemoryStore(db_path)
    return _store


def remember_success(
    agent_name: str,
    step_name: str,
    user_request_type: str,
    pattern: Dict[str, Any],
    quality_score: int,
) -> None:
    """Remember a successful pattern."""
    if quality_score < 7:
        return
    
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_request_type": user_request_type,
        "quality_score": quality_score,
        "pattern": pattern,
    }
    
    store = get_store()
    # workflow_id="global" for cross-project learning
    store.save_memory("global", f"{agent_name}:{step_name}", "pattern", entry)
    
    print(f"[MEMORY] 🧠 Remembered pattern for {agent_name}:{step_name}")


def recall_patterns(
    agent_name: str,
    step_name: str,
) -> List[Dict[str, Any]]:
    """Recall successful patterns."""
    store = get_store()
    return store.recall_patterns(agent_name, step_name)


def get_memory_hint(agent_name: str, step_name: str) -> str:
    """Get a hint from memory to include in agent instructions."""
    patterns = recall_patterns(agent_name, step_name)
    
    if not patterns:
        return ""
    
    best = patterns[0]
    return f"""
=== LEARNED FROM PREVIOUS SUCCESSFUL PROJECTS ===
Quality Score: {best.get('quality_score')}/10
Pattern: {json.dumps(best.get('pattern', {}), indent=2)[:300]}
"""
