# app/lib/file_system.py
# GenCode Studio - Unified File System Operations
# ✅ UPDATED: Added sanitize_project_id, within_workspace, fixed __pycache__ filter
# Last Updated: November 8, 2025

import re
import aiofiles
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel

# ================================================================
# MODELS
# ================================================================

class GeneratedFile(BaseModel):
    """Represents a file to be written to disk"""
    path: str
    code: str

class FileTreeEntry(BaseModel):
    """Represents a file or folder in the file tree"""
    name: str
    path: str
    type: str  # "file" or "folder"
    children: Optional[List["FileTreeEntry"]] = None

# ================================================================
# ✅ PATH SAFETY FUNCTIONS
# ================================================================

def sanitize_project_id(project_id: str) -> str:
    """
    Normalize project IDs for safe filesystem use.
    Replaces any character not in [a-zA-Z0-9._-] with underscore.
    """
    return re.sub(r'[^a-zA-Z0-9._-]', '_', project_id)


def get_safe_workspace_path(base_path: Path, project_id: str) -> Path:
    """
    Build a safe, absolute project workspace path under base_path.
    
    NOTE: For new code, prefer using app.utils.path_utils.get_project_path()
    which uses centralized settings. This function is maintained for
    backwards compatibility with existing code that passes explicit base_path.
    """
    safe_id = sanitize_project_id(project_id)
    
    # If base_path is already absolute, trust it to avoid CWD issues
    if base_path.is_absolute():
        root = base_path / safe_id
    else:
        # Try to resolve relative path
        try:
            base = base_path.resolve()
        except FileNotFoundError:
            try:
                base = base_path.absolute()
            except FileNotFoundError:
                # If CWD is gone, we can't resolve relative path. 
                # Just use it as-is and hope for the best.
                base = base_path
        root = base / safe_id

    root.mkdir(parents=True, exist_ok=True)
    return root

def within_workspace(workspace_base: Path, project_id: str, candidate: Path) -> bool:
    project_root = get_safe_workspace_path(workspace_base, project_id)
    try:
        candidate.resolve().relative_to(project_root.resolve())
        return True
    except Exception:
        return False

# ================================================================
# FILE I/O OPERATIONS
# ================================================================

async def read_file_content(file_path: Path) -> str:
    """Read a text file asynchronously."""
    async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
        return await f.read()

async def write_file_content(file_path: Path, content: str) -> None:
    """Write text content to a file asynchronously, ensuring parent directory exists."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
        await f.write(content)


def write_file_content_sync(file_path: Path, content: str, encoding: str = "utf-8") -> None:
    """
    Write text content to a file synchronously, ensuring parent directory exists.
    
    This is the SINGLE SOURCE OF TRUTH for synchronous file writing.
    Use this instead of direct path.write_text() calls for consistency.
    
    Args:
        file_path: Path to the file to write
        content: Text content to write
        encoding: File encoding (default: utf-8)
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding=encoding)

async def save_generated_files(workspace_base: Path, project_id: str, files: List[GeneratedFile]) -> List[str]:
    """
    Save a batch of generated files relative to the project root.
    Returns a list of written relative paths.
    """
    project_root = get_safe_workspace_path(workspace_base, project_id)
    written: List[str] = []
    for gf in files:
        rel = gf.path.lstrip("/").replace("\\", "/")
        target = project_root / rel
        # Safety: ensure write remains within project directory
        if not within_workspace(workspace_base, project_id, target):
            continue
        await write_file_content(target, gf.code)
        written.append(rel)
    return written

# ================================================================
# FILE TREE OPERATIONS
# ================================================================

async def get_project_file_tree(workspace_path: Path, project_id: str) -> Optional[FileTreeEntry]:
    """
    ✅ UPDATED: Build a recursive file tree for the given project.
    Now uses sanitize_project_id and filters __pycache__ correctly.
    Skips hidden files and __pycache__ directories.
    """
    project_root = get_safe_workspace_path(workspace_path, project_id)
    if not project_root.exists():
        return None
    return await _read_dir_recursive(project_root, project_root)

async def _read_dir_recursive(directory: Path, project_root: Path) -> FileTreeEntry:
    """
    ✅ UPDATED: Recursively read directory structure, returning FileTreeEntry.
    Now correctly filters __pycache__ (was "pycache" before).
    Skips dotfiles and __pycache__.
    """
    children: List[FileTreeEntry] = []
    for item in sorted(directory.iterdir()):
        # ✅ FIXED: Now filters __pycache__ correctly
        if item.name.startswith(".") or item.name == "__pycache__":
            continue
        
        # Use absolute path if available to avoid CWD issues
        if item.is_absolute():
            item_path = item
        else:
            try:
                item_path = item.resolve()
            except FileNotFoundError:
                try:
                    item_path = item.absolute()
                except FileNotFoundError:
                    item_path = item

        if project_root.is_absolute():
            root_path = project_root
        else:
            try:
                root_path = project_root.resolve()
            except FileNotFoundError:
                try:
                    root_path = project_root.absolute()
                except FileNotFoundError:
                    root_path = project_root

        rel = str(item_path.relative_to(root_path))
        
        if item.is_dir():
            children.append(await _read_dir_recursive(item, project_root))
        else:
            children.append(FileTreeEntry(name=item.name, path=rel, type="file"))
            
    # Handle the directory path itself
    if directory.is_absolute():
        dir_path = directory
    else:
        try:
            dir_path = directory.resolve()
        except FileNotFoundError:
            try:
                dir_path = directory.absolute()
            except FileNotFoundError:
                dir_path = directory
        
    if project_root.is_absolute():
        root_path = project_root
    else:
        try:
            root_path = project_root.resolve()
        except FileNotFoundError:
            try:
                root_path = project_root.absolute()
            except FileNotFoundError:
                root_path = project_root

    return FileTreeEntry(
        name=directory.name,
        path=str(dir_path.relative_to(root_path)),
        type="folder",
        children=children or None,
    )
