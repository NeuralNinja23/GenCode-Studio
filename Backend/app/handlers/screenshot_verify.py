# app/handlers/screenshot_verify.py
"""
Step 4: Visual QA - Screenshot verification after frontend mock.

Workflow order: ... → Frontend Mock (3) → Screenshot Verify (4) → Contracts (5) → ...

GenCode Studio pattern:
- After frontend mock is built, take a screenshot
- Use AI to analyze the screenshot for design issues
- Check: padding, alignment, color contrast, component usage, empty states
"""
from pathlib import Path
from typing import Any, List

from app.core.types import ChatMessage, StepResult
from app.core.constants import WorkflowStep
from app.core.exceptions import RateLimitError
from app.handlers.base import broadcast_status, broadcast_agent_log
from app.core.logging import log
from app.tools import run_tool
from app.orchestration.state import WorkflowStateManager

# Phase 0: Failure Boundary Enforcement
from app.core.failure_boundary import FailureBoundary


@FailureBoundary.enforce
async def step_screenshot_verify(
    project_id: str,
    user_request: str,
    manager: Any,
    project_path: Path,
    chat_history: List[ChatMessage],
    provider: str,
    model: str,
    current_turn: int,
    max_turns: int,
) -> StepResult:
    """
    Step 4: Visual QA after frontend mock is created.
    
    GenCode Studio pattern:
    - Take screenshot of the running frontend
    - Analyze for design issues:
      * Padding and alignment
      * Color contrast and visibility
      * Component usage (shadcn vs HTML)
      * Empty states and loading states
      * Gradient overuse
      * Missing animations (can't check in static screenshot)
    
    If issues found, we can optionally have Derek fix them before proceeding.
    """
    # V3: Track token usage for cost reporting
    step_token_usage = None
    
    await broadcast_status(
        manager,
        project_id,
        "screenshot_verify",
        f"Turn {current_turn}/{max_turns}: Taking screenshot for visual QA...",
        current_turn,
        max_turns,
    )

    screenshot_path = project_path / "frontend_screenshot.png"
    screenshot_success = False
    screenshot_error = ""
    
    # ═══════════════════════════════════════════════════════════════════
    # 1. Skip screenshot capture on Windows/local dev (Playwright issues)
    # ═══════════════════════════════════════════════════════════════════
    
    import sys
    is_windows = sys.platform.startswith('win')
    
    if is_windows:
        # Skip screenshot on Windows - Playwright subprocess creation fails
        # This is expected behavior: Windows dev environments don't support
        # headless screenshot capture in the same way Linux/Docker does.
        # Instead, we perform code-based analysis only.
        log("SCREENSHOT", "⏭️ Windows detected: Skipping visual screenshot capture")
        log("SCREENSHOT", "   ℹ️ Code-based UI analysis will be performed instead")
        log("SCREENSHOT", "   ℹ️ For visual QA, deploy to Docker or run on Linux/WSL")
        screenshot_error = "Screenshot skipped on Windows (visual capture not supported in dev mode)"
    else:
        try:
            # Try to take screenshot using uxvisualizer tool
            # Note: This requires the frontend to be running
            result = await run_tool(
                name="uxvisualizer",
                args={
                    "url": "http://localhost:5174",
                    "output_path": str(screenshot_path),
                    "viewport_width": 1280,
                    "viewport_height": 720,
                },
            )
            
            if result.get("success"):
                screenshot_success = True
                log("SCREENSHOT", f"✅ Screenshot captured: {screenshot_path}")
            else:
                screenshot_error = result.get("error", "Unknown error")
                log("SCREENSHOT", f"⚠️ Screenshot failed: {screenshot_error}")
                
        except Exception as e:
            screenshot_error = str(e)
            log("SCREENSHOT", f"⚠️ Screenshot tool error: {e}")

    # ═══════════════════════════════════════════════════════════════════
    # 2. Log if screenshot failed but continue with code analysis
    # ═══════════════════════════════════════════════════════════════════
    
    if not screenshot_success:
        await broadcast_agent_log(
            manager,
            project_id,
            "AGENT:Marcus",
            f"Screenshot skipped ({screenshot_error}). Running code-based design analysis instead."
        )
        # Continue to code analysis - DON'T return early

    # ═══════════════════════════════════════════════════════════════════
    # 3. Marcus-driven UI/UX review instead of static heuristics
    # ═══════════════════════════════════════════════════════════════════
    
    from app.supervision import supervised_agent_call
    
    # Read architecture.md for UI Design System
    arch_content = ""
    try:
        arch_file = project_path / "architecture.md"
        if arch_file.exists():
            arch_content = arch_file.read_text(encoding="utf-8")
    except Exception as e:
        log("SCREENSHOT", f"Could not read architecture.md: {e}")
    
    # Read design tokens if they exist
    tokens_content = ""
    try:
        tokens_file = project_path / "frontend" / "src" / "design" / "tokens.json"
        if tokens_file.exists():
            tokens_content = tokens_file.read_text(encoding="utf-8")
    except Exception as e:
        log("SCREENSHOT", f"Could not read design tokens: {e}")
        pass
    
    # Read a sample of frontend code
    frontend_code_samples = []
    frontend_src = project_path / "frontend" / "src"
    if frontend_src.exists():
        try:
            # Get up to 3 page files
            for jsx_file in list(frontend_src.rglob("*.jsx"))[:3]:
                try:
                    content = jsx_file.read_text(encoding="utf-8")[:1500]  # First 1500 chars
                    frontend_code_samples.append(f"--- {jsx_file.name} ---\n{content}\n")
                except Exception as e:
                    log("SCREENSHOT", f"Error reading frontend sample {jsx_file.name}: {e}")
                    pass
        except Exception as e:
            log("SCREENSHOT", f"Error sampling frontend code: {e}")
    
    code_samples_str = "\n".join(frontend_code_samples)
    
    # Get UI vibe from intent
    intent = await WorkflowStateManager.get_intent(project_id) or {}
    ui_vibe = ((intent.get("uiVibeRouting") or {}).get("top")) or "unknown"
    
    # Build Marcus UI Critic prompt
    ui_critic_prompt = f"""You are acting as a UI/UX reviewer and design critic.

USER REQUEST: {user_request[:200]}

DETECTED UI VIBE: {ui_vibe}

═══════════════════════════════════════════════════════
📐 ARCHITECTURE.MD (UI DESIGN SYSTEM)
═══════════════════════════════════════════════════════

{arch_content[:3000] if arch_content else "No architecture.md found."}

═══════════════════════════════════════════════════════
🎨 DESIGN TOKENS
═══════════════════════════════════════════════════════

{tokens_content if tokens_content else "No design tokens found."}

═══════════════════════════════════════════════════════
📄 FRONTEND CODE SAMPLES
═══════════════════════════════════════════════════════

{code_samples_str if code_samples_str else "No frontend code found."}

═══════════════════════════════════════════════════════
📸 SCREENSHOT INFORMATION
═══════════════════════════════════════════════════════

Screenshot captured: {screenshot_success}
Screenshot path: {screenshot_path if screenshot_success else "N/A"}

Note: Visual screenshot analysis is limited in this environment. Focus on code-based review.

═══════════════════════════════════════════════════════
YOUR TASK
═══════════════════════════════════════════════════════

Review the frontend implementation against the UI Design System and design tokens.

CHECK FOR THESE ISSUES:

1. **Vibe Mismatch**:
   - Does the color palette match the UI vibe ({ui_vibe})?
   - Dark vibe using light backgrounds or vice versa?

2. **Spacing & Layout**:
   - Cramped spacing (p-1, p-2, space-y-1, space-y-2)?
   - Should use 2-3x more whitespace
   - Check for center-aligned containers (disrupts reading flow)

3. **Component Usage**:
   - Using raw HTML (\u003cbutton\u003e, \u003cinput\u003e) instead of shadcn components?
   - Should use \u003cButton\u003e, \u003cInput\u003e, \u003cCard\u003e from @/components/ui

4. **Icon Usage**:
   - Using emojis (🚀🎯💡🔮📊✨💰🤖🧠) instead of lucide-react?
   - MUST use lucide-react for all icons

5. **Transitions & Animations**:
   - Missing hover effects on buttons/cards?
   - Every interactive element needs micro-animations
   - Avoid "transition: all" (use specific properties)

6. **Design Token Compliance**:
   - Are components using the design token classes from tokens.json?
   - Or are they using ad-hoc Tailwind classes?

7. **Content Quality**:
   - Dashboard/Home page has real content (not just "Welcome")?
   - Mock data properly separated in mock.js?

8. **Gradient Usage** (if applicable):
   - Gradients should be \u003c 20% of viewport
   - Avoid generic purple-blue or purple-pink combinations

OUTPUT FORMAT:
Return JSON with this structure:

{{
  "thinking": "Analyze the UI Design System, tokens, and code samples. Identify specific mismatches.",
  "files": [
    {{
      "path": "visual_qa_issues.md",
      "content": "# Visual QA Issues\\n\\nReviewed by Marcus (UI Critic)\\n\\n## Issues Found:\\n\\n- Issue 1: Specific problem with file/line reference\\n- Issue 2: Another specific problem\\n\\n## Positive Findings:\\n\\n- What looks good\\n\\n## Recommendations:\\n\\n- Concrete suggestions for improvement"
    }}
  ]
}}

If NO issues found, still create visual_qa_issues.md with a positive review.

Be SPECIFIC: mention file names, approximate line numbers, exact class names to change.
Be CONSTRUCTIVE: explain WHY something is an issue and HOW to fix it.
"""

    try:
        # Have Marcus review the UI
        await broadcast_agent_log(
            manager,
            project_id,
            "AGENT:Marcus",
            f"Reviewing UI implementation against design system (vibe: {ui_vibe})..."
        )
        
        result = await supervised_agent_call(
            project_id=project_id,
            manager=manager,
            agent_name="Marcus",
            step_name="UI Screenshot Review",
            base_instructions=ui_critic_prompt,
            project_path=project_path,
            user_request=user_request,
            contracts="",  # Not needed for UI review
            max_retries=1,
        )
        
        # V3: Extract token usage for cost tracking
        step_token_usage = result.get("token_usage")
        
        parsed = result.get("output", {})
        
        # Write the visual_qa_issues.md file
        from app.persistence import persist_agent_output
        from app.persistence.validator import validate_file_output
        
        if "files" in parsed and parsed["files"]:
            validated = validate_file_output(parsed, WorkflowStep.SCREENSHOT_VERIFY, max_files=1)
            await persist_agent_output(manager, project_id, project_path, validated, WorkflowStep.SCREENSHOT_VERIFY)
            
            # Extract issues count from the content
            issues_file = project_path / "visual_qa_issues.md"
            issues_count = 0
            issues_list = []
            
            if issues_file.exists():
                try:
                    content = issues_file.read_text(encoding="utf-8")
                    # Count lines starting with "- Issue" or similar
                    for line in content.split("\n"):
                        if line.strip().startswith("- ") and ":" in line:
                            issues_count += 1
                            issues_list.append(line.strip())
                except Exception as e:
                    log("SCREENSHOT", f"Error parsing visual_qa_issues.md: {e}")
                    pass
            
            status = "✅ approved" if result.get("approved") else "⚠️ best effort"
            
            if issues_count > 0:
                await broadcast_agent_log(
                    manager,
                    project_id,
                    "AGENT:Marcus",
                    f"📸 UI Review complete ({status}). Found {issues_count} design issues. "
                    f"See visual_qa_issues.md for details. These can be addressed during refinement."
                )
            else:
                await broadcast_agent_log(
                    manager,
                    project_id,
                    "AGENT:Marcus",
                    f"📸 UI Review complete ({status}). No major design issues detected. "
                    f"Frontend follows the design system well!"
                )
            
            # Store for step result
            design_issues = issues_list[:10]  # First 10 for data
            
        else:
            # Fallback if Marcus didn't return files
            log("SCREENSHOT", "Marcus didn't return visual_qa_issues.md, creating default")
            issues_file = project_path / "visual_qa_issues.md"
            issues_file.write_text(
                "# Visual QA Issues\n\n"
                "Marcus review completed. No structured issues file generated.\n\n"
                "Frontend appears to follow basic design patterns.\n",
                encoding="utf-8"
            )
            design_issues = []
            issues_count = 0
        
    except RateLimitError:
        log("SCREENSHOT", "Rate limit exhausted - stopping workflow", project_id=project_id)
        raise
        
    except Exception as e:
        log("SCREENSHOT", f"Marcus UI review failed: {e}", project_id=project_id)
        
        # Fallback: create a basic issues file
        issues_file = project_path / "visual_qa_issues.md"
        issues_file.write_text(
            f"# Visual QA Issues\n\n"
            f"Marcus review encountered an error: {str(e)[:200]}\n\n"
            f"Proceeding to contracts step.\n",
            encoding="utf-8"
        )
        design_issues = []
        issues_count = 0

    # Proceed to contracts
    return StepResult(
        nextstep=WorkflowStep.CONTRACTS,
        turn=current_turn + 1,
        data={
            "screenshot_captured": screenshot_success,
            "issues_found": issues_count,
            "issues": design_issues[:10] if 'design_issues' in locals() else []
        },
        token_usage=step_token_usage,  # V3
    )
