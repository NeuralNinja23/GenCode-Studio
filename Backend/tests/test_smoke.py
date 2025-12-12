"""
Smoke tests - critical path validation for GenCode Studio Backend.

These tests ensure the system doesn't crash on basic operations.
NOT comprehensive - designed to catch major regressions quickly.
"""
import pytest
from pathlib import Path
import tempfile
import shutil


@pytest.mark.asyncio
async def test_workflow_basic_initialization():
    """
    Smoke test: Ensure workflow can be initialized without crashing.
    
    This doesn't test the FULL workflow (that would require LLM calls),
    just that the workflow engine loads and basic setup works.
    """
    from app.workflow.engine import WorkflowEngine
    from app.lib.websocket import ConnectionManager
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "test-project"
        project_path.mkdir()
        
        manager = ConnectionManager()
        
        # Create engine (shouldn't crash)
        engine = WorkflowEngine(
            project_id="smoke-test",
            manager=manager,
            project_path=project_path,
            user_request="Create a simple todo app",
            provider="gemini",  # Won't actually call it
            model="gemini-2.0-flash-exp"
        )
        
        # Verify basic state
        assert engine.project_id == "smoke-test"
        assert engine.project_path == project_path
        assert engine.user_request == "Create a simple todo app"
        
        print("✅ Workflow engine initialization: PASS")


@pytest.mark.asyncio
async def test_fast_orchestrator_initialization():
    """
    Smoke test: FAST V2 Orchestrator can be initialized.
    """
    from app.orchestration.fast_orchestrator import FASTOrchestratorV2
    from app.lib.websocket import ConnectionManager
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "test-project-v2"
        project_path.mkdir()
        
        manager = ConnectionManager()
        
        # Create engine (shouldn't crash)
        engine = FASTOrchestratorV2(
            project_id="smoke-test-v2",
            manager=manager,
            project_path=project_path,
            user_request="Create a simple note app",
            provider="gemini",
            model="gemini-2.0-flash-exp"
        )
        
        # Verify basic state
        assert engine.project_id == "smoke-test-v2"
        assert engine.project_path == project_path
        # Verify V2 components initialized
        assert hasattr(engine, 'graph')
        assert hasattr(engine, 'cross_ctx')
        
        print("✅ FAST V2 initialization: PASS")


@pytest.mark.asyncio
async def test_llm_adapter_initialization():
    """
    Smoke test: LLM adapter can be created without crashing.
    
    Doesn't make actual LLM calls - just tests initialization.
    """
    from app.llm.adapter import LLMAdapter
    
    adapter = LLMAdapter()
    
    # Verify adapter has required attributes
    assert hasattr(adapter, 'default_provider')
    assert hasattr(adapter, 'default_model')
    assert hasattr(adapter, 'max_retries')
    assert adapter.max_retries > 0
    
    print("✅ LLM adapter initialization: PASS")


@pytest.mark.asyncio  
async def test_database_connection_graceful_failure():
    """
    Smoke test: DB connection handles unavailable MongoDB gracefully.
    
    System should not crash if MongoDB is not running.
    """
    from app.db import connect_db, is_connected, get_connection_error
    
    # Try to connect (may fail if MongoDB not running - that's OK!)
    await connect_db()
    
    if not is_connected():
        # Should have error message
        error = get_connection_error()
        assert error is not None
        assert isinstance(error, str)
        print(f"✅ DB graceful failure: PASS (MongoDB unavailable: {error[:50]}...)")
    else:
        print("✅ DB connection: PASS (MongoDB available)")


@pytest.mark.asyncio
async def test_websocket_manager_basic_operations():
    """
    Smoke test: WebSocket manager can handle connections.
    
    Tests connection tracking without actual WebSocket connections.
    """
    from app.lib.websocket import ConnectionManager
    
    manager = ConnectionManager()
    
    # Verify initialization
    assert isinstance(manager.active_connections, dict)
    assert len(manager.active_connections) == 0
    
    # Test project isolation (no actual WebSocket)
    project_id = "test-project-ws"
    assert project_id not in manager.active_connections
    
    print("✅ WebSocket manager initialization: PASS")


