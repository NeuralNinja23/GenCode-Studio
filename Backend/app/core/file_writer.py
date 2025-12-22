# app/core/file_writer.py
"""
Centralized file writing utility for LLM outputs.
"""
from pathlib import Path
from typing import Any, Dict, List
from app.core.logging import log
from app.core.llm_output_integrity import validate_llm_files, LLMOutputIntegrityError


def convert_files_list_to_dict(files: List[Dict[str, str]]) -> Dict[str, str]:
    """
    Convert list of {"path": ..., "content": ...} to dict {path: content}.
    """
    return {f["path"]: f["content"] for f in files if "path" in f and "content" in f}


async def write_validated_files(
    project_path: Path,
    files: List[Dict[str, str]],
    step: str,
) -> int:
    """
    Validate and write LLM-generated files to disk.
    
    Args:
        project_path: Base project directory
        files: List of {"path": ..., "content": ...} dicts
        step: Current workflow step name for logging
        
    Returns:
        Number of files written
        
    Raises:
        LLMOutputIntegrityError: If validation fails
    """
    if not files:
        return 0
    
    # Convert to dict format for validation
    files_dict = convert_files_list_to_dict(files)
    
    # Validate (raises on error)
    validate_llm_files(files_dict, step)
    
    # Write files
    written = 0
    for path, content in files_dict.items():
        try:
            full_path = project_path / path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")
            written += 1
        except Exception as e:
            log(step, f"❌ Failed to write {path}: {e}")
    
    return written


# Legacy compatibility aliases
async def persist_agent_output(
    manager: Any,
    project_id: str,
    project_path: Path,
    parsed: Dict[str, Any],
    step: str,
) -> int:
    """
    Legacy wrapper for write_validated_files.
    Extracts files from parsed dict and writes them.
    """
    files = parsed.get("files", [])
    return await write_validated_files(project_path, files, step)


def validate_file_output(
    parsed: Dict[str, Any],
    step: str,
    max_files: int = 10,
) -> Dict[str, Any]:
    """
    Legacy wrapper - validates and returns the same parsed dict.
    """
    files = parsed.get("files", [])
    if not files:
        return parsed
    
    # Convert and validate
    files_dict = convert_files_list_to_dict(files)
    validate_llm_files(files_dict, step)
    
    # Return original structure (validated)
    return parsed


async def safe_write_llm_files(
    manager: Any,
    project_id: str,
    project_path: Path,
    files: List[Dict[str, str]],
    step_name: str,
) -> int:
    """
    Legacy compatibility wrapper for write_validated_files.
    """
    return await write_validated_files(project_path, files, step_name)
