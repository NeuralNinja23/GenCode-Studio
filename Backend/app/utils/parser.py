import json
import re
from contextvars import ContextVar
from typing import Optional, Any, List, Dict, cast
from app.core.types import TestReport, MarcusPlan

# =======================================================
# 🚫 INVALID PSEUDO-FILENAMES (HTML-ish junk we ignore)
# =======================================================

INVALID_FILENAMES = {
    "div",
    "span",
    "ul",
    "li",
    "BrowserRouter",
    "section",
    "main",
    "header",
    "footer",
}


def extract_files_from_pseudo_json(raw: str) -> List[Dict[str, str]]:
    """
    Try to salvage file entries of the form:
      { "path": "some/file.jsx", "content": "...." }
    from non-strict JSON the LLM might have returned.
    Does NOT require the whole string to be valid JSON.
    """
    if not raw or not isinstance(raw, str):
        return []

    # Match objects that contain both "path": "..." and "content": "..."
    pattern = re.compile(
        r'\{[^{}]*"path"\s*:\s*"([^"]+)"[^{}]*"content"\s*:\s*"((?:[^"\\]|\\.)*)"[^{}]*\}',
        re.DOTALL,
    )

    files: List[Dict[str, str]] = []

    for match in pattern.finditer(raw):
        path = match.group(1).strip()
        if not path:
            continue

        # Filter out garbage like "div", "ul", etc.
        if path in INVALID_FILENAMES:
            print(f"[normalize_llm_output] ⚠️ Rejecting invalid pseudo path: '{path}'")
            continue

        # Must look like a file path (contains /, \, or a dot)
        if not ("/" in path or "\\" in path or "." in path):
            print(f"[normalize_llm_output] ⚠️ Rejecting non-file-like path: '{path}'")
            continue

        raw_content = match.group(2)

        # Decode escapes like \n, \", \t
        try:
            content = bytes(raw_content, "utf-8").decode("unicode_escape")
        except Exception:
            content = raw_content

        # 🚨 CRITICAL: Skip empty content - this should NEVER happen
        if not content or not content.strip():
            print(f"[extract_files_from_pseudo_json] 🚨 REJECTING empty file: {path}")
            continue

        files.append({"path": path, "content": content})

    return files


# =======================================================
# 🌍 UNIVERSAL NORMALIZER (for any LLM / any format)
# =======================================================

# Recursion guard to prevent infinite loops (async-safe using ContextVar)
_parsing_depth: ContextVar[int] = ContextVar("parsing_depth", default=0)
_MAX_PARSING_DEPTH = 3

def normalize_llm_output(raw_output: str) -> Dict[str, Any]:
    """
    Universal parser that converts any LLM output (JSON, markdown, or plain code)
    into a standard dict with {"files": [...]} for downstream persistence.
    Works across all models (Qwen, Gemini, GPT, Mistral, etc.)
    """
    if not raw_output or not isinstance(raw_output, str):
        return {}
    
    # FIX #8: Use ContextVar for async-safe recursion guard
    current_depth = _parsing_depth.get()
    if current_depth > _MAX_PARSING_DEPTH:
        print("[normalize_llm_output] ⚠️ Max parsing depth exceeded, returning empty")
        return {}
    
    # Set incremented depth for this context
    token = _parsing_depth.set(current_depth + 1)
    try:
        return _normalize_llm_output_inner(raw_output)
    finally:
        _parsing_depth.reset(token)


