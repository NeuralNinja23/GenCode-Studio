# app/agents/state.py
# GenCode Studio - State Management with Emergent Features (Windows-Compatible)
# Last Updated: November 7, 2025
# Includes: Persistent Memory, Telemetry, Reflex Loop, Context Compression, API Call Tracking

import sqlite3
import json
import hashlib
import os  # ✅ WINDOWS COMPATIBILITY FIX
import tempfile  # ✅ WINDOWS COMPATIBILITY FIX
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict

# ================================================================
# LEGACY: API Call Tracking (for api_client.py compatibility)
# ================================================================

api_call_counter: Dict[str, int] = {}

class ModelStat(TypedDict):
    """Statistics for model usage"""
    model_name: str
    total_calls: int
    successful_calls: int
    failed_calls: int
    total_tokens: int
    average_latency_seconds: float

model_stats: Dict[str, ModelStat] = {}

def initialize_counter(project_id: Optional[str] = None):
    """Initialize API call counter for a project"""
    global api_call_counter
    api_call_counter = {}
    if project_id:
        print(f"[STATE] Initialized counter for project: {project_id}")

def get_counter(agent_name: str) -> int:
    """Get current count for an agent"""
    return api_call_counter.get(agent_name, 0)

def increment_counter(agent_name: str) -> int:
    """Increment and return counter for an agent"""
    current = api_call_counter.get(agent_name, 0)
    api_call_counter[agent_name] = current + 1
    return api_call_counter[agent_name]

# ================================================================
# PHASE 1: PERSISTENT MEMORY STORE (Long-term Context)
# ================================================================

