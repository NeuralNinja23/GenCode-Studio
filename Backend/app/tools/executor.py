# app/tools/executor.py
"""
Tool Plan Executor

LINEAR EXECUTION ONLY:
- No loops
- No retries
- No self-healing
- No reflection

Just execution of an explicit plan.

OBSERVATION:
Every tool invocation is recorded:
- Before: record_tool_invocation_start
- After: record_tool_invocation_end
"""

from datetime import datetime, timezone
from typing import Any, Optional
import traceback

from app.tools.planning import (
    ToolPlan,
    ToolInvocationPlan,
    ToolInvocationResult,
    ToolPlanExecutionResult,
    StepFailure,
)
from app.core.logging import log

# TIT: Tool Invocation Trace
from app.arbormind.observation.tool_trace import (
    record_tool_invocation,
    build_tool_event,
    ARBORMIND_TIT_ENABLED,
)


# ═══════════════════════════════════════════════════════════════════════════════
# P0.1: HDAP PARSING + FILE WRITING (CRITICAL FIX)
# ═══════════════════════════════════════════════════════════════════════════════

async def _parse_and_write_hdap_files(
    output: Any,
    branch: Any,
    step: str,
) -> list[str]:
    """
    Extract files from subagentcaller output and write to disk.
    
    CRITICAL: This function is the SOLE OWNER of artifact materialization.
    
    Handles THREE output structures:
    1. Pre-parsed files: output.output.files = [{"path": "...", "content": "..."}]
    2. Raw HDAP text: output.raw_generation = "<<<FILE path=...>>>..."
    3. Nested dict: output.output.raw_generation
    
    Returns:
        List of file paths that were written
    """
    from pathlib import Path
    import re
    
    try:
        # Get project path from branch
        project_path = None
        if hasattr(branch, "project_path"):
            project_path = Path(branch.project_path)
        elif isinstance(branch, dict):
            project_path = Path(branch.get("project_path", "."))
        
        if not project_path:
            log("TOOL-EXEC", f"   ⚠️ Cannot write files: no project_path in branch")
            return []
        
        files_to_write = []
        
        # ═══════════════════════════════════════════════════════════════
        # STRATEGY 1: Check for pre-parsed files (from marcus_call_sub_agent)
        # Structure: output.output.files = [{"path": "...", "content": "..."}]
        # ═══════════════════════════════════════════════════════════════
        if isinstance(output, dict):
            inner_output = output.get("output", {})
            if isinstance(inner_output, dict):
                parsed_files = inner_output.get("files", [])
                if parsed_files and isinstance(parsed_files, list):
                    for f in parsed_files:
                        if isinstance(f, dict) and f.get("path") and f.get("content"):
                            files_to_write.append({
                                "path": f["path"],
                                "content": f["content"]
                            })
                    if files_to_write:
                        log("TOOL-EXEC", f"   📦 Found {len(files_to_write)} pre-parsed files")
        
        # ═══════════════════════════════════════════════════════════════
        # STRATEGY 2: Parse raw HDAP text if no pre-parsed files
        # ═══════════════════════════════════════════════════════════════
        if not files_to_write:
            raw_text = None
            
            # Try multiple extraction paths
            if isinstance(output, dict):
                # Path A: output.raw_generation
                raw_text = output.get("raw_generation")
                
                # Path B: output.output (if string)
                if not raw_text:
                    inner = output.get("output")
                    if isinstance(inner, str):
                        raw_text = inner
                    elif isinstance(inner, dict):
                        # Path C: output.output.raw_generation
                        raw_text = inner.get("raw_generation")
            elif isinstance(output, str):
                raw_text = output
            
            if raw_text and isinstance(raw_text, str):
                # Parse HDAP markers
                # Pattern: <<<FILE path="...">>>> content <<<END_FILE>>>
                # Also try: <<<FILE path="...">>> content <<<END_FILE>>>
                patterns = [
                    r'<<<FILE\s+path=["\']([^"\']+)["\']>>>>(.*?)<<<END_FILE>>>',
                    r'<<<FILE\s+path=["\']([^"\']+)["\']>>>(.*?)<<<END_FILE>>>',
                ]
                
                matches = []
                for pattern in patterns:
                    matches = re.findall(pattern, raw_text, re.DOTALL)
                    if matches:
                        break
                
                for file_path, content in matches:
                    files_to_write.append({
                        "path": file_path.strip(),
                        "content": content.strip()
                    })
                
                if files_to_write:
                    log("TOOL-EXEC", f"   📝 Parsed {len(files_to_write)} files from HDAP")
        
        # ═══════════════════════════════════════════════════════════════
        # WRITE FILES TO DISK
        # ═══════════════════════════════════════════════════════════════
        if not files_to_write:
            log("TOOL-EXEC", f"   ⚠️ No files found in output for step '{step}'")
            return []
        
        written_files = []
        
        for file_info in files_to_write:
            file_path = file_info["path"]
            content = file_info["content"]
            
            # Resolve full path
            full_path = project_path / file_path
            
            # Create parent directories
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            full_path.write_text(content, encoding="utf-8")
            written_files.append(str(full_path))
            
            log("TOOL-EXEC", f"      ✏️ Wrote: {file_path}")
        
        log("TOOL-EXEC", f"   ✅ Materialized {len(written_files)} artifact(s)")
        return written_files
        
    except Exception as e:
        log("TOOL-EXEC", f"   ⚠️ HDAP file extraction failed: {e}")
        import traceback
        log("TOOL-EXEC", f"      {traceback.format_exc()[:200]}")
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# OBSERVATION HOOKS
# ═══════════════════════════════════════════════════════════════════════════════

