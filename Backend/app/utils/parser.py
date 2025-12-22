# app/utils/parser.py
"""
HDAP Parser - Human-Definition Artifact Protocol

Parses LLM output using deterministic artifact markers.

FORMAT (attribute-based):
<<<FILE path="path/to/file.ext">>>
file content here
<<<END_FILE>>>

OPTIONAL ATTRIBUTES:
- path (required): File path
- lang: Language hint (py, jsx, md, etc.)
- mode: write (default), append, patch

BENEFITS:
- No JSON escaping issues
- No truncation ambiguity (missing END_FILE = incomplete)
- Windows path safe (C: won't confuse parser)
- Extensible via attributes
- Thinking/reasoning ignored (anything outside FILE markers)

STRICT PROTOCOL:
- If HDAP markers present → parse HDAP only
- If HDAP markers absent → FAIL (don't fall back to markdown)
- Protocol boundaries are SHARP, not forgiving
"""

import re
from typing import Dict, Any, List, Tuple

# ═══════════════════════════════════════════════════════════════════════════════
# HDAP MARKERS (Attribute-based format)
# ═══════════════════════════════════════════════════════════════════════════════

# Primary format: <<<FILE path="backend/app/models.py">>>
FILE_START_PATTERN = re.compile(
    r'<<<FILE\s+path=["\']([^"\']+)["\'](?:\s+[^>]*)?\s*>>>',
    re.IGNORECASE
)
FILE_END_PATTERN = re.compile(r'<<<END_FILE>>>', re.IGNORECASE)

# Legacy colon format (for backwards compatibility during migration)
# <<<FILE: path/to/file.ext>>>
LEGACY_FILE_START = re.compile(r'<<<FILE:\s*([^>]+)>>>', re.IGNORECASE)


# ═══════════════════════════════════════════════════════════════════════════════
# HDAP PARSER
# ═══════════════════════════════════════════════════════════════════════════════

def parse_hdap(raw_output: str) -> Dict[str, Any]:
    """
    Parse HDAP-formatted LLM output into files dictionary.
    
    STRICT MODE:
    - If HDAP markers present → parse only those
    - If HDAP markers absent → return empty (caller should fail/retry)
    - NO markdown fallback (protocol boundaries must be sharp)
    
    Args:
        raw_output: Raw LLM response with HDAP markers
        
    Returns:
        {
            "files": [{"path": "...", "content": "..."}, ...],
            "complete": True/False,
            "incomplete_files": ["path1", ...]  # Files missing END_FILE
        }
    """
    if not raw_output or not isinstance(raw_output, str):
        return {"files": [], "complete": True, "incomplete_files": []}
    
    files: List[Dict[str, str]] = []
    incomplete_files: List[str] = []
    
    # Try attribute-based format first
    all_starts = list(FILE_START_PATTERN.finditer(raw_output))
    
    # Fall back to legacy colon format if no attribute-based markers found
    if not all_starts:
        all_starts = list(LEGACY_FILE_START.finditer(raw_output))
    
    # If still no markers, return empty (strict mode - no markdown fallback)
    if not all_starts:
        return {
            "files": [],
            "complete": True,  # No files is "complete" (nothing truncated)
            "incomplete_files": [],
            "no_hdap_markers": True  # Signal to caller that HDAP was not found
        }
    
    # Parse each file marker
    for i, match in enumerate(all_starts):
        file_path = match.group(1).strip()
        content_start = match.end()
        
        # Find the end position (either next FILE marker or END_FILE)
        if i + 1 < len(all_starts):
            next_start = all_starts[i + 1].start()
        else:
            next_start = len(raw_output)
        
        # Look for END_FILE within this file's content region
        search_region = raw_output[content_start:next_start]
        end_match = FILE_END_PATTERN.search(search_region)
        
        if end_match:
            # Complete file found
            content = search_region[:end_match.start()].strip()
            files.append({"path": file_path, "content": content})
        else:
            # Incomplete file (truncated output - missing END_FILE)
            content = search_region.strip()
            if content:  # Only add if there's some content
                files.append({"path": file_path, "content": content})
                incomplete_files.append(file_path)
    
    return {
        "files": files,
        "complete": len(incomplete_files) == 0,
        "incomplete_files": incomplete_files
    }


def _is_valid_file_path(path: str) -> bool:
    """Check if a path looks like a valid file path."""
    if not path or len(path) < 3:
        return False
    
    # Must contain a dot (extension) or slash (directory)
    if '.' not in path and '/' not in path and '\\' not in path:
        return False
    
    # Reject HTML-like junk
    invalid_names = {'div', 'span', 'ul', 'li', 'section', 'main', 'header', 'footer'}
    if path.lower() in invalid_names:
        return False
    
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN API (normalize_llm_output replacement)
# ═══════════════════════════════════════════════════════════════════════════════

def normalize_llm_output(raw_output: str, step_name: str = "") -> Dict[str, Any]:
    """
    Parse LLM output into standardized format.
    
    HDAP-only parsing - STRICT protocol enforcement.
    
    Args:
        raw_output: Raw LLM response
        step_name: Step name (for logging)
        
    Returns:
        {"files": [...], "complete": bool, ...}
    """
    if not raw_output or not isinstance(raw_output, str):
        return {"files": [], "complete": True}
    
    # Parse using HDAP (strict mode)
    result = parse_hdap(raw_output)
    
    # Log results
    no_markers = result.get("no_hdap_markers", False)
    
    if no_markers:
        print(f"[HDAP] ❌ NO HDAP MARKERS in {step_name} - output will be rejected")
        print(f"[HDAP]    Expected: <<<FILE path=\"...\">>>> content <<<END_FILE>>>")
        print(f"[HDAP]    Preview: {raw_output[:300]}...")
    elif not result["complete"]:
        print(f"[HDAP] ⚠️ Incomplete output detected in {step_name}")
        print(f"[HDAP]    Incomplete files: {result['incomplete_files']}")
    elif result["files"]:
        print(f"[HDAP] ✅ Parsed {len(result['files'])} files from {step_name}")
    else:
        print(f"[HDAP] ⚠️ No files found in output for {step_name}")
    
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# COMPLETENESS CHECK (for step invariants)
# ═══════════════════════════════════════════════════════════════════════════════

