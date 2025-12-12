# app/learning/failure_store.py
"""
Failure Memory & Learning System
-------------------------------
Stores detailed records of failures (syntax errors, logic bugs, test failures)
so agents can avoid repeating the same mistakes in future projects.

This acts as a "long-term anti-pattern memory".
"""
import sqlite3
import hashlib
from pathlib import Path
from typing import Optional, List
from datetime import datetime, timezone
from dataclasses import dataclass

from app.core.logging import log


@dataclass
class FailurePattern:
    """A documented failure worth avoiding."""
    failure_id: str
    archetype: str
    agent: str
    step: str
    error_type: str  # "syntax", "logic", "timeout", "test_failure"
    description: str  # Human/LLM readable summary of what went wrong
    code_snippet: str  # The problematic code
    fix_summary: str  # How it was eventually fixed (if known)
    timestamp: str
    occurrence_count: int = 1


class FailureStore:
    """
    SQLite-based storage for failure patterns.
    DB: backend/data/failure_memory.db
    """
    
    DB_NAME = "failure_memory.db"
    
    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = storage_dir / self.DB_NAME
        self._init_db()
    
    def _init_db(self):
        """Initialize the SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            # Main failure table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS failures (
                    failure_id TEXT PRIMARY KEY,
                    archetype TEXT NOT NULL,
                    agent TEXT NOT NULL,
                    step TEXT NOT NULL,
                    error_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    code_snippet TEXT,
                    fix_summary TEXT,
                    timestamp TEXT NOT NULL,
                    occurrence_count INTEGER DEFAULT 1
                )
            """)
            # Indices for fast lookups during prompting
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_fail_context 
                ON failures(agent, step)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_fail_type 
                ON failures(error_type)
            """)
            conn.commit()
    
    def record_failure(
        self,
        archetype: str,
        agent: str,
        step: str,
        error_type: str,
        description: str,
        code_snippet: str = "",
        fix_summary: str = "",
    ) -> str:
        """
        Record a failure. If a similar failure exists, increment its count.
        Returns the failure_id.
        """
        # Generate ID based on the nature of the error (deduplication)
        # We handle similarity by hashing the error description + code snippet signature
        fail_key = f"{agent}:{step}:{error_type}:{description[:50]}"
        failure_id = hashlib.sha256(fail_key.encode()).hexdigest()
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                existing = conn.execute(
                    "SELECT occurrence_count FROM failures WHERE failure_id = ?",
                    (failure_id,)
                ).fetchone()
                
                timestamp = datetime.now(timezone.utc).isoformat()
                
                if existing:
                    new_count = existing[0] + 1
                    conn.execute("""
                        UPDATE failures 
                        SET occurrence_count = ?, timestamp = ?, fix_summary = ?
                        WHERE failure_id = ?
                    """, (new_count, timestamp, fix_summary or "", failure_id))
                    log("LEARNING", f"📝 Updated existing failure pattern (count={new_count})")
                else:
                    conn.execute("""
                        INSERT INTO failures 
                        (failure_id, archetype, agent, step, error_type, description, 
                         code_snippet, fix_summary, timestamp, occurrence_count)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        failure_id, archetype, agent, step, error_type, 
                        description, code_snippet, fix_summary, timestamp, 1
                    ))
                    log("LEARNING", f"🧠 Recorded NEW failure pattern: {description[:50]}...")
                
                conn.commit()
                return failure_id
                
        except Exception as e:
            log("LEARNING", f"⚠️ Failed to record failure: {e}")
            return ""

    def retrieve_relevant_failures(
        self,
        agent: str,
        step: str,
        limit: int = 3
    ) -> List[FailurePattern]:
        """
        Get similar failures to warn the agent before they start.
        Returns top recurrent failures for this specific agent/step.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Fetch failures sorted by frequency (occurrence_count)
                rows = conn.execute("""
                    SELECT * FROM failures 
                    WHERE agent = ? AND step = ?
                    ORDER BY occurrence_count DESC
                    LIMIT ?
                """, (agent, step, limit)).fetchall()
                
                return [
                    FailurePattern(
                        failure_id=row["failure_id"],
                        archetype=row["archetype"],
                        agent=row["agent"],
                        step=row["step"],
                        error_type=row["error_type"],
                        description=row["description"],
                        code_snippet=row["code_snippet"],
                        fix_summary=row["fix_summary"],
                        timestamp=row["timestamp"],
                        occurrence_count=row["occurrence_count"]
                    )
                    for row in rows
                ]
        except Exception as e:
            log("LEARNING", f"⚠️ Failed to retrieve failures: {e}")
            return []

    def get_anti_pattern_context(self, agent: str, step: str) -> str:
        """
        Generate a 'KNOWN PITFALLS' string for the system prompt.
        """
        failures = self.retrieve_relevant_failures(agent, step, limit=3)
        if not failures:
            return ""
        
        context = "\n\n⛔ KNOWN PITFALLS (Avoid these mistakes from previous projects):\n"
        
        for f in failures:
            context += f"❌ {f.error_type.upper()}: {f.description}\n"
            if f.code_snippet:
                # Show distinct, short snippet
                snippet = f.code_snippet.strip()
                if len(snippet) > 80:
                    snippet = snippet[:80] + "..."
                context += f"   Bad Pattern: `{snippet}`\n"
            if f.fix_summary:
                context += f"   ✅ Fix: {f.fix_summary}\n"
            context += "\n"
            
        return context


# Global Instance
_failure_store: Optional[FailureStore] = None

def get_failure_store() -> FailureStore:
    global _failure_store
    if _failure_store is None:
        # Store in project's backend/data directory
        # Same logic as pattern_store
        root_dir = Path(__file__).parent.parent.parent
        storage_dir = root_dir / "data"
        _failure_store = FailureStore(storage_dir)
    return _failure_store

