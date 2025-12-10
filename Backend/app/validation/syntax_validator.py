# app/validation/syntax_validator.py
"""
PRE-FLIGHT VALIDATION - Layer 1 Quality Gate

Catches 90% of syntax errors BEFORE sending to expensive LLM review.
Executes in <0.5s, saves $0.10+ per rejected file.

Validates:
- Python syntax (AST parsing)
- JavaScript/JSX basic structure
- Import statement formatting
- data-testid presence in React components
- Common LLM mistakes (all code on one line)
"""
import ast
import re
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path

from app.core.logging import log


class ValidationResult:
    """Result of syntax validation."""
    def __init__(
        self, 
        valid: bool, 
        errors: List[str] = None, 
        warnings: List[str] = None,
        fixed_content: Optional[str] = None
    ):
        self.valid = valid
        self.errors = errors or []
        self.warnings = warnings or []
        self.fixed_content = fixed_content
    
    def __bool__(self):
        return self.valid
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "fixed_content": self.fixed_content is not None
        }


class IncompleteCodeError(Exception):
    pass


def assert_no_empty_defs(path: str, content: str) -> None:
    """Check for empty function/class definitions (only pass/docstring)."""
    try:
        tree = ast.parse(content, filename=path)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                # Check if body has any substantive code
                has_code = False
                for stmt in node.body:
                    if isinstance(stmt, ast.Pass):
                        continue
                    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, (ast.Str, ast.Constant, ast.Ellipsis)):
                        continue
                    has_code = True
                    break
                
                if not has_code:
                     raise IncompleteCodeError(
                        f"Incomplete {type(node).__name__} '{node.name}' in {path} (empty body)"
                     )

    except SyntaxError:
        # Let SyntaxError propagate or be handled by caller
        raise

def validate_python_syntax(code: str, filename: str = "unknown.py") -> ValidationResult:
    """
    Validate Python code using AST parsing.
    
    Catches and AUTO-FIXES:
    - Malformed imports (multiple imports on one line)
    
    Catches:
    - Syntax errors
    - Incomplete statements
    - Empty class/function bodies (TRUNCATION)
    """
    errors = []
    warnings = []
    fixed_content = None
    
    if not code or not code.strip():
        return ValidationResult(False, ["Empty file content"])
    
    # Check for "all on one line" issue (common LLM artifact)
    lines = code.split('\n')
    if len(lines) == 1 and len(code) > 200:
        errors.append(
            f"CRITICAL: Entire file content appears to be on a single line ({len(code)} chars). "
            "This is a JSON parsing artifact - newlines were stripped from the code content."
        )
        return ValidationResult(False, errors)
    
    # AUTO-FIX: Malformed imports
    malformed_import_pattern = r'(\bimport\s+[\w\.]+)([ \t;]+import\s+)|(\bfrom\s+[\w\.]+\s+import\s+[\w\.\*]+)([ \t;]+from\s+)'
    if re.search(malformed_import_pattern, code):
        fixed_code = code
        fixed_code = re.sub(r'(\bimport\s+[\w\.]+)[ \t;]+(import\s+)', r'\1\n\2', fixed_code)
        fixed_code = re.sub(r'(\bfrom\s+[\w\.]+\s+import\s+[\w\.\*]+)[ \t;]+(from\s+)', r'\1\n\2', fixed_code)
        
        if fixed_code != code:
            code = fixed_code
            fixed_content = fixed_code
            warnings.append("Auto-fixed malformed import statements")
            log("VALIDATION", f"🔧 Auto-fixed imports in {filename}")

    # Try to parse the AST + check for empty defs
    try:
        assert_no_empty_defs(filename, code)
    except SyntaxError as e:
        errors.append(f"Python SyntaxError at line {e.lineno}: {e.msg}")
        if e.lineno and e.lineno <= len(lines):
             errors.append(f"  → Line {e.lineno}: {lines[e.lineno - 1][:80]}...")
        return ValidationResult(False, errors)
    except IncompleteCodeError as e:
        errors.append(str(e))
        return ValidationResult(False, errors)
    except Exception as e:
        errors.append(f"Failed to parse Python code: {str(e)}")
        return ValidationResult(False, errors)
    
    # Additional checks for common issues
    
    # Check for unclosed brackets/braces
    open_parens = code.count('(') - code.count(')')
    open_brackets = code.count('[') - code.count(']')
    open_braces = code.count('{') - code.count('}')
    
    if open_parens != 0:
        warnings.append(f"Unbalanced parentheses: {'+' if open_parens > 0 else ''}{open_parens}")
    if open_brackets != 0:
        warnings.append(f"Unbalanced brackets: {'+' if open_brackets > 0 else ''}{open_brackets}")
    if open_braces != 0:
        warnings.append(f"Unbalanced braces: {'+' if open_braces > 0 else ''}{open_braces}")
    
    return ValidationResult(True, [], warnings, fixed_content)


