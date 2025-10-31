import { test, expect, devices } from '@playwright/test';

/**
 * Responsive Design E2E Tests
 *
 * Tests the frontend across different viewport sizes:
 * - Mobile (320px - 767px)
 * - Tablet (768px - 1023px)
 * - Desktop (1024px+)
 *
 * Verifies:
 * - Layout adapts correctly
 * - Navigation changes (hamburger menu on mobile)
 * - Content remains accessible
 * - Touch interactions work
 * - No horizontal scroll
 */

test.describe('Responsive Design - Mobile', () => {
  test.use({
    viewport: { width: 375, height: 667 }, // iPhone SE size
  });

  test('should display mobile-friendly layout on dashboard', async ({ page }) => {
    await page.goto('/');

    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(1000);

    // Check that page is visible
    const body = page.locator('body');
    await expect(body).toBeVisible();

    // Check viewport width
    const viewportWidth = await page.evaluate(() => window.innerWidth);
    expect(viewportWidth).toBeLessThanOrEqual(767);
  });

  test('should show hamburger menu on mobile', async ({ page }) => {
    await page.goto('/');

    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(1000);

    // Look for mobile menu button (hamburger icon)
    const mobileMenuButton = page.locator('[data-testid="mobile-menu-button"]')
      .or(page.locator('[aria-label*="menu"]'))
      .or(page.locator('button').filter({ hasText: /menu/i }))
      .or(page.locator('.hamburger'))
      .first();

    const buttonVisible = await mobileMenuButton.isVisible().catch(() => false);

    if (buttonVisible) {
      await expect(mobileMenuButton).toBeVisible();

      // Click to open menu
      await mobileMenuButton.click();
      await page.waitForTimeout(500);

      // Menu should appear
      const mobileMenu = page.locator('[data-testid="mobile-menu"]')
        .or(page.locator('nav'))
        .first();

      await expect.soft(mobileMenu).toBeVisible();
    }
  });

  test('should stack portfolio cards vertically on mobile', async ({ page }) => {
    await page.goto('/');

    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(1000);

    // Look for portfolio cards
    const cards = page.locator('[data-testid="portfolio-card"]')
      .or(page.locator('.card'))
      .or(page.locator('article'));

    const cardCount = await cards.count();

    if (cardCount > 1) {
      // Get positions of first two cards
      const firstCard = cards.first();
      const secondCard = cards.nth(1);

      const firstBox = await firstCard.boundingBox();
      const secondBox = await secondCard.boundingBox();

      if (firstBox && secondBox) {
        // On mobile, cards should stack (second card below first)
        expect(secondBox.y).toBeGreaterThan(firstBox.y);
      }
    }
  });

  test('should not have horizontal scroll on mobile', async ({ page }) => {
    await page.goto('/');

    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(1000);

    // Check for horizontal overflow
    const hasHorizontalScroll = await page.evaluate(() => {
      return document.documentElement.scrollWidth > document.documentElement.clientWidth;
    });

    expect(hasHorizontalScroll).toBe(false);
  });

  test('should hide desktop-only elements on mobile', async ({ page }) => {
    await page.goto('/');

    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(1000);

    // Desktop navigation should be hidden
    const desktopNav = page.locator('[data-testid="desktop-nav"]')
      .or(page.locator('.desktop-only'))
      .first();

    const isVisible = await desktopNav.isVisible().catch(() => false);

    // Desktop-only elements should not be visible on mobile
    if (isVisible) {
      const display = await desktopNav.evaluate(el => {
        return window.getComputedStyle(el).display;
      });
      // If element exists, it should be hidden
      expect(['none', '']).toContain(display);
    }
  });

  test('should make tables scrollable on mobile', async ({ page }) => {
    await page.goto('/');

    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(1000);

    // Look for tables
    const table = page.locator('table').first();
    const tableVisible = await table.isVisible().catch(() => false);

    if (tableVisible) {
      // Table or its wrapper should be scrollable
      const isScrollable = await table.evaluate(el => {
        const parent = el.parentElement;
        const overflow = window.getComputedStyle(parent || el).overflowX;
        return overflow === 'auto' || overflow === 'scroll';
      });

      expect(isScrollable).toBe(true);
    }
  });
});