def _normalize_llm_output_inner(raw_output: str) -> Dict[str, Any]:
    """Inner implementation without recursion guard."""
    raw_output = raw_output.strip()
    
    # 1️⃣ Try clean JSON parsing first
    try:
        parsed = parse_json(raw_output)
        
        # ✅ FIX: Validate file paths if it's a dict with files
        if isinstance(parsed, dict):
            # ✅ Add explicit check that files is a list
            files_list = parsed.get("files")
            if files_list and isinstance(files_list, list):
                # Validate that paths are real file paths, not HTML tags
                valid_files: List[Dict[str, Any]] = []
                for f in files_list:  # ✅ Now iterating over explicitly typed list
                    if isinstance(f, dict):
                        # 🛡️ FIX: Handle "name", "filename", "filepath" as aliases for "path"
                        if "path" not in f:
                            for alias in ["name", "filename", "filepath", "file_path", "filePath"]:
                                if alias in f:
                                    f["path"] = f.pop(alias)
                                    print(f"[normalize_llm_output] 🔧 Converted '{alias}' to 'path'")
                                    break
                        
                        path = f.get("path", "")
                        # ✅ Check if path contains file extension or directory separator
                        if ("/" in path or "\\" in path or "." in path) and len(path) > 3:
                            valid_files.append(f)
                        else:
                            print(f"[normalize_llm_output] ⚠️ Rejecting invalid path: '{path}'")
                
                if valid_files:
                    return {"files": valid_files}
                else:
                    print("[normalize_llm_output] ⚠️ No valid files after path validation")
            
            return cast(Dict[str, Any], parsed)
        
        elif isinstance(parsed, list):
            return {"files": cast(List[Dict[str, Any]], parsed)}
    
    except Exception as e:
        print(f"[normalize_llm_output] JSON parse attempt failed: {e}")
        # fall through to salvage / tag-based extraction
    
    # 2️⃣ NEW: Try to salvage `"path": ..., "content": ...` pairs from pseudo-JSON
    salvaged = extract_files_from_pseudo_json(raw_output)
    if salvaged:
        print(f"[normalize_llm_output] ✅ Salvaged {len(salvaged)} files from pseudo-JSON")
        return {"files": salvaged}
    
    # 3️⃣ Extract markers or fenced code blocks
    files: List[Dict[str, str]] = []
    pattern = (
        r"<file(?:\s+(?:name|path)=['\"]([^'\"]+)['\"])?>\s*([\s\S]*?)<\/file>"  # <file>
        r"|<([^>]+)>\s*([\s\S]*?)<\/\3>"  # <tag>content</tag>
        r"|``````"  # ``````
    )
    
    for match in re.finditer(pattern, raw_output, re.DOTALL):
        file_name, content = None, None
        
        # Handle <file> and <tag> patterns
        if match.group(1) and match.group(2):
            file_name, content = match.group(1).strip(), match.group(2).strip()
        elif match.group(3) and match.group(4):
            file_name, content = match.group(3).strip(), match.group(4).strip()
        elif match.lastindex and match.group(match.lastindex):
            # This branch is mostly unused given the pattern, but kept for safety
            content = match.group(match.lastindex).strip()
        
        if not content:
            continue
        
        # 4️⃣ Guess file name if missing
        if not file_name:
            lower = content.lower()
            if "<!doctype html>" in lower or "<html" in lower:
                file_name = "index.html"
            elif "import react" in lower or "from react" in lower:
                file_name = "component.tsx"
            elif "function " in lower or "const " in lower or "let " in lower:
                file_name = "script.js"
            elif "def " in lower or "import " in lower:
                file_name = "script.py"
            else:
                file_name = "file.txt"
        
        # ✅ FIX: Only add if file_name looks valid
        if file_name and ("/" in file_name or "\\" in file_name or "." in file_name):
            files.append({"path": file_name, "content": content})
        else:
            print(f"[normalize_llm_output] ⚠️ Skipping invalid extracted filename: '{file_name}'")
    
    if files:
        return {"files": files}
    
    # FIX #10: Don't create garbage files - return empty dict instead
    # The caller (supervision) will handle the "no files" case appropriately
    print("[normalize_llm_output] ⚠️ Could not extract any valid files from LLM output")
    print(f"[normalize_llm_output] Raw output preview: {raw_output[:200]}...")
    return {"files": [], "parse_warning": "No valid files could be extracted from LLM response"}


# =======================================================
# 🧠 JSON SANITIZATION (The core LLM robustness logic)
# =======================================================

def _attempt_force_repair(text: str) -> str:
    """
    Force-close brackets if JSON is truncated or incomplete.
    Salvages partial Marcus outputs so workflow can continue.
    """
    open_braces = text.count("{")
    close_braces = text.count("}")
    if close_braces < open_braces:
        text += "}" * (open_braces - close_braces)

    open_brackets = text.count("[")
    close_brackets = text.count("]")
    if close_brackets < open_brackets:
        text += "]" * (open_brackets - close_brackets)

    return text


