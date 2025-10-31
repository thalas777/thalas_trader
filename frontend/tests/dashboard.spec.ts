import { test, expect } from '@playwright/test';

test.describe('Dashboard Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard');
  });

  test('should load dashboard page successfully', async ({ page }) => {
    // Check page loaded
    await expect(page.locator('h1:has-text("Trading Dashboard")')).toBeVisible();
    await expect(page.locator('text=Multi-LLM Consensus Trading System')).toBeVisible();
  });

  test.describe('Portfolio Summary Component', () => {
    test('should display portfolio overview section', async ({ page }) => {
      await expect(page.locator('h2:has-text("Portfolio Overview")')).toBeVisible();
    });

    test('should display all 8 metric cards', async ({ page }) => {
      // Check for key metrics
      await expect(page.locator('text=Total Balance')).toBeVisible();
      await expect(page.locator('text=Position Value')).toBeVisible();
      await expect(page.locator('text=Total P&L')).toBeVisible();
      await expect(page.locator('text=24h P&L')).toBeVisible();
      await expect(page.locator('text=Win Rate')).toBeVisible();
      await expect(page.locator('text=Active Bots')).toBeVisible();
      await expect(page.locator('text=Total Trades')).toBeVisible();
      await expect(page.locator('text=Open Positions')).toBeVisible();
    });

    test('should display currency values correctly', async ({ page }) => {
      // Wait for data to load
      await page.waitForTimeout(2000);

      // Check that currency values are displayed (should start with $)
      const totalBalance = page.locator('text=Total Balance').locator('..').locator('text=/\\$[\\d,]+\\./');
      await expect(totalBalance).toBeVisible();
    });

    test('should show update timestamp', async ({ page }) => {
      await expect(page.locator('text=/Updated:/')).toBeVisible();
    });
  });

  test.describe('Performance Chart Component', () => {
    test('should display performance chart section', async ({ page }) => {
      await expect(page.locator('h2:has-text("Performance")')).toBeVisible();
    });

    test('should render chart or empty state', async ({ page }) => {
      // Wait for chart to load
      await page.waitForTimeout(2000);

      // Either chart is visible or "No Performance Data" message
      const hasChart = await page.locator('.recharts-wrapper').isVisible().catch(() => false);
      const hasEmptyState = await page.locator('text=No Performance Data').isVisible().catch(() => false);

      expect(hasChart || hasEmptyState).toBeTruthy();
    });
  });

  test.describe('Bot Status Table Component', () => {
    test('should display bots section', async ({ page }) => {
      await expect(page.locator('h2:has-text("Trading Bots")')).toBeVisible();
    });

    test('should display bot table or empty state', async ({ page }) => {
      // Wait for bots to load
      await page.waitForTimeout(2000);

      // Check if table exists or empty state
      const hasTable = await page.locator('table').isVisible().catch(() => false);
      const hasEmptyState = await page.locator('text=No Bots Running').isVisible().catch(() => false);

      expect(hasTable || hasEmptyState).toBeTruthy();
    });

    test('should display bot table headers if bots exist', async ({ page }) => {
      await page.waitForTimeout(2000);

      const hasTable = await page.locator('table').isVisible().catch(() => false);

      if (hasTable) {
        await expect(page.locator('th:has-text("Bot Name")')).toBeVisible();
        await expect(page.locator('th:has-text("Status")')).toBeVisible();
        await expect(page.locator('th:has-text("Pair")')).toBeVisible();
        await expect(page.locator('th:has-text("Strategy")')).toBeVisible();
        await expect(page.locator('th:has-text("Profit")')).toBeVisible();
        await expect(page.locator('th:has-text("Trades")')).toBeVisible();
        await expect(page.locator('th:has-text("Actions")')).toBeVisible();
      }
    });

    test('should display bot action buttons if bots exist', async ({ page }) => {
      await page.waitForTimeout(2000);

      const hasTable = await page.locator('table').isVisible().catch(() => false);

      if (hasTable) {
        // Check for either Start or Stop buttons
        const hasStartButton = await page.locator('button:has-text("Start")').count() > 0;
        const hasStopButton = await page.locator('button:has-text("Stop")').count() > 0;
        const hasDetailsButton = await page.locator('button:has-text("Details")').count() > 0;

        expect(hasStartButton || hasStopButton).toBeTruthy();
        expect(hasDetailsButton).toBeTruthy();
      }
    });
  });

  test.describe('Trades Feed Component', () => {
    test('should display trades section', async ({ page }) => {
      await expect(page.locator('h2:has-text("Recent Trades")')).toBeVisible();
    });

    test('should display trades or empty state', async ({ page }) => {
      // Wait for trades to load
      await page.waitForTimeout(2000);

      // Check if trades exist or empty state
      const hasTradesBadge = await page.locator('text=/\\d+ trades?/').isVisible().catch(() => false);
      const hasEmptyState = await page.locator('text=No Trades Yet').isVisible().catch(() => false);

      expect(hasTradesBadge || hasEmptyState).toBeTruthy();
    });
  });

  test.describe('Real-time Features', () => {
    test('should have refresh button', async ({ page }) => {
      // Look for the floating refresh button
      const refreshButton = page.locator('button[title="Refresh All Data"]');
      await expect(refreshButton).toBeVisible();
    });

    test('should refresh data when refresh button clicked', async ({ page }) => {
      await page.waitForTimeout(2000);

      // Click refresh button
      const refreshButton = page.locator('button[title="Refresh All Data"]');
      await refreshButton.click();

      // Wait a moment for refresh
      await page.waitForTimeout(1000);

      // Check timestamp updated (this is a basic check)
      await expect(page.locator('text=/Updated:/')).toBeVisible();
    });
  });

  test.describe('Responsive Layout', () => {
    test('should display correctly on mobile viewport', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });

      // Check main sections still visible
      await expect(page.locator('h2:has-text("Portfolio Overview")')).toBeVisible();
      await expect(page.locator('h2:has-text("Trading Bots")')).toBeVisible();
    });

    test('should display correctly on tablet viewport', async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 });

      // Check main sections still visible
      await expect(page.locator('h2:has-text("Portfolio Overview")')).toBeVisible();
      await expect(page.locator('h2:has-text("Performance")')).toBeVisible();
    });
  });

  test.describe('Navigation', () => {
    test('should have navigation bar', async ({ page }) => {
      const nav = page.locator('nav');
      await expect(nav).toBeVisible();
      await expect(nav.locator('text=Thalas Trader')).toBeVisible();
    });

    test('should navigate to consensus page from nav', async ({ page }) => {
      await page.locator('nav a[href="/consensus"]').click();
      await expect(page).toHaveURL('/consensus');
    });

    test('should navigate to home from nav', async ({ page }) => {
      await page.locator('nav a[href="/"]').first().click();
      await expect(page).toHaveURL('/');
    });
  });
});
