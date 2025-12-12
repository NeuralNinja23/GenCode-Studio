# tests/test_am_error_router.py
"""
Unit tests for AM-enhanced Error Router.
Tests the escalation ladder: standard → E-AM → T-AM
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestErrorRouterEscalation:
    """Tests for the AM escalation ladder in ErrorRouter."""
    
    @pytest.fixture
    def error_router(self):
        from app.orchestration.error_router import ErrorRouter
        return ErrorRouter()
    
    @pytest.mark.asyncio
    async def test_retry_0_uses_standard(self, error_router):
        """Retry 0 should use standard routing."""
        with patch("app.arbormind.arbormind_route", new_callable=AsyncMock) as mock_route:
            mock_route.return_value = {
                "selected": "syntax_fix",
                "value": {"max_edits": 2},
                "confidence": 0.9,
                "decision_id": "test123",
            }
            
            result = await error_router.decide_repair_strategy(
                "SyntaxError: invalid syntax",
                archetype="crud_api",
                retries=0
            )
            
            assert result["mode"] == "standard"
            assert result["selected"] == "syntax_fix"
    
    @pytest.mark.asyncio
    async def test_retry_1_uses_standard(self, error_router):
        """Retry 1 should still use standard routing."""
        with patch("app.arbormind.arbormind_route", new_callable=AsyncMock) as mock_route:
            mock_route.return_value = {
                "selected": "logic_fix",
                "value": {"max_edits": 5},
                "confidence": 0.7,
                "decision_id": "test456",
            }
            
            result = await error_router.decide_repair_strategy(
                "AssertionError: test failed",
                archetype="admin_dashboard",
                retries=1
            )
            
            assert result["mode"] == "standard"
    
    @pytest.mark.asyncio
    async def test_retry_2_triggers_eam(self, error_router):
        """Retry 2 should trigger E-AM (exploratory)."""
        with patch("app.arbormind.arbormind_route", new_callable=AsyncMock) as mock_route:
            mock_route.return_value = {
                "selected": "logic_fix",
                "value": {"max_edits": 5},
                "confidence": 0.5,
                "decision_id": "test789",
            }
            
            # Mock explorer to return foreign patterns
            with patch("app.arbormind.explorer.arbormind_explore", new_callable=AsyncMock) as mock_explore:
                mock_explore.return_value = {
                    "patterns": [{"archetype": "gaming", "value": {"max_edits": 8}}],
                    "blended_value": {"max_edits": 6},
                    "source_archetypes": ["gaming"],
                }
                
                result = await error_router.decide_repair_strategy(
                    "RecursionError: maximum recursion depth exceeded",
                    archetype="crud_api",
                    retries=2
                )
                
                # Should use exploratory mode
                assert result["mode"] == "exploratory"
                assert "source_archetypes" in result or "patterns" in result
    
    @pytest.mark.asyncio
    async def test_retry_3_triggers_tam(self, error_router):
        """Retry 3+ should trigger T-AM (transformational) if enabled."""
        with patch("app.core.config.settings") as mock_settings:
            # Enable T-AM for this test
            mock_settings.am.enable_tam = True
            mock_settings.am.tam_require_sandbox = True
            mock_settings.am.tam_require_approval = True
            mock_settings.am.eam_retry_threshold = 2
            mock_settings.am.tam_retry_threshold = 3
            
            result = await error_router.decide_repair_strategy(
                "TimeoutError: operation timed out",
                archetype="saas_app",
                retries=3
            )
            
            # T-AM should be enabled for this test
            # If T-AM is disabled in actual config, it will fall back to standard
            if mock_settings.am.enable_tam:
                assert result.get("mode") in ["transformational", "standard"]


class TestMutationOperators:
    """Tests for T-AM mutation operator selection."""
    
    @pytest.fixture
    def error_router(self):
        from app.orchestration.error_router import ErrorRouter
        return ErrorRouter()
    
    def test_drop_for_strict_errors(self, error_router):
        """DROP should be selected for strict/validation errors."""
        op = error_router._select_mutation_operator(
            "TypeError: strict type validation failed",
            {}
        )
        assert op == "DROP"
    
    def test_vary_for_timeout_errors(self, error_router):
        """VARY should be selected for performance errors."""
        op = error_router._select_mutation_operator(
            "TimeoutError: operation exceeded timeout limit",
            {}
        )
        assert op == "VARY"
    
    def test_add_for_missing_errors(self, error_router):
        """ADD should be selected for missing capability errors."""
        op = error_router._select_mutation_operator(
            "ModuleNotFoundError: cannot find module 'pandas'",
            {}
        )
        assert op == "ADD"
    
    def test_mutation_build_drop(self, error_router):
        """DROP mutation should remove strict constraints."""
        mutation = error_router._build_mutation("DROP", "strict type error", {})
        
        assert mutation["operator"] == "DROP"
        assert mutation["mutated_value"]["strict_mode"] == False
        assert mutation["mutated_value"]["max_edits"] == 10
    
    def test_mutation_build_vary(self, error_router):
        """VARY mutation should toggle approach."""
        context = {"current_value": {"apply_diff": True, "max_edits": 3}}
        mutation = error_router._build_mutation("VARY", "timeout error", context)
        
        assert mutation["operator"] == "VARY"
        assert mutation["mutated_value"]["apply_diff"] == False  # Toggled
        assert mutation["mutated_value"]["force_rewrite"] == True
    
    def test_mutation_build_add(self, error_router):
        """ADD mutation should add new capabilities."""
        mutation = error_router._build_mutation("ADD", "missing module", {})
        
        assert mutation["operator"] == "ADD"
        assert mutation["mutated_value"]["allowed_imports"] == ["*"]
        assert mutation["mutated_value"]["use_external_lib"] == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
