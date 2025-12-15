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
from typing import Optional, List


class StructuralCompiler:
    """
    Acts like a mini-compiler to ensure the generated code is structurally valid.
    - Python AST validation
    - JS structural validation (regex-level + bracket analysis)
    - Router CRUD completeness (flexible pattern matching)
    - API client export completeness
    """

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
    
    # FLEXIBLE CRUD patterns - accept common naming conventions
    # Derek might use list_items, get_item, etc. instead of get_all, get_one
    # FIX: Made patterns more flexible to avoid false validation failures
    CRUD_PATTERNS = {
        "create": [
            r"async\s+def\s+create\b",           # create()
            r"async\s+def\s+create_\w+",          # create_item()
            r"async\s+def\s+add_?\w*",            # add(), add_item()
            r"async\s+def\s+new_?\w*",            # new(), new_item()
            r"@router\.post",                     # Has POST endpoint (fallback)
        ],
        "read_all": [
            r"async\s+def\s+get_all\b",          # get_all()
            r"async\s+def\s+get_all_\w+",         # get_all_items()
            r"async\s+def\s+list_?\w*",           # list(), list_items()
            r"async\s+def\s+get_\w+s\b",          # get_items() (plural)
            r"@router\.get.*[\"']/[\"']",         # FIX: GET "/" (multi-line safe)
        ],
        "read_one": [
            r"async\s+def\s+get_one\b",          # get_one()
            r"async\s+def\s+get_one_\w+",         # get_one_item()
            r"async\s+def\s+get_\w+\b(?!s\b)",    # get_item() but NOT get_items()
            r"async\s+def\s+get_\w*by_id",        # FIX: get_by_id() or get_ticket_by_id()
            r"async\s+def\s+get_\w+_by_\w+",      # FIX: get_item_by_id() (flexible)
            r"async\s+def\s+read_?\w*",           # read(), read_item()
            r"@router\.get.*[\"']/\{",            # FIX: GET "/{id}" (multi-line safe)
        ],
        "update": [
            r"async\s+def\s+update\b",           # update()
            r"async\s+def\s+update_\w+",          # update_item()
            r"async\s+def\s+edit_?\w*",           # edit(), edit_item()
            r"async\s+def\s+modify_?\w*",         # modify(), modify_item()
            r"@router\.put",                      # Has PUT endpoint (fallback)
        ],
        "delete": [
            r"async\s+def\s+delete\b",           # delete()
            r"async\s+def\s+delete_\w+",          # delete_item()
            r"async\s+def\s+remove_?\w*",         # remove(), remove_item()
            r"@router\.delete",                   # Has DELETE endpoint (fallback)
        ],
    }
    
    def router_is_complete(self, code: str) -> bool:
        """
        Check if router has all required CRUD operations.
        
        FLEXIBLE: Accepts common naming patterns, not just exact names.
        Derek might use list_items, get_item, etc.
        """
        for operation, patterns in self.CRUD_PATTERNS.items():
            found = False
            for pattern in patterns:
                if re.search(pattern, code):
                    found = True
                    break
            if not found:
                return False
        return True

    def get_missing_router_functions(self, code: str) -> List[str]:
        """Get list of missing CRUD operations."""
        missing = []
        for operation, patterns in self.CRUD_PATTERNS.items():
            found = False
            for pattern in patterns:
                if re.search(pattern, code):
                    found = True
                    break
            if not found:
                missing.append(operation)
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
    def validate_file_structure(self, filename: str, content: str) -> bool:
        """Validate file structure based on extension (brackets, basic syntax)."""
        if filename.endswith('.py'):
            return self.validate_python(content)
        elif filename.endswith(('.js', '.jsx', '.ts', '.tsx')):
            return self.validate_js(content)
        return True  # Unknown file types pass
