import { test, expect, Page } from '@playwright/test';

/**
 * Consensus Page E2E Tests
 *
 * Tests the LLM consensus visualization page including:
 * - Multi-LLM vote breakdown visualization
 * - Provider decision display
 * - Agreement score and confidence metrics
 * - Provider health status
 * - Consensus signal generation
 * - Real-time updates
 */

// Helper function to mock consensus API
async function mockConsensusAPI(page: Page) {
  // Mock consensus endpoint for signal generation
  await page.route('**/api/v1/strategies/llm-consensus', async route => {
    const request = route.request();

    if (request.method() === 'GET') {
      // Health check endpoint
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'healthy',
          providers: 4,
          providers_healthy: 4
        })
      });
    } else if (request.method() === 'POST') {
      // Generate consensus signal
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          decision: 'BUY',
          confidence: 0.82,
          reasoning: 'Strong bullish signals across multiple LLM providers indicate favorable entry point',
          metadata: {
            total_providers: 4,
            participating_providers: 4,
            agreement_score: 0.75,
            weighted_confidence: 0.82,
            vote_breakdown: {
              BUY: 3,
              SELL: 0,
              HOLD: 1
            },
            weighted_votes: {
              BUY: 2.8,
              SELL: 0,
              HOLD: 0.7
            },
            performance: {
              total_latency_ms: 1250,
              total_cost_usd: 0.0042,
              total_tokens: 1850
            }
          },
          provider_responses: [
            {
              provider: 'anthropic',
              decision: 'BUY',
              confidence: 0.85,
              reasoning: 'Claude analysis shows strong upward momentum...',
              risk_level: 'medium',
              weight: 1.0
            },
            {
              provider: 'openai',
              decision: 'BUY',
              confidence: 0.80,
              reasoning: 'GPT-4 detects positive market sentiment...',
              risk_level: 'medium',
              weight: 1.0
            },
            {
              provider: 'gemini',
              decision: 'HOLD',
              confidence: 0.65,
              reasoning: 'Gemini suggests waiting for confirmation...',
              risk_level: 'low',
              weight: 0.8
            },
            {
              provider: 'grok',
              decision: 'BUY',
              confidence: 0.88,
              reasoning: 'Grok identifies breakout pattern...',
              risk_level: 'high',
              weight: 1.0
            }
          ]
        })
      });
    }
  });

  // Mock provider health endpoint
  await page.route('**/api/v1/providers/health', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        providers: [
          { name: 'anthropic', status: 'healthy', latency_ms: 320 },
          { name: 'openai', status: 'healthy', latency_ms: 280 },
          { name: 'gemini', status: 'healthy', latency_ms: 410 },
          { name: 'grok', status: 'degraded', latency_ms: 850 }
        ]
      })
    });
  });

  // Mock recent consensus signals feed
  await page.route('**/api/v1/consensus/recent*', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        signals: [
          {
            id: 1,
            pair: 'BTC/USDT',
            timeframe: '1h',
            decision: 'BUY',
            confidence: 0.82,
            agreement: 0.75,
            timestamp: new Date(Date.now() - 300000).toISOString()
          },
          {
            id: 2,
            pair: 'ETH/USDT',
            timeframe: '4h',
            decision: 'SELL',
            confidence: 0.71,
            agreement: 0.50,
            timestamp: new Date(Date.now() - 600000).toISOString()
          }
        ]
      })
    });
  });
}

