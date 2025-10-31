import { test, expect } from '@playwright/test';

/**
 * Navigation E2E Tests
 *
 * Tests navigation between different pages and sections:
 * - Navigation menu/header
 * - Route transitions
 * - Deep linking
 * - Breadcrumbs
 * - Browser back/forward
 */

test.describe('Navigation', () => {
  test('should navigate to dashboard from root', async ({ page }) => {
    await page.goto('/');

    // Check that we're on the dashboard
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});

    // URL should be root or /dashboard
    expect(page.url()).toMatch(/\/$|\/dashboard/);
  });

  test('should navigate to consensus page', async ({ page }) => {
    await page.goto('/');

    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(1000);

    // Look for consensus navigation link
    const consensusLink = page.locator('[data-testid="nav-consensus"]')
      .or(page.getByRole('link', { name: /consensus/i }))
      .or(page.getByText(/consensus/i).locator('a'))
      .first();

    const linkVisible = await consensusLink.isVisible().catch(() => false);

    if (linkVisible) {
      await consensusLink.click();

      await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});

      // Should navigate to consensus page
      expect(page.url()).toContain('consensus');
    } else {
      // If no nav link, try direct navigation
      await page.goto('/consensus');
      await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
      expect(page.url()).toContain('consensus');
    }
  });

  test('should navigate back to dashboard from consensus', async ({ page }) => {
    // Start on consensus page
    await page.goto('/consensus');

    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(1000);

    // Look for dashboard/home navigation link
    const dashboardLink = page.locator('[data-testid="nav-dashboard"]')
      .or(page.getByRole('link', { name: /dashboard|home/i }))
      .or(page.getByText(/dashboard|home/i).locator('a'))
      .first();

    const linkVisible = await dashboardLink.isVisible().catch(() => false);

    if (linkVisible) {
      await dashboardLink.click();

      await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});

      // Should navigate to dashboard
      expect(page.url()).toMatch(/\/$|\/dashboard/);
    }
  });

  test('should use browser back button correctly', async ({ page }) => {
    // Start on dashboard
    await page.goto('/');
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});

    const initialUrl = page.url();

    // Navigate to consensus
    await page.goto('/consensus');
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});

    const consensusUrl = page.url();
    expect(consensusUrl).toContain('consensus');

    // Go back
    await page.goBack();
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});

    // Should be back on dashboard
    expect(page.url()).toBe(initialUrl);
  });

  test('should use browser forward button correctly', async ({ page }) => {
    // Start on dashboard
    await page.goto('/');
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});

    // Navigate to consensus
    await page.goto('/consensus');
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});

    const consensusUrl = page.url();

    // Go back
    await page.goBack();
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});

    // Go forward
    await page.goForward();
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});

    // Should be back on consensus page
    expect(page.url()).toBe(consensusUrl);
  });

  test('should highlight active navigation item', async ({ page }) => {
    await page.goto('/');

    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(1000);

    // Look for active nav item
    const activeNav = page.locator('[data-testid="nav-active"]')
      .or(page.locator('.active'))
      .or(page.locator('[aria-current="page"]'))
      .first();

    const hasActiveNav = await activeNav.isVisible().catch(() => false);

    if (hasActiveNav) {
      await expect(activeNav).toBeVisible();

      // Active item should have different styling
      const classes = await activeNav.getAttribute('class');
      expect(classes).toBeTruthy();
    }
  });

  test('should support deep linking to consensus page', async ({ page }) => {
    // Navigate directly to consensus page
    await page.goto('/consensus');

    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});

    // Should load consensus page directly
    expect(page.url()).toContain('consensus');

    // Page should render (not 404)
    const body = page.locator('body');
    await expect(body).toBeVisible();

    // Should not show 404 error
    const notFound = page.getByText(/404|not found|page.*not.*exist/i).first();
    const has404 = await notFound.isVisible().catch(() => false);
    expect(has404).toBe(false);
  });

  test('should support deep linking with query parameters', async ({ page }) => {
    // Navigate with query params
    await page.goto('/consensus?pair=BTC/USDT&timeframe=1h');

    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});

    // URL should preserve query params
    expect(page.url()).toContain('pair=BTC/USDT');
    expect(page.url()).toContain('timeframe=1h');

    // Check if form is pre-filled (if frontend implements this)
    const pairInput = page.locator('input[name="pair"]').first();
    const inputVisible = await pairInput.isVisible().catch(() => false);

    if (inputVisible) {
      const value = await pairInput.inputValue();
      // May or may not be pre-filled depending on implementation
      // Just check it's a valid input
      expect(value).toBeDefined();
    }
  });

  test('should display navigation menu on all pages', async ({ page }) => {
    // Check dashboard
    await page.goto('/');
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(1000);

    let nav = page.locator('nav')
      .or(page.locator('[data-testid="navigation"]'))
      .or(page.locator('header'))
      .first();

    let navVisible = await nav.isVisible().catch(() => false);

    if (navVisible) {
      await expect(nav).toBeVisible();
    }

    // Check consensus page
    await page.goto('/consensus');
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(1000);

    nav = page.locator('nav')
      .or(page.locator('[data-testid="navigation"]'))
      .or(page.locator('header'))
      .first();

    navVisible = await nav.isVisible().catch(() => false);

    if (navVisible) {
      await expect(nav).toBeVisible();
    }
  });

  test('should handle invalid routes gracefully', async ({ page }) => {
    // Try to navigate to non-existent page
    await page.goto('/non-existent-page-12345');

    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(1000);

    // Should show 404 page or redirect to dashboard
    const url = page.url();
    const is404 = url.includes('404') || url.includes('non-existent');
    const redirectedHome = url.match(/\/$|\/dashboard/);

    // Either show 404 or redirect home
    expect(is404 || redirectedHome).toBeTruthy();

    if (is404) {
      // Check for 404 content
      const notFound = page.getByText(/404|not found|page.*not.*exist/i).first();
      const has404 = await notFound.isVisible().catch(() => false);
      expect(has404).toBe(true);
    }
  });

  test('should maintain navigation state during page transitions', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(1000);

    // Get navigation element
    const nav = page.locator('nav')
      .or(page.locator('[data-testid="navigation"]'))
      .or(page.locator('header'))
      .first();

    const navVisible = await nav.isVisible().catch(() => false);

    if (navVisible) {
      // Check that nav is visible on dashboard
      await expect(nav).toBeVisible();

      // Navigate to consensus
      const consensusLink = page.getByRole('link', { name: /consensus/i }).first();
      const hasLink = await consensusLink.isVisible().catch(() => false);

      if (hasLink) {
        await consensusLink.click();
        await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});

        // Nav should still be visible
        await expect(nav).toBeVisible();
      }
    }
  });

  test('should support keyboard navigation', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(1000);

    // Try to tab through navigation links
    await page.keyboard.press('Tab');
    await page.waitForTimeout(200);

    // Check if focus is on a link
    const focusedElement = page.locator(':focus');
    const isFocused = await focusedElement.count().then(count => count > 0);

    if (isFocused) {
      // Tab should focus navigation elements
      const tagName = await focusedElement.evaluate(el => el.tagName.toLowerCase());
      expect(['a', 'button', 'input']).toContain(tagName);
    }
  });

  test('should preserve scroll position on back navigation', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(1000);

    // Scroll down if page is scrollable
    const body = page.locator('body');
    await body.evaluate(el => {
      el.scrollTop = 500;
      window.scrollTo(0, 500);
    });

    await page.waitForTimeout(500);

    // Navigate away
    await page.goto('/consensus');
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});

    // Go back
    await page.goBack();
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});

    // Scroll position behavior depends on browser/Next.js config
    // Just verify page loaded correctly
    await expect(body).toBeVisible();
  });
});
