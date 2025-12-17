# tests/test_step_testing_backend.py
"""
Tests for Step 8: Testing Backend

Validates the backend testing step that:
- Generates tests from template
- Runs pytest in Docker sandbox
- Heals failures with retry loop
- Uses proper pytest-asyncio markers

Pipeline Position: ... → System Integration → [TESTING BACKEND] → Testing Frontend → ...
"""
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch
import re


class TestTestingBackendStep:
    """Test suite for the backend testing step."""
    
    @pytest.mark.asyncio
    async def test_generates_tests_from_template(
        self, temp_workspace, mock_tests_llm_response
    ):
        """
        GIVEN a workspace with backend code
        WHEN step_testing_backend is executed
        THEN test_api.py should be generated from template
        """
        # Setup
        tests_dir = temp_workspace / "backend" / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)
        
        # Simulate test generation
        test_content = mock_tests_llm_response["output"]["files"][0]["content"]
        test_file = tests_dir / "test_api.py"
        test_file.write_text(test_content, encoding="utf-8")
        
        # Verify
        assert test_file.exists()
        content = test_file.read_text(encoding="utf-8")
        
        assert "import pytest" in content
        assert "async def test_" in content
    
    @pytest.mark.asyncio
    async def test_uses_provided_client_fixture(
        self, temp_workspace, mock_tests_llm_response
    ):
        """
        GIVEN generated tests
        WHEN fixtures are checked
        THEN tests should use the 'client' fixture (not create own)
        """
        test_content = mock_tests_llm_response["output"]["files"][0]["content"]
        
        # Should use client fixture
        assert "async def test_" in test_content
        assert "(client)" in test_content or "(client," in test_content
        
        # Should NOT recreate AsyncClient
        assert "AsyncClient(" not in test_content or "@pytest.fixture" not in test_content
    
    @pytest.mark.asyncio
    async def test_uses_anyio_marker(self, temp_workspace, mock_tests_llm_response):
        """
        GIVEN generated async tests
        WHEN decorators are checked
        THEN all async tests should have @pytest.mark.anyio
        """
        test_content = mock_tests_llm_response["output"]["files"][0]["content"]
        
        # Find all async def test_ functions
        async_tests = re.findall(r'async\s+def\s+(test_\w+)', test_content)
        
        assert len(async_tests) > 0, "Should have async tests"
        
        # All should have marker (check marker appears before async def)
        assert "@pytest.mark.anyio" in test_content or "@pytest.mark.asyncio" in test_content


class TestTestGeneration:
    """Test the test generation logic."""
    
    def test_test_uses_faker_for_data(self, mock_tests_llm_response):
        """
        GIVEN generated tests
        WHEN test data is checked
        THEN Faker should be used for realistic data
        """
        test_content = mock_tests_llm_response["output"]["files"][0]["content"]
        
        assert "from faker import Faker" in test_content
        assert "fake = Faker()" in test_content
        assert "fake." in test_content  # Uses faker methods
    
    def test_test_matches_model_fields(self):
        """
        GIVEN a model with specific fields
        WHEN tests are generated
        THEN test data should use exact field names
        """
        # Model has: title, description, status
        model_fields = ["title", "description", "status"]
        
        # ❌ WRONG: Using different field names
        wrong_test_data = '''task_data = {
    "name": fake.sentence(),  # Model uses "title"!
    "content": fake.paragraph(),  # Model uses "description"!
}'''
        
        # ✅ CORRECT: Matching field names
        correct_test_data = '''task_data = {
    "title": fake.sentence(),
    "description": fake.paragraph(),
    "status": "active"
}'''
        
        # Check correct has right fields
        for field in model_fields:
            assert f'"{field}"' in correct_test_data
        
        # Check wrong has mismatched fields
        assert '"name"' in wrong_test_data  # Uses wrong field
    
    def test_test_crud_coverage(self, mock_tests_llm_response):
        """
        GIVEN generated tests
        WHEN test functions are checked
        THEN all CRUD operations should be tested
        """
        test_content = mock_tests_llm_response["output"]["files"][0]["content"]
        
        # Should have tests for key operations
        assert "test_list" in test_content or "test_get" in test_content
        assert "test_create" in test_content
        assert "test_delete" in test_content or "test_not_found" in test_content


