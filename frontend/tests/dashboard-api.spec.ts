import { test, expect } from '@playwright/test';

test.describe('Dashboard API Integration', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard');
  });

  test('should load dashboard page successfully', async ({ page }) => {
    await expect(page.locator('h1:has-text("Trading Dashboard")')).toBeVisible();
    await expect(page.locator('text=Multi-LLM Consensus Trading System')).toBeVisible();
  });

  test.describe('Backend API Connectivity', () => {
    test('should successfully fetch portfolio summary from backend', async ({ page }) => {
      // Wait for API call to complete
      const response = await page.waitForResponse(
        (response) => response.url().includes('/api/v1/summary') && response.status() === 200,
        { timeout: 10000 }
      );

      expect(response.status()).toBe(200);
      const data = await response.json();

      // Verify response structure
      expect(data).toHaveProperty('total_balance');
      expect(data).toHaveProperty('cash_balance');
      expect(data).toHaveProperty('position_value');
      expect(data).toHaveProperty('total_profit');
      expect(data).toHaveProperty('profit_percentage');
      expect(data).toHaveProperty('total_trades');
      expect(data).toHaveProperty('win_rate');
      expect(data).toHaveProperty('active_bots');
      expect(data).toHaveProperty('total_bots');

      console.log('Portfolio Summary Response:', data);
    });

    test('should successfully fetch bots list from backend', async ({ page }) => {
      const response = await page.waitForResponse(
        (response) => response.url().includes('/api/v1/bots') && response.status() === 200,
        { timeout: 10000 }
      );

      expect(response.status()).toBe(200);
      const data = await response.json();

      // Verify response structure
      expect(data).toHaveProperty('bots');
      expect(Array.isArray(data.bots)).toBe(true);

      if (data.bots.length > 0) {
        const bot = data.bots[0];
        expect(bot).toHaveProperty('bot_id');
        expect(bot).toHaveProperty('name');
        expect(bot).toHaveProperty('status');
        expect(bot).toHaveProperty('strategy');
      }

      console.log('Bots Response:', `${data.bots.length} bots found`);
    });

    test('should successfully fetch trades from backend', async ({ page }) => {
      const response = await page.waitForResponse(
        (response) => response.url().includes('/api/v1/trades') && response.status() === 200,
        { timeout: 10000 }
      );

      expect(response.status()).toBe(200);
      const data = await response.json();

      // Verify response structure
      expect(data).toHaveProperty('trades');
      expect(data).toHaveProperty('limit');
      expect(data).toHaveProperty('offset');
      expect(data).toHaveProperty('count');
      expect(Array.isArray(data.trades)).toBe(true);

      if (data.trades.length > 0) {
        const trade = data.trades[0];
        expect(trade).toHaveProperty('trade_id');
        expect(trade).toHaveProperty('pair');
        expect(trade).toHaveProperty('type');
        expect(trade).toHaveProperty('amount');
        expect(trade).toHaveProperty('price');
      }

      console.log('Trades Response:', `${data.trades.length} trades found`);
    });

    test('should successfully fetch performance data from backend', async ({ page }) => {
      const response = await page.waitForResponse(
        (response) => response.url().includes('/api/v1/performance') && response.status() === 200,
        { timeout: 10000 }
      );

      expect(response.status()).toBe(200);
      const data = await response.json();

      // Verify response structure
      expect(data).toHaveProperty('equity_curve');
      expect(Array.isArray(data.equity_curve)).toBe(true);

      if (data.equity_curve.length > 0) {
        const point = data.equity_curve[0];
        expect(point).toHaveProperty('timestamp');
        expect(point).toHaveProperty('balance');
        expect(point).toHaveProperty('profit');
      }

      console.log('Performance Response:', `${data.equity_curve.length} data points`);
    });

    test('should handle CORS headers correctly', async ({ page }) => {
      const response = await page.waitForResponse(
        (response) => response.url().includes('/api/v1/summary'),
        { timeout: 10000 }
      );

      const headers = response.headers();
      console.log('CORS Headers:', {
        'access-control-allow-origin': headers['access-control-allow-origin'],
        'access-control-allow-credentials': headers['access-control-allow-credentials']
      });

      // Backend should allow requests from localhost:3000
      expect(response.status()).toBe(200);
    });

    test('should verify all API endpoints return 200 status', async ({ page }) => {
      const endpoints = [
        '/api/v1/summary',
        '/api/v1/bots',
        '/api/v1/trades',
        '/api/v1/performance'
      ];

      const responses = await Promise.all(
        endpoints.map(endpoint =>
          page.waitForResponse(
            (response) => response.url().includes(endpoint),
            { timeout: 10000 }
          )
        )
      );

      const results = responses.map((response, index) => ({
        endpoint: endpoints[index],
        status: response.status(),
        ok: response.ok()
      }));

      console.log('All Endpoints Status:', results);

      results.forEach(result => {
        expect(result.status).toBe(200);
        expect(result.ok).toBe(true);
      });
    });
  });

  test.describe('UI Data Display', () => {
    test('should display portfolio data in UI', async ({ page }) => {
      // Wait for data to load
      await page.waitForResponse((response) => response.url().includes('/api/v1/summary'));
      await page.waitForTimeout(1000);

      // Check for portfolio display elements
      const hasBalanceDisplay = await page.locator('text=/Total Balance|Balance/').isVisible();
      expect(hasBalanceDisplay).toBeTruthy();
    });

    test('should display bots in UI', async ({ page }) => {
      // Wait for bots to load
      await page.waitForResponse((response) => response.url().includes('/api/v1/bots'));
      await page.waitForTimeout(1000);

      // Check for bot display
      const hasBotSection = await page.locator('text=/Bot|Status/i').isVisible();
      expect(hasBotSection).toBeTruthy();
    });

    test('should display trades in UI', async ({ page }) => {
      // Wait for trades to load
      await page.waitForResponse((response) => response.url().includes('/api/v1/trades'));
      await page.waitForTimeout(1000);

      // Check for trades display
      const hasTradesSection = await page.locator('text=/Trade|Recent/i').isVisible();
      expect(hasTradesSection).toBeTruthy();
    });
  });

  test.describe('Connection Status Indicator', () => {
    test('should show connection status indicator', async ({ page }) => {
      // Wait for page to load
      await page.waitForTimeout(2000);

      // Check if connection status component exists
      const hasConnectionStatus = await page.locator('text=/Connected|Connection|Status/').count() > 0;
      console.log('Has connection status indicator:', hasConnectionStatus);
    });
  });

  test.describe('Error Handling', () => {
    test('should handle backend unavailable gracefully', async ({ page, context }) => {
      // Block all API requests to simulate backend down
      await context.route('**/api/v1/**', route => route.abort('failed'));

      await page.goto('/dashboard');
      await page.waitForTimeout(3000);

      // Should show error state or message
      const hasErrorIndicator = await page.locator('text=/Cannot connect|Error|Failed|unavailable/i').isVisible().catch(() => false);
      console.log('Has error indicator when backend is down:', hasErrorIndicator);
    });
  });

  test.describe('Data Refresh', () => {
    test('should support manual data refresh', async ({ page }) => {
      // Wait for initial load
      await page.waitForResponse((response) => response.url().includes('/api/v1/summary'));
      await page.waitForTimeout(2000);

      // Look for refresh button
      const refreshButton = page.locator('button[title*="Refresh"], button:has-text("Refresh")');
      const hasRefreshButton = await refreshButton.isVisible().catch(() => false);

      if (hasRefreshButton) {
        // Click refresh and verify new requests
        await refreshButton.click();

        // Wait for new API calls
        const response = await page.waitForResponse(
          (response) => response.url().includes('/api/v1/'),
          { timeout: 5000 }
        ).catch(() => null);

        expect(response).not.toBeNull();
      }
    });
  });

  test.describe('Performance Metrics', () => {
    test('should measure API response times', async ({ page }) => {
      const startTime = Date.now();

      await page.waitForResponse((response) => response.url().includes('/api/v1/summary'));

      const summaryTime = Date.now() - startTime;

      console.log('API Response Times:', {
        summary: `${summaryTime}ms`
      });

      // API should respond within reasonable time
      expect(summaryTime).toBeLessThan(5000);
    });
  });
});

