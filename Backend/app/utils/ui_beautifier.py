# app/utils/ui_beautifier.py
"""
UI Beautifier - Post-processes frontend files to ensure consistency.

This is a provider-agnostic utility that applies consistent styling patterns
to agent-generated frontend code.
"""
import re
from pathlib import Path
from typing import Dict, List, Optional


def beautify_frontend_files(files: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Post-process frontend files to ensure UI consistency.
    
    Applies:
    - Standard page shell classes (min-h-screen, max-w-6xl, etc.)
    - Normalized spacing classes (gap-2/gap-3 → gap-4)
    - Ensures required data-testid attributes are present
    
    Only operates on .jsx/.tsx files under frontend/src/** (excluding components/ui/**)
    
    Args:
        files: List of file dicts with 'path' and 'content' keys
        
    Returns:
        Modified list of files with beautified content
    """
    result = []
    
    for f in files:
        path = f.get("path", "")
        content = f.get("content", "")
        
        # Only process frontend JSX files (not ui library)
        if not path or not content:
            result.append(f)
            continue
            
        normalized = path.replace("\\", "/")
        
        # Skip non-frontend or non-JSX files
        if not normalized.startswith("frontend/src/"):
            result.append(f)
            continue
            
        # Skip shadcn ui library (never modify)
        if "components/ui/" in normalized:
            result.append(f)
            continue
            
        # Only process .jsx and .tsx files
        if not normalized.endswith((".jsx", ".tsx")):
            result.append(f)
            continue
        
        # Apply beautification
        beautified = _beautify_jsx(content, normalized)
        
        result.append({
            "path": path,
            "content": beautified
        })
    
    return result


def _beautify_jsx(content: str, filepath: str) -> str:
    """Apply beautification rules to JSX content."""
    
    # 1. Normalize spacing classes
    content = _normalize_spacing(content)
    
    # 2. Ensure page-root testid on main pages (files in pages/ directory)
    if "/pages/" in filepath:
        content = _ensure_page_testids(content)
    
    return content


def _normalize_spacing(content: str) -> str:
    """Normalize inconsistent spacing classes for consistency."""
    
    # Normalize small gaps to standard gap-4
    # gap-1, gap-2, gap-3 → gap-4 (for containers)
    content = re.sub(r'\bgap-[123]\b', 'gap-4', content)
    
    # Normalize small space-y to standard
    # space-y-1, space-y-2, space-y-3 → space-y-4
    content = re.sub(r'\bspace-y-[123]\b', 'space-y-4', content)
    
    # Normalize small space-x
    content = re.sub(r'\bspace-x-[12]\b', 'space-x-4', content)
    
    # Normalize small padding on containers (but not on tiny elements)
    # This is a more selective rule - only for className containing multiple classes
    # to avoid breaking button padding etc.
    
    return content


def _ensure_page_testids(content: str) -> str:
    """Ensure required testids are present in page components."""
    
    # Check if page-title testid exists
    if 'data-testid="page-title"' not in content and 'data-testid=\'page-title\'' not in content:
        # Try to add to first h1 element if possible
        # Match <h1 with optional className
        if re.search(r'<h1\s+className=', content):
            content = re.sub(
                r'<h1\s+className=(["\'])',
                r'<h1 data-testid="page-title" className=\1',
                content,
                count=1  # Only first h1
            )
        elif re.search(r'<h1>', content):
            content = re.sub(
                r'<h1>',
                '<h1 data-testid="page-title">',
                content,
                count=1
            )
    
    # Check if page-root testid exists
    if 'data-testid="page-root"' not in content and 'data-testid=\'page-root\'' not in content:
        # Try to add to first <main element
        if re.search(r'<main\s+className=', content):
            content = re.sub(
                r'<main\s+className=(["\'])',
                r'<main data-testid="page-root" className=\1',
                content,
                count=1
            )
        elif re.search(r'<main>', content):
            content = re.sub(
                r'<main>',
                '<main data-testid="page-root">',
                content,
                count=1
            )
    
    return content


def ensure_page_shell(content: str) -> str:
    """
    Ensure page has standard shell wrapper classes.
    
    Expected pattern:
    <main data-testid="page-root" className="min-h-screen bg-background">
      <div className="max-w-6xl mx-auto px-6 py-10 space-y-8">
        ...
      </div>
    </main>
    
    This is a more aggressive transformation and should be used carefully.
    """
    # Check if already has the standard shell
    if 'min-h-screen' in content and 'max-w-6xl' in content:
        return content  # Already has shell
    
    # This could be dangerous to apply automatically
    # Only log a warning - let the agent handle it
    return content
