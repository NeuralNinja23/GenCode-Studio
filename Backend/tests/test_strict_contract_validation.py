import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
import sys

# Ensure app/ is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.orchestration.self_healing_manager import SelfHealingManager

@pytest.mark.asyncio
async def test_validate_backend_can_start_strict_success():
    """
    Prove that backend validation passes ONLY if success rate is 100%.
    """
    with patch("app.orchestration.backend_probe.HTTPBackendProbe") as MockProbe, \
         patch("subprocess.run") as mock_run:
        
        # Mock successful app import
        mock_run.return_value.stdout = "SUCCESS"
        mock_run.return_value.stderr = ""
        
        # Mock probe instance
        probe_instance = MockProbe.return_value
        probe_instance.validate_all_contract_routes.return_value = {
            "passed": ["GET /api/tasks", "POST /api/tasks"],
            "failed": [],
            "total": 2,
            "success_rate": 1.0
        }
        
        mgr = SelfHealingManager(Path("/tmp/test"), project_id="test")
        
        # Should pass
        result = await mgr._validate_backend_can_start()
        assert result is True, "Should pass when success rate is 100%"

@pytest.mark.asyncio
async def test_validate_backend_can_start_strict_failure():
    """
    Prove that backend validation fails if success rate is < 100%.
    Even a single failure must cause the whole check to return False.
    """
    with patch("app.orchestration.backend_probe.HTTPBackendProbe") as MockProbe, \
         patch("subprocess.run") as mock_run:
        
        # Mock successful app import
        mock_run.return_value.stdout = "SUCCESS"
        mock_run.return_value.stderr = ""
        
        # Mock probe instance with 1 failure
        probe_instance = MockProbe.return_value
        # 90% success rate
        probe_instance.validate_all_contract_routes.return_value = {
            "passed": ["GET /api/tasks"] * 9,
            "failed": ["GET /api/missing -> 404"],
            "total": 10,
            "success_rate": 0.9
        }
        
        mgr = SelfHealingManager(Path("/tmp/test"), project_id="test")
        
        # Should FAIL
        result = await mgr._validate_backend_can_start()
        assert result is False, "Should FAIL when success rate is not 100%"

@pytest.mark.asyncio
async def test_validate_backend_can_start_strict_exception():
    """
    Prove that backend validation fails if an exception occurs (no fallback).
    """
    with patch("app.orchestration.backend_probe.HTTPBackendProbe") as MockProbe, \
         patch("subprocess.run") as mock_run:
        
        # Mock successful app import
        mock_run.return_value.stdout = "SUCCESS"
        
        # Mock probe instance raises exception
        probe_instance = MockProbe.return_value
        probe_instance.validate_all_contract_routes.side_effect = Exception("Connection refused")
        
        mgr = SelfHealingManager(Path("/tmp/test"), project_id="test")
        
        # Should FAIL
        result = await mgr._validate_backend_can_start()
        assert result is False, "Should FAIL when exception occurs"