def validate_javascript_syntax(code: str, filename: str = "unknown.js") -> ValidationResult:
    """
    Basic JavaScript/JSX validation without a full parser.
    
    AUTO-FIXES:
    - Errant backslashes after comments (common LLM mistake)
    """
    errors = []
    warnings = []
    fixed_content = None
    
    if not code or not code.strip():
        return ValidationResult(False, ["Empty file content"])
    
    # Check for "all on one line" issue
    lines = code.split('\n')
    if len(lines) == 1 and len(code) > 200:
        errors.append(
            f"CRITICAL: Entire file content appears to be on a single line ({len(code)} chars). "
            "This is a JSON parsing artifact."
        )
        return ValidationResult(False, errors)
    
    # AUTO-FIX PATTERN 1: Errant backslashes in string literals
    # Pattern: "text\ more_text" or 'text\ more_text' (backslash before closing quote or mid-string)
    # This is THE MOST COMMON LLM error - backslashes appearing in mock data strings
    # Example: content: "Planning the initial\ status: 'Draft'" -> "Planning the initial status: 'Draft'"
    fixed_code = code
    fixes = []
    
    # Fix backslashes before closing quotes or linebreaks in strings
    # This pattern handles: "text\" or "text\  or "text\n within a string
    string_backslash_pattern = r'(["\'])([^"\']*?)\\+\s*([^"\']*?)\1'
    if re.search(string_backslash_pattern, fixed_code):
        # Remove backslashes within string literals
        fixed_code = re.sub(string_backslash_pattern, r'\1\2 \3\1', fixed_code)
        fixes.append("Fixed backslash in string literal")
    
    # Fix backslashes at end of lines within strings (split strings)
    # Pattern: "text\<newline>moretext"
    multiline_string_backslash = r'(["\'])([^"\']*?)\\\s*\n\s*([^"\']*?)\1'
    if re.search(multiline_string_backslash, fixed_code):
        fixed_code = re.sub(multiline_string_backslash, r'\1\2 \3\1', fixed_code)
        fixes.append("Fixed multiline string with backslash")
    
    # AUTO-FIX PATTERN 2: Backslashes after comments
    # Pattern: /* Comment */\  retries: or // Comment\  code
    # This is a common LLM error where it inserts a backslash at the end of a comment line
    backslash_after_comment_pattern = r'(//[^\n]*)\\\s*$'
    if re.search(backslash_after_comment_pattern, fixed_code, re.MULTILINE):
        fixed_code = re.sub(backslash_after_comment_pattern, r'\1', fixed_code, flags=re.MULTILINE)
        fixes.append("Removed backslash after comment line")
    
    # Also check for backslashes after block comments
    block_comment_backslash = r'(\*/|\*\/)\s*\\\s+([a-zA-Z_])'
    if re.search(block_comment_backslash, fixed_code):
        fixed_code = re.sub(block_comment_backslash, r'\1\n  \2', fixed_code)
        fixes.append("Fixed backslash after block comment")
    
    # Apply fixes and log
    if fixes:
        code = fixed_code
        fixed_content = fixed_code
        warnings.append(f"Auto-fixed {len(fixes)} backslash issue(s): {', '.join(fixes)}")
        log("VALIDATION", f"🔧 Auto-fixed {len(fixes)} backslash patterns in {filename}")

    
    # Check bracket balance
    open_parens = code.count('(') - code.count(')')
    open_brackets = code.count('[') - code.count(']')
    open_braces = code.count('{') - code.count('}')
    
    if abs(open_parens) > 2:
        errors.append(f"Severely unbalanced parentheses: {open_parens}")
    if abs(open_brackets) > 2:
        errors.append(f"Severely unbalanced brackets: {open_brackets}")
    if abs(open_braces) > 2:
        errors.append(f"Severely unbalanced braces: {open_braces}")
    
    if errors:
        return ValidationResult(False, errors)
    
    # Check for data-testid in component files
    is_component = any(pattern in filename.lower() for pattern in ['page', 'component', 'card', 'form', 'list'])
    if is_component and 'data-testid' not in code:
        warnings.append(f"Component '{filename}' is missing data-testid attributes for testing")
    
    # NEW: Check for duplicate HTML/JSX attributes on the same element
    # This is a common LLM mistake: <main data-testid="a" className="..." data-testid="b">
    # Only the last attribute value is used by browsers, causing test failures
    duplicate_attr_issues = check_duplicate_attributes(code, filename)
    if duplicate_attr_issues:
        for issue in duplicate_attr_issues:
            warnings.append(issue)

    # Minor balance issues are warnings
    if open_parens != 0:
        warnings.append(f"Slightly unbalanced parentheses: {open_parens}")
    if open_brackets != 0:
        warnings.append(f"Slightly unbalanced brackets: {open_brackets}")
    if open_braces != 0:
        warnings.append(f"Slightly unbalanced braces: {open_braces}")

    return ValidationResult(True, [], warnings, fixed_content)


