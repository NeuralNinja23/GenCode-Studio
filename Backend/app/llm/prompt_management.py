# app/llm/prompt_management.py
"""
FAST‑V2 / FAST‑V3 HDAP‑SAFE Prompt Context Builder
=================================================

This version is **artifact‑first** and **protocol‑locked**.
It removes all schema leakage (path/content, FILE labels, thinking blocks)
and guarantees that the LLM believes it is **writing files directly**.

CORE PRINCIPLES (NON‑NEGOTIABLE):
- The LLM sees **raw text only** — never structured file metadata
- Files are treated as **world state**, not data structures
- HDAP is enforced at the **protocol boundary**, not as a formatting hint
- "Thinking" or planning output is explicitly FORBIDDEN
"""

from typing import Any, Dict, List, Optional, Union

print("🔥 LOADED HDAP‑SAFE prompt_management.py FROM:", __file__)


# ------------------------------------------------------------------
# FILE FILTERING (INTERNAL ONLY — NEVER SHOWN AS STRUCTURE TO LLM)
# ------------------------------------------------------------------

def filter_files_for_step(
    step: str,
    files: Union[Dict[str, str], List[dict]],
    max_files: int = 12
) -> Dict[str, str]:
    if not files or not step:
        return {}

    # 🔥 HDAP NORMALIZATION FIX
    # Convert HDAP list format → dict[path -> content]
    if isinstance(files, list):
        normalized: Dict[str, str] = {}
        for f in files:
            if not isinstance(f, dict):
                continue
            path = f.get("path")
            content = f.get("content")
            if path and content is not None:
                normalized[path] = content
        files = normalized

    if not isinstance(files, dict):
        return {}

    step = step.lower()

    # ═══════════════════════════════════════════════════════════════════
    # SCOPE EXCLUSION (Prevent Step Contamination)
    # ═══════════════════════════════════════════════════════════════════
    # Frontend steps should NEVER see backend files
    # Backend steps should NEVER see frontend source files
    # ═══════════════════════════════════════════════════════════════════
    
    exclusion_patterns = {
        "frontend": ["backend/"],           # Frontend: exclude ALL backend files
        "backend": ["frontend/src/"],       # Backend: exclude frontend source (but allow package.json reference)
        "testing": [],                      # Testing: can see both
        "architecture": [],                 # Architecture: can see both
    }
    
    # Determine exclusions for this step
    step_exclusions = []
    for step_type, patterns in exclusion_patterns.items():
        if step_type in step:
            step_exclusions = patterns
            break
    
    # Apply exclusions FIRST (before scoring)
    if step_exclusions:
        filtered_files = {}
        excluded_count = 0
        for path, content in files.items():
            # Normalize path separators for consistent matching
            normalized_path = path.replace("\\", "/")
            # Exclude if path starts with any exclusion pattern
            if not any(normalized_path.startswith(excl) for excl in step_exclusions):
                filtered_files[path] = content
            else:
                excluded_count += 1
        
        if excluded_count > 0:
            print(f"[FILTER] Step '{step}' excluded {excluded_count} files matching {step_exclusions}")
        
        files = filtered_files

    # ═══════════════════════════════════════════════════════════════════
    # ARCHITECTURE-ONLY POLICY (Clean Slate By Design)
    # ═══════════════════════════════════════════════════════════════════
    # GenCode Studio uses GENERATIVE workflow - agents generate fresh code
    # They should ONLY see architecture/*.md files, NEVER workspace code
   # This prevents:
    # - Token waste on irrelevant files
    # - Scope confusion (seeing old code)
    # - Modification patterns (we want generation, not editing)
    #
    # System Integration is now Python-based, so NO step needs workspace files
    # ═══════════════════════════════════════════════════════════════════
    
    # Filter to ONLY architecture files for all steps
    architecture_only = {}
    
    # Define step-specific allowlists (Default: All architecture files)
    allowlist_pattern = "architecture/"
    
    step_lower = str(step).lower()
    
    # DEBUG: Print step detection to verify logic
    # print(f"[DEBUG] Filtering for step: '{step_lower}'")

    if "backend" in step_lower and ("model" in step_lower or "router" in step_lower):
        allowlist_pattern = "architecture/backend.md"
    elif "frontend" in step_lower:
        allowlist_pattern = "architecture/frontend.md"
    elif "architecture" in step_lower:
         allowlist_pattern = "architecture/"
    
    # print(f"[DEBUG] Allowlist pattern: '{allowlist_pattern}'")

    for path, content in files.items():
        normalized_path = path.replace("\\", "/")
        
        # 1. Must be an architecture file
        if not (normalized_path.startswith("architecture/") and normalized_path.endswith(".md")):
            continue
            
        # 2. Scope Check
        # If allowlist is a directory (ends with /), match prefix
        if allowlist_pattern.endswith("/"):
            if normalized_path.startswith(allowlist_pattern):
                architecture_only[path] = content
        
        # If allowlist is a specific file, match exact
        else:
            if normalized_path == allowlist_pattern:
                architecture_only[path] = content
    
    if len(architecture_only) < len(files):
        excluded = len(files) - len(architecture_only)
        kept_names = list(architecture_only.keys())
        print(f"[FILTER] Step '{step}' using architecture-only policy: kept {len(architecture_only)} arch files ({kept_names}), excluded {excluded} workspace files")
    
    files = architecture_only
    
    return files

