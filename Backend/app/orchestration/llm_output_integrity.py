# app/workflow/engine_v2/llm_output_integrity.py
"""
LLM Output Structural Integrity Validator — Python 3.12

Ensures model output is complete, not truncated, and structurally valid
BEFORE passing to syntax validators or compiler layer.
"""
import re
from typing import Optional


class LLMOutputIntegrity:
    """
    Ensures model output is complete, not truncated, and structurally valid
    BEFORE passing to syntax validators or compiler layer.
    """
    
    BRACKET_PAIRS = {
        "{": "}",
        "[": "]",
        "(": ")"
    }

    def __init__(self):
        pass

    # ---------------------------------------------------------
    # Entry point: validate raw text
    # ---------------------------------------------------------
    def validate(self, text: str) -> bool:
        if not text or len(text.strip()) == 0:
            return False

        if self._looks_truncated(text):
            return False

        if not self._balanced_brackets(text):
            return False

        if self._has_unterminated_string(text):
            return False

        if self._has_incomplete_class_or_function(text):
            return False

        return True

    # ---------------------------------------------------------
    # Truncation heuristics
    # ---------------------------------------------------------
    def _looks_truncated(self, text: str) -> bool:
        truncated_markers = [
            "...",
            "```",  # if LLM accidentally tries to open a fenced block
            "<<EOF",
            "<<END",
        ]
        for m in truncated_markers:
            if text.rstrip().endswith(m):
                return True
        return False

    # ---------------------------------------------------------
    # Bracket balance
    # ---------------------------------------------------------
    def _balanced_brackets(self, text: str) -> bool:
        stack = []
        in_string = False
        string_char = None
        prev_char = None
        
        for ch in text:
            # Handle string literals
            if ch in ('"', "'") and prev_char != '\\':
                if not in_string:
                    in_string = True
                    string_char = ch
                elif ch == string_char:
                    in_string = False
                    string_char = None
            
            # Only count brackets outside strings
            if not in_string:
                if ch in self.BRACKET_PAIRS:
                    stack.append(ch)
                elif ch in self.BRACKET_PAIRS.values():
                    if not stack:
                        return False
                    opening = stack.pop()
                    if self.BRACKET_PAIRS[opening] != ch:
                        return False
            
            prev_char = ch
        
        return len(stack) == 0

    # ---------------------------------------------------------
    # Unterminated strings
    # ---------------------------------------------------------
    def _has_unterminated_string(self, text: str) -> bool:
        # Count triple quotes separately
        triple_double = text.count('"""')
        triple_single = text.count("'''")
        
        if triple_double % 2 != 0:
            return True
        if triple_single % 2 != 0:
            return True
        
        # For single quotes, we need smarter counting
        # (escaped quotes, quotes in strings, etc.)
        # Simple heuristic: check last line for unclosed quotes
        lines = text.strip().split('\n')
        if lines:
            last_line = lines[-1]
            # Check if last line has odd number of unescaped quotes
            double_count = len(re.findall(r'(?<!\\)"', last_line))
            single_count = len(re.findall(r"(?<!\\)'", last_line))
            
            # If line ends with an open string, it's truncated
            if double_count % 2 != 0 or single_count % 2 != 0:
                return True
        
        return False

    # ---------------------------------------------------------
    # Empty function / class blocks
    # ---------------------------------------------------------
    def _has_incomplete_class_or_function(self, text: str) -> bool:
        patterns = [
            r"def\s+\w+\([^)]*\)\s*:\s*$",   # Function with no body
            r"class\s+\w+\s*:\s*$",           # Class with no body
            r"async\s+def\s+\w+\([^)]*\)\s*:\s*$",  # Async function with no body
        ]
        for p in patterns:
            if re.search(p, text, re.MULTILINE):
                return True
        return False
    
    # ---------------------------------------------------------
    # Additional validation methods
    # ---------------------------------------------------------
    def get_issues(self, text: str) -> list:
        """Get list of all issues found."""
        issues = []
        
        if not text or len(text.strip()) == 0:
            issues.append("Empty or whitespace-only output")
            return issues
        
        if self._looks_truncated(text):
            issues.append("Output appears truncated (ends with ..., ```, <<EOF, or <<END)")
        
        if not self._balanced_brackets(text):
            issues.append("Unbalanced brackets/braces/parentheses")
        
        if self._has_unterminated_string(text):
            issues.append("Unterminated string literal detected")
        
        if self._has_incomplete_class_or_function(text):
            issues.append("Incomplete function or class definition (empty body)")
        
        return issues