def _find_json_object(raw_text: str) -> str:
    """
    Isolates the outermost JSON object in the text.
    Used to trim LLM chatter before/after JSON blocks.
    """
    first_brace = raw_text.find("{")
    if first_brace == -1:
        return raw_text

    depth = 0
    last_brace = -1
    in_string = False
    escape_next = False

    for i in range(first_brace, len(raw_text)):
        char = raw_text[i]

        if escape_next:
            escape_next = False
            continue
        if char == "\\":
            escape_next = True
            continue
        if char == '"':
            in_string = not in_string
            continue

        if not in_string:
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    last_brace = i
                    break

    if last_brace == -1 or last_brace <= first_brace:
        return raw_text

    return raw_text[first_brace : last_brace + 1]


def sanitize_marcus_output(raw: str) -> str:
    """
    Cleans and normalizes messy model output before JSON parsing.
    Handles markdown fences, trailing chatter, and malformed endings.
    """
    if not raw or not isinstance(raw, str):
        return raw

    cleaned = raw.strip()

    # 1️⃣ Remove code fences and chatter
    cleaned = re.sub(r"^```(?:json|javascript|typescript)?\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"```\s*$", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^(?:Here is|Here’s|This is|Output:|Result:).*?(?=\{)", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"}(\s*(?:This|Note:|Explanation:|I've|The above).*)$", "}", cleaned, flags=re.IGNORECASE | re.DOTALL)

    # 2️⃣ Extract main JSON object
    cleaned = _find_json_object(cleaned)

    # 3️⃣ Fix common syntax issues
    cleaned = cleaned.replace("\r\n", "\n")
    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)

    return cleaned.strip()


# =======================================================
# 📝 TYPE VALIDATION
# =======================================================

def validate_qa_report_shape(report: Any) -> bool:
    """Validates structure of QA report against TestReport type."""
    try:
        if not isinstance(report, dict):
            return False

        has_summary = isinstance(report.get("summary"), str)
        has_passed = isinstance(report.get("passed"), bool)
        has_issues = isinstance(report.get("issues"), list)

        if not all([has_summary, has_passed, has_issues]):
            return False

        for issue in report["issues"]:
            has_required_fields = (
                isinstance(issue, dict)
                and isinstance(issue.get("file"), str)
                and isinstance(issue.get("line"), int)
                and isinstance(issue.get("area"), str)
                and isinstance(issue.get("description"), str)
                and isinstance(issue.get("suggested_fix"), str)
                and issue.get("severity") in ["critical", "major", "minor"]
            )
            if not has_required_fields:
                return False

        return True
    except Exception:
        return False


# =======================================================
# 💻 API & PARSE FUNCTIONS
# =======================================================

def log_api_error(provider: str, model: str, err: Any):
    """Logs API failures with provider and model context."""
    if hasattr(err, "response") and err.response is not None:
        print(f"[{provider} FAIL] ({model}) Status:{err.response.status_code}", err.response.text)
    else:
        print(f"[{provider} FAIL] ({model}) Setup", str(err))



def _replace_newlines_outside_strings(text: str) -> str:
    """
    Replace newlines with spaces ONLY outside of JSON string literals.
    
    This preserves multi-line code content inside "content": "..." fields
    while fixing JSON structure issues caused by newlines between JSON tokens.
    
    Example:
        Input:  {"path": "test.py",\n"content": "import foo\\nimport bar"}
        Output: {"path": "test.py", "content": "import foo\\nimport bar"}
        
    The literal \\n inside the string content is preserved, but the raw
    newline between JSON keys is replaced with a space.
    """
    result = []
    in_string = False
    escape_next = False
    
    for char in text:
        if escape_next:
            # This character is escaped, add it as-is
            result.append(char)
            escape_next = False
            continue
        
        if char == '\\':
            # Next character is escaped
            result.append(char)
            escape_next = True
            continue
        
        if char == '"':
            # Toggle string state
            in_string = not in_string
            result.append(char)
            continue
        
        if char == '\n' and not in_string:
            # Replace newline outside string with space
            result.append(' ')
        else:
            result.append(char)
    
    return ''.join(result)


def parse_json(raw: str) -> Optional[MarcusPlan]:
    """
    Production-grade JSON parser with multi-pass sanitization, repair, and salvage.
    
    Handles:
    - Truncated responses (unterminated strings)
    - Missing brackets/braces
    - Markdown code fences
    - LLM chatter before/after JSON
    
    Returns parsed dict or raises ValueError if completely unparseable.
    """
    sanitized = sanitize_marcus_output(raw)

    # Step 1: Try normal parsing
    try:
        return json.loads(sanitized)
    except Exception:
        pass

    # Step 2: Smart newline repair - only replace newlines OUTSIDE string literals
    # to preserve multi-line code content inside "content" fields
    try:
        repaired_structure = _replace_newlines_outside_strings(sanitized)
        parsed = json.loads(repaired_structure)
        print("[parse_json] Required smart newline repair to parse JSON (content preserved)")
        return cast(MarcusPlan, parsed)
    except Exception:
        pass

    # Step 3: Force structural repair (close brackets/braces)
    try:
        repaired = _attempt_force_repair(sanitized)
        parsed = json.loads(repaired)
        print("[parse_json] ✅ Force repair succeeded.")
        return cast(MarcusPlan, parsed)
    except Exception:
        pass
    
    # Step 4: NEW - Handle unterminated strings by closing them
    try:
        # Find last complete string and close it
        fixed = _fix_unterminated_strings(sanitized)
        if fixed != sanitized:
            repaired = _attempt_force_repair(fixed)
            parsed = json.loads(repaired)
            print("[parse_json] ✅ Fixed unterminated string and parsed successfully")
            return cast(MarcusPlan, parsed)
    except Exception:
        pass
    
    # Step 5: NEW - Try to extract partial files array even from broken JSON
    try:
        files = _extract_partial_files(raw)
        if files:
            print(f"[parse_json] ✅ Salvaged {len(files)} files from broken JSON")
            return {"files": files}
    except Exception:
        pass
    
    print("[parse_json] ❌ All repair attempts failed")
    print(f"[parse_json] Sanitized snippet: {sanitized[:500]}...")
    raise ValueError("JSON parse failed after all repair attempts")


def _fix_unterminated_strings(text: str) -> str:
    """
    Fix unterminated strings by finding the last open quote and closing it.
    Handles cases where LLM output is truncated mid-string.
    """
    # Count unbalanced quotes
    in_string = False
    last_quote_pos = -1
    escape_next = False
    
    for i, char in enumerate(text):
        if escape_next:
            escape_next = False
            continue
        if char == '\\':
            escape_next = True
            continue
        if char == '"':
            if not in_string:
                in_string = True
                last_quote_pos = i
            else:
                in_string = False
    
    # If we ended inside a string, close it
    if in_string and last_quote_pos >= 0:
        # Find a safe place to close - look for common truncation patterns
        # Truncate content at last complete word and close
        truncate_at = len(text)
        
        # Look for incomplete escape sequences at the end
        if text.endswith('\\'):
            truncate_at = len(text) - 1
        
        # Build repaired text: everything up to truncation + closing quote
        repaired = text[:truncate_at].rstrip()
        if repaired.endswith(','):
            repaired = repaired[:-1]
        repaired += '"'
        
        return repaired
    
    return text


def _salvage_complete_functions(code: str) -> str:
    """
    Extract only complete function/class definitions from truncated Python code.
    Discards incomplete functions at the end.
    
    Returns:
        - Salvaged code with complete functions only
        - Empty string if no complete code could be salvaged
    
    Strategy:
        1. Try to parse the whole thing (if it works, return as-is)
        2. Split into lines and find last complete function/class
        3. Return everything up to the last complete definition
        4. Verify the salvaged code parses without errors
    """
    import ast
    
    # Try to parse the whole thing first
    try:
        ast.parse(code)
        return code  # No truncation, return as-is
    except SyntaxError:
        pass  # Expected for truncated code
    
    # Split by lines and find last complete function/class
    lines = code.split('\n')
    
    # Track function/class boundaries by indentation
    last_complete_line = 0
    function_starts = []  # Stack of (line_number, indent_level)
    
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if not stripped or stripped.startswith('#'):
            continue
        
        # Calculate indentation
        indent = len(line) - len(stripped)
        
        # New top-level function/class definition
        if (stripped.startswith('def ') or 
            stripped.startswith('class ') or 
            stripped.startswith('async def ')) and indent == 0:
            function_starts.append((i, indent))
        
        # If we have function starts and current line returns to base indentation
        # it means previous function is complete
        if function_starts and indent == 0 and i > function_starts[-1][0] + 1:
            if not (stripped.startswith('def ') or 
                   stripped.startswith('class ') or 
                   stripped.startswith('async def ')):
                # We've exited a function block
                last_complete_line = i - 1
    
    # Also check if we have at least one complete function by looking at the stack
    if function_starts and len(function_starts) >= 1:
        # If we have multiple functions, the second-to-last is definitely complete
        if len(function_starts) >= 2:
            # Find the line where the second-to-last function ends
            # (start of last function - 1)
            last_complete_line = function_starts[-1][0] - 1
        elif last_complete_line == 0:
            # Single function - try to find where it ends naturally
            # Look for the last line with content at base indentation
            for i in range(len(lines) - 1, function_starts[0][0], -1):
                stripped = lines[i].lstrip()
                if stripped and not stripped.startswith('#'):
                    indent = len(lines[i]) - len(stripped)
                    if indent > 0:  # Still inside function
                        last_complete_line = i
                        break
    
    # Try to salvage up to the last complete line
    if last_complete_line > 10:  # At least some meaningful code
        salvaged = '\n'.join(lines[:last_complete_line + 1])
        
        # Verify it parses
        try:
            ast.parse(salvaged)
            return salvaged
        except SyntaxError:
            # Final attempt: remove last few lines and try again
            for attempt in range(5, 0, -1):
                try_line = last_complete_line - attempt
                if try_line > 10:
                    salvaged = '\n'.join(lines[:try_line + 1])
                    try:
                        ast.parse(salvaged)
                        return salvaged
                    except SyntaxError:
                        continue
    
    return ""  # Could not salvage anything


def _extract_partial_files(raw: str) -> List[Dict[str, str]]:

    """
    Extract files array from partially broken JSON.
    Handles cases where the JSON structure is valid but content is truncated.
    Also handles triple-quoted content that LLMs sometimes produce.
    
    CRITICAL: Now validates that extracted files are syntactically complete.
    """
    files = []
    
    def _is_truncated_code(path: str, content: str) -> bool:
        """
        Detect if code content appears to be truncated mid-statement.
        Returns True if the code looks incomplete.
        """
        if not content or len(content) < 10:
            return True
        
        content = content.rstrip()
        
        # Check for Python files
        if path.endswith('.py'):
            # Check for unclosed parentheses/brackets
            open_parens = content.count('(') - content.count(')')
            open_brackets = content.count('[') - content.count(']')
            open_braces = content.count('{') - content.count('}')
            
            if open_parens > 0 or open_brackets > 0 or open_braces > 0:
                print(f"[_extract_partial_files] ⚠️ Truncated Python file detected: {path} (unclosed brackets)")
                return True
            
            # Check for incomplete statements
            bad_endings = [
                ', json', ', json=', '= json', # Truncated API calls
                '(', '[', '{',  # Unclosed brackets at end
                'await ', 'return ', 'yield ',  # Incomplete statements
                'def ', 'class ', 'if ', 'elif ', 'else:', 'for ', 'while ',  # Incomplete blocks
                'import ', 'from ',  # Incomplete imports
            ]
            for ending in bad_endings:
                if content.endswith(ending) or content.endswith(ending.strip()):
                    print(f"[_extract_partial_files] ⚠️ Truncated Python file detected: {path} (ends with '{ending.strip()}')")
                    return True
        
        # Check for JS/JSX/TS/TSX files
        if path.endswith(('.js', '.jsx', '.ts', '.tsx')):
            open_parens = content.count('(') - content.count(')')
            open_brackets = content.count('[') - content.count(']')
            open_braces = content.count('{') - content.count('}')
            
            if open_parens > 0 or open_brackets > 0 or open_braces > 0:
                print(f"[_extract_partial_files] ⚠️ Truncated JS file detected: {path} (unclosed brackets)")
                return True
        
        return False
    
    # First, try to handle triple-quote syntax: """content"""
    # This is a common LLM error when generating JSON with code content
    triple_quote_pattern = r'"path"\s*:\s*"([^"]+)"[^}]*"content"\s*:\s*"""([\s\S]*?)"""'
    for match in re.finditer(triple_quote_pattern, raw, re.DOTALL):
        path = match.group(1)
        content = match.group(2)
        
        if path in INVALID_FILENAMES:
            continue
        if not ("/" in path or "\\" in path or "." in path):
            continue
        
        if content and content.strip():
            # IMPROVED: Validate content and attempt salvage if truncated
            if _is_truncated_code(path, content):
                print(f"[_extract_partial_files] ⚠️ Detected truncation in triple-quote: {path}")
                
                # Try to salvage complete functions (Python only)
                if path.endswith('.py'):
                    salvaged_content = _salvage_complete_functions(content)
                    if salvaged_content and len(salvaged_content) > 100:
                        print(f"[_extract_partial_files] ✅ Salvaged {len(salvaged_content)} bytes from triple-quoted content: {path}")
                        files.append({"path": path, "content": salvaged_content})
                        continue
                
                # If salvage failed, reject
                print(f"[_extract_partial_files] 🚨 REJECTING truncated file from triple-quote: {path}")
                continue
            
            print(f"[_extract_partial_files] ✅ Extracted {path} from triple-quoted content")
            files.append({"path": path, "content": content})
    
    if files:
        return files
    
    # Second, try standard escaped JSON pattern
    pattern = r'"path"\s*:\s*"([^"]+)"[^}]*"content"\s*:\s*"((?:[^"\\]|\\.)*)'
    
    for match in re.finditer(pattern, raw, re.DOTALL):
        path = match.group(1)
        content = match.group(2)
        
        # Skip invalid paths
        if path in INVALID_FILENAMES:
            continue
        if not ("/" in path or "\\" in path or "." in path):
            continue
        
        # Decode escapes
        try:
            content = bytes(content, "utf-8").decode("unicode_escape")
        except Exception:
            pass
        
        # CRITICAL: Skip files with empty content
        if not content or not content.strip():
            print(f"[_extract_partial_files] ⚠️ Skipping empty file: {path}")
            continue
        
        # IMPROVED: Check for truncation and try to salvage complete code
        if _is_truncated_code(path, content):
            print(f"[_extract_partial_files] ⚠️ Detected truncation in: {path}")
            
            # Try to salvage complete functions (Python only)
            if path.endswith('.py'):
                salvaged_content = _salvage_complete_functions(content)
                if salvaged_content and len(salvaged_content) > 100:
                    print(f"[_extract_partial_files] ✅ Salvaged {len(salvaged_content)} bytes from truncated file: {path}")
                    files.append({"path": path, "content": salvaged_content})
                    continue
            
            # If salvage failed, reject the file
            print(f"[_extract_partial_files] 🚨 REJECTING truncated file: {path}")
            continue
        
        files.append({"path": path, "content": content})

    
    if files:
        return files
    
    # Third, try to extract from markdown code blocks with file path comments
    # Pattern: ```python\n# path/to/file.py\ncontent...\n```
    md_pattern = r'```(?:python|javascript|jsx|typescript|tsx)?\s*\n#\s*([^\n]+\.(?:py|js|jsx|ts|tsx))\s*\n([\s\S]*?)```'
    for match in re.finditer(md_pattern, raw, re.DOTALL):
        path = match.group(1).strip()
        content = match.group(2).strip()
        
        if content and len(content) > 10:
            # CRITICAL: Validate content is not truncated
            if _is_truncated_code(path, content):
                print(f"[_extract_partial_files] 🚨 REJECTING truncated markdown file: {path}")
                continue
            
            print(f"[_extract_partial_files] ✅ Extracted {path} from markdown code block")
            files.append({"path": path, "content": content})
    
    return files


def parse_kenji(raw: str) -> Optional[TestReport]:
    """
    Specialized parser for Kenji (QA agent) outputs.
    Validates shape and returns a TestReport if valid.
    """
    if not raw or not isinstance(raw, str):
        return None

    try:
        repaired = parse_json(raw)
        if repaired and validate_qa_report_shape(repaired):
            print("[parse_kenji] ✅ Successfully parsed and validated QA report.")
            return cast(TestReport, repaired)
    except Exception:
        pass

    print("[parse_kenji] ⚠️ Unable to parse valid QA report shape from input.")
    return None