class PersistentMemoryStore:
    """SQLite-backed persistent memory for architectural decisions"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        # ✅ WINDOWS FIX: Create parent directories if they don't exist
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

    def get_memory(self, workflow_id: str, category: str, key: str) -> Optional[Any]:
        """Retrieve a specific memory"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT value FROM memories
            WHERE workflow_id = ? AND category = ? AND key = ?
            ORDER BY timestamp DESC LIMIT 1
        """, (workflow_id, category, key))

        result = cursor.fetchone()
        conn.close()

        if result:
            return json.loads(result[0])
        return None

    def get_category_memories(self, workflow_id: str, category: str) -> List[Dict]:
        """Get all memories for a category"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT key, value, timestamp, metadata FROM memories
            WHERE workflow_id = ? AND category = ?
            ORDER BY timestamp DESC
        """, (workflow_id, category))

        results = cursor.fetchall()
        conn.close()

        return [
            {
                "key": row[0],
                "value": json.loads(row[1]),
                "timestamp": row[2],
                "metadata": json.loads(row[3])
            }
            for row in results
        ]

# ================================================================
# PHASE 2: WORKFLOW METRICS (Telemetry Tracking)
# ================================================================

class WorkflowMetrics:
    """Comprehensive workflow performance tracking"""

    def __init__(self):
        self.start_time = datetime.now(timezone.utc).timestamp()
        self.steps: List[Dict[str, Any]] = []
        self.tool_calls: List[Dict[str, Any]] = []
        self.errors: List[Dict[str, Any]] = []

    def record_step(self, step_name: str, duration_seconds: float, success: bool = True):
        """Record completion of a workflow step"""
        self.steps.append({
            "step": step_name,
            "duration_seconds": duration_seconds,
            "success": success,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    def record_tool_call(
        self, 
        tool_name: str, 
        success: bool, 
        duration_seconds: Optional[float] = None,
        error_message: Optional[str] = None
    ):
        """Record tool execution"""
        self.tool_calls.append({
            "tool": tool_name,
            "success": success,
            "duration_seconds": duration_seconds,
            "error": error_message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    def record_error(self, error_type: str, message: str, context: Optional[Dict] = None):
        """Record workflow error"""
        self.errors.append({
            "type": error_type,
            "message": message,
            "context": context or {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    def get_report(self) -> Dict[str, Any]:
        """Generate comprehensive metrics report"""
        total_duration = datetime.now(timezone.utc).timestamp() - self.start_time

        successful_steps = sum(1 for s in self.steps if s["success"])
        failed_steps = len(self.steps) - successful_steps

        successful_tools = sum(1 for t in self.tool_calls if t["success"])
        failed_tools = len(self.tool_calls) - successful_tools

        step_durations = [s["duration_seconds"] for s in self.steps if s.get("duration_seconds")]
        avg_step_duration = sum(step_durations) / len(step_durations) if step_durations else 0

        tool_durations = [t["duration_seconds"] for t in self.tool_calls if t.get("duration_seconds")]
        avg_tool_duration = sum(tool_durations) / len(tool_durations) if tool_durations else 0

        return {
            "total_duration_seconds": total_duration,
            "steps_completed": len(self.steps),
            "steps_successful": successful_steps,
            "steps_failed": failed_steps,
            "tool_calls_total": len(self.tool_calls),
            "tool_calls_successful": successful_tools,
            "tool_calls_failed": failed_tools,
            "errors_count": len(self.errors),
            "average_step_duration_seconds": avg_step_duration,
            "average_tool_duration_seconds": avg_tool_duration,
            "steps_detail": self.steps,
            "tool_calls_detail": self.tool_calls,
            "errors_detail": self.errors,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

# ================================================================
# PHASE 3: CONTEXT COMPRESSION (Adaptive Context Trimming)
# ================================================================

class ContextCompressor:
    """Intelligently compress conversation history to save tokens"""

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Rough token estimation (1 token ≈ 4 characters)"""
        return len(text) // 4

    @staticmethod
    def create_summary(messages: List[Dict[str, str]]) -> str:
        """Create a concise summary of older messages"""
        if not messages:
            return ""

        steps_completed = []
        files_created = []
        decisions_made = []

        for msg in messages:
            content = msg.get("content", "")

            if "STEP" in content.upper():
                steps_completed.append(content[:100])

            if "created" in content.lower() or "wrote" in content.lower():
                files_created.append(content[:80])

            if "decision" in content.lower() or "architecture" in content.lower():
                decisions_made.append(content[:100])

        summary_parts = []

        if steps_completed:
            summary_parts.append(f"Steps: {'; '.join(steps_completed[:3])}")

        if files_created:
            summary_parts.append(f"Files: {'; '.join(files_created[:5])}")

        if decisions_made:
            summary_parts.append(f"Decisions: {'; '.join(decisions_made[:3])}")

        return "[CONTEXT_SUMMARY] " + " | ".join(summary_parts)

    @staticmethod
    def condense_chat_history(
        messages: List[Dict[str, str]], 
        keep_recent: int = 5
    ) -> List[Dict[str, str]]:
        """Condense chat history by summarizing older messages"""
        if len(messages) <= keep_recent:
            return messages

        old_messages = messages[:-keep_recent]
        recent_messages = messages[-keep_recent:]

        summary_text = ContextCompressor.create_summary(old_messages)

        return [
            {"role": "system", "content": summary_text}
        ] + recent_messages

# ================================================================
# LEGACY: Virtual File System & Phase Memories
# ================================================================

VIRTUAL_FILE_SYSTEM: List[Dict[str, str]] = []
CONTRACT_CONTENT: str = ""
counters: Dict[str, int] = {}
phase_memories: Dict[str, Any] = {}

def update_file_system(files: List[Dict[str, str]]):
    """Update virtual file system"""
    global VIRTUAL_FILE_SYSTEM
    VIRTUAL_FILE_SYSTEM = files

def get_file_system() -> List[Dict[str, str]]:
    """Get current virtual file system"""
    return VIRTUAL_FILE_SYSTEM

def save_phase_memory(project_path: str, key: str, value: Any):
    """Save phase memory (in-memory)"""
    phase_memories[f"{project_path}:{key}"] = value

def get_phase_memory(project_path: str, key: str) -> Optional[Any]:
    """Get phase memory"""
    return phase_memories.get(f"{project_path}:{key}")

def save_contract(content: str):
    """Save contract content"""
    global CONTRACT_CONTENT
    CONTRACT_CONTENT = content

def get_contract() -> str:
    """Get contract content"""
    return CONTRACT_CONTENT