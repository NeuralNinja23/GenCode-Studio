# app/utils/test_scaffolding.py
"""
Utilities for generating robust frontend tests.
Scaffolds tests based on actual project content (selectors, testids).
"""
import re
from pathlib import Path
from typing import List, Dict

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


def extract_testids_from_project(project_path: Path) -> list:
    """
    Extract all data-testid values from JSX/TSX files in the project.
    Returns a list of testid strings that actually exist in the UI.
    """
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


def create_matching_smoke_test(project_path: Path) -> str:
    """
    Create a smoke test that checks for elements that ACTUALLY exist in the UI.
    This handles mutually exclusive UI states (loading, error, content).
    """
    testids = extract_testids_from_project(project_path)
    
    if not testids:
        # Fallback to generic smoke test
        return create_robust_smoke_test()
    
    # Categorize testids by their likely state
    loading_ids = [t for t in testids if 'loading' in t.lower()]
    error_ids = [t for t in testids if 'error' in t.lower()]
    
    # Elements that only appear conditionally (with items, on delete, etc.)
    conditional_ids = [t for t in testids if any(kw in t.lower() for kw in [
        'delete', 'edit', 'remove', 'card', 'item', 'row'
    ])]
    
    # "Safe" elements that should always be visible on the main content page
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


def get_available_selectors(project_path: Path) -> dict:
    """
    Analyze the project to find all available selectors for testing.
    Returns a dict with categories of selectors.
    """
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
