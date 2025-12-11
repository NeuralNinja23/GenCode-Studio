# app/orchestration/structural_compiler.py
"""
Compiler-Layer Structural Validator (Python + JS) — Python 3.12

Acts like a mini-compiler to ensure the generated code is structurally valid.
- Python AST validation
- JS structural validation (regex-level + bracket analysis)
- Router CRUD completeness
- API client export completeness
"""
import ast
import re
from typing import Optional, Dict, List


class StructuralCompiler:
    """
    Acts like a mini-compiler to ensure the generated code is structurally valid.
    - Python AST validation
    - JS structural validation (regex-level + bracket analysis)
    - Router CRUD completeness
    - API client export completeness
    """
    
    REQUIRED_ROUTER_FUNCTIONS = [
        "create",
        "get_all",
        "get_one",
        "update",
        "delete",
    ]

    def __init__(self):
        pass

    # ---------------------------------------------------------
    # Python structural validation
    # ---------------------------------------------------------
    def validate_python(self, code: str) -> bool:
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False

    def get_python_errors(self, code: str) -> Optional[str]:
        """Get Python syntax error details."""
        try:
            ast.parse(code)
            return None
        except SyntaxError as e:
            return f"Line {e.lineno}: {e.msg}"

    # ---------------------------------------------------------
    # JavaScript structural validation
    # ---------------------------------------------------------
    def validate_js(self, code: str) -> bool:
        if not self._balanced_brackets(code):
            return False

        # Basic sanity: no unfinished export
        if "export" in code and not re.search(r"export\s+\w", code):
            return False

        return True

    # ---------------------------------------------------------
    # Router completeness check
    # ---------------------------------------------------------
    def router_is_complete(self, code: str) -> bool:
        """Check if router has all required CRUD functions."""
        for fn in self.REQUIRED_ROUTER_FUNCTIONS:
            # Match async def create, async def get_all, etc.
            pattern = rf"async\s+def\s+{fn}\b"
            if not re.search(pattern, code):
                # Also check for alternate naming (e.g., create_note, get_notes)
                alt_pattern = rf"async\s+def\s+{fn}_?\w*\b"
                if not re.search(alt_pattern, code):
                    return False
        return True

    def get_missing_router_functions(self, code: str) -> List[str]:
        """Get list of missing CRUD functions."""
        missing = []
        for fn in self.REQUIRED_ROUTER_FUNCTIONS:
            pattern = rf"async\s+def\s+{fn}\b"
            alt_pattern = rf"async\s+def\s+{fn}_?\w*\b"
            if not re.search(pattern, code) and not re.search(alt_pattern, code):
                missing.append(fn)
        return missing

    # ---------------------------------------------------------
    # API export completeness check
    # ---------------------------------------------------------
    def api_is_complete(self, code: str, entity_name: str) -> bool:
        """
        Check if API client has all required exports for the entity.
        e.g. getNotes, createNote, updateNote, deleteNote
        
        Args:
            code: The API client code to validate
            entity_name: Entity name (REQUIRED - no hardcoded default)
        """
        # Smart pluralization/capitalization
        singular = entity_name.capitalize()
        # Simple pluralization guess
        plural = singular + "s" if not singular.endswith("s") else singular
        
        required_exports = [
            f"get{plural}",      # getNotes
            f"create{singular}", # createNote
            f"update{singular}", # updateNote
            f"delete{singular}", # deleteNote
        ]
        
        for fn in required_exports:
            pattern = rf"export\s+(async\s+)?function\s+{fn}\b"
            if not re.search(pattern, code):
                return False
        return True

    def get_missing_api_exports(self, code: str, entity_name: str) -> List[str]:
        """Get list of missing API exports.
        
        Args:
            code: The API client code to validate
            entity_name: Entity name (REQUIRED - no hardcoded default)
        """
        singular = entity_name.capitalize()
        plural = singular + "s" if not singular.endswith("s") else singular
        
        required_exports = [
            f"get{plural}",
            f"create{singular}",
            f"update{singular}",
            f"delete{singular}",
        ]
        
        missing = []
        for fn in required_exports:
            pattern = rf"export\s+(async\s+)?function\s+{fn}\b"
            if not re.search(pattern, code):
                missing.append(fn)
        return missing

    # ---------------------------------------------------------
    # Helper: JS/Python bracket balance
    # ---------------------------------------------------------
    def _balanced_brackets(self, text: str) -> bool:
        pairs = {"{": "}", "[": "]", "(": ")"}
        stack = []
        in_string = False
        string_char = None
        prev_char = None
        
        for ch in text:
            # Handle string literals
            if ch in ('"', "'", '`') and prev_char != '\\':
                if not in_string:
                    in_string = True
                    string_char = ch
                elif ch == string_char:
                    in_string = False
                    string_char = None
            
            # Only count brackets outside strings
            if not in_string:
                if ch in pairs:
                    stack.append(ch)
                elif ch in pairs.values():
                    if not stack:
                        return False
                    if pairs[stack.pop()] != ch:
                        return False
            
            prev_char = ch
        
        return len(stack) == 0

    # ---------------------------------------------------------
    # Combined validation
    # ---------------------------------------------------------
    def validate_file(self, filename: str, content: str) -> bool:
        """Validate file based on extension."""
        if filename.endswith('.py'):
            return self.validate_python(content)
        elif filename.endswith(('.js', '.jsx', '.ts', '.tsx')):
            return self.validate_js(content)
        return True  # Unknown file types pass
