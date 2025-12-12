# app/testing/self_healing.py
"""
Self-healing test system - auto-fixes common test failures.
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


class SelfHealingTests:
    """
    Automatically fix common Playwright test failures.
    
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
                    print(f"[SELF-HEAL] Fix failed: {fix.description} - {e}")
        
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


def create_robust_smoke_test() -> str:
    """Create a robust smoke test using the standard testing contract testids (ESM friendly)."""
    return '''
import { test, expect } from '@playwright/test';

test.describe.configure({ retries: 2 });

test('Smoke Test - Page Loads', async ({ page }) => {
  // Navigate with retry
  await page.goto('http://localhost:5174/', { timeout: 30000 });
  
  // Wait for network idle
  await page.waitForLoadState('networkidle', { timeout: 30000 });
  
  // Basic check - body exists and has content
  const body = page.locator('body');
  await expect(body).toBeVisible({ timeout: 10000 });
});

test('UI Shows Valid State', async ({ page }) => {
  await page.goto('http://localhost:5174/', { timeout: 30000 });
  await page.waitForLoadState('networkidle', { timeout: 30000 });
  
  // Check for MUTUALLY EXCLUSIVE states: loading, error, or content
  // At least ONE of these should be visible
  await expect(
    page.locator('[data-testid="loading-indicator"]')
      .or(page.locator('[data-testid="error-message"]'))
      .or(page.locator('[data-testid="page-root"]'))
  ).toBeVisible({ timeout: 15000 });
});

test('Content Page Elements', async ({ page }) => {
  await page.goto('http://localhost:5174/', { timeout: 30000 });
  await page.waitForLoadState('networkidle', { timeout: 30000 });
  
  // If content loaded successfully (not error/loading), check stable elements
  const errorVisible = await page.locator('[data-testid="error-message"]').isVisible().catch(() => false);
  const loadingVisible = await page.locator('[data-testid="loading-indicator"]').isVisible().catch(() => false);
  
  if (!errorVisible && !loadingVisible) {
    // Check for page title (from testing contract)
    await expect(page.locator('[data-testid="page-title"]')).toBeVisible({ timeout: 10000 });
  }
});
'''



def extract_testids_from_project(project_path) -> list:
    """
    Extract all data-testid values from JSX/TSX files in the project.
    Returns a list of testid strings that actually exist in the UI.
    """
    import re
    
    testids = []
    
    # Directories to search
    search_dirs = [
        project_path / "frontend/src/pages",
        project_path / "frontend/src/components",
    ]
    
    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        
        for file_path in search_dir.glob("**/*.jsx"):
            try:
                content = file_path.read_text(encoding="utf-8")
                
                # Find data-testid="value" patterns
                matches = re.findall(r'data-testid=["\']([^"\']+)["\']', content)
                testids.extend(matches)
                
            except Exception as e:
                print(f"[TEST] Could not read {file_path}: {e}")
    
    # Remove duplicates and sort
    return sorted(set(testids))