def record_tool_invocation_start(
    plan_id: str,
    invocation: ToolInvocationPlan,
    step: str,
    agent: str,
) -> None:
    """
    Record the start of a tool invocation.
    
    This is where observation happens.
    """
    log("TOOL-EXEC", f"▶️ [{invocation.tool_name}] Starting ({invocation.reason})")
    
    # Record to ArborMind (if available)
    try:
        from app.arbormind.observation.sqlite_store import record_decision, get_current_run_id
        
        run_id = get_current_run_id()
        if run_id:
            record_decision(
                run_id=run_id,
                step=step,
                agent=agent,
                action="TOOL_INVOKE",
                tool=invocation.tool_name,
                outcome="pending",
                reason=invocation.reason,
            )
    except Exception:
        pass  # Observation is best-effort


def record_tool_invocation_end(
    plan_id: str,
    result: ToolInvocationResult,
    step: str,
    agent: str,
) -> None:
    """
    Record the end of a tool invocation.
    """
    status = "✅" if result.success else "❌"
    log("TOOL-EXEC", f"{status} [{result.tool_name}] Completed in {result.duration_ms}ms")
    
    # Record to ArborMind (if available)
    try:
        from app.arbormind.observation.sqlite_store import update_decision_outcome, get_current_run_id
        
        run_id = get_current_run_id()
        if run_id:
            update_decision_outcome(
                run_id=run_id,
                step=step,
                outcome="success" if result.success else "failure",
                duration_ms=result.duration_ms,
                artifacts_count=1 if result.success else 0,
            )
    except Exception:
        pass  # Observation is best-effort
    
    # If failed, record to failure memory
    if not result.success:
        try:
            from app.arbormind.learning import (
                ingest_runtime_exception,
                ingest_external_failure,
                FailureScope,
            )
            from app.arbormind.observation.sqlite_store import get_current_run_id
            
            run_id = get_current_run_id()
            if run_id:
                ingest_runtime_exception(
                    run_id=run_id,
                    step=step,
                    exception_info=f"Tool '{result.tool_name}' failed: {result.error}",
                    agent=agent,
                )
        except Exception:
            pass  # Observation is best-effort


# ═══════════════════════════════════════════════════════════════════════════════
# LINEAR EXECUTOR
# ═══════════════════════════════════════════════════════════════════════════════

