# app/learning/v_vector_store.py
"""
V-Vector Learning Store
-----------------------
Tracks routing decisions (V-vectors) and their outcomes to enable
the Self-Evolving Architecture.

Core Concept:
- Every routing decision (query → synthesized config) is recorded
- Outcomes (success/failure) are linked back to these decisions
- The system learns which V-vector configurations work best for which contexts

Database: backend/data/v_vector_history.db
"""
import json
import sqlite3
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from dataclasses import dataclass

from app.core.logging import log


@dataclass
class VVectorDecision:
    """A recorded V!=K routing decision."""
    decision_id: str
    query_hash: str  # Hash of the query (privacy-preserving)
    query_preview: str  # First 100 chars for debugging
    context_type: str  # "tool_selection", "error_routing", "file_context", etc.
    archetype: str  # Project archetype (e.g., "admin_dashboard")
    selected_option: str  # The option ID selected
    synthesized_value: Dict[str, Any]  # The actual V-vector (config) used
    attention_weights: Dict[str, float]  # The attention distribution
    timestamp: str
    outcome: Optional[str] = None  # "success", "failure", "partial"
    outcome_score: Optional[float] = None  # 0.0 to 10.0
    outcome_details: Optional[str] = None  # Why it succeeded/failed


@dataclass 
class EvolvedVVector:
    """A learned/evolved V-vector configuration."""
    context_key: str  # e.g., "tool_selection:admin_dashboard:code_generator"
    base_value: Dict[str, Any]  # Original static V-vector
    evolved_value: Dict[str, Any]  # Learned adjustments
    confidence: float  # How confident we are (based on sample size)
    success_rate: float  # Historical success rate
    sample_count: int  # Number of observations
    last_updated: str


