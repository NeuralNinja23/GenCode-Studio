# app/learning/pattern_store.py
"""
Pattern Memory & Learning System

Stores successful code patterns so quality improves over time.
After a successful "admin_dashboard" build with 9/10 quality,
the next "admin_dashboard" request can start from proven patterns.

Benefits:
- Quality improves over time (7/10 → 9/10 on first attempt)
- Faster generation (reuse proven patterns)
- Fewer revisions needed
"""
import json
import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from dataclasses import dataclass
import hashlib

from app.core.logging import log


@dataclass
class CodePattern:
    """A successful code pattern worth remembering."""
    pattern_id: str
    archetype: str  # e.g., "admin_dashboard", "ecommerce"
    agent: str  # "Derek", "Luna", "Victoria"
    step: str  # "frontend_mock", "backend_models", etc.
    quality_score: float
    file_patterns: List[Dict[str, Any]]  # Successful file structures
    entity_type: str  # Primary entity type
    user_request_summary: str
    timestamp: str
    success_count: int = 1


class PatternStore:
    """
    SQLite-based pattern storage for learning from successes.
    
    Stores:
    - Successful archetypes and their code structures
    - High-quality patterns indexed by context
    - Retrieval hints for similar requests
    """
    
    DB_NAME = "pattern_memory.db"
    
    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = storage_dir / self.DB_NAME
        self._init_db()
    
    def _init_db(self):
        """Initialize the SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS patterns (
                    pattern_id TEXT PRIMARY KEY,
                    archetype TEXT NOT NULL,
                    agent TEXT NOT NULL,
                    step TEXT NOT NULL,
                    quality_score REAL NOT NULL,
                    file_patterns TEXT NOT NULL,
                    entity_type TEXT,
                    user_request_summary TEXT,
                    timestamp TEXT NOT NULL,
                    success_count INTEGER DEFAULT 1
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_archetype 
                ON patterns(archetype, step, quality_score DESC)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_agent_step 
                ON patterns(agent, step, quality_score DESC)
            """)
            conn.commit()
    
    def store_success(
        self,
        archetype: str,
        agent: str,
        step: str,
        quality_score: float,
        files: List[Dict[str, Any]],
        entity_type: str = "",
        user_request: str = "",
    ) -> Optional[str]:
        """
        Store a successful pattern for future reference.
        
        Only stores patterns with quality >= 7 (worth learning from).
        
        Args:
            archetype: Application archetype (e.g., "admin_dashboard")
            agent: Agent that generated it
            step: Workflow step
            quality_score: Marcus quality score (1-10)
            files: Generated files with structure (not full content)
            entity_type: Primary entity type
            user_request: Original user request (first 200 chars)
            
        Returns:
            pattern_id if stored, None if quality too low
        """
        if quality_score < 7:
            return None
        
        # Create pattern ID from key attributes
        pattern_id = self._generate_pattern_id(archetype, agent, step, entity_type)
        
        # Extract file structure (not full content)
        file_patterns = []
        for f in files:
            path = f.get("path", "")
            content = f.get("content", "")
            
            file_patterns.append({
                "path": path,
                "size": len(content),
                "has_testid": "data-testid" in content,
                "imports": self._extract_imports(path, content),
                "structure_hash": hashlib.md5(content[:500].encode()).hexdigest()[:8],
            })
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Check if pattern exists
                existing = conn.execute(
                    "SELECT success_count, quality_score FROM patterns WHERE pattern_id = ?",
                    (pattern_id,)
                ).fetchone()
                
                if existing:
                    # Update success count and quality if better
                    new_count = existing[0] + 1
                    new_quality = max(existing[1], quality_score)
                    
                    conn.execute("""
                        UPDATE patterns 
                        SET success_count = ?, quality_score = ?, timestamp = ?
                        WHERE pattern_id = ?
                    """, (new_count, new_quality, datetime.now(timezone.utc).isoformat(), pattern_id))
                    
                    log("LEARNING", f"📈 Updated pattern {pattern_id[:16]}... (count={new_count}, quality={new_quality})")
                else:
                    # Insert new pattern
                    conn.execute("""
                        INSERT INTO patterns 
                        (pattern_id, archetype, agent, step, quality_score, file_patterns, 
                         entity_type, user_request_summary, timestamp, success_count)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        pattern_id,
                        archetype,
                        agent,
                        step,
                        quality_score,
                        json.dumps(file_patterns),
                        entity_type,
                        user_request[:200],
                        datetime.now(timezone.utc).isoformat(),
                        1,
                    ))
                    
                    log("LEARNING", f"🧠 Stored new pattern for {archetype}/{step} (quality={quality_score})")
                
                conn.commit()
                return pattern_id
                
        except Exception as e:
            log("LEARNING", f"⚠️ Failed to store pattern: {e}")
            return None
    
    def retrieve_patterns(
        self,
        archetype: str,
        step: str,
        min_quality: float = 7.0,
        limit: int = 3,
    ) -> List[CodePattern]:
        """
        Retrieve successful patterns for a given archetype and step.
        
        Args:
            archetype: Application archetype
            step: Workflow step
            min_quality: Minimum quality score to consider
            limit: Maximum patterns to return
            
        Returns:
            List of CodePattern objects, sorted by quality
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                rows = conn.execute("""
                    SELECT * FROM patterns 
                    WHERE archetype = ? AND step = ? AND quality_score >= ?
                    ORDER BY quality_score DESC, success_count DESC
                    LIMIT ?
                """, (archetype, step, min_quality, limit)).fetchall()
                
                patterns = []
                for row in rows:
                    patterns.append(CodePattern(
                        pattern_id=row["pattern_id"],
                        archetype=row["archetype"],
                        agent=row["agent"],
                        step=row["step"],
                        quality_score=row["quality_score"],
                        file_patterns=json.loads(row["file_patterns"]),
                        entity_type=row["entity_type"] or "",
                        user_request_summary=row["user_request_summary"] or "",
                        timestamp=row["timestamp"],
                        success_count=row["success_count"],
                    ))
                
                if patterns:
                    log("LEARNING", f"📚 Found {len(patterns)} patterns for {archetype}/{step}")
                
                return patterns
                
        except Exception as e:
            log("LEARNING", f"⚠️ Failed to retrieve patterns: {e}")
            return []
    
    def get_prompt_enhancement(
        self,
        archetype: str,
        step: str,
        agent: str,
    ) -> str:
        """
        Get a prompt enhancement based on learned patterns.
        
        Returns text to append to agent prompts to guide them
        toward proven successful patterns.
        """
        patterns = self.retrieve_patterns(archetype, step, min_quality=8.0, limit=2)
        
        if not patterns:
            return ""
        
        best = patterns[0]
        
        # Build enhancement text
        enhancement = f"""

═══════════════════════════════════════════════════════
🧠 LEARNED PATTERN (from {best.success_count} successful build(s))
═══════════════════════════════════════════════════════

For "{archetype}" applications, high-quality code typically includes:

📁 File Structure:
"""
        for fp in best.file_patterns[:5]:
            has_testid = "✅ has data-testid" if fp.get("has_testid") else ""
            enhancement += f"  - {fp['path']} (~{fp['size']} bytes) {has_testid}\n"
        
        if best.file_patterns and best.file_patterns[0].get("imports"):
            imports = best.file_patterns[0]["imports"][:5]
            enhancement += f"\n📦 Common Imports: {', '.join(imports)}\n"
        
        enhancement += f"""
⭐ This pattern achieved {best.quality_score}/10 quality.
   Follow this structure for best results.
═══════════════════════════════════════════════════════
"""
        return enhancement
    
    def get_stats(self) -> Dict[str, Any]:
        """Get learning statistics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                total = conn.execute("SELECT COUNT(*) FROM patterns").fetchone()[0]
                avg_quality = conn.execute("SELECT AVG(quality_score) FROM patterns").fetchone()[0]
                top_archetypes = conn.execute("""
                    SELECT archetype, COUNT(*) as count, AVG(quality_score) as avg_q
                    FROM patterns 
                    GROUP BY archetype 
                    ORDER BY count DESC 
                    LIMIT 5
                """).fetchall()
                
                return {
                    "total_patterns": total,
                    "avg_quality": round(avg_quality or 0, 2),
                    "top_archetypes": [
                        {"archetype": a, "count": c, "avg_quality": round(q, 2)}
                        for a, c, q in top_archetypes
                    ],
                }
        except Exception as e:
            return {"error": str(e)}
    
    def _generate_pattern_id(self, archetype: str, agent: str, step: str, entity_type: str) -> str:
        """Generate a unique pattern ID."""
        key = f"{archetype}:{agent}:{step}:{entity_type}"
        return hashlib.sha256(key.encode()).hexdigest()
    
    def _extract_imports(self, path: str, content: str) -> List[str]:
        """Extract import statements from code."""
        imports = []
        
        if path.endswith('.py'):
            for line in content.split('\n')[:20]:
                line = line.strip()
                if line.startswith('import ') or line.startswith('from '):
                    # Extract module name
                    parts = line.split()
                    if len(parts) >= 2:
                        imports.append(parts[1].split('.')[0])
        elif path.endswith(('.js', '.jsx', '.ts', '.tsx')):
            import re
            for match in re.finditer(r'import\s+.*?from\s+[\'"]([^\'"]+)[\'"]', content[:2000]):
                imports.append(match.group(1).split('/')[0])
        
        return list(set(imports))[:10]

    def penalize_pattern(
        self,
        archetype: str,
        agent: str,
        step: str,
        entity_type: str = "",
        penalty: float = 2.0,
    ) -> bool:
        """
        Retroactively penalize a pattern if it led to a failure later.
        
        This handles the "False Positive" problem where Marcus generates
        a high score for code that actually crashes during testing.
        
        Args:
            penalty: Amount to deduct from quality_score
        """
        pattern_id = self._generate_pattern_id(archetype, agent, step, entity_type)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                existing = conn.execute(
                    "SELECT quality_score, success_count FROM patterns WHERE pattern_id = ?",
                    (pattern_id,)
                ).fetchone()
                
                if existing:
                    old_score = existing[0]
                    new_score = max(1.0, old_score - penalty)
                    
                    # If score drops too low, reset success count too
                    if new_score < 6.0:
                        new_count = 0  # It's no longer a "proven" pattern
                    else:
                        new_count = existing[1]
                    
                    conn.execute("""
                        UPDATE patterns 
                        SET quality_score = ?, success_count = ?, timestamp = ?
                        WHERE pattern_id = ?
                    """, (new_score, new_count, datetime.now(timezone.utc).isoformat(), pattern_id))
                    
                    log("LEARNING", f"📉 Penalized pattern {pattern_id[:8]} (False Positive Detected): {old_score} → {new_score}")
                    conn.commit()
                    return True
                
            return False
        except Exception as e:
            log("LEARNING", f"⚠️ Failed to penalize pattern: {e}")
            return False



# Global instance
_pattern_store: Optional[PatternStore] = None


def get_pattern_store() -> PatternStore:
    """Get the global pattern store instance."""
    global _pattern_store
    if _pattern_store is None:
        # Store in project's backend/data directory
        # We assume this code runs from within the app, so we find the path relative to this file
        # File is in: app/learning/pattern_store.py
        # Root is: app/../..
        root_dir = Path(__file__).parent.parent.parent
        storage_dir = root_dir / "data"
        _pattern_store = PatternStore(storage_dir)
    return _pattern_store



def learn_from_success(
    archetype: str,
    agent: str,
    step: str,
    quality_score: float,
    files: List[Dict[str, Any]],
    **kwargs
) -> Optional[str]:
    """Convenience function to store successful patterns."""
    store = get_pattern_store()
    return store.store_success(archetype, agent, step, quality_score, files, **kwargs)


def get_learned_enhancement(archetype: str, step: str, agent: str) -> str:
    """Get prompt enhancement from learned patterns."""
    store = get_pattern_store()
    return store.get_prompt_enhancement(archetype, step, agent)
