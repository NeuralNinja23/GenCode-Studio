# app/handlers/architecture.py
"""
Step 1: Victoria creates architecture plan with Marcus supervision.


This matches the legacy workflows.py step_architecture logic exactly.
"""
from pathlib import Path
from typing import Any, List

from app.core.types import ChatMessage, StepResult
from app.core.constants import WorkflowStep
from app.core.exceptions import RateLimitError
from app.handlers.base import broadcast_status
from app.core.logging import log
from app.orchestration.state import WorkflowStateManager
from app.supervision import supervised_agent_call
from app.core.failure_boundary import FailureBoundary
from app.core.file_writer import validate_file_output, persist_agent_output
from app.core.step_invariants import StepInvariants, StepInvariantError
from app.llm.prompts.victoria import VICTORIA_PROMPT




@FailureBoundary.enforce
async def step_architecture(branch) -> StepResult:
    """
    Step 1: Victoria creates architecture plan with Marcus supervision.
    
    Produces:
    - architecture.md with system design
    - Component hierarchy
    - Data flow diagrams
    
    Returns:
        StepResult with next step = FRONTEND_MOCK (GenCode Studio pattern: frontend-first)
  
    Raises:
        RateLimitError: If rate limited - workflow should stop
    """
    from app.arbormind.cognition.branch import Branch
    assert isinstance(branch, Branch)
    
    # Extract context from branch
    project_id = branch.intent["project_id"]
    user_request = branch.intent["user_request"]
    manager = branch.intent["manager"]
    project_path = branch.intent["project_path"]
    provider = branch.intent["provider"]
    model = branch.intent["model"]
    
    await broadcast_status(
        manager, project_id, WorkflowStep.ARCHITECTURE,
        f"Victoria planning architecture...",
        1, 9
    )
    
    intent = await WorkflowStateManager.get_intent(project_id) or {}
    
    # Extract attention routing results
    archetype_routing = intent.get("archetypeRouting", {})
    ui_vibe_routing = intent.get("uiVibeRouting", {})
    archetype = archetype_routing.get("top", "general")
    ui_vibe = ui_vibe_routing.get("top", "minimal_light")
    
    
    # Get archetype-specific architecture guidance (Simplified)
    architecture_archetype_guidance = f"""
    ARCHETYPE: {archetype}
    UI VIBE: {ui_vibe}
    
    Ensure the architecture supports the specific needs of this archetype.
    """
    
    # log("ARCHITECTURE", f"🏗️ Creating architecture for archetype: {archetype}, vibe: {ui_vibe}")
    
    
    try:
        # Extract retry/override context if any
        temperature_override = branch.intent.get("temperature_override")
        is_retry = branch.intent.get("is_retry", False)

        # Use supervised call - no retries, ArborMind handles that
        result = await supervised_agent_call(
            project_id=project_id,
            manager=manager,
            agent_name="Victoria",
            step_name="Architecture",
            base_instructions=VICTORIA_PROMPT,
            project_path=project_path,
            user_request=user_request,
            temperature_override=temperature_override,
            is_retry=is_retry,
        )
        
        # V3: Extract token usage for cost tracking
        step_token_usage = result.get("token_usage")
        
        parsed = result.get("output", {})
        
        # ═══════════════════════════════════════════════════════════════════════════
        # INVARIANT: Architecture bundle MUST contain exactly the 5 required sections
        # ═══════════════════════════════════════════════════════════════════════════
        required_files = {
            "architecture/overview.md",
            "architecture/frontend.md",
            "architecture/backend.md",
            "architecture/system.md",
            "architecture/invariants.md",
        }
        
        generated_files = {f.get("path", "") for f in parsed.get("files", [])}
        missing_files = required_files - generated_files
        
        if missing_files:
             log("ARCHITECTURE", f"❌ Missing required architecture sections: {missing_files}")
             # This is a FATAL failure for architecture (Phase-1 Rule: Architecture is strict)
             raise StepInvariantError(f"Architecture missing mandatory sections: {missing_files}")
        
        for f in parsed.get("files", []):
            if not f.get("content", "").strip():
                raise StepInvariantError(
                    f"Architecture file is empty: {f.get('path')}"
                )
        
        StepInvariants.require_non_empty_content(parsed, "ARCHITECTURE")
        

        validated = validate_file_output(parsed, WorkflowStep.ARCHITECTURE, max_files=5)
        await persist_agent_output(manager, project_id, project_path, validated, WorkflowStep.ARCHITECTURE)
        
        # ═══════════════════════════════════════════════════════════════════════════
        # SUCCESS PATH: Store artifacts for downstream steps
        # ═══════════════════════════════════════════════════════════════════════════
        branch.artifacts["architecture"] = {
            "files": list(generated_files),
            "root": "architecture/",
        }

        # Extract summary for cognitive context
        overview_content = next((f.get("content", "") for f in parsed.get("files", []) if "overview.md" in f.get("path", "")), "")
        architecture_summary = overview_content[:500] if overview_content else "Architecture planning completed."
        
        # ═══════════════════════════════════════════════════════════════════════════
        # GOVERNANCE CHECK: Supervisor rejection is NOT an execution failure
        # It's a quality gate verdict that allows controlled retry or halt
        # ═══════════════════════════════════════════════════════════════════════════
        if not result.get("approved"):
            log("ARCHITECTURE", f"⚠️ Architecture not approved by supervisor (Quality: {result.get('quality_score', '?')})")
            
            # Return a structured rejection - NOT an exception
            # This allows the orchestrator to decide: retry, halt, or branch
            return StepResult(
                nextstep=None,  # Signal: decision needed
                turn=1,
                status="rejected",  # Governance verdict
                data={
                    "rejection_reason": result.get('error', 'Quality threshold not met'),
                    "quality_score": result.get('quality_score'),
                    "feedback": result.get('feedback', ''),
                    "files_generated": list(generated_files),
                    "files_persisted": True,  # Files WERE written
                    "architecture_summary": architecture_summary,
                },
                error=f"Supervisor verdict: rejected - {result.get('error', 'Quality threshold not met')}"
            )

    except RateLimitError:
        log("ARCHITECTURE", "Rate limit exhausted - stopping workflow", project_id=project_id)
        raise
        
    except StepInvariantError as e:
        # Invariant violations are structural failures - let boundary classify
        log("ARCHITECTURE", f"Invariant violation: {e}", project_id=project_id)
        raise
        
    except Exception as e:
        log("ARCHITECTURE", f"Victoria failed: {e}", project_id=project_id)
        raise  # 🛑 Real failures propagate

    return StepResult(
        nextstep=WorkflowStep.FRONTEND_MOCK,
        turn=2,  # Architecture is step 1
        data={
            "architecture_summary": architecture_summary,
            "files_count": len(generated_files)
        },
        token_usage=step_token_usage if 'step_token_usage' in locals() else None,  # V3
    )


