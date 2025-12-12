# app/persistence/validator.py
"""
Output validation before persistence.
"""
from typing import Any, Dict

from app.core.config import settings
from app.core.logging import log  # Use canonical import


def normalize_python_filename(path: str) -> str:
    """
    Normalize Python filenames for Linux/Docker compatibility.
    
    On Windows, file imports are case-insensitive, but on Linux they are case-sensitive.
    This ensures router files like 'Reports.py' become 'reports.py' so that
    'from app.routers import reports' works correctly in Docker.
    
    Applies to:
    - backend/app/routers/*.py -> lowercase filename
    - backend/app/*.py -> lowercase filename (except __init__.py)
    """
    original = path
    
    # Only process Python files in backend
    if not path.endswith('.py'):
        return path
    
    # Paths that should have lowercase filenames
    lowercase_dirs = [
        'backend/app/routers/',
        'backend/app/api/',
    ]
    
    for dir_prefix in lowercase_dirs:
        if path.startswith(dir_prefix):
            # Extract filename and make it lowercase
            dir_part = path[:len(dir_prefix)]
            filename = path[len(dir_prefix):]
            
            # Skip __init__.py and already lowercase files
            if filename == '__init__.py':
                return path
            
            lowercase_filename = filename.lower()
            
            if filename != lowercase_filename:
                new_path = dir_part + lowercase_filename
                log("VALIDATE", f"🔧 Normalized filename for Linux: {original} -> {new_path}")
                return new_path
    
    return path


def fix_path_prefix(path: str) -> str:
    """
    Auto-fix common path prefix issues.
    
    Fixes:
    - components/X.jsx -> frontend/src/components/X.jsx
    - pages/X.jsx -> frontend/src/pages/X.jsx
    - src/X -> frontend/src/X
    - tests/e2e.spec.js -> frontend/tests/e2e.spec.js
    """
    original = path
    
    # Already correct
    if path.startswith("frontend/") or path.startswith("backend/"):
        return path
    
    # Fix src/ prefix
    if path.startswith("src/"):
        path = "frontend/" + path
        log("VALIDATE", f"Fixed path: {original} -> {path}")
        return path
    
    # Fix components/ or pages/ or lib/ etc
    frontend_dirs = ["components/", "pages/", "lib/", "data/", "hooks/", "utils/"]
    for prefix in frontend_dirs:
        if path.startswith(prefix):
            path = "frontend/src/" + path
            log("VALIDATE", f"Fixed path: {original} -> {path}")
            return path
    
    # Fix tests/ for frontend
    if path.startswith("tests/") and any(path.endswith(ext) for ext in [".jsx", ".js", ".ts", ".tsx"]):
        path = "frontend/" + path
        log("VALIDATE", f"Fixed path: {original} -> {path}")
        return path
    
    return path


def validate_jsx_completeness(content: str, path: str) -> bool:
    """
    Basic validation that JSX has balanced tags.
    Returns True if valid, False if suspicious.
    """
    if not path.endswith(('.jsx', '.tsx')):
        return True
    
    # Count opening and closing braces
    open_braces = content.count('{')
    close_braces = content.count('}')
    if abs(open_braces - close_braces) > 2:  # Allow small tolerance
        log("VALIDATE", f"⚠️ JSX may have unbalanced braces in {path}: {{ {open_braces}, }} {close_braces}")
        return False
    
    # Count opening and closing parens
    open_parens = content.count('(')
    close_parens = content.count(')')
    if abs(open_parens - close_parens) > 2:
        log("VALIDATE", f"⚠️ JSX may have unbalanced parens in {path}: ( {open_parens}, ) {close_parens}")
        return False
    
    # Check for common truncation patterns
    if content.rstrip().endswith('...') or content.rstrip().endswith('// ...'):
        log("VALIDATE", f"⚠️ JSX appears truncated in {path}")
        return False
    
    return True