def is_output_complete(parsed: Dict[str, Any]) -> bool:
    """
    Check if parsed output is complete (no truncation).
    
    Returns True if:
    - All files have matching END_FILE markers
    - At least one file was extracted
    - HDAP markers were present
    """
    if parsed.get("no_hdap_markers", False):
        return False  # No HDAP = not complete
    return parsed.get("complete", False) and len(parsed.get("files", [])) > 0


def get_incomplete_files(parsed: Dict[str, Any]) -> List[str]:
    """Get list of files that were truncated (missing END_FILE)."""
    return parsed.get("incomplete_files", [])


def has_hdap_markers(parsed: Dict[str, Any]) -> bool:
    """Check if the output contained HDAP markers at all."""
    return not parsed.get("no_hdap_markers", False)


# ═══════════════════════════════════════════════════════════════════════════════
# JSON METADATA PARSER (For structured data, NOT files)
# ═══════════════════════════════════════════════════════════════════════════════

def parse_json_metadata(raw: str) -> Dict[str, Any]:
    """
    Parse JSON metadata from LLM output.
    
    Use this for steps that return STRUCTURED DATA (not files):
    - Analysis step (domain, entities, features)
    - Review/approval responses
    - Classification results
    
    This does NOT expect HDAP markers - it parses plain JSON.
    
    Args:
        raw: Raw LLM response (should be JSON)
        
    Returns:
        Parsed JSON dict, or {"parse_error": "..."} on failure
    """
    import json
    
    if not raw or not isinstance(raw, str):
        return {"parse_error": "Empty or invalid input"}
    
    # Clean the input
    cleaned = raw.strip()
    
    # Remove markdown code fences if present
    if cleaned.startswith('```'):
        lines = cleaned.split('\n')
        # Remove first line (```json or ```)
        if lines:
            lines = lines[1:]
        # Remove last line if it's just ```
        if lines and lines[-1].strip() == '```':
            lines = lines[:-1]
        cleaned = '\n'.join(lines)
    
    # Try to parse JSON
    try:
        result = json.loads(cleaned)
        return result
    except json.JSONDecodeError as e:
        # Try to find JSON object in the text
        import re
        json_match = re.search(r'\{[\s\S]*\}', cleaned)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass
        
        return {"parse_error": f"JSON parse failed: {str(e)}", "raw_preview": cleaned[:200]}


def parse_json(raw: str) -> Dict[str, Any]:
    """
    Legacy JSON parser - delegates to parse_json_metadata.
    
    Kept for backwards compatibility.
    """
    return parse_json_metadata(raw)


def sanitize_marcus_output(raw: str) -> str:
    """Legacy function - now just returns cleaned input."""
    if not raw:
        return raw
    return raw.strip()


# ═══════════════════════════════════════════════════════════════════════════════
# UNICODE NORMALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

def normalize_unicode_aggressively(content: str, filepath: str = "") -> str:
    """
    Aggressively normalize Unicode to ASCII in code content.
    
    LLMs sometimes output fancy Unicode characters that break parsers:
    - Smart quotes ("" '' instead of "" '')
    - En/em dashes (– — instead of -)
    - Non-breaking spaces
    - Full-width characters
    
    This function strips ALL non-ASCII characters to prevent syntax errors.
    
    Args:
        content: Raw file content from LLM
        filepath: Path for logging (optional)
        
    Returns:
        ASCII-only content with problematic chars replaced
    """
    if not content:
        return content
    
    # Replacement map for common Unicode -> ASCII
    replacements = {
        # Smart quotes
        '"': '"', '"': '"',  # Curly double quotes
        ''': "'", ''': "'",  # Curly single quotes
        '‟': '"', '‚': "'",  # More quote variants
        # Dashes
        '–': '-', '—': '-',  # En/em dashes
        '−': '-',            # Minus sign
        # Spaces
        '\u00a0': ' ',       # Non-breaking space
        '\u2002': ' ',       # En space
        '\u2003': ' ',       # Em space
        '\u2009': ' ',       # Thin space
        # Arrows
        '→': '->',           # Right arrow
        '←': '<-',           # Left arrow
        '↔': '<->',          # Bidirectional arrow
        # Math symbols
        '×': '*',            # Multiplication
        '÷': '/',            # Division
        '≠': '!=',           # Not equal
        '≤': '<=',           # Less than or equal
        '≥': '>=',           # Greater than or equal
        # Ellipsis
        '…': '...',          # Horizontal ellipsis
    }
    
    # Apply replacements
    result = content
    for unicode_char, ascii_replacement in replacements.items():
        result = result.replace(unicode_char, ascii_replacement)
    
    # Strip any remaining non-ASCII characters
    # This is the "aggressive" part - anything not in ASCII range gets removed
    result = result.encode('ascii', 'ignore').decode('ascii')
    
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "normalize_llm_output",
    "parse_hdap",
    "parse_json",
    "parse_json_metadata",
    "sanitize_marcus_output",
    "is_output_complete",
    "get_incomplete_files",
    "has_hdap_markers",
    "normalize_unicode_aggressively",
]