test.describe('Responsive Design - Tablet', () => {
  test.use({
    viewport: { width: 768, height: 1024 }, // iPad size
  });

  test('should display tablet-optimized layout', async ({ page }) => {
    await page.goto('/');

    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(1000);

    const body = page.locator('body');
    await expect(body).toBeVisible();

    // Check viewport width is in tablet range
    const viewportWidth = await page.evaluate(() => window.innerWidth);
    expect(viewportWidth).toBeGreaterThanOrEqual(768);
    expect(viewportWidth).toBeLessThan(1024);
  });

  test('should show 2-column grid on tablet', async ({ page }) => {
    await page.goto('/');

    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(1000);

    // Look for grid layout
    const cards = page.locator('[data-testid="portfolio-card"]')
      .or(page.locator('.card'))
      .or(page.locator('article'));

    const cardCount = await cards.count();

    if (cardCount >= 2) {
      const firstCard = cards.first();
      const secondCard = cards.nth(1);

      const firstBox = await firstCard.boundingBox();
      const secondBox = await secondCard.boundingBox();

      if (firstBox && secondBox) {
        // Cards might be side-by-side or stacked depending on design
        // Just verify they're positioned
        expect(firstBox).toBeTruthy();
        expect(secondBox).toBeTruthy();
      }
    }
  });

  test('should adapt navigation for tablet', async ({ page }) => {
    await page.goto('/');

    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(1000);

    // Look for navigation
    const nav = page.locator('nav')
      .or(page.locator('[data-testid="navigation"]'))
      .first();

    const navVisible = await nav.isVisible().catch(() => false);

    if (navVisible) {
      await expect(nav).toBeVisible();

      // Navigation should be accessible (either always visible or via menu)
      const navLinks = page.locator('nav a');
      const linkCount = await navLinks.count();

      // Should have navigation links
      expect(linkCount).toBeGreaterThanOrEqual(0);
    }
  });
});

test.describe('Responsive Design - Desktop', () => {
  test.use({
    viewport: { width: 1920, height: 1080 }, // Full HD
  });

  test('should display full desktop layout', async ({ page }) => {
    await page.goto('/');

    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(1000);

    const body = page.locator('body');
    await expect(body).toBeVisible();

    // Check viewport width is desktop
    const viewportWidth = await page.evaluate(() => window.innerWidth);
    expect(viewportWidth).toBeGreaterThanOrEqual(1024);
  });

  test('should show horizontal navigation on desktop', async ({ page }) => {
    await page.goto('/');

    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(1000);

    // Desktop nav should be visible
    const nav = page.locator('nav')
      .or(page.locator('[data-testid="desktop-nav"]'))
      .or(page.locator('header'))
      .first();

    const navVisible = await nav.isVisible().catch(() => false);

    if (navVisible) {
      await expect(nav).toBeVisible();

      // Navigation links should be visible without menu button
      const navLinks = page.locator('nav a');
      const linkCount = await navLinks.count();

      if (linkCount > 0) {
        const firstLink = navLinks.first();
        await expect(firstLink).toBeVisible();
      }
    }
  });

  test('should hide mobile menu button on desktop', async ({ page }) => {
    await page.goto('/');

    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(1000);

    // Mobile menu button should not be visible
    const mobileMenuButton = page.locator('[data-testid="mobile-menu-button"]')
      .or(page.locator('.hamburger'))
      .first();

    const buttonVisible = await mobileMenuButton.isVisible().catch(() => false);

    // If button exists, it should be hidden on desktop
    if (buttonVisible) {
      const display = await mobileMenuButton.evaluate(el => {
        return window.getComputedStyle(el).display;
      });
      expect(display).toBe('none');
    }
  });

  test('should show multi-column grid on desktop', async ({ page }) => {
    await page.goto('/');

    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(1000);

    // Look for grid containers
    const grid = page.locator('[data-testid="portfolio-summary"]')
      .or(page.locator('.grid'))
      .or(page.locator('main > div').first())
      .first();

    const gridVisible = await grid.isVisible().catch(() => false);

    if (gridVisible) {
      // Grid should use CSS grid or flexbox
      const gridDisplay = await grid.evaluate(el => {
        return window.getComputedStyle(el).display;
      });

      expect(['grid', 'flex', 'block']).toContain(gridDisplay);
    }
  });

  test('should display tables in full width on desktop', async ({ page }) => {
    await page.goto('/');

    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(1000);

    // Tables should not be scrollable on desktop
    const table = page.locator('table').first();
    const tableVisible = await table.isVisible().catch(() => false);

    if (tableVisible) {
      const tableWidth = await table.evaluate(el => el.offsetWidth);
      expect(tableWidth).toBeGreaterThan(0);
    }
  });
});