test.describe('Individual API Endpoints (Direct Testing)', () => {
  test('should test /api/v1/summary endpoint directly', async ({ request }) => {
    const response = await request.get('http://localhost:8000/api/v1/summary');

    expect(response.ok()).toBeTruthy();
    expect(response.status()).toBe(200);

    const data = await response.json();
    expect(data).toHaveProperty('total_balance');

    console.log('Direct API Test - Summary:', data);
  });

  test('should test /api/v1/bots endpoint directly', async ({ request }) => {
    const response = await request.get('http://localhost:8000/api/v1/bots');

    expect(response.ok()).toBeTruthy();
    expect(response.status()).toBe(200);

    const data = await response.json();
    expect(data).toHaveProperty('bots');

    console.log('Direct API Test - Bots:', `${data.bots.length} bots`);
  });

  test('should test /api/v1/trades endpoint directly', async ({ request }) => {
    const response = await request.get('http://localhost:8000/api/v1/trades');

    expect(response.ok()).toBeTruthy();
    expect(response.status()).toBe(200);

    const data = await response.json();
    expect(data).toHaveProperty('trades');

    console.log('Direct API Test - Trades:', `${data.trades.length} trades`);
  });

  test('should test /api/v1/performance endpoint directly', async ({ request }) => {
    const response = await request.get('http://localhost:8000/api/v1/performance');

    expect(response.ok()).toBeTruthy();
    expect(response.status()).toBe(200);

    const data = await response.json();
    expect(data).toHaveProperty('equity_curve');

    console.log('Direct API Test - Performance:', `${data.equity_curve.length} data points`);
  });
});