def validate_file_output(
    response: Dict[str, Any],
    step_name: str,
    max_files: int = None,
    skip_incomplete_jsx: bool = False,
) -> Dict[str, Any]:
    """
    Validate and sanitize agent output before writing.
    
    - Filters invalid files
    - Limits file count
    - Normalizes paths
    - Auto-fixes path prefixes
    - Validates JSX completeness
    - REJECTS empty content
    
    Args:
        response: Agent output dict with 'files' key
        step_name: Name of the workflow step (for logging)
        max_files: Maximum files allowed (defaults to config)
        skip_incomplete_jsx: If True, skip incomplete JSX files instead of including them
    
    Returns:
        Validated response with cleaned files list
    
    Raises:
        ValueError: If response structure is invalid
    """
    
    max_files = max_files or settings.workflow.max_files_per_step
    
    # Handle parse errors
    if "parseerror" in response:
        raise ValueError(f"JSON parsing failed: {response.get('parseerror')}")
    
    files = response.get("files", [])
    
    if not files:
        log("VALIDATE", f"[{step_name}] No files in response")
        return {"files": [], "thinking": response.get("thinking", "")}
    
    if not isinstance(files, list):
        raise ValueError(f"'files' must be a list, got {type(files).__name__}")
    
    validated = []
    
    for idx, f in enumerate(files):
        if not isinstance(f, dict):
            log("VALIDATE", f"[{step_name}] Skipping non-dict file entry at index {idx}")
            continue
        
        # 🛡️ FIX: Handle "name", "filename", "filepath" as aliases for "path"
        # Derek sometimes uses wrong key names - accept them all
        if "path" not in f:
            for alias in ["name", "filename", "filepath", "file_path", "filePath"]:
                if alias in f:
                    f["path"] = f.pop(alias)
                    log("VALIDATE", f"[{step_name}] 🔧 Converted '{alias}' to 'path' for file at index {idx}")
                    break
        
        path = f.get("path", "")
        content = f.get("content", "")
        
        # 🚨 CRITICAL: Reject empty content
        if not path:
            log("VALIDATE", f"[{step_name}] Skipping file with no path at index {idx}")
            continue
        
        if not content or not content.strip():
            log("VALIDATE", f"[{step_name}] 🚨 REJECTING empty file: {path}")
            continue
        
        # Skip placeholder paths
        invalid_names = {"...", "example.py", "output.txt", "file.txt", "unknown"}
        if path in invalid_names:
            log("VALIDATE", f"[{step_name}] Skipping placeholder path: {path}")
            continue
        
        # Normalize path
        path = path.replace("\\", "/").lstrip("/")
        
        # Auto-fix path prefix
        path = fix_path_prefix(path)
        
        # Normalize Python filenames for Linux/Docker compatibility
        path = normalize_python_filename(path)
        
        # Must have extension or be a known filename
        if "." not in path and path not in {"Dockerfile", "Makefile", ".gitignore"}:
            log("VALIDATE", f"[{step_name}] Skipping path without extension: {path}")
            continue
        
        # Validate Python Syntax
        if path.endswith(".py"):
             if not validate_python_syntax(content, path):
                 continue
        
        # Validate JSX completeness
        if path.endswith((".jsx", ".tsx")):
            is_valid = validate_jsx_completeness(content, path)
            if not is_valid and skip_incomplete_jsx:
                log("VALIDATE", f"[{step_name}] ⚠️ Skipping incomplete JSX: {path}")
                continue
            elif not is_valid:
                log("VALIDATE", f"[{step_name}] ⚠️ JSX may have issues: {path} (will write anyway)")
        
        validated.append({"path": path, "content": content})
        
        if len(validated) >= max_files:
            log("VALIDATE", f"[{step_name}] Reached max files ({max_files}), truncating")
            break
    
    
    return {"files": validated, "thinking": response.get("thinking", "")}


def validate_python_syntax(content: str, path: str) -> bool:
    """
    Validate Python syntax using AST.
    Returns True if valid, False if SyntaxError.
    """
    import ast
    try:
        ast.parse(content)
        return True
    except SyntaxError as e:
        log("VALIDATE", f"🚨 REJECTING invalid Python file: {path} - {e}")
        return False
    except Exception as e:
        # Don't block on other AST errors (unlikely), but log them
        log("VALIDATE", f"⚠️ AST validation error for {path}: {e}")
        return True