class VVectorStore:
    """
    SQLite-based storage for V-vector learning.
    
    Two tables:
    1. decisions - Raw routing decisions with outcomes
    2. evolved_vectors - Learned V-vector adjustments
    """
    
    DB_NAME = "v_vector_history.db"
    
    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = storage_dir / self.DB_NAME
        self._init_db()
    
    def _init_db(self):
        """Initialize the SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            # Decisions table - raw routing decisions
            conn.execute("""
                CREATE TABLE IF NOT EXISTS decisions (
                    decision_id TEXT PRIMARY KEY,
                    query_hash TEXT NOT NULL,
                    query_preview TEXT,
                    context_type TEXT NOT NULL,
                    archetype TEXT NOT NULL,
                    selected_option TEXT NOT NULL,
                    synthesized_value TEXT NOT NULL,
                    attention_weights TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    outcome TEXT,
                    outcome_score REAL,
                    outcome_details TEXT
                )
            """)
            
            # Evolved vectors table - learned configurations
            conn.execute("""
                CREATE TABLE IF NOT EXISTS evolved_vectors (
                    context_key TEXT PRIMARY KEY,
                    base_value TEXT NOT NULL,
                    evolved_value TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    success_rate REAL NOT NULL,
                    sample_count INTEGER NOT NULL,
                    last_updated TEXT NOT NULL
                )
            """)
            
            # Indices for fast queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_decisions_context 
                ON decisions(context_type, archetype, selected_option)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_decisions_outcome 
                ON decisions(outcome)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_evolved_context
                ON evolved_vectors(context_key)
            """)
            
            conn.commit()
    
    def record_decision(
        self,
        query: str,
        context_type: str,
        archetype: str,
        selected_option: str,
        synthesized_value: Dict[str, Any],
        attention_weights: Dict[str, float],
    ) -> str:
        """
        Record a routing decision for future learning.
        
        Args:
            query: The original query text
            context_type: Type of routing (e.g., "tool_selection")
            archetype: Project archetype
            selected_option: The option ID that was selected
            synthesized_value: The V-vector configuration used
            attention_weights: The attention distribution
            
        Returns:
            decision_id for linking outcomes later
        """
        query_hash = hashlib.sha256(query.encode()).hexdigest()[:16]
        query_preview = query[:100]
        decision_id = hashlib.sha256(
            f"{query_hash}:{context_type}:{archetype}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:24]
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO decisions 
                    (decision_id, query_hash, query_preview, context_type, archetype,
                     selected_option, synthesized_value, attention_weights, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    decision_id,
                    query_hash,
                    query_preview,
                    context_type,
                    archetype,
                    selected_option,
                    json.dumps(synthesized_value),
                    json.dumps(attention_weights),
                    datetime.now(timezone.utc).isoformat()
                ))
                conn.commit()
                
            log("V_VECTOR", f"📊 Recorded decision: {context_type}/{selected_option}")
            return decision_id
            
        except Exception as e:
            log("V_VECTOR", f"⚠️ Failed to record decision: {e}")
            return ""
    
    def record_outcome(
        self,
        decision_id: str,
        outcome: str,
        outcome_score: float,
        outcome_details: str = ""
    ) -> bool:
        """
        Record the outcome of a routing decision.
        
        Args:
            decision_id: The ID from record_decision
            outcome: "success", "failure", or "partial"
            outcome_score: 0.0 to 10.0 quality score
            outcome_details: Explanation of outcome
            
        Returns:
            True if recorded successfully
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE decisions 
                    SET outcome = ?, outcome_score = ?, outcome_details = ?
                    WHERE decision_id = ?
                """, (outcome, outcome_score, outcome_details, decision_id))
                conn.commit()
                
            log("V_VECTOR", f"📈 Recorded outcome: {outcome} ({outcome_score:.1f}/10)")
            
            # Trigger learning update
            self._update_evolved_vector(decision_id)
            
            return True
            
        except Exception as e:
            log("V_VECTOR", f"⚠️ Failed to record outcome: {e}")
            return False
    
    def _update_evolved_vector(self, decision_id: str):
        """
        Update the evolved V-vector based on the new outcome.
        Uses Exponential Moving Average (EMA) for smooth updates.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Get the decision with outcome
                row = conn.execute("""
                    SELECT * FROM decisions WHERE decision_id = ?
                """, (decision_id,)).fetchone()
                
                if not row or not row["outcome"]:
                    return
                
                # Build context key for this type of decision
                context_key = f"{row['context_type']}:{row['archetype']}:{row['selected_option']}"
                
                # Get existing evolved vector or create new
                existing = conn.execute("""
                    SELECT * FROM evolved_vectors WHERE context_key = ?
                """, (context_key,)).fetchone()
                
                synthesized = json.loads(row["synthesized_value"])
                outcome_score = row["outcome_score"] or 0.0
                is_success = row["outcome"] == "success"
                
                if existing:
                    # Update existing with EMA
                    old_evolved = json.loads(existing["evolved_value"])
                    old_rate = existing["success_rate"]
                    old_count = existing["sample_count"]
                    
                    # EMA alpha (more recent = more weight)
                    alpha = min(0.3, 2.0 / (old_count + 2))
                    
                    # Update success rate
                    new_rate = (1 - alpha) * old_rate + alpha * (1.0 if is_success else 0.0)
                    
                    # Update evolved values (blend towards successful configs)
                    new_evolved = {}
                    for key, val in synthesized.items():
                        old_val = old_evolved.get(key, val)
                        if isinstance(val, (int, float)) and not isinstance(val, bool):
                            # Weight successful configs more heavily
                            weight = outcome_score / 10.0
                            new_evolved[key] = old_val * (1 - alpha * weight) + val * alpha * weight
                        else:
                            # For non-numeric, use winning value if successful
                            new_evolved[key] = val if is_success else old_val
                    
                    # Calculate confidence based on sample size
                    new_confidence = min(0.95, 1 - 1 / (old_count + 2))
                    
                    conn.execute("""
                        UPDATE evolved_vectors
                        SET evolved_value = ?, success_rate = ?, sample_count = ?,
                            confidence = ?, last_updated = ?
                        WHERE context_key = ?
                    """, (
                        json.dumps(new_evolved),
                        new_rate,
                        old_count + 1,
                        new_confidence,
                        datetime.now(timezone.utc).isoformat(),
                        context_key
                    ))
                else:
                    # Create new evolved vector
                    conn.execute("""
                        INSERT INTO evolved_vectors
                        (context_key, base_value, evolved_value, confidence, 
                         success_rate, sample_count, last_updated)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        context_key,
                        json.dumps(synthesized),  # Base is the first observed
                        json.dumps(synthesized),  # Evolved starts same as base
                        0.1,  # Low initial confidence
                        1.0 if is_success else 0.0,
                        1,
                        datetime.now(timezone.utc).isoformat()
                    ))
                
                conn.commit()
                log("V_VECTOR", f"🧬 Evolved V-vector: {context_key}")
                
        except Exception as e:
            log("V_VECTOR", f"⚠️ Failed to update evolved vector: {e}")
    
    def get_evolved_vector(
        self,
        context_type: str,
        archetype: str,
        option_id: str,
        min_confidence: float = 0.3
    ) -> Optional[Dict[str, Any]]:
        """
        Get the evolved V-vector for a specific context.
        
        Args:
            context_type: Type of routing decision
            archetype: Project archetype
            option_id: The option ID
            min_confidence: Minimum confidence to use evolved vector
            
        Returns:
            Evolved V-vector dict or None if not enough confidence
        """
        context_key = f"{context_type}:{archetype}:{option_id}"
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute("""
                    SELECT * FROM evolved_vectors 
                    WHERE context_key = ? AND confidence >= ?
                """, (context_key, min_confidence)).fetchone()
                
                if row:
                    evolved = json.loads(row["evolved_value"])
                    log("V_VECTOR", f"🎯 Using evolved vector (conf={row['confidence']:.2f}): {context_key}")
                    return {
                        "value": evolved,
                        "confidence": row["confidence"],
                        "success_rate": row["success_rate"],
                        "sample_count": row["sample_count"]
                    }
                return None
                
        except Exception as e:
            log("V_VECTOR", f"⚠️ Failed to get evolved vector: {e}")
            return None
    
    def get_adjustment_for_options(
        self,
        context_type: str,
        archetype: str,
        options: List[Dict[str, Any]],
        min_confidence: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Adjust a list of options based on learned V-vectors.
        
        This is the main entry point for self-evolution:
        - Takes static options from registry
        - Applies learned adjustments from history
        - Returns evolved options
        
        Args:
            context_type: Type of routing
            archetype: Project archetype
            options: Original options with static V-vectors
            min_confidence: Minimum confidence to apply evolution
            
        Returns:
            Options with evolved V-vectors where available
        """
        adjusted = []
        
        for opt in options:
            opt_copy = dict(opt)
            option_id = opt.get("id", "")
            
            # Try to get evolved vector
            evolved = self.get_evolved_vector(
                context_type, archetype, option_id, min_confidence
            )
            
            if evolved:
                # Blend evolved values with original
                original_value = opt.get("value", {})
                evolved_value = evolved["value"]
                
                # Create blended value
                blended = dict(original_value)
                for key, val in evolved_value.items():
                    if key in blended:
                        # Blend based on confidence
                        conf = evolved["confidence"]
                        orig = blended[key]
                        if isinstance(val, (int, float)) and isinstance(orig, (int, float)):
                            blended[key] = orig * (1 - conf) + val * conf
                        elif conf > 0.5:  # Use evolved for non-numeric only with high confidence
                            blended[key] = val
                
                opt_copy["value"] = blended
                opt_copy["_evolved"] = True
                opt_copy["_evolution_meta"] = {
                    "confidence": evolved["confidence"],
                    "success_rate": evolved["success_rate"],
                    "sample_count": evolved["sample_count"]
                }
            
            adjusted.append(opt_copy)
        
        evolved_count = sum(1 for o in adjusted if o.get("_evolved"))
        if evolved_count > 0:
            log("V_VECTOR", f"🧬 Applied evolution to {evolved_count}/{len(options)} options")
        
        return adjusted
    
    def get_learning_stats(self) -> Dict[str, Any]:
        """Get statistics about the learning system."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                decisions_count = conn.execute(
                    "SELECT COUNT(*) FROM decisions"
                ).fetchone()[0]
                
                outcomes_count = conn.execute(
                    "SELECT COUNT(*) FROM decisions WHERE outcome IS NOT NULL"
                ).fetchone()[0]
                
                evolved_count = conn.execute(
                    "SELECT COUNT(*) FROM evolved_vectors"
                ).fetchone()[0]
                
                avg_success_rate = conn.execute(
                    "SELECT AVG(success_rate) FROM evolved_vectors"
                ).fetchone()[0] or 0.0
                
                avg_confidence = conn.execute(
                    "SELECT AVG(confidence) FROM evolved_vectors"
                ).fetchone()[0] or 0.0
                
                return {
                    "total_decisions": decisions_count,
                    "decisions_with_outcomes": outcomes_count,
                    "evolved_vectors": evolved_count,
                    "avg_success_rate": avg_success_rate,
                    "avg_confidence": avg_confidence,
                    "coverage": outcomes_count / max(1, decisions_count)
                }
                
        except Exception as e:
            log("V_VECTOR", f"⚠️ Failed to get stats: {e}")
            return {}
    
    def get_anti_patterns_for_context(
        self,
        context_type: str,
        archetype: str,
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Get configurations that consistently failed for a context.
        Used to warn the system what NOT to do.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Find options with low success rates
                rows = conn.execute("""
                    SELECT context_key, base_value, evolved_value, success_rate, sample_count
                    FROM evolved_vectors
                    WHERE context_key LIKE ? 
                    AND success_rate < 0.3
                    AND sample_count >= 3
                    ORDER BY success_rate ASC
                    LIMIT ?
                """, (f"{context_type}:{archetype}:%", limit)).fetchall()
                
                return [
                    {
                        "option": row["context_key"].split(":")[-1],
                        "avoid_value": json.loads(row["evolved_value"]),
                        "success_rate": row["success_rate"],
                        "observations": row["sample_count"]
                    }
                    for row in rows
                ]
                
        except Exception as e:
            log("V_VECTOR", f"⚠️ Failed to get anti-patterns: {e}")
            return []
    
    def _seed_evolved_vector(
        self,
        context_type: str,
        archetype: str,
        option_id: str,
        evolved_value: Dict[str, Any],
        confidence: float,
        sample_count: int,
        source: str = "pretraining",
    ) -> bool:
        """
        Directly seed an evolved V-vector (for pre-training from GitHub).
        
        This bypasses the normal learning loop and directly inserts
        a learned configuration into the evolved_vectors table.
        
        Args:
            context_type: Type of routing decision
            archetype: Project archetype
            option_id: The option ID
            evolved_value: The learned V-vector values
            confidence: Confidence level (0-1)
            sample_count: Number of observations this is based on
            source: Source of the data (e.g., "github_pretraining")
            
        Returns:
            True if seeded successfully
        """
        context_key = f"{context_type}:{archetype}:{option_id}"
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Check if exists
                existing = conn.execute(
                    "SELECT sample_count FROM evolved_vectors WHERE context_key = ?",
                    (context_key,)
                ).fetchone()
                
                if existing:
                    # Merge with existing (weighted by sample counts)
                    old_count = existing[0]
                    total = old_count + sample_count
                    
                    # Get existing value
                    row = conn.execute(
                        "SELECT evolved_value, success_rate FROM evolved_vectors WHERE context_key = ?",
                        (context_key,)
                    ).fetchone()
                    
                    old_evolved = json.loads(row[0])
                    
                    # Blend values
                    new_evolved = {}
                    for key, val in evolved_value.items():
                        old_val = old_evolved.get(key, val)
                        if isinstance(val, (int, float)) and isinstance(old_val, (int, float)):
                            # Weighted average
                            new_evolved[key] = (old_val * old_count + val * sample_count) / total
                        else:
                            new_evolved[key] = val if sample_count > old_count else old_val
                    
                    new_conf = min(0.95, (old_count * confidence + sample_count * confidence) / total)
                    
                    conn.execute("""
                        UPDATE evolved_vectors
                        SET evolved_value = ?, confidence = ?, sample_count = ?, last_updated = ?
                        WHERE context_key = ?
                    """, (
                        json.dumps(new_evolved),
                        new_conf,
                        total,
                        datetime.now(timezone.utc).isoformat(),
                        context_key
                    ))
                else:
                    # Insert new
                    conn.execute("""
                        INSERT INTO evolved_vectors
                        (context_key, base_value, evolved_value, confidence, 
                         success_rate, sample_count, last_updated)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        context_key,
                        json.dumps(evolved_value),  # Base = evolved for seeding
                        json.dumps(evolved_value),
                        confidence,
                        0.8,  # Assume reasonable success rate for seeded data
                        sample_count,
                        datetime.now(timezone.utc).isoformat()
                    ))
                
                conn.commit()
                log("V_VECTOR", f"🌱 Seeded V-vector: {context_key} (n={sample_count}, source={source})")
                return True
                
        except Exception as e:
            log("V_VECTOR", f"⚠️ Failed to seed V-vector: {e}")
            return False

    async def search_patterns(self, query: str, exclude_archetype: str, limit: int = 5) -> List[Dict]:
        """
        Search for successful patterns in foreign archetypes.
        Used by E-AM to find solutions from other domains.
        """
        results = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                # Select all vectors that don't belong to the excluded archetype
                # context_key format: "{context_type}:{archetype}:{option_id}"
                # We use NOT LIKE to exclude current archetype
                cursor = conn.execute("""
                    SELECT context_key, evolved_value, confidence, success_rate 
                    FROM evolved_vectors 
                    WHERE context_key NOT LIKE ? 
                    ORDER BY success_rate DESC, confidence DESC 
                    LIMIT ?
                """, (f"%:{exclude_archetype}:%", limit * 5))
                
                rows = cursor.fetchall()
                for row in rows:
                    parts = row["context_key"].split(":")
                    if len(parts) >= 3:
                        ctx_type = parts[0]
                        arch = parts[1]
                        
                        # Double check exclusion
                        if arch == exclude_archetype:
                            continue
                        
                        # Only return patterns relevant to the query context type if possible
                        # If query mentions "security", we might favor security context types?
                        # For now, return generally successful patterns
                            
                        try:
                            val = json.loads(row["evolved_value"])
                            results.append({
                                "archetype": arch,
                                "context_type": ctx_type,
                                "value": val,
                                "score": row["success_rate"] * row["confidence"],
                                "description": f"Learned {ctx_type} pattern from {arch}",
                                "context_key": row["context_key"]
                            })
                        except Exception as e:
                            log("V_VECTOR", f"Row decode failed: {e}")
                            continue
                        
            # Pseudo-ranking could happen here if we matched 'query' to 'val' keys
            return results[:limit]
            
        except Exception as e:
            log("V_VECTOR", f"⚠️ Search patterns failed: {e}")
            return []


# ═══════════════════════════════════════════════════════
# Global Instance & Helpers
# ═══════════════════════════════════════════════════════

_v_vector_store: Optional[VVectorStore] = None


def get_v_vector_store() -> VVectorStore:
    """Get the global V-vector store instance."""
    global _v_vector_store
    if _v_vector_store is None:
        root_dir = Path(__file__).parent.parent.parent
        storage_dir = root_dir / "data"
        _v_vector_store = VVectorStore(storage_dir)
    return _v_vector_store


def record_routing_decision(
    query: str,
    context_type: str,
    archetype: str,
    selected_option: str,
    synthesized_value: Dict[str, Any],
    attention_weights: Dict[str, float]
) -> str:
    """Convenience function to record a routing decision."""
    return get_v_vector_store().record_decision(
        query, context_type, archetype, 
        selected_option, synthesized_value, attention_weights
    )


def record_decision_outcome(
    decision_id: str,
    outcome: str,
    score: float,
    details: str = ""
) -> bool:
    """Convenience function to record outcome."""
    return get_v_vector_store().record_outcome(
        decision_id, outcome, score, details
    )


def get_evolved_options(
    context_type: str,
    archetype: str,
    options: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Convenience function to get evolved options."""
    return get_v_vector_store().get_adjustment_for_options(
        context_type, archetype, options
    )