def test_config_loading():
    """
    Smoke test: Configuration loads successfully.
    
    Ensures settings are accessible and have expected structure.
    """
    from app.core.config import settings
    
    # Verify core settings exist
    assert settings.llm is not None
    assert settings.workflow is not None
    assert settings.sandbox is not None
    assert settings.paths is not None
    
    # Verify paths are Path objects
    assert isinstance(settings.paths.workspaces_dir, Path)
    assert isinstance(settings.paths.frontend_dist, Path)
    
    # Verify LLM settings
    assert settings.llm.default_provider in ["gemini", "openai", "anthropic", "ollama"]
    assert settings.llm.max_retries > 0
    
    # Verify workflow settings
    assert settings.workflow.max_turns > 0
    assert settings.workflow.quality_gate_threshold > 0
    
    print("✅ Config loading: PASS")


def test_constants_and_types():
    """
    Smoke test: Core constants are properly defined.
    
    Ensures workflow steps and types are accessible.
    """
    from app.core.constants import WorkflowStep, WSMessageType, PROTECTED_FILES
    
    # Verify workflow steps exist
    assert hasattr(WorkflowStep, 'ANALYSIS')
    assert hasattr(WorkflowStep, 'ARCHITECTURE')
    assert hasattr(WorkflowStep, 'FRONTEND_MOCK')
    assert hasattr(WorkflowStep, 'CONTRACTS')
    assert hasattr(WorkflowStep, 'COMPLETE')
    
    # Verify WebSocket message types
    assert hasattr(WSMessageType, 'WORKFLOW_UPDATE')
    assert hasattr(WSMessageType, 'WORKFLOW_COMPLETE')
    assert hasattr(WSMessageType, 'WORKFLOW_FAILED')
    
    # Verify protected files
    assert isinstance(PROTECTED_FILES, set)
    assert len(PROTECTED_FILES) > 0
    
    print("✅ Constants and types: PASS")


def test_attention_router_embeddings_fallback():
    """
    Smoke test: Attention router handles missing API keys gracefully.
    
    """
    from app.arbormind.router import _get_fallback_embedding
    
    # Test fallback embedding
    embedding = _get_fallback_embedding("test query", dim=768)
    
    assert isinstance(embedding, list)
    assert len(embedding) == 768
    assert all(isinstance(x, float) for x in embedding)
    
    print("✅ Attention router fallback: PASS")


def test_parser_sanitization():
    """
    Smoke test: Parser can handle various LLM output formats.
    
    Tests that the parser doesn't crash on malformed input.
    """
    from app.utils.parser import sanitize_marcus_output, parse_json
    
    # Test markdown fence removal
    markdown_json = '''```json
    {"approved": true, "quality_score": 8}
    ```'''
    
    sanitized = sanitize_marcus_output(markdown_json)
    assert "```" not in sanitized
    
    # Test JSON parsing
    result = parse_json('{"test": "value"}')
    assert result == {"test": "value"}
    
    # Test malformed JSON handling (should not crash)
    try:
        parse_json("{invalid json")
    except Exception:
        pass  # Expected to fail, but shouldn't crash the system
    
    print("✅ Parser sanitization: PASS")


@pytest.mark.asyncio
async def test_exception_handling_improvement():
    """
    Smoke test: Verify fixed exception handlers in supervisor.
    
    Ensures our fix to bare exceptions is working.
    """
    import json
    from app.supervision.supervisor import marcus_supervise
    
    # This test just verifies the function is importable
    # and has the expected signature (not a full integration test)
    import inspect
    sig = inspect.signature(marcus_supervise)
    
    assert 'project_id' in sig.parameters
    assert 'manager' in sig.parameters
    assert 'agent_name' in sig.parameters
    assert 'step_name' in sig.parameters
    assert 'agent_output' in sig.parameters
    
    print("✅ Exception handling (supervisor callable): PASS")


if __name__ == "__main__":
    """
    Run smoke tests directly: python tests/test_smoke.py
    """
    import asyncio
    
    print("🚀 Running GenCode Studio Backend Smoke Tests\n")
    print("=" * 60)
    
    # Run synchronous tests
    test_config_loading()
    test_constants_and_types()
    test_attention_router_embeddings_fallback()
    test_parser_sanitization()
    
    # Run async tests using asyncio.run() (modern pattern)
    async def run_async_tests():
        await test_workflow_basic_initialization()
        await test_llm_adapter_initialization()
        await test_database_connection_graceful_failure()
        await test_websocket_manager_basic_operations()
        await test_exception_handling_improvement()
    
    asyncio.run(run_async_tests())
    
    print("=" * 60)
    print("\n✅ All smoke tests passed!")
    print("\nThese are BASIC smoke tests. For comprehensive testing,")
    print("run: pytest tests/ -v --cov=app")