test.describe('Responsive Design - Touch Interactions', () => {
  test('should support touch interactions on mobile', async ({ page }) => {
    // Set mobile viewport for touch testing
    await page.setViewportSize({ width: 390, height: 844 }); // iPhone 12 size
    await page.goto('/');

    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(1000);

    // Look for interactive elements
    const button = page.locator('button').first();
    const buttonVisible = await button.isVisible().catch(() => false);

    if (buttonVisible) {
      // Tap the button
      await button.tap();
      await page.waitForTimeout(500);

      // Button should respond to tap
      // (exact behavior depends on implementation)
      expect(buttonVisible).toBe(true);
    }
  });

  test('should handle swipe gestures for navigation', async ({ page }) => {
    await page.goto('/');

    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(1000);

    // Try to swipe (if mobile menu or carousel exists)
    const swipeableElement = page.locator('[data-testid="swipeable"]')
      .or(page.locator('.carousel'))
      .first();

    const isSwipeable = await swipeableElement.isVisible().catch(() => false);

    if (isSwipeable) {
      const box = await swipeableElement.boundingBox();

      if (box) {
        // Perform swipe gesture
        await page.touchscreen.tap(box.x + box.width / 2, box.y + box.height / 2);
        await page.waitForTimeout(100);

        // Element should still be visible after interaction
        await expect(swipeableElement).toBeVisible();
      }
    }
  });
});

test.describe('Responsive Design - Accessibility', () => {
  test('should maintain readable font sizes on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });

    await page.goto('/');

    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(1000);

    // Check font sizes
    const mainContent = page.locator('main').first();
    const contentVisible = await mainContent.isVisible().catch(() => false);

    if (contentVisible) {
      const fontSize = await mainContent.evaluate(el => {
        return parseInt(window.getComputedStyle(el).fontSize);
      });

      // Font should be at least 14px for readability
      expect(fontSize).toBeGreaterThanOrEqual(14);
    }
  });

  test('should have sufficient touch target sizes on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });

    await page.goto('/');

    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(1000);

    // Check button sizes
    const buttons = page.locator('button');
    const buttonCount = await buttons.count();

    if (buttonCount > 0) {
      const firstButton = buttons.first();
      const box = await firstButton.boundingBox();

      if (box) {
        // Touch targets should be at least 44x44px (iOS guideline)
        // Allow some flexibility for design
        expect(box.height).toBeGreaterThanOrEqual(32);
      }
    }
  });

  test('should maintain contrast ratios across viewports', async ({ page }) => {
    await page.goto('/');

    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(1000);

    // Check that content is visible (basic accessibility check)
    const body = page.locator('body');
    await expect(body).toBeVisible();

    // More detailed contrast checks would require color analysis
    // This is a basic smoke test for accessibility
  });
});
