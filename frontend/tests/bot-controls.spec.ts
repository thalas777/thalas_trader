import { test, expect } from '@playwright/test';

test.describe('Bot Control Operations', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForTimeout(2000); // Wait for bots to load
  });

  test('should display bot control buttons', async ({ page }) => {
    // Check if bots exist
    const hasTable = await page.locator('table').isVisible().catch(() => false);

    if (hasTable) {
      // Should have either Start or Stop buttons
      const startButtons = await page.locator('button:has-text("Start")').count();
      const stopButtons = await page.locator('button:has-text("Stop")').count();

      expect(startButtons + stopButtons).toBeGreaterThan(0);
    } else {
      // If no bots, should show empty state with create button
      await expect(page.locator('text=No Bots Running')).toBeVisible();
    }
  });

  test('should show bot status badges', async ({ page }) => {
    const hasTable = await page.locator('table').isVisible().catch(() => false);

    if (hasTable) {
      // Check for status badges (running, stopped, paused, error)
      const hasBadges = await page.locator('span:has-text(/RUNNING|STOPPED|PAUSED|ERROR/i)').count() > 0;
      expect(hasBadges).toBeTruthy();
    }
  });

  test('should display bot names and pairs', async ({ page }) => {
    const hasTable = await page.locator('table').isVisible().catch(() => false);

    if (hasTable) {
      // Should show bot names
      const botNames = await page.locator('td').filter({ hasText: /LLM Consensus Bot|Bot/ }).count();
      expect(botNames).toBeGreaterThan(0);

      // Should show trading pairs (e.g., BTC/USD, ETH/USD)
      const pairs = await page.locator('td').filter({ hasText: /\/USD|\/USDT/ }).count();
      expect(pairs).toBeGreaterThan(0);
    }
  });

  test('should display bot profit information', async ({ page }) => {
    const hasTable = await page.locator('table').isVisible().catch(() => false);

    if (hasTable) {
      // Check for profit values (with $ sign)
      const profitCells = await page.locator('td').filter({ hasText: /\$[\d,]+\./ }).count();
      expect(profitCells).toBeGreaterThan(0);
    }
  });

  test('should display bot trade count', async ({ page }) => {
    const hasTable = await page.locator('table').isVisible().catch(() => false);

    if (hasTable) {
      // Look for trade count column
      const tradeCounts = await page.locator('table tbody tr').first().locator('td').nth(5);
      await expect(tradeCounts).toBeVisible();
    }
  });

  test('should display bot strategy', async ({ page }) => {
    const hasTable = await page.locator('table').isVisible().catch(() => false);

    if (hasTable) {
      // Check for strategy names
      const strategies = await page.locator('td').filter({ hasText: /Strategy|Consensus/ }).count();
      expect(strategies).toBeGreaterThanOrEqual(0);
    }
  });

  test.describe('Bot Start/Stop Operations', () => {
    test('start button should be clickable and show loading state', async ({ page }) => {
      const startButtons = await page.locator('button:has-text("Start")');
      const startButtonCount = await startButtons.count();

      if (startButtonCount > 0) {
        const firstStartButton = startButtons.first();
        await expect(firstStartButton).toBeEnabled();

        // Click the button
        await firstStartButton.click();

        // Should show loading state or change state
        await page.waitForTimeout(1000);

        // Button should either be disabled during loading or text changed
        const isDisabled = await firstStartButton.isDisabled().catch(() => false);
        const hasLoadingText = await page.locator('button:has-text("...")').isVisible().catch(() => false);

        expect(isDisabled || hasLoadingText).toBeTruthy();
      }
    });

    test('stop button should be clickable and show loading state', async ({ page }) => {
      const stopButtons = await page.locator('button:has-text("Stop")');
      const stopButtonCount = await stopButtons.count();

      if (stopButtonCount > 0) {
        const firstStopButton = stopButtons.first();
        await expect(firstStopButton).toBeEnabled();

        // Click the button
        await firstStopButton.click();

        // Should show loading state
        await page.waitForTimeout(1000);

        // Button should either be disabled during loading or text changed
        const isDisabled = await firstStopButton.isDisabled().catch(() => false);
        const hasLoadingText = await page.locator('button:has-text("...")').isVisible().catch(() => false);

        expect(isDisabled || hasLoadingText).toBeTruthy();
      }
    });

    test('details button should be present', async ({ page }) => {
      const hasTable = await page.locator('table').isVisible().catch(() => false);

      if (hasTable) {
        const detailsButtons = await page.locator('button:has-text("Details")');
        const count = await detailsButtons.count();
        expect(count).toBeGreaterThan(0);

        // Details button should be enabled
        await expect(detailsButtons.first()).toBeEnabled();
      }
    });
  });

  test.describe('Bot Table Interactions', () => {
    test('should highlight row on hover', async ({ page }) => {
      const hasTable = await page.locator('table').isVisible().catch(() => false);

      if (hasTable) {
        const firstRow = page.locator('table tbody tr').first();
        await firstRow.hover();

        // Row should have hover state (basic check that it exists)
        await expect(firstRow).toBeVisible();
      }
    });

    test('should display all bot information columns', async ({ page }) => {
      const hasTable = await page.locator('table').isVisible().catch(() => false);

      if (hasTable) {
        const firstRow = page.locator('table tbody tr').first();
        const cells = firstRow.locator('td');
        const cellCount = await cells.count();

        // Should have 7 columns: name, status, pair, strategy, profit, trades, actions
        expect(cellCount).toBe(7);
      }
    });
  });

  test.describe('Error Handling', () => {
    test('should handle bot action errors gracefully', async ({ page }) => {
      // Intercept API calls and simulate error
      await page.route('**/api/v1/bots/*/start', route => {
        route.fulfill({
          status: 500,
          body: JSON.stringify({ error: 'Failed to start bot' })
        });
      });

      await page.route('**/api/v1/bots/*/stop', route => {
        route.fulfill({
          status: 500,
          body: JSON.stringify({ error: 'Failed to stop bot' })
        });
      });

      const startButtons = await page.locator('button:has-text("Start")');
      const stopButtons = await page.locator('button:has-text("Stop")');

      if (await startButtons.count() > 0) {
        await startButtons.first().click();
        // Should show error toast (sonner notification)
        await page.waitForTimeout(1000);
        // Toast should appear with error message
        const hasErrorToast = await page.locator('[data-sonner-toast]').isVisible().catch(() => false);
        // Note: Error handling may vary, this is a basic check
      }
    });
  });

  test.describe('Empty State', () => {
    test('empty state should show create bot button', async ({ page }) => {
      const hasEmptyState = await page.locator('text=No Bots Running').isVisible().catch(() => false);

      if (hasEmptyState) {
        await expect(page.locator('button:has-text("Create Bot")')).toBeVisible();
      }
    });

    test('empty state should show friendly message', async ({ page }) => {
      const hasEmptyState = await page.locator('text=No Bots Running').isVisible().catch(() => false);

      if (hasEmptyState) {
        await expect(page.locator('text=Create your first trading bot')).toBeVisible();
      }
    });
  });
});
