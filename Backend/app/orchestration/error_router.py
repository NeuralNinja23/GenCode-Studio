# app/orchestration/error_router.py
"""
FAST v2 Error Router (Self-Evolving + AM)

Maps FAST v2 step failures to the correct repair action.
Used by the healing pipeline to determine what to repair.

SELF-EVOLUTION: Repair strategy decisions are tracked and outcomes
fed back to improve future routing decisions.

AM EXTENSION (ArborMind):
- Standard routing for first attempts
- E-AM (Exploratory) after 2+ retries: Inject foreign patterns
- T-AM (Transformational) after 3+ retries: Mutate constraints
"""
from typing import Dict, Optional, Any, List
from app.core.logging import log
from app.core.config import settings
from app.orchestration.artifact_types import Artifact


class ErrorRouter:
    """
    Maps FAST v2 step failures to the correct repair action.
    
    When step X fails, this tells us what artifact needs repair.
    
    SELF-EVOLVING: Tracks repair decisions and learns from outcomes.
    AM-ENABLED: Escalates through creative reasoning modes on retry.
    """
    
    # Map steps to artifact names for repair (using centralized Artifact enum)
    STEP_TO_ARTIFACT = {
        "backend_implementation": Artifact.BACKEND_VERTICAL,
        "BACKEND_IMPLEMENTATION": Artifact.BACKEND_VERTICAL,
        "system_integration": Artifact.BACKEND_MAIN,
        "SYSTEM_INTEGRATION": Artifact.BACKEND_MAIN,
        "frontend_integration": Artifact.FRONTEND_API,
        "FRONTEND_INTEGRATION": Artifact.FRONTEND_API,
    }
    
    # Priority order for repair (lower = higher priority)
    REPAIR_PRIORITY = {
        Artifact.BACKEND_VERTICAL: 1,
        Artifact.BACKEND_MAIN: 2,
        Artifact.FRONTEND_API: 3,
    }
    
    # Store last decision_id for outcome reporting
    _last_decision_id: str = ""
    _last_archetype: str = "unknown"
    _last_mode: str = "standard"

    def route(self, step: str) -> Artifact:
        """Get the artifact name to repair for a failed step."""
        return self.STEP_TO_ARTIFACT.get(step, Artifact.NOOP)

    def is_repairable(self, step: str) -> bool:
        """Check if a step can be repaired."""
        return step in self.STEP_TO_ARTIFACT or step.upper() in self.STEP_TO_ARTIFACT

    def get_repair_priority(self, step: str) -> int:
        """Get repair priority (lower = higher priority)."""
        artifact = self.route(step)
        return self.REPAIR_PRIORITY.get(artifact, 99)

    def get_repair_order(self, failed_steps: list) -> list:
        """Sort failed steps by repair priority."""
        return sorted(failed_steps, key=lambda s: self.get_repair_priority(s))

    async def decide_repair_strategy(
        self, 
        error_log: str,
        archetype: str = "unknown",
        retries: int = 0,
        max_retries: int = 3,
        context: Dict[str, Any] = None
    ) -> dict:
        """
        Use Attention + AM to decide the best repair strategy.
        
        ESCALATION LADDER:
        - retries=0-1: Standard routing (sharp attention)
        - retries=2: E-AM (inject foreign patterns)
        - retries=3+: T-AM (mutate constraints)
        
        Args:
            error_log: The error message to analyze
            archetype: Project archetype for context-aware evolution
            retries: Current retry count (for AM escalation)
            max_retries: Maximum retries before T-AM
            context: Additional context for decision making
        
        Returns:
            Dict with 'selected' strategy ID, 'value' configuration,
            'mode' (standard/exploratory/transformational), and 'decision_id'
        """
        context = context or {}
        self._last_archetype = archetype
        
        # ═══════════════════════════════════════════════════════
        # CONVERGENT PATH (Standard Routing)
        # ═══════════════════════════════════════════════════════
        if retries < settings.am.eam_retry_threshold:
            return await self._standard_route(error_log, archetype)
        
        # ═══════════════════════════════════════════════════════
        # E-AM PATH (Exploratory - Foreign Patterns)
        # ═══════════════════════════════════════════════════════
        if retries < settings.am.tam_retry_threshold:
            if settings.am.enable_eam:
                log("AM", f"🔄 Retry {retries}: Escalating to E-AM (Exploratory)")
                eam_result = await self._exploratory_route(error_log, archetype)
                if eam_result.get("patterns"):
                    self._last_mode = "exploratory"
                    return eam_result
            
            # Fallback to standard if E-AM didn't find patterns
            return await self._standard_route(error_log, archetype)
        
        # ═══════════════════════════════════════════════════════
        # T-AM PATH (Transformational - Constraint Mutation)
        # ═══════════════════════════════════════════════════════
        if settings.am.enable_tam:
            log("AM", f"🔮 Retry {retries}: Escalating to T-AM (Transformational)")
            self._last_mode = "transformational"
            return await self._transformational_route(error_log, archetype, context)
        
        # T-AM disabled, fall back to standard
        log("AM", "⚠️ T-AM disabled, using standard route")
        return await self._standard_route(error_log, archetype)

    async def _standard_route(self, error_log: str, archetype: str) -> dict:
        """Standard attention-based routing."""
        from app.arbormind.router import arbormind_route
        
        strategies = self._get_repair_strategies()
        
        result = await arbormind_route(
            error_log[:500], 
            strategies,
            context_type="repair_strategy",
            archetype=archetype
        )
        
        self._last_decision_id = result.get("decision_id", "")
        self._last_mode = "standard"
        result["mode"] = "standard"
        
        # Default to logic_fix if low confidence
        if result["confidence"] < 0.15:
            return {
                "selected": "logic_fix",
                "value": strategies[2]["value"],
                "decision_id": self._last_decision_id,
                "confidence": result["confidence"],
                "evolved": result.get("evolved", False),
                "mode": "standard"
            }
        
        result["decision_id"] = self._last_decision_id
        return result

    async def _exploratory_route(self, error_log: str, archetype: str) -> dict:
        """E-AM: Inject foreign patterns from other archetypes."""
        try:
            from app.arbormind.explorer import arbormind_explore
            
            foreign = await arbormind_explore(archetype, error_log)
            
            if foreign.get("patterns"):
                # Blend standard strategy with foreign insights
                standard_result = await self._standard_route(error_log, archetype)
                
                return {
                    "selected": standard_result.get("selected", "logic_fix"),
                    "value": self._merge_values(
                        standard_result.get("value", {}),
                        foreign.get("blended_value", {})
                    ),
                    "decision_id": self._last_decision_id,
                    "confidence": standard_result.get("confidence", 0.5),
                    "mode": "exploratory",
                    "patterns": foreign["patterns"],
                    "source_archetypes": foreign.get("source_archetypes", []),
                    "entropy": foreign.get("entropy", 0),
                }
            
            return {"patterns": [], "mode": "exploratory"}
            
        except Exception as e:
            log("E-AM", f"⚠️ Exploratory routing failed: {e}")
            return {"patterns": [], "mode": "exploratory", "error": str(e)}

    async def _transformational_route(
        self, 
        error_log: str, 
        archetype: str,
        context: Dict[str, Any]
    ) -> dict:
        """T-AM: Mutate constraints when fundamentally stuck."""
        # Select mutation operator based on error type
        mutation_op = self._select_mutation_operator(error_log, context)
        mutation = self._build_mutation(mutation_op, error_log, context)
        
        return {
            "selected": "mutation",
            "value": mutation["mutated_value"],
            "decision_id": self._last_decision_id,
            "mode": "transformational",
            "mutation": mutation,
            "apply_mode": "sandbox" if settings.am.tam_require_sandbox else "direct",
            "require_approval": settings.am.tam_require_approval,
        }

    def _select_mutation_operator(self, error_log: str, context: Dict) -> str:
        """
        Select T-AM mutation operator based on error analysis.
        
        Operators:
        - DROP: Remove a constraint
        - VARY: Modify a constraint using analogy
        - ADD: Introduce a new constraint
        """
        error_lower = error_log.lower()
        
        # DROP: Good for overly strict constraints
        if any(kw in error_lower for kw in ["strict", "validation", "schema", "type"]):
            return "DROP"
        
        # VARY: Good for wrong approach
        if any(kw in error_lower for kw in ["timeout", "memory", "performance", "slow"]):
            return "VARY"
        
        # ADD: Good for missing capabilities
        if any(kw in error_lower for kw in ["not found", "missing", "undefined", "cannot"]):
            return "ADD"
        
        # Default to VARY (most flexible)
        return "VARY"

    def _build_mutation(
        self, 
        operator: str, 
        error_log: str, 
        context: Dict
    ) -> Dict[str, Any]:
        """Build the mutation based on operator and context."""
        base_value = context.get("current_value", {
            "max_edits": 3,
            "apply_diff": True,
            "verify_after_fix": True,
            "strict_mode": True,
        })
        
        mutated_value = dict(base_value)
        mutation_desc = ""
        
        if operator == "DROP":
            # Drop strict constraints
            mutated_value["strict_mode"] = False
            mutated_value["verify_types"] = False
            mutated_value["max_edits"] = 10
            mutation_desc = "Dropped strict_mode and type verification"
            
        elif operator == "VARY":
            # Vary the approach
            mutated_value["apply_diff"] = not base_value.get("apply_diff", True)
            mutated_value["force_rewrite"] = True
            mutated_value["max_edits"] = base_value.get("max_edits", 3) * 2
            mutation_desc = "Varied approach: toggled diff mode, increased edit limit"
            
        elif operator == "ADD":
            # Add new constraints/capabilities
            mutated_value["allowed_imports"] = ["*"]  # Allow any import
            mutated_value["use_external_lib"] = True
            mutated_value["search_solutions"] = True
            mutation_desc = "Added: allow any imports, external libs, solution search"
        
        log("T-AM", f"🔮 Mutation [{operator}]: {mutation_desc}")
        
        return {
            "operator": operator,
            "original_value": base_value,
            "mutated_value": mutated_value,
            "description": mutation_desc,
        }

    def _merge_values(self, base: Dict, foreign: Dict) -> Dict:
        """Merge base strategy values with foreign pattern values."""
        merged = dict(base)
        
        for key, val in foreign.items():
            if key not in merged:
                merged[key] = val
            elif isinstance(val, (int, float)) and isinstance(merged[key], (int, float)):
                # Average numeric values
                merged[key] = (merged[key] + val) / 2
            # Keep base value for non-numeric conflicts
        
        return merged

    def _get_repair_strategies(self) -> List[Dict]:
        """Get the standard repair strategies."""
        return [
            {
                "id": "syntax_fix", 
                "description": "SyntaxError, IndentationError, invalid syntax, missing parentheses",
                "value": {
                    "max_edits": 2,
                    "apply_diff": True,
                    "verify_after_fix": True,
                    "retry_on_fail": 0,
                    "priority": 0.9
                }
            },
            {
                "id": "dependency_fix", 
                "description": "ModuleNotFoundError, ImportError, No module named, package not found",
                "value": {
                    "max_edits": 1,
                    "apply_diff": False,
                    "verify_after_fix": True,
                    "retry_on_fail": 1,
                    "priority": 0.8
                }
            },
            {
                "id": "logic_fix", 
                "description": "AssertionError, wrong output, infinite loop, 404/500 error, logic bug",
                "value": {
                    "max_edits": 5,
                    "apply_diff": False,
                    "verify_after_fix": True,
                    "retry_on_fail": 1,
                    "priority": 0.6
                }
            },
            {
                "id": "config_fix", 
                "description": "KeyError: 'ENV_VAR', connection refused, configuration missing",
                "value": {
                    "max_edits": 1,
                    "apply_diff": True,
                    "verify_after_fix": False,
                    "retry_on_fail": 0,
                    "priority": 0.7
                }
            },
            {
                "id": "stub_fix",
                "description": "NotImplementedError, pass, TODO, placeholder, not implemented",
                "value": {
                    "max_edits": 3,
                    "apply_diff": False,
                    "verify_after_fix": True,
                    "retry_on_fail": 0,
                    "priority": 0.5
                }
            }
        ]
    
    def report_repair_outcome(
        self, 
        decision_id: Optional[str] = None,
        success: bool = False,
        quality_score: float = 5.0,
        details: str = ""
    ) -> bool:
        """
        Report the outcome of a repair strategy decision.
        
        This feeds back into the self-evolution system to improve
        future repair strategy selections.
        """
        try:
            from app.arbormind.router import report_routing_outcome
            
            did = decision_id or self._last_decision_id
            if not did:
                return False
            
            # Include AM mode in details
            if self._last_mode != "standard":
                details = f"[{self._last_mode.upper()}] {details}"
            
            return report_routing_outcome(
                decision_id=did,
                success=success,
                quality_score=quality_score,
                details=details
            )
        except Exception:
            return False
    
    def get_last_decision_id(self) -> str:
        """Get the decision_id from the last repair strategy decision."""
        return self._last_decision_id
    
    def get_last_mode(self) -> str:
        """Get the AM mode used in the last decision."""
        return self._last_mode
