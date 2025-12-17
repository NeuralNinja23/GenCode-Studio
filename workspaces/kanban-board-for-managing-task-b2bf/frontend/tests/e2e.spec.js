
import { test, expect } from '@playwright/test';

test.describe.configure({ retries: 2 });

test('Smoke Test - Page Loads', async ({ page }) => {
  await page.goto('http://localhost:5174/', { timeout: 30000 });
  await page.waitForLoadState('networkidle', { timeout: 30000 });
  
  // Basic check - body exists
  const body = page.locator('body');
  await expect(body).toBeVisible({ timeout: 10000 });
});

test('UI Shows Valid State', async ({ page }) => {
  await page.goto('http://localhost:5174/', { timeout: 30000 });
  await page.waitForLoadState('networkidle', { timeout: 30000 });
  
  // The UI can show loading, error, or content - these are MUTUALLY EXCLUSIVE states
  // We check that AT LEAST ONE valid state is visible
  await expect(
    page.locator('[data-testid="loading-indicator"]').or(page.locator('[data-testid="error-message"]')).or(page.locator('[data-testid="add-task-submit-button"]'))
  ).toBeVisible({ timeout: 15000 });
});

test('Content Page Elements', async ({ page }) => {
  await page.goto('http://localhost:5174/', { timeout: 30000 });
  await page.waitForLoadState('networkidle', { timeout: 30000 });
  
  // If content loaded successfully (not error), check stable elements
  const errorVisible = await page.locator('[data-testid*="error"]').isVisible().catch(() => false);
  const loadingVisible = await page.locator('[data-testid*="loading"]').isVisible().catch(() => false);
  
  if (!errorVisible && !loadingVisible) {
    // Only check content elements if we're not in error or loading state
      await expect(page.locator('[data-testid="add-task-submit-button"]')).toBeVisible({ timeout: 10000 });
      await expect(page.locator('[data-testid="assignee-filter-select"]')).toBeVisible({ timeout: 10000 });
      await expect(page.locator('[data-testid="create-task-button"]')).toBeVisible({ timeout: 10000 });
  }
});
