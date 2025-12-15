"""
Loop Consolidation Invariant Tests

These tests PROVE that loop consolidation is working correctly.
They assert invariants, not behavior.

INVARIANTS:
1. Derek is called at most once per healing attempt
2. ArborMind selects strategy once (no escalation loops)
3. Healing budget enforces hard caps
4. Docker restarts are bounded
5. healing_mode disables supervisor retries
6. Budget resets correctly
7. Error depth analysis is deterministic
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure app/ and tests/ are importable
sys.path.insert(0, str(Path(__file__).parent.parent))


from tests.utils.call_counter import CallCounter


# ════════════════════════════════════════════════════════════════════
# TEST 1: Derek is single-shot
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_backend_vertical_healing_is_single_shot():
    counter = CallCounter()

    async def fake_derek(*args, **kwargs):
        counter.inc("derek")
        return False

    with patch(
        "app.orchestration.self_healing_manager.SelfHealingManager._derek_generate_backend",
        side_effect=fake_derek,
    ), patch(
        "app.orchestration.self_healing_manager.discover_primary_entity",
        return_value=("bug", "Bug"),
    ), patch(
        "app.orchestration.self_healing_manager.get_entity_plural",
        return_value="bugs",
    ), patch(
        "app.orchestration.healing_budget.get_healing_budget"
    ) as mock_budget:

        budget = MagicMock()
        budget.can_regen_critical.return_value = True
        budget.use_critical_regen.return_value = True
        mock_budget.return_value = budget

        from app.orchestration.self_healing_manager import SelfHealingManager

        mgr = SelfHealingManager(
            project_path=Path("/tmp/test"),
            llm_caller=None,
            project_id="test",
        )
        mgr.latest_test_failures = "404 on /api/bugs"

        result = await mgr._repair_backend_vertical()

        assert result is False
        counter.assert_max("derek", 1)


# ════════════════════════════════════════════════════════════════════
# TEST 2: ArborMind selects once (no escalation)
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_arbormind_selects_once_per_error():
    counter = CallCounter()

    async def fake_standard(*args, **kwargs):
        counter.inc("route")
        return {
            "selected": "logic_fix",
            "decision_id": "x",
            "mode": "standard",
        }

    with patch(
        "app.orchestration.error_router.ErrorRouter._standard_route",
        side_effect=fake_standard,
    ):
        from app.orchestration.error_router import ErrorRouter

        router = ErrorRouter()

        for _ in range(3):
            result = await router.decide_repair_strategy(
                error_log="404 on /api/bugs",
                archetype="general",
                context={},
            )
            assert result["selected"] == "logic_fix"

        counter.assert_max("route", 3)


# ════════════════════════════════════════════════════════════════════
# TEST 3: Healing budget caps LLM calls (SYNC)
# ════════════════════════════════════════════════════════════════════

def test_healing_budget_caps_llm_calls():
    from app.orchestration.healing_budget import reset_healing_budget

    budget = reset_healing_budget("budget_test")

    # Consume exactly 6 calls
    for _ in range(6):
        assert budget.use_llm_call() is True

    # 7th must fail
    assert budget.use_llm_call() is False

    # HARD ASSERTION: state-based, no helper calls
    assert budget.llm_calls_remaining == 0


# ════════════════════════════════════════════════════════════════════
# TEST 4: Healing pipeline fails fast when budget exhausted
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_healing_pipeline_respects_exhausted_budget():
    from app.orchestration.healing_budget import reset_healing_budget

    project_id = "pipeline_budget_test"
    budget = reset_healing_budget(project_id)

    for _ in range(6):
        budget.use_llm_call()
    for _ in range(2):
        budget.use_critical_regen()

    assert budget.is_exhausted()

    with patch("app.orchestration.healing_pipeline.SelfHealingManager"), patch(
        "app.orchestration.healing_pipeline.HealingPipeline._load_healing_memory"
    ):
        from app.orchestration.healing_pipeline import HealingPipeline

        pipeline = HealingPipeline(
            project_path=Path("/tmp/test"),
            llm_caller=None,
            project_id=project_id,
        )

        result = await pipeline.attempt_heal(
            step="testing_backend",
            error_log="404",
            archetype="general",
            test_failures="fail",
        )

        assert result is None


# ════════════════════════════════════════════════════════════════════
# TEST 5: Docker restarts bounded (SYNC)
# ════════════════════════════════════════════════════════════════════

def test_docker_restart_is_bounded():
    from app.orchestration.healing_budget import reset_healing_budget

    budget = reset_healing_budget("docker_test")

    assert budget.use_docker_restart() is True
    assert budget.use_docker_restart() is True
    assert budget.use_docker_restart() is False


# ════════════════════════════════════════════════════════════════════
# TEST 6: healing_mode disables supervisor retries
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_healing_mode_prevents_supervisor_retries(capsys):
    """
    REGRESSION TEST:
    When healing_mode=True, supervisor must perform exactly ONE attempt.
    No retries, no Marcus loop.
    """

    from app.supervision.supervisor import supervised_agent_call

    with patch("app.orchestration.healing_budget.get_healing_budget") as mock_budget:
        budget = MagicMock()
        budget.can_call_llm.return_value = True
        budget.use_llm_call.return_value = True
        mock_budget.return_value = budget

        await supervised_agent_call(
            project_id="test",
            manager=None,
            agent_name="Derek",
            step_name="Healing",
            base_instructions="Fix bug",
            project_path=Path("/tmp/test"),
            user_request="Test request",
            healing_mode=True,
        )

    # Capture stdout (custom log() prints here)
    captured = capsys.readouterr().out

    # HARD INVARIANTS
    assert "Attempt 1/1" in captured, "First attempt missing"
    assert "Attempt 2" not in captured, "Supervisor retried in healing_mode"

    print("✅ healing_mode enforced single supervisor attempt")



# ════════════════════════════════════════════════════════════════════
# TEST 7: Budget reset works (SYNC)
# ════════════════════════════════════════════════════════════════════

def test_healing_budget_reset_at_test_start():
    from app.orchestration.healing_budget import get_healing_budget, reset_healing_budget

    project_id = "reset_test"
    budget = get_healing_budget(project_id)
    budget.use_llm_call()
    budget.use_llm_call()

    new_budget = reset_healing_budget(project_id)

    assert new_budget.llm_calls_remaining == 6


# ════════════════════════════════════════════════════════════════════
# TEST 8: Error depth analysis
# ════════════════════════════════════════════════════════════════════

def test_error_depth_analysis_classifies_correctly():
    from app.orchestration.error_router import ErrorRouter

    router = ErrorRouter()

    assert router._analyze_error_depth("NameError: x", {}) == "surface"
    assert router._analyze_error_depth("404 on /api/bugs", {}) == "integration"
    assert router._analyze_error_depth("circular import detected", {}) == "architectural"
