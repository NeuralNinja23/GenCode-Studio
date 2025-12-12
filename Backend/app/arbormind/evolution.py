# app/arbormind/evolution.py
"""
ArborMind Evolution Layer
-------------------------
Integrates the V-Vector Learning Store with the ArborMind Router.

This is the bridge that makes the system SELF-EVOLVING:
1. Before routing: Evolves options based on historical learning
2. After routing: Records decisions for future learning
3. On outcome: Updates the evolved V-vectors

The evolution process:
    Static V-vectors (registry.py)
           ↓
    Evolved V-vectors (learning history)
           ↓
    ArborMind Router makes decision
           ↓
    Outcome recorded
           ↓
    V-vectors updated (EMA)
           ↓
    Next decision benefits from learning
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from app.core.logging import log
from app.learning.v_vector_store import (
    get_v_vector_store,
    record_routing_decision,
    record_decision_outcome,
    get_evolved_options,
    VVectorStore
)
from app.learning.pattern_store import get_pattern_store
from app.learning.failure_store import get_failure_store


@dataclass
class EvolutionContext:
    """Context for tracking a routing decision through its lifecycle."""
    decision_id: str
    context_type: str
    archetype: str
    query_preview: str
    selected_option: str
    synthesized_value: Dict[str, Any]


# ═══════════════════════════════════════════════════════
# EVOLUTION HOOKS - Integrate with existing stores
# ═══════════════════════════════════════════════════════

class ArborMindEvolution:
    """
    ArborMind Evolution Manager.
    
    Manages the evolution of attention-based routing decisions.
    
    Integrates:
    - VVectorStore (routing decisions)
    - PatternStore (successful patterns)
    - FailureStore (anti-patterns)
    """
    
    def __init__(self):
        self._active_decisions: Dict[str, EvolutionContext] = {}
        self._v_store: Optional[VVectorStore] = None
    
    @property
    def v_store(self) -> VVectorStore:
        if self._v_store is None:
            self._v_store = get_v_vector_store()
        return self._v_store
    
    def evolve_options(
        self,
        context_type: str,
        archetype: str,
        options: List[Dict[str, Any]],
        enhance_from_patterns: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Apply evolution to a list of options before routing.
        
        This is called BEFORE the attention router makes a decision.
        It modifies the V-vectors based on historical learning.
        
        Args:
            context_type: Type of routing (e.g., "tool_selection")
            archetype: Project archetype
            options: Original options from registry
            enhance_from_patterns: Also check PatternStore for hints
            
        Returns:
            Evolved options with adjusted V-vectors
        """
        # Step 1: Apply V-vector evolution from decision history
        evolved = get_evolved_options(context_type, archetype, options)
        
        # Step 2: Enhance with insights from PatternStore (successful patterns)
        if enhance_from_patterns:
            evolved = self._enhance_from_patterns(context_type, archetype, evolved)
        
        # Step 3: Apply warnings from FailureStore (anti-patterns)
        evolved = self._apply_failure_warnings(context_type, archetype, evolved)
        
        return evolved
    
    def _enhance_from_patterns(
        self,
        context_type: str,
        archetype: str,
        options: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Enhance options with insights from successful patterns."""
        try:
            pattern_store = get_pattern_store()
            
            # Get patterns for this archetype (step = context_type for mapping)
            patterns = pattern_store.retrieve_patterns(
                archetype=archetype,
                step=context_type,
                min_quality=8.0,  # Only very successful patterns
                limit=3
            )
            
            if not patterns:
                return options
            
            # Extract common configurations from successful patterns
            # This is a soft hint, not a hard override
            successful_configs = {}
            for pattern in patterns:
                if hasattr(pattern, 'file_patterns') and pattern.file_patterns:
                    for fp in pattern.file_patterns:
                        if isinstance(fp, dict) and 'config' in fp:
                            for k, v in fp['config'].items():
                                if k not in successful_configs:
                                    successful_configs[k] = []
                                successful_configs[k].append(v)
            
            if not successful_configs:
                return options
            
            # Apply hints to options (soft blend)
            enhanced = []
            for opt in options:
                opt_copy = dict(opt)
                value = dict(opt.get("value", {}))
                
                for k, vals in successful_configs.items():
                    if k in value:
                        # Average of successful values
                        if all(isinstance(v, (int, float)) for v in vals):
                            hint_val = sum(vals) / len(vals)
                            # Soft blend with 20% weight for pattern hints
                            value[k] = value[k] * 0.8 + hint_val * 0.2
                
                opt_copy["value"] = value
                enhanced.append(opt_copy)
            
            log("EVOLUTION", f"📚 Enhanced with {len(patterns)} successful patterns")
            return enhanced
            
        except Exception as e:
            log("EVOLUTION", f"⚠️ Pattern enhancement failed: {e}")
            return options
    
    def _apply_failure_warnings(
        self,
        context_type: str,
        archetype: str,
        options: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Apply warnings and confidence adjustments from failure history.
        
        CRITICAL INSIGHT:
        - Failures tell us "don't trust this config"
        - But they DON'T tell us "reduce by 30%"
        - Maybe the fix needs MORE edits, not fewer!
        
        So we:
        1. LOWER CONFIDENCE in failed options (make router less likely to pick them)
        2. Add "_unreliable" flag so router can deprioritize
        3. Let the EMA from SUCCESSES determine the actual correct values
        
        The direction of adjustment comes from PatternStore + VVectorStore
        successes, NOT from failure penalties.
        """
        try:
            # ═══════════════════════════════════════════════════════
            # SOURCE 1: Anti-patterns from V-vector store
            # ═══════════════════════════════════════════════════════
            anti_patterns = self.v_store.get_anti_patterns_for_context(
                context_type, archetype, limit=5
            )
            
            # ═══════════════════════════════════════════════════════
            # SOURCE 2: Failures from FailureStore
            # ═══════════════════════════════════════════════════════
            failure_store = get_failure_store()
            failures = failure_store.retrieve_relevant_failures(
                agent=context_type,
                step=archetype,
                limit=5
            )
            
            # Get option-specific failures
            option_specific_failures = {}
            for opt in options:
                opt_id = opt.get("id", "")
                if opt_id:
                    opt_failures = failure_store.retrieve_relevant_failures(
                        agent=context_type,
                        step=opt_id,
                        limit=2
                    )
                    if opt_failures:
                        option_specific_failures[opt_id] = opt_failures
            
            if not anti_patterns and not failures and not option_specific_failures:
                return options
            
            # ═══════════════════════════════════════════════════════
            # APPLY CONFIDENCE PENALTIES (NOT VALUE CHANGES)
            # ═══════════════════════════════════════════════════════
            anti_option_ids = {ap["option"] for ap in anti_patterns}
            warned = []
            
            for opt in options:
                opt_copy = dict(opt)
                value = dict(opt.get("value", {}))
                opt_id = opt.get("id", "")
                
                reliability_factor = 1.0  # 1.0 = fully reliable
                failure_reasons = []
                
                # Check anti-patterns (from V-vector store)
                if opt_id in anti_option_ids:
                    ap_meta = next((ap for ap in anti_patterns if ap["option"] == opt_id), {})
                    success_rate = ap_meta.get("success_rate", 0.5)
                    
                    # Lower reliability based on success rate
                    # 0% success → reliability = 0.3
                    # 50% success → reliability = 0.65
                    # 100% success → reliability = 1.0
                    reliability_factor = 0.3 + (success_rate * 0.7)
                    
                    opt_copy["_warning"] = "historically_unreliable"
                    opt_copy["_warning_meta"] = ap_meta
                    failure_reasons.append(f"success rate: {success_rate:.0%}")
                
                # Check option-specific failures
                if opt_id in option_specific_failures:
                    fail_list = option_specific_failures[opt_id]
                    occurrence_count = sum(f.occurrence_count for f in fail_list)
                    
                    opt_copy["_failure_history"] = [
                        {
                            "error_type": f.error_type,
                            "description": f.description[:100],
                            "occurrence_count": f.occurrence_count
                        }
                        for f in fail_list
                    ]
                    
                    # More failures = less reliable
                    # 1 failure → reliability *= 0.9
                    # 5+ failures → reliability *= 0.5
                    failure_penalty = max(0.5, 1.0 - (occurrence_count * 0.1))
                    reliability_factor *= failure_penalty
                    failure_reasons.append(f"{occurrence_count} failures recorded")
                
                # ═══════════════════════════════════════════════════════
                # KEY: Inject reliability as a ROUTING SIGNAL, not a value change
                # The router uses this to weight attention scores
                # ═══════════════════════════════════════════════════════
                if reliability_factor < 1.0:
                    opt_copy["_reliability"] = reliability_factor
                    opt_copy["_failure_reasons"] = failure_reasons
                    
                    # Add a "soft" routing hint - this DOES affect selection
                    # but doesn't change the actual V-vector values
                    if "_routing_penalty" not in value:
                        value["_routing_penalty"] = 1.0 - reliability_factor
                    
                    log("EVOLUTION", f"⚠️ '{opt_id}' reliability: {reliability_factor:.0%} ({', '.join(failure_reasons)})")
                
                opt_copy["value"] = value
                warned.append(opt_copy)
            
            total_warnings = len(anti_patterns) + len(option_specific_failures)
            if total_warnings > 0:
                log("EVOLUTION", f"🔴 Marked {total_warnings} options with reliability warnings")
            
            return warned
            
        except Exception as e:
            log("EVOLUTION", f"⚠️ Failure warning failed: {e}")
            return options
    
    def start_tracking(
        self,
        query: str,
        context_type: str,
        archetype: str,
        selected_option: str,
        synthesized_value: Dict[str, Any],
        attention_weights: Dict[str, float]
    ) -> str:
        """
        Start tracking a routing decision.
        
        This is called AFTER the attention router makes a decision.
        Returns a decision_id that should be passed to complete_tracking.
        
        Args:
            query: The original query
            context_type: Type of routing
            archetype: Project archetype
            selected_option: The option that was selected
            synthesized_value: The V-vector configuration used
            attention_weights: The attention distribution
            
        Returns:
            decision_id for later outcome recording
        """
        decision_id = record_routing_decision(
            query=query,
            context_type=context_type,
            archetype=archetype,
            selected_option=selected_option,
            synthesized_value=synthesized_value,
            attention_weights=attention_weights
        )
        
        if decision_id:
            self._active_decisions[decision_id] = EvolutionContext(
                decision_id=decision_id,
                context_type=context_type,
                archetype=archetype,
                query_preview=query[:100],
                selected_option=selected_option,
                synthesized_value=synthesized_value
            )
        
        return decision_id
    
    def complete_tracking(
        self,
        decision_id: str,
        success: bool,
        quality_score: float,
        details: str = ""
    ) -> bool:
        """
        Complete tracking by recording the outcome.
        
        This is the FEEDBACK signal that drives learning.
        
        Args:
            decision_id: The ID from start_tracking
            success: Whether the decision led to success
            quality_score: 0.0 to 10.0 quality rating
            details: Why it succeeded or failed
            
        Returns:
            True if outcome was recorded
        """
        outcome = "success" if success else "failure"
        if 4.0 <= quality_score < 7.0:
            outcome = "partial"
        
        result = record_decision_outcome(
            decision_id=decision_id,
            outcome=outcome,
            score=quality_score,
            details=details
        )
        
        # Clean up active tracking
        if decision_id in self._active_decisions:
            ctx = self._active_decisions.pop(decision_id)
            
            # Also record to PatternStore if successful
            if success and quality_score >= 7.0:
                self._record_to_pattern_store(ctx, quality_score)
            
            # Record to FailureStore if failed
            if not success and quality_score < 4.0:
                self._record_to_failure_store(ctx, details)
        
        return result
    
    def _record_to_pattern_store(self, ctx: EvolutionContext, score: float):
        """Cross-record successful patterns for redundancy."""
        try:
            pattern_store = get_pattern_store()
            pattern_store.store_success(
                archetype=ctx.archetype,
                agent=ctx.context_type,
                step=ctx.selected_option,
                quality_score=score,
                files=[{"config": ctx.synthesized_value, "query": ctx.query_preview}],
                entity_type="v_vector_success",
                user_request=ctx.query_preview
            )
        except Exception as e:
            log("EVOLUTION", f"⚠️ Failed to cross-record to PatternStore: {e}")
    
    def _record_to_failure_store(self, ctx: EvolutionContext, details: str):
        """Cross-record failures for anti-pattern learning."""
        try:
            failure_store = get_failure_store()
            failure_store.record_failure(
                archetype=ctx.archetype,
                agent=ctx.context_type,
                step=ctx.selected_option,
                error_type="routing_failure",
                description=f"V-vector routing failed: {details[:200]}",
                code_snippet=str(ctx.synthesized_value)[:200],
                fix_summary=""
            )
        except Exception as e:
            log("EVOLUTION", f"⚠️ Failed to cross-record to FailureStore: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get evolution statistics."""
        v_stats = self.v_store.get_learning_stats()
        
        try:
            pattern_store = get_pattern_store()
            pattern_stats = pattern_store.get_stats()
        except Exception as e:
            log("EVOLUTION", f"Failed to get pattern stats: {e}")
            pattern_stats = {}
        
        return {
            "v_vector_learning": v_stats,
            "pattern_learning": pattern_stats,
            "active_decisions": len(self._active_decisions)
        }


# ═══════════════════════════════════════════════════════
# Global Instance & Integration Helpers
# ═══════════════════════════════════════════════════════

_evolution_manager: Optional[ArborMindEvolution] = None


def get_evolution_manager() -> ArborMindEvolution:
    """Get the global ArborMind evolution manager."""
    global _evolution_manager
    if _evolution_manager is None:
        _evolution_manager = ArborMindEvolution()
    return _evolution_manager


# ═══════════════════════════════════════════════════════
# HIGH-LEVEL API FOR ROUTER INTEGRATION
# ═══════════════════════════════════════════════════════

def evolve_before_routing(
    context_type: str,
    archetype: str,
    options: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Called by router BEFORE making a decision.
    Returns evolved options.
    """
    return get_evolution_manager().evolve_options(context_type, archetype, options)


def track_routing_decision(
    query: str,
    context_type: str,
    archetype: str,
    selected_option: str,
    synthesized_value: Dict[str, Any],
    attention_weights: Dict[str, float]
) -> str:
    """
    Called by router AFTER making a decision.
    Returns decision_id for outcome tracking.
    """
    return get_evolution_manager().start_tracking(
        query, context_type, archetype,
        selected_option, synthesized_value, attention_weights
    )


def report_routing_outcome(
    decision_id: str,
    success: bool,
    quality_score: float,
    details: str = ""
) -> bool:
    """
    Called when the outcome of a routing decision is known.
    This is the learning signal.
    """
    return get_evolution_manager().complete_tracking(
        decision_id, success, quality_score, details
    )


def get_evolution_stats() -> Dict[str, Any]:
    """Get overall evolution statistics."""
    return get_evolution_manager().get_stats()
