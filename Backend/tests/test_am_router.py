# tests/test_am_router.py
"""
Unit tests for AM (ArborMind) router functions.
Tests C-AM combinational blending, entropy scoring, and mode detection.
"""
import pytest
import numpy as np
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.arbormind.router import (
    arbormind_attention,
    arbormind_blend,
    should_use_combinational_mode,
    DEFAULT_SCALE_STANDARD,
    DEFAULT_SCALE_COMBINATIONAL,
    ENTROPY_HIGH_THRESHOLD,
)


class TestCreativeAttention:
    """Tests for the creative_attention function."""
    
    def test_standard_mode_sharp_attention(self):
        """Standard mode should produce sharp (winner-takes-all) weights."""
        Q = np.array([1.0, 0.0, 0.0])
        K = np.array([
            [1.0, 0.0, 0.0],   # Exact match
            [0.5, 0.5, 0.0],   # Partial match
            [0.0, 1.0, 0.0],   # No match
        ])
        
        result = arbormind_attention(Q, K, mode="standard")
        
        # Standard mode should heavily favor the first option
        assert result["weights"][0] > 0.9, "Standard mode should make sharp decisions"
        assert result["mode"] == "standard"
        assert "entropy" in result
    
    def test_combinational_mode_soft_blending(self):
        """Combinational mode should produce softer weight distribution."""
        Q = np.array([0.7, 0.5, 0.2])
        K = np.array([
            [0.8, 0.4, 0.1],   # Similar
            [0.6, 0.6, 0.3],   # Also similar
            [0.5, 0.5, 0.3],   # Also similar
        ])
        
        result = arbormind_attention(Q, K, mode="combinational")
        
        # Combinational mode should distribute weights more evenly
        max_weight = np.max(result["weights"])
        assert max_weight < 0.9, "Combinational mode should blend multiple options"
        assert result["mode"] == "combinational"
    
    def test_entropy_calculation(self):
        """Entropy should be lower for confident decisions."""
        # Sharp Q/K match
        Q_sharp = np.array([1.0, 0.0, 0.0])
        K = np.array([
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ])
        result_sharp = arbormind_attention(Q_sharp, K, mode="standard")
        
        # Ambiguous Q that matches multiple K
        Q_ambig = np.array([0.6, 0.6, 0.5])
        result_ambig = arbormind_attention(Q_ambig, K, mode="standard")
        
        # Sharp decision should have lower entropy
        assert result_sharp["entropy"] < result_ambig["entropy"]
    
    def test_value_blending_output(self):
        """When V is provided, should return blended_value."""
        Q = np.array([1.0, 0.5])
        K = np.array([
            [1.0, 0.0],
            [0.5, 0.8],
        ])
        V = [
            {"max_files": 10, "strict": True},
            {"max_files": 5, "strict": False},
        ]
        
        result = arbormind_attention(Q, K, V, mode="combinational")
        
        assert "blended_value" in result
        assert "max_files" in result["blended_value"]


class TestBlendValues:
    """Tests for the blend_values function."""
    
    def test_numeric_blend(self):
        """Numeric values should be weighted averages."""
        weights = np.array([0.7, 0.3])
        values = [
            {"max_files": 10, "priority": 0.8},
            {"max_files": 4, "priority": 0.4},
        ]
        
        result = arbormind_blend(weights, values)
        
        # 0.7 * 10 + 0.3 * 4 = 8.2
        assert abs(result["max_files"] - 8.2) < 0.01
        # 0.7 * 0.8 + 0.3 * 0.4 = 0.68
        assert abs(result["priority"] - 0.68) < 0.01
    
    def test_string_winner_takes_all(self):
        """String values should use the highest weight option."""
        weights = np.array([0.3, 0.7])
        values = [
            {"mode": "fast", "type": "A"},
            {"mode": "slow", "type": "B"},
        ]
        
        result = arbormind_blend(weights, values)
        
        # Winner (index 1) should provide string values
        assert result["mode"] == "slow"
        assert result["type"] == "B"
    
    def test_boolean_winner_takes_all(self):
        """Boolean values should use the highest weight option."""
        weights = np.array([0.6, 0.4])
        values = [
            {"verify": True, "strict": False},
            {"verify": False, "strict": True},
        ]
        
        result = arbormind_blend(weights, values)
        
        assert result["verify"] == True
        assert result["strict"] == False
    
    def test_missing_keys_handled(self):
        """Missing keys in some dicts should be handled gracefully."""
        weights = np.array([0.5, 0.5])
        values = [
            {"a": 1, "b": 2},
            {"b": 4, "c": 6},  # Missing 'a', has extra 'c'
        ]
        
        result = arbormind_blend(weights, values)
        
        assert "a" in result
        assert "b" in result
        assert "c" in result
    
    def test_empty_values_list(self):
        """Empty values list should return empty dict."""
        result = arbormind_blend(np.array([]), [])
        assert result == {}


class TestModeDetection:
    """Tests for AM mode detection."""
    
    def test_high_entropy_suggests_combinational(self):
        """High entropy should suggest combinational mode."""
        assert should_use_combinational_mode(2.0) == True
        assert should_use_combinational_mode(1.8) == True
    
    def test_low_entropy_suggests_standard(self):
        """Low entropy should suggest standard mode."""
        assert should_use_combinational_mode(0.5) == False
        assert should_use_combinational_mode(1.0) == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
