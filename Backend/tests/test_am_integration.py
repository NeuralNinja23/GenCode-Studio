# tests/test_am_integration.py
"""
Integration tests for ArborMind (AM) system.
Verifies interactions between Router, ErrorRouter, and settings.
"""
import pytest
from unittest.mock import patch, AsyncMock
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings

class TestAMIntegration:

    @pytest.fixture
    def mock_explorer(self):
        """Mock the explorer module to avoid DB calls."""
        with patch("app.arbormind.explorer.arbormind_explore", new_callable=AsyncMock) as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_full_error_escalation_flow(self, mock_explorer):
        """Test the journey from Standard -> E-AM -> T-AM."""
        from app.orchestration.error_router import ErrorRouter
        
        router = ErrorRouter()
        
        # 1. Standard Mode (Retry 0)
        with patch("app.arbormind.arbormind_route", new_callable=AsyncMock) as mock_route:
            mock_route.return_value = {
                "selected": "code_fix", 
                "value": {"edits": 1}, 
                "confidence": 0.9,
                "decision_id": "d1"
            }
            
            res1 = await router.decide_repair_strategy("Error", "test_arch", retries=0)
            assert res1["mode"] == "standard"
            assert res1["decision_id"] == "d1"

        # 2. E-AM Mode (Retry 2)
        mock_explorer.return_value = {
            "patterns": [{"archetype": "foreign", "value": {}}],
            "blended_value": {"edits": 5},
            "source_archetypes": ["foreign"]
        }
        
        # We need to mock route_query for the standard fallback part of E-AM
        with patch("app.arbormind.arbormind_route", new_callable=AsyncMock) as mock_route:
            mock_route.return_value = {
                "selected": "code_fix", 
                "value": {"edits": 1}, 
                "confidence": 0.5
            }
            
            res2 = await router.decide_repair_strategy(
                "Error", 
                "test_arch", 
                retries=settings.am.eam_retry_threshold
            )
            
            assert res2["mode"] == "exploratory"
            assert res2["patterns"] is not None
            assert mock_explorer.called

        # 3. T-AM Mode (Retry 3+)
        # Ensure T-AM is enabled
        with patch.object(settings.am, "enable_tam", True):
            with patch.object(settings.am, "tam_retry_threshold", 3):
                
                res3 = await router.decide_repair_strategy(
                    "TimeoutError: process failed", 
                    "test_arch", 
                    retries=3,
                    context={"current_value": {"max_edits": 1}}
                )
                
                assert res3["mode"] == "transformational"
                assert "mutation" in res3
                assert res3["selected"] == "mutation"
                # Check VARY logic for TimeoutError
                assert res3["mutation"]["operator"] == "VARY" 

    def test_settings_propagation(self):
        """Verify settings affect logic checks."""
        from app.arbormind.router import should_use_combinational_mode
        
        # Default is 1.5
        assert should_use_combinational_mode(2.0) is True
        assert should_use_combinational_mode(1.0) is False
        
        # Change setting
        with patch.object(settings.am, "entropy_high", 0.8):
            # Now 1.0 should be True
            assert should_use_combinational_mode(1.0) is True

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