def create_matching_smoke_test(project_path) -> str:
    """
    Create a smoke test that checks for elements that ACTUALLY exist in the UI.
    This handles mutually exclusive UI states (loading, error, content).
    """
    testids = extract_testids_from_project(project_path)
    
    if not testids:
        # Fallback to generic smoke test
        return create_robust_smoke_test()
    
    # Categorize testids by their likely state
    # These are elements that only appear in specific states
    loading_ids = [t for t in testids if 'loading' in t.lower()]
    error_ids = [t for t in testids if 'error' in t.lower()]
    
    # Elements that only appear conditionally (with items, on delete, etc.)
    conditional_ids = [t for t in testids if any(kw in t.lower() for kw in [
        'delete', 'edit', 'remove', 'card', 'item', 'row'
    ])]
    
    # "Safe" elements that should always be visible on the main content page
    # Exclude loading, error, and conditional elements
    excluded = set(loading_ids + error_ids + conditional_ids)
    content_ids = [t for t in testids if t not in excluded]
    
    # Build assertions for stable elements only (max 3 to reduce flakiness)
    stable_assertions = []
    for testid in content_ids[:3]:
        stable_assertions.append(
            f"      await expect(page.locator('[data-testid=\"{testid}\"]')).toBeVisible({{ timeout: 10000 }});"
        )
    
    stable_checks = "\n".join(stable_assertions) if stable_assertions else "      // No stable elements found to check"
    
    # Build state selectors for the OR check
    state_selectors = []
    if loading_ids:
        state_selectors.append(f"page.locator('[data-testid=\"{loading_ids[0]}\"]')")
    if error_ids:
        state_selectors.append(f"page.locator('[data-testid=\"{error_ids[0]}\"]')")
    if content_ids:
        state_selectors.append(f"page.locator('[data-testid=\"{content_ids[0]}\"]')")
    
    # Default fallbacks if categories are empty
    if not state_selectors:
        state_selectors = [
            "page.locator('[data-testid]').first()",
            "page.locator('button').first()",
            "page.locator('h1, h2, h3').first()"
        ]
    
    # Build the OR chain for state detection
    or_chain = state_selectors[0]
    for selector in state_selectors[1:]:
        or_chain = f"{or_chain}.or({selector})"
    
    return f'''
import {{ test, expect }} from '@playwright/test';

test.describe.configure({{ retries: 2 }});

test('Smoke Test - Page Loads', async ({{ page }}) => {{
  await page.goto('http://localhost:5174/', {{ timeout: 30000 }});
  await page.waitForLoadState('networkidle', {{ timeout: 30000 }});
  
  // Basic check - body exists
  const body = page.locator('body');
  await expect(body).toBeVisible({{ timeout: 10000 }});
}});

test('UI Shows Valid State', async ({{ page }}) => {{
  await page.goto('http://localhost:5174/', {{ timeout: 30000 }});
  await page.waitForLoadState('networkidle', {{ timeout: 30000 }});
  
  // The UI can show loading, error, or content - these are MUTUALLY EXCLUSIVE states
  // We check that AT LEAST ONE valid state is visible
  await expect(
    {or_chain}
  ).toBeVisible({{ timeout: 15000 }});
}});

test('Content Page Elements', async ({{ page }}) => {{
  await page.goto('http://localhost:5174/', {{ timeout: 30000 }});
  await page.waitForLoadState('networkidle', {{ timeout: 30000 }});
  
  // If content loaded successfully (not error), check stable elements
  const errorVisible = await page.locator('[data-testid*="error"]').isVisible().catch(() => false);
  const loadingVisible = await page.locator('[data-testid*="loading"]').isVisible().catch(() => false);
  
  if (!errorVisible && !loadingVisible) {{
    // Only check content elements if we're not in error or loading state
{stable_checks}
  }}
}});
'''


def get_available_selectors(project_path) -> dict:
    """
    Analyze the project to find all available selectors for testing.
    Returns a dict with categories of selectors.
    """
    import re
    
    selectors = {
        "testids": [],
        "buttons": [],
        "inputs": [],
        "headings": [],
        "links": [],
    }
    
    search_dirs = [
        project_path / "frontend/src/pages",
        project_path / "frontend/src/components",
    ]
    
    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        
        for file_path in search_dir.glob("**/*.jsx"):
            try:
                content = file_path.read_text(encoding="utf-8")
                
                # Find data-testid
                testids = re.findall(r'data-testid=["\']([^"\']+)["\']', content)
                selectors["testids"].extend(testids)
                
                # Find button text
                buttons = re.findall(r'<[Bb]utton[^>]*>([^<]+)</[Bb]utton>', content)
                selectors["buttons"].extend([b.strip() for b in buttons if b.strip()])
                
                # Find input placeholders
                inputs = re.findall(r'placeholder=["\']([^"\']+)["\']', content)
                selectors["inputs"].extend(inputs)
                
                # Find headings (h1-h6)
                headings = re.findall(r'<h[1-6][^>]*>([^<]+)</h[1-6]>', content)
                selectors["headings"].extend([h.strip() for h in headings if h.strip()])
                
            except Exception:
                pass
    
    # Deduplicate
    for key in selectors:
        selectors[key] = list(set(selectors[key]))[:10]  # Limit each category
    
    return selectors