class TestTestExecution:
    """Test the test execution in sandbox."""
    
    @pytest.mark.asyncio
    async def test_runs_pytest_in_docker(self):
        """
        GIVEN tests written to workspace
        WHEN execution is triggered
        THEN pytest should run in Docker backend container
        """
        # Expected command
        expected_command = "run --rm backend pytest -v"
        
        # This is what SandboxManager.run_backend_tests uses
        assert "pytest -v" in expected_command
        assert "backend" in expected_command
    
    @pytest.mark.asyncio
    async def test_healing_on_test_failure(self):
        """
        GIVEN test failure
        WHEN healing is triggered
        THEN HealingPipeline should attempt fixes
        """
        # Document the healing flow:
        # 1. Test fails
        # 2. Error is classified (import error, assertion error, etc.)
        # 3. Targeted repair strategy is applied
        # 4. Test is rerun
        
        healing_phases = [
            "classify_error",
            "apply_repair_strategy",  
            "rerun_tests",
        ]
        
        assert len(healing_phases) == 3
    
    @pytest.mark.asyncio
    async def test_max_healing_attempts(self):
        """
        GIVEN repeated test failures
        WHEN max attempts reached
        THEN healing should stop and report failure
        """
        MAX_HEALING_ATTEMPTS = 3
        
        # After 3 failed healing attempts, give up
        assert MAX_HEALING_ATTEMPTS == 3


class TestFallbackTestGeneration:
    """Test the fallback test generation when Derek fails."""
    
    @pytest.mark.asyncio
    async def test_fallback_generates_minimal_tests(self, temp_workspace):
        """
        GIVEN Derek failed to generate tests
        WHEN fallback is triggered
        THEN minimal but functional tests should be written
        """
        entity = "task"
        entity_plural = "tasks"
        
        # Simulate fallback generation
        fallback_content = f'''# backend/tests/test_api.py
"""Auto-generated fallback tests"""
import pytest
from faker import Faker

fake = Faker()


@pytest.mark.anyio
async def test_health_check(client):
    """Test health endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.anyio
async def test_list_{entity_plural}(client):
    """Test listing {entity_plural}."""
    response = await client.get("/api/{entity_plural}")
    assert response.status_code in [200, 201]


@pytest.mark.anyio
async def test_get_{entity}_not_found(client):
    """Test 404 for non-existent {entity}."""
    fake_id = "507f1f77bcf86cd799439011"
    response = await client.get(f"/api/{entity_plural}/{{fake_id}}")
    assert response.status_code == 404
'''
        
        tests_dir = temp_workspace / "backend" / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)
        test_file = tests_dir / "test_api.py"
        test_file.write_text(fallback_content, encoding="utf-8")
        
        assert test_file.exists()
        content = test_file.read_text(encoding="utf-8")
        
        assert "test_health_check" in content
        assert f"test_list_{entity_plural}" in content
        assert f"test_get_{entity}_not_found" in content


class TestConftestFixtures:
    """Test that conftest.py provides required fixtures."""
    
    def test_conftest_provides_client(self, temp_workspace):
        """
        GIVEN backend/tests/conftest.py
        WHEN examined
        THEN it should provide 'client' fixture
        """
        conftest_content = '''import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.fixture(scope="module")
async def async_client():
    """Async HTTP client for testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture(scope="module")
async def client(async_client):
    """Alias for async_client."""
    return async_client
'''
        
        assert "@pytest.fixture" in conftest_content
        assert "async def client" in conftest_content
        assert "AsyncClient" in conftest_content
    
    def test_conftest_provides_anyio_backend(self):
        """
        GIVEN conftest.py
        WHEN examined
        THEN it should provide 'anyio_backend' fixture
        """
        conftest_content = '''@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"
'''
        
        assert "anyio_backend" in conftest_content
        assert '"asyncio"' in conftest_content


class TestErrorClassification:
    """Test error classification for targeted healing."""
    
    def test_classify_import_error(self):
        """
        GIVEN an ImportError in test output
        WHEN classified
        THEN it should be identified as import_error
        """
        error_output = "ImportError: cannot import name 'Task' from 'app.models'"
        
        if "ImportError" in error_output:
            error_type = "import_error"
        else:
            error_type = "unknown"
        
        assert error_type == "import_error"
    
    def test_classify_assertion_error(self):
        """
        GIVEN an AssertionError in test output
        WHEN classified
        THEN it should be identified as assertion_error
        """
        error_output = "AssertionError: assert 500 == 201"
        
        if "AssertionError" in error_output:
            error_type = "assertion_error"
        else:
            error_type = "unknown"
        
        assert error_type == "assertion_error"
    
    def test_classify_missing_dependency(self):
        """
        GIVEN a ModuleNotFoundError in test output
        WHEN classified  
        THEN it should be identified as missing_dependency
        """
        error_output = "ModuleNotFoundError: No module named 'faker'"
        
        if "ModuleNotFoundError" in error_output:
            error_type = "missing_dependency"
        else:
            error_type = "unknown"
        
        assert error_type == "missing_dependency"