# ------------------------------------------------------------------
# CONTEXT BUILDER — HDAP‑SAFE
# ------------------------------------------------------------------

def build_context(
    *,
    agent_name: Optional[str] = None,
    task: Optional[str] = None,
    step_name: Optional[str] = None,
    archetype: Optional[str] = None,
    vibe: Optional[str] = None,
    files: Optional[Any] = None,   # Dict[path, content] ONLY (internal)
    contracts: Optional[str] = None,
    errors: Optional[List[str]] = None,
    tools: Optional[List[str]] = None,
    system_prompt: Optional[str] = None,
    user_prompt: Optional[str] = None,
    is_retry: bool = False,
) -> str:
    """
    Build the final prompt sent to the LLM.

    ⚠️ CRITICAL GUARANTEE:
    - The LLM NEVER sees file metadata, schemas, path/content structures,
      or any representation that implies "files as data".
      
    NOTE: ARTIFACT mode (HDAP) enforcement is now handled by enforce_artifact_mode().
    This function is only used for FREEFORM/STRUCTURED modes.
    """

    context_parts: List[str] = []

    # 1️⃣ System persona (verbatim)
    if system_prompt:
        context_parts.append(system_prompt.strip())

    # 2️⃣ User request / task
    if user_prompt:
        context_parts.append(f"USER REQUEST:\n{user_prompt.strip()}")
    elif task:
        context_parts.append(f"USER REQUEST:\n{task.strip()}")

    # 3️⃣ Contextual hints (archetype / vibe) — PLAIN TEXT ONLY
    if archetype or vibe:
        hints = []
        if archetype:
            hints.append(f"Archetype: {archetype}")
        if vibe:
            hints.append(f"Vibe: {vibe}")
        context_parts.append("CONTEXT:\n" + "\n".join(hints))

    # 4️⃣ Existing project files (RAW CONTENT ONLY — NO LABELS)
    if files and isinstance(files, dict):
        if step_name:
            files = filter_files_for_step(step_name, files)

        if files:
            raw_files: List[str] = []
            for content in files.values():
                # 🚫 NO PATHS, NO HEADERS, NO MARKERS
                raw_files.append(content.strip())

            context_parts.append("EXISTING PROJECT STATE:\n" + "\n\n".join(raw_files))

    # 5️⃣ Architecture & Contracts (RAW TEXT)
    if contracts:
        context_parts.append("ARCHITECTURE / CONTRACTS (REFERENCE ONLY):\n" + contracts.strip())


    # 6️⃣ Previous errors (instructional, not structural)
    if errors:
        error_block = "\n".join(f"- {e}" for e in errors)
        context_parts.append("PREVIOUS ERRORS — MUST FIX:\n" + error_block)

    # 7️⃣ Tools (capabilities only — not output format)
    if tools:
        tool_block = "\n".join(f"- {t}" for t in tools)
        context_parts.append("AVAILABLE TOOLS:\n" + tool_block)

    # FINAL ASSEMBLY
    return "\n\n".join(context_parts)