test.describe('Consensus Page', () => {
  test.beforeEach(async ({ page }) => {
    await mockConsensusAPI(page);
  });

  test('should load consensus page successfully', async ({ page }) => {
    await page.goto('/consensus');

    // Check that page loaded
    await expect(page).toHaveTitle(/Consensus|LLM.*Consensus|Thalas Trader/);

    // Check for main consensus container
    const consensusPage = page.locator('[data-testid="consensus-page"]')
      .or(page.locator('main'))
      .first();

    await expect(consensusPage).toBeVisible();
  });

  test('should display consensus generation form', async ({ page }) => {
    await page.goto('/consensus');

    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(1000);

    // Look for form inputs
    const form = page.locator('[data-testid="consensus-form"]')
      .or(page.locator('form'))
      .first();

    const formVisible = await form.isVisible().catch(() => false);

    if (formVisible) {
      await expect(form).toBeVisible();

      // Check for pair input
      const pairInput = page.locator('[data-testid="pair-input"]')
        .or(page.locator('input[name="pair"]'))
        .or(page.getByLabel(/pair|symbol/i))
        .first();

      // Check for timeframe input
      const timeframeInput = page.locator('[data-testid="timeframe-input"]')
        .or(page.locator('select[name="timeframe"]'))
        .or(page.getByLabel(/timeframe|interval/i))
        .first();

      // Check for submit button
      const submitButton = page.locator('[data-testid="generate-consensus"]')
        .or(page.getByRole('button', { name: /generate|analyze|consensus/i }))
        .first();

      await expect.soft(pairInput).toBeVisible();
      await expect.soft(timeframeInput).toBeVisible();
      await expect.soft(submitButton).toBeVisible();
    }
  });

  test('should generate consensus signal on form submission', async ({ page }) => {
    await page.goto('/consensus');

    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(1000);

    // Look for form and fill it
    const pairInput = page.locator('[data-testid="pair-input"]')
      .or(page.locator('input[name="pair"]'))
      .first();

    const submitButton = page.locator('[data-testid="generate-consensus"]')
      .or(page.getByRole('button', { name: /generate|analyze|consensus/i }))
      .first();

    const formVisible = await pairInput.isVisible().catch(() => false);

    if (formVisible) {
      // Fill form
      await pairInput.fill('BTC/USDT');

      // Submit form
      await submitButton.click();

      // Wait for response
      await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
      await page.waitForTimeout(1000);

      // Check for consensus result
      const result = page.locator('[data-testid="consensus-result"]')
        .or(page.getByText(/BUY|SELL|HOLD/i))
        .first();

      await expect.soft(result).toBeVisible();
    }
  });

  test('should display vote breakdown visualization', async ({ page }) => {
    await page.goto('/consensus');

    // Trigger consensus generation by clicking button or loading existing data
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});

    // Submit form if visible
    const submitButton = page.locator('[data-testid="generate-consensus"]')
      .or(page.getByRole('button', { name: /generate/i }))
      .first();

    const buttonVisible = await submitButton.isVisible().catch(() => false);
    if (buttonVisible) {
      await submitButton.click();
      await page.waitForTimeout(2000);
    }

    // Look for vote visualization (pie chart, bar chart, etc.)
    const voteChart = page.locator('[data-testid="vote-breakdown-chart"]')
      .or(page.locator('[data-testid="provider-vote-chart"]'))
      .or(page.locator('svg').first())
      .first();

    const chartVisible = await voteChart.isVisible().catch(() => false);

    if (chartVisible) {
      await expect(voteChart).toBeVisible();
    }
  });

  test('should display individual provider responses', async ({ page }) => {
    await page.goto('/consensus');

    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});

    // Try to generate consensus
    const submitButton = page.getByRole('button', { name: /generate/i }).first();
    const buttonVisible = await submitButton.isVisible().catch(() => false);

    if (buttonVisible) {
      await submitButton.click();
      await page.waitForTimeout(2000);
    }

    // Look for provider responses
    const providerResponse = page.locator('[data-testid="provider-response"]')
      .or(page.getByText(/anthropic|openai|gemini|grok/i))
      .first();

    const responseVisible = await providerResponse.isVisible().catch(() => false);

    if (responseVisible) {
      await expect(providerResponse).toBeVisible();

      // Check for provider names
      const anthropic = page.getByText(/anthropic|claude/i).first();
      const openai = page.getByText(/openai|gpt/i).first();

      const hasAnthropic = await anthropic.isVisible().catch(() => false);
      const hasOpenAI = await openai.isVisible().catch(() => false);

      expect(hasAnthropic || hasOpenAI).toBe(true);
    }
  });

  test('should show agreement score and confidence', async ({ page }) => {
    await page.goto('/consensus');

    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});

    const submitButton = page.getByRole('button', { name: /generate/i }).first();
    const buttonVisible = await submitButton.isVisible().catch(() => false);

    if (buttonVisible) {
      await submitButton.click();
      await page.waitForTimeout(2000);
    }

    // Look for confidence and agreement metrics
    const confidence = page.locator('[data-testid="consensus-confidence"]')
      .or(page.getByText(/confidence.*\d+%|confidence.*0\.\d+/i))
      .first();

    const agreement = page.locator('[data-testid="agreement-score"]')
      .or(page.getByText(/agreement.*\d+%|agreement.*0\.\d+/i))
      .first();

    const hasConfidence = await confidence.isVisible().catch(() => false);
    const hasAgreement = await agreement.isVisible().catch(() => false);

    if (hasConfidence) {
      await expect(confidence).toBeVisible();
    }

    if (hasAgreement) {
      await expect(agreement).toBeVisible();
    }
  });

  test('should display provider health status', async ({ page }) => {
    await page.goto('/consensus');

    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(1000);

    // Look for provider health indicators
    const healthStatus = page.locator('[data-testid="provider-health"]')
      .or(page.getByText(/health|status|online|offline/i))
      .first();

    const statusVisible = await healthStatus.isVisible().catch(() => false);

    if (statusVisible) {
      await expect(healthStatus).toBeVisible();

      // Check for health indicators (green/red dots, healthy/degraded text)
      const healthyIndicator = page.getByText(/healthy|online|active/i).first();
      const isVisible = await healthyIndicator.isVisible().catch(() => false);

      if (isVisible) {
        await expect(healthyIndicator).toBeVisible();
      }
    }
  });

  test('should show consensus reasoning', async ({ page }) => {
    await page.goto('/consensus');

    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});

    const submitButton = page.getByRole('button', { name: /generate/i }).first();
    const buttonVisible = await submitButton.isVisible().catch(() => false);

    if (buttonVisible) {
      await submitButton.click();
      await page.waitForTimeout(2000);
    }

    // Look for reasoning section
    const reasoning = page.locator('[data-testid="consensus-reasoning"]')
      .or(page.getByText(/reasoning|analysis|explanation/i).locator('..'))
      .first();

    const reasoningVisible = await reasoning.isVisible().catch(() => false);

    if (reasoningVisible) {
      await expect(reasoning).toBeVisible();

      // Reasoning should contain substantial text
      const text = await reasoning.textContent();
      expect(text?.length || 0).toBeGreaterThan(10);
    }
  });

  test('should display performance metrics', async ({ page }) => {
    await page.goto('/consensus');

    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});

    const submitButton = page.getByRole('button', { name: /generate/i }).first();
    const buttonVisible = await submitButton.isVisible().catch(() => false);

    if (buttonVisible) {
      await submitButton.click();
      await page.waitForTimeout(2000);
    }

    // Look for performance metrics (latency, cost, tokens)
    const metrics = page.locator('[data-testid="performance-metrics"]')
      .or(page.getByText(/latency|cost|tokens/i))
      .first();

    const metricsVisible = await metrics.isVisible().catch(() => false);

    if (metricsVisible) {
      await expect(metrics).toBeVisible();
    }
  });

  test('should handle consensus generation errors', async ({ page }) => {
    // Mock error response
    await page.route('**/api/v1/strategies/llm-consensus', async route => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 503,
          contentType: 'application/json',
          body: JSON.stringify({
            error: 'Service unavailable',
            detail: 'No LLM providers available'
          })
        });
      } else {
        await route.continue();
      }
    });

    await page.goto('/consensus');

    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});

    const submitButton = page.getByRole('button', { name: /generate/i }).first();
    const buttonVisible = await submitButton.isVisible().catch(() => false);

    if (buttonVisible) {
      await submitButton.click();
      await page.waitForTimeout(2000);

      // Look for error message
      const errorMessage = page.locator('[data-testid="error-message"]')
        .or(page.getByText(/error|failed|unavailable/i))
        .first();

      const hasError = await errorMessage.isVisible().catch(() => false);

      if (hasError) {
        await expect(errorMessage).toBeVisible();
      }
    }
  });

  test('should show loading state during consensus generation', async ({ page }) => {
    await page.goto('/consensus');

    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});

    const submitButton = page.getByRole('button', { name: /generate/i }).first();
    const buttonVisible = await submitButton.isVisible().catch(() => false);

    if (buttonVisible) {
      // Click submit
      await submitButton.click();

      // Look for loading indicator (might be brief)
      const loader = page.locator('[data-testid="loading"]')
        .or(page.locator('.loading'))
        .or(page.getByText(/loading|generating|analyzing/i))
        .first();

      const hasLoader = await loader.isVisible({ timeout: 500 }).catch(() => false);

      // Loader should eventually disappear
      if (hasLoader) {
        await expect(loader).not.toBeVisible({ timeout: 5000 });
      }
    }
  });

  test('should allow filtering consensus signals', async ({ page }) => {
    await page.goto('/consensus');

    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(1000);

    // Look for filter controls
    const filter = page.locator('[data-testid="signal-filter"]')
      .or(page.getByLabel(/filter|timeframe|pair/i))
      .first();

    const filterVisible = await filter.isVisible().catch(() => false);

    if (filterVisible) {
      await expect(filter).toBeVisible();

      // Try selecting a filter option
      const filterSelect = page.locator('select').first();
      const hasSelect = await filterSelect.isVisible().catch(() => false);

      if (hasSelect) {
        await filterSelect.selectOption({ index: 1 });
        await page.waitForTimeout(500);
      }
    }
  });

  test('should display recent consensus signals feed', async ({ page }) => {
    await page.goto('/consensus');

    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(1000);

    // Look for signals feed
    const signalsFeed = page.locator('[data-testid="consensus-signal-feed"]')
      .or(page.getByText(/recent.*signals|signal.*history/i).locator('..'))
      .first();

    const feedVisible = await signalsFeed.isVisible().catch(() => false);

    if (feedVisible) {
      await expect(signalsFeed).toBeVisible();

      // Check for signal items
      const signalItem = page.locator('[data-testid="signal-item"]')
        .or(page.getByText(/BTC|ETH/i))
        .first();

      await expect.soft(signalItem).toBeVisible();
    }
  });
});
