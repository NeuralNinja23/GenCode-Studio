import pytest
import numpy as np
from unittest.mock import AsyncMock, patch
from app.arbormind import ArborMindRouter

# Mock embedding function to avoid API calls
async def mock_get_embedding(text):
    # Deterministic mock based on text content
    if "Option A" in text:
        return [1.0, 0.0]
    if "Option B" in text:
        return [0.0, 1.0]
    if "Query A" in text:
        return [1.0, 0.0]  # Matches A perfectly
    if "Query Mix" in text:
        return [0.707, 0.707]  # Matches both equally
    return [0.5, 0.5]

@pytest.mark.asyncio
async def test_attention_routing_exact_match():
    """Test standard routing where V=K (One clear winner)."""
    router = ArborMindRouter()
    
    options = [
        {"id": "opt_a", "description": "Option A", "value": {"speed": 100}},
        {"id": "opt_b", "description": "Option B", "value": {"speed": 0}}
    ]
    
    with patch("app.arbormind.router.get_embedding", side_effect=mock_get_embedding):
        result = await router.route("Query A", options)
        
    assert result["selected"] == "opt_a"
    # value should be close to opt_a's value (winner takes all logic dominates usually or high weight)
    # With [1,0] and [1,0], dot product is huge compared to [0,1]. Softmax will be ~1.0 for A.
    assert result["value"]["speed"] > 90

@pytest.mark.asyncio
async def test_attention_value_synthesis():
    """Test V!=K parameter synthesis (Blending)."""
    router = ArborMindRouter()
    
    options = [
        {"id": "opt_a", "description": "Option A", "value": {"param": 10.0}},
        {"id": "opt_b", "description": "Option B", "value": {"param": 20.0}}
    ]
    
    # Query Mix is [0.707, 0.707].
    # Dot product A: 0.707 * 1 + 0 = 0.707
    # Dot product B: 0.707 * 0 + 0.707 = 0.707
    # Scores are equal. Softmax should be 0.5, 0.5.
    # Blended param: 0.5*10 + 0.5*20 = 15.0
    
    with patch("app.arbormind.router.get_embedding", side_effect=mock_get_embedding):
        result = await router.route("Query Mix", options)
        
    synthesized_param = result["value"]["param"]
    print(f"Synthesized Param: {synthesized_param}")
    
    # Allow small float error
    assert 14.0 < synthesized_param < 16.0 

if __name__ == "__main__":
    # verification run manually if needed
    import asyncio
    asyncio.run(test_attention_value_synthesis())