async def execute_tool_plan(
    plan: ToolPlan,
    branch: Any,
    stop_on_failure: bool = True,
) -> ToolPlanExecutionResult:
    """
    Execute a tool plan LINEARLY.
    
    Rules:
    - No loops
    - No retries
    - No self-healing
    - No reflection
    
    Just execution of an explicit plan.
    
    Args:
        plan: The immutable ToolPlan to execute
        branch: The execution branch context
        stop_on_failure: If True, stop on first required tool failure
    
    Returns:
        ToolPlanExecutionResult with all invocation results
    """
    from app.tools.registry import run_tool
    
    log("TOOL-EXEC", f"📋 Executing plan '{plan.plan_id}' for step '{plan.step}'")
    log("TOOL-EXEC", f"   Goal: {plan.goal}")
    log("TOOL-EXEC", f"   Tools: {' → '.join(plan.tool_names)}")
    
    results: list[ToolInvocationResult] = []
    final_output = None
    overall_success = True
    overall_error = None
    total_start = datetime.now(timezone.utc)
    
    for i, invocation in enumerate(plan.sequence):
        log("TOOL-EXEC", f"   [{i+1}/{plan.tool_count}] {invocation.tool_name}")
        
        # Record start
        record_tool_invocation_start(
            plan_id=plan.plan_id,
            invocation=invocation,
            step=plan.step,
            agent=plan.agent,
        )
        
        # Execute
        started_at = datetime.now(timezone.utc)
        try:
            output = await run_tool(invocation.tool_name, invocation.args)
            ended_at = datetime.now(timezone.utc)
            
            # Determine success from output
            success = True
            error = None
            
            if isinstance(output, dict):
                # Check for explicit failure indicators
                if output.get("success") is False:
                    success = False
                    error = output.get("error") or output.get("message") or "Tool returned failure"
                elif output.get("error"):
                    success = False
                    error = output.get("error")
            
            result = ToolInvocationResult(
                invocation_id=invocation.invocation_id,
                tool_name=invocation.tool_name,
                success=success,
                output=output,
                error=error,
                duration_ms=int((ended_at - started_at).total_seconds() * 1000),
                started_at=started_at.isoformat(),
                ended_at=ended_at.isoformat(),
            )
            
            # ═══════════════════════════════════════════════════════════════
            # P0.1 FIX: HDAP Parsing + File Writing for subagentcaller
            # ═══════════════════════════════════════════════════════════════
            # When subagentcaller succeeds, parse HDAP markers and write files
            if success and invocation.tool_name == "subagentcaller":
                files_written = await _parse_and_write_hdap_files(
                    output=output,
                    branch=branch,
                    step=plan.step,
                )
                if files_written:
                    log("TOOL-EXEC", f"   📝 Wrote {len(files_written)} files from HDAP output")
                    # Attach written files to output for downstream
                    if isinstance(output, dict):
                        output["_written_files"] = files_written
                        result = ToolInvocationResult(
                            invocation_id=invocation.invocation_id,
                            tool_name=invocation.tool_name,
                            success=True,
                            output=output,
                            error=None,
                            duration_ms=result.duration_ms,
                            started_at=result.started_at,
                            ended_at=result.ended_at,
                        )
            
            # Track last successful output
            if success:
                final_output = output
            
        except Exception as e:
            ended_at = datetime.now(timezone.utc)
            tb = traceback.format_exc()
            
            result = ToolInvocationResult(
                invocation_id=invocation.invocation_id,
                tool_name=invocation.tool_name,
                success=False,
                output=None,
                error=f"{str(e)}\n{tb}",
                duration_ms=int((ended_at - started_at).total_seconds() * 1000),
                started_at=started_at.isoformat(),
                ended_at=ended_at.isoformat(),
            )
        
        # Record end
        record_tool_invocation_end(
            plan_id=plan.plan_id,
            result=result,
            step=plan.step,
            agent=plan.agent,
        )
        
        # ═══════════════════════════════════════════════════════════════
        # TIT: Tool Invocation Trace (Primary Hook)
        # ═══════════════════════════════════════════════════════════════
        if ARBORMIND_TIT_ENABLED:
            try:
                from app.arbormind.observation.sqlite_store import get_current_run_id
                run_id = get_current_run_id() or "unknown"
                
                tit_event = build_tool_event(
                    run_id=run_id,
                    step=plan.step,
                    agent=plan.agent,
                    tool_name=invocation.tool_name,
                    tool_type="plan_invocation",
                    invocation_index=i,
                    called_at=started_at,
                    duration_ms=result.duration_ms,
                    status="success" if result.success else "failure",
                    input_args=invocation.args,
                    output_result=result.output if result.success else None,
                    error=Exception(result.error) if result.error else None,
                )
                record_tool_invocation(tit_event)
            except Exception:
                pass  # TIT must never crash execution
        
        results.append(result)
        
        # Handle failure
        if not result.success:
            if invocation.required and stop_on_failure:
                overall_success = False
                overall_error = f"Required tool '{invocation.tool_name}' failed: {result.error}"
                log("TOOL-EXEC", f"   ❌ STOPPING: Required tool failed")
                
                raise StepFailure(
                    step=plan.step,
                    tool_name=invocation.tool_name,
                    error=result.error or "Unknown error",
                    invocation_id=invocation.invocation_id,
                )
            else:
                log("TOOL-EXEC", f"   ⚠️ Optional tool failed, continuing...")
    
    total_end = datetime.now(timezone.utc)
    total_duration = int((total_end - total_start).total_seconds() * 1000)
    
    log("TOOL-EXEC", f"📋 Plan '{plan.plan_id}' completed in {total_duration}ms")
    
    return ToolPlanExecutionResult(
        plan_id=plan.plan_id,
        step=plan.step,
        success=overall_success,
        results=results,
        final_output=final_output,
        error=overall_error,
        total_duration_ms=total_duration,
    )
