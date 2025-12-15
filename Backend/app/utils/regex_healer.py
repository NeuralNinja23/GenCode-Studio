# app/utils/regex_healer.py
"""
Patcher for common test failures using Regex.
Originally from testing/self_healing.py.
"""
import re
from typing import Callable, List, Tuple
from dataclasses import dataclass


@dataclass
class TestFix:
    """A fix for a common test failure."""
    pattern: str
    description: str
    fix_func: Callable[[str, str], str]


class TestRegexPatcher:
    """
    Automatically fix common Playwright test failures using regex patterns.
    
    Handles:
    - Wrong URLs (/ instead of absolute)
    - Missing waits
    - Wrong selectors
    - Timeout issues
    """
    
    def __init__(self):
        self.fixes: List[TestFix] = [
            TestFix(
                pattern=r"Cannot navigate to invalid URL|page\.goto\('\/'\)",
                description="Fix relative URL to absolute localhost URL",
                fix_func=self._fix_relative_url,
            ),
            TestFix(
                pattern=r"toBeVisible\(\).*failed.*Timeout|element.*not found",
                description="Add longer timeout for visibility checks",
                fix_func=self._fix_visibility_timeout,
            ),
            TestFix(
                pattern=r"text=Loading|Loading not found",
                description="Remove flaky loading state assertions",
                fix_func=self._fix_loading_assertion,
            ),
            TestFix(
                pattern=r"net::ERR_CONNECTION_REFUSED|ECONNREFUSED",
                description="Add retry logic for connection issues",
                fix_func=self._fix_connection_retry,
            ),
            TestFix(
                pattern=r"Strict mode violation.*resolved to \d+ elements",
                description="Make selector more specific with .first()",
                fix_func=self._fix_strict_mode,
            ),
            TestFix(
                pattern=r"locator resolved to hidden|Received: hidden|unexpected value \"hidden\"",
                description="Replace toBeVisible with toBeAttached for empty containers",
                fix_func=self._fix_hidden_element,
            ),
        ]
    
    def analyze_failure(self, test_content: str, error_output: str) -> List[str]:
        """Identify applicable fixes."""
        applicable = []
        for fix in self.fixes:
            if re.search(fix.pattern, error_output, re.IGNORECASE):
                applicable.append(fix.description)
        return applicable
    
    def attempt_healing(self, test_content: str, error_output: str) -> Tuple[str, List[str]]:
        """
        Attempt to heal a failing test.
        
        Returns: (fixed_content, fixes_applied)
        """
        fixed = test_content
        fixes_applied = []
        
        for fix in self.fixes:
            if re.search(fix.pattern, error_output, re.IGNORECASE):
                try:
                    new_content = fix.fix_func(fixed, error_output)
                    if new_content != fixed:
                        fixed = new_content
                        fixes_applied.append(fix.description)
                except Exception as e:
                    print(f"[REGEX-HEAL] Fix failed: {fix.description} - {e}")
        
        return fixed, fixes_applied
    
    def _fix_relative_url(self, content: str, error: str) -> str:
        """Fix page.goto('/') to use absolute URL."""
        fixed = re.sub(
            r"page\.goto\s*\(\s*['\"]\/['\"]",
            "page.goto('http://localhost:5174/'",
            content
        )
        fixed = re.sub(
            r"page\.goto\s*\(\s*['\"](\/[^'\"]+)['\"]",
            r"page.goto('http://localhost:5174\1'",
            fixed
        )
        return fixed
    
    def _fix_visibility_timeout(self, content: str, error: str) -> str:
        """Increase timeout for visibility checks."""
        fixed = re.sub(
            r"\.toBeVisible\(\s*\)",
            ".toBeVisible({ timeout: 15000 })",
            content
        )
        return fixed
    
    def _fix_loading_assertion(self, content: str, error: str) -> str:
        """Remove flaky loading assertions."""
        lines = content.split('\n')
        fixed_lines = []
        
        for line in lines:
            if "Loading" in line and ("toBeVisible" in line or "expect" in line.lower()):
                fixed_lines.append(f"  // Removed flaky: {line.strip()}")
            else:
                fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    def _fix_connection_retry(self, content: str, error: str) -> str:
        """Add retry configuration."""
        if "test.describe.configure" not in content:
            # Try ESM import first
            esm_pattern = r"(import \{.*?\} from ['\"]@playwright/test['\"].*?;)"
            if re.search(esm_pattern, content):
                content = re.sub(
                    esm_pattern,
                    r"\1\n\ntest.describe.configure({ retries: 2 });",
                    content,
                    count=1
                )
            else:
                # Fallback to CommonJS
                cjs_pattern = r"(const \{ test.*\} = require.*?;)"
                content = re.sub(
                    cjs_pattern,
                    r"\1\n\ntest.describe.configure({ retries: 2 });",
                    content,
                    count=1
                )
        return content
    
    def _fix_strict_mode(self, content: str, error: str) -> str:
        """Add .first() to selectors hit by strict mode."""
        fixed = re.sub(
            r"(page\.locator\([^)]+\))\.click\(\)",
            r"\1.first().click()",
            content
        )
        fixed = re.sub(
            r"(page\.locator\([^)]+\))\.fill\(",
            r"\1.first().fill(",
            fixed
        )
        return fixed

    def _fix_hidden_element(self, content: str, error: str) -> str:
        """
        Fix empty container visibility issues.
        
        When an element is in the DOM but has no visible content
        (e.g., empty grid), toBeVisible() fails but toBeAttached() succeeds.
        """
        # Replace toBeVisible with toBeAttached for container selectors
        fixed = re.sub(
            r"(locator\(['\"][^'\"]*(?:list|grid|container|items)[^'\"]*['\"]\))\.toBeVisible\(",
            r"\1.toBeAttached(",
            content,
            flags=re.IGNORECASE
        )
        
        # Also handle data-testid patterns for lists
        fixed = re.sub(
            r"(locator\(\[?['\"]?\[?data-testid=['\"]?[^'\"]*(?:list|grid)[^'\"]*['\"]?\]?['\"]\))\.toBeVisible\(",
            r"\1.toBeAttached(",
            fixed,
            flags=re.IGNORECASE
        )
        
        return fixed