def check_duplicate_attributes(code: str, filename: str) -> List[str]:
    """
    Check for duplicate HTML/JSX attributes on the same element.
    
    Common LLM mistake:
        <main data-testid="page-root" className="..." data-testid="home-page">
    
    Browsers only use the LAST occurrence, causing Playwright tests to fail
    when they look for „data-testid="page-root"".
    """
    issues = []
    
    # Find all JSX opening tags with attributes
    # Pattern matches: <TagName attr1="val1" attr2="val2" ...>
    # We look for self-closing /> or regular >
    tag_pattern = r'<([A-Z][a-zA-Z0-9]*|[a-z][a-zA-Z0-9-]*)\s+([^>]+?)(?:/?>)'
    
    for match in re.finditer(tag_pattern, code):
        tag_name = match.group(1)
        attributes_str = match.group(2)
        
        # Find line number for better error messages
        line_num = code[:match.start()].count('\n') + 1
        
        # Extract all attribute names (handles attr="val", attr={expr}, attr)
        # Pattern: word characters, optionally followed by - (for data-testid, etc.)
        attr_pattern = r'([a-zA-Z][a-zA-Z0-9-]*)(?:\s*=)'
        attr_list = re.findall(attr_pattern, attributes_str)
        
        # Check for duplicates
        seen = {}
        for attr in attr_list:
            attr_lower = attr.lower()  # Case-insensitive for HTML
            if attr_lower in seen:
                issues.append(
                    f"Duplicate attribute '{attr}' on <{tag_name}> at line {line_num}. "
                    f"Only the last value will be used! (First: line {seen[attr_lower]}, Second: line {line_num})"
                )
            else:
                seen[attr_lower] = line_num
    
    return issues


def validate_file(path: str, content: str) -> ValidationResult:
    """
    Validate a file based on its extension.
    """
    path_lower = path.lower()
    
    if path_lower.endswith('.py'):
        return validate_python_syntax(content, path)
    elif path_lower.endswith(('.js', '.jsx', '.ts', '.tsx')):
        return validate_javascript_syntax(content, path)
    else:
        return ValidationResult(True, [], [])


def validate_files_batch(files: List[Dict[str, str]]) -> Tuple[List[Dict], List[Dict]]:
    """
    Validate a batch of files from LLM output.
    
    Args:
        files: List of {"path": str, "content": str} dicts
    
    Returns:
        Tuple of (valid_files, invalid_files)
        
    Each invalid file dict includes validation errors.
    Valid files will have their content UPDATED if auto-fixes were applied.
    """
    valid_files = []
    invalid_files = []
    
    for file_entry in files:
        path = file_entry.get("path", "")
        content = file_entry.get("content", "")
        
        result = validate_file(path, content)
        
        if result.valid:
            if result.warnings:
                log("PREFLIGHT", f"⚠️ {path}: {len(result.warnings)} warnings")
                # Add warnings to log but don't fail
            
            # Apply fix if available
            final_entry = file_entry.copy()
            if result.fixed_content:
                final_entry["content"] = result.fixed_content
                log("PREFLIGHT", f"✅ Applied auto-fix to {path}")
            
            valid_files.append(final_entry)
        else:
            log("PREFLIGHT", f"❌ {path}: REJECTED - {result.errors[0]}")
            invalid_file = {
                **file_entry,
                "validation_errors": result.errors,
                "validation_warnings": result.warnings,
            }
            invalid_files.append(invalid_file)
    
    return valid_files, invalid_files


def preflight_check(agent_output: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """
    Pre-flight validation gate for agent output.
    
    This is the main entry point, called BEFORE Marcus review.
    
    Args:
        agent_output: The parsed agent response with "files" list
        
    Returns:
        Tuple of (cleaned_output, rejection_reasons)
        
    If rejection_reasons is non-empty, the output should be rejected
    and the agent should be asked to regenerate.
    """
    rejection_reasons = []
    
    files = agent_output.get("files", [])
    if not files:
        # No files to validate
        return agent_output, []
    
    valid_files, invalid_files = validate_files_batch(files)
    
    # Build rejection reasons
    for invalid in invalid_files:
        path = invalid.get("path", "unknown")
        errors = invalid.get("validation_errors", [])
        rejection_reasons.append(f"{path}: {errors[0] if errors else 'Unknown error'}")
    
    # Return cleaned output with only valid files
    cleaned_output = {**agent_output, "files": valid_files}
    
    # Log summary
    if invalid_files:
        log("PREFLIGHT", f"🚨 PRE-FLIGHT REJECTED {len(invalid_files)}/{len(files)} files")
        log("PREFLIGHT", f"✅ {len(valid_files)} files passed validation")
    else:
        log("PREFLIGHT", f"✅ All {len(files)} files passed pre-flight validation")
    
    return cleaned_output, rejection_reasons
