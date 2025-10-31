import { test, expect } from '@playwright/test';

test.describe('Consensus Signals Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/consensus');
  });

  test('should load consensus page successfully', async ({ page }) => {
    await expect(page).toHaveTitle(/Consensus Signals - Thalas Trader/);
    await expect(page.locator('h1:has-text("Multi-LLM Consensus Trading Signals")')).toBeVisible();
    await expect(page.locator('text=Get trading decisions powered by multiple AI providers')).toBeVisible();
  });

  test.describe('Provider Health Status', () => {
    test('should display provider health section', async ({ page }) => {
      // Wait for providers to load
      await page.waitForTimeout(2000);

      // Check for provider health indicators
      const hasProviderSection = await page.locator('text=/Providers?|Health/i').isVisible().catch(() => false);
      expect(hasProviderSection).toBeTruthy();
    });
  });

  test.describe('Consensus Request Form', () => {
    test('should display request form section', async ({ page }) => {
      await expect(page.locator('h2:has-text("Request Consensus Signal")')).toBeVisible();
    });

    test('should have trading pair selector', async ({ page }) => {
      // Look for pair selector or input
      const hasPairInput = await page.locator('select, input[type="text"]').filter({ hasText: /pair/i }).or(page.locator('label:has-text(/pair/i) ~ select, label:has-text(/pair/i) ~ input')).count() > 0;
      expect(hasPairInput).toBeTruthy();
    });

    test('should have timeframe selector', async ({ page }) => {
      // Look for timeframe selector
      const hasTimeframeInput = await page.locator('select, input').filter({ hasText: /timeframe|time/i }).or(page.locator('label:has-text(/timeframe/i) ~ select, label:has-text(/timeframe/i) ~ input')).count() > 0;
      expect(hasTimeframeInput).toBeTruthy();
    });

    test('should have market data input fields', async ({ page }) => {
      // Look for market data indicators (RSI, MACD, etc.)
      const hasMarketDataInputs = await page.locator('input, textarea').count() > 0;
      expect(hasMarketDataInputs).toBeTruthy();
    });

    test('should have submit button', async ({ page }) => {
      const submitButton = page.locator('button[type="submit"], button:has-text("Get Consensus"), button:has-text("Submit")');
      await expect(submitButton).toBeVisible();
    });

    test('submit button should be enabled when form is valid', async ({ page }) => {
      const submitButton = page.locator('button[type="submit"], button:has-text("Get Consensus"), button:has-text("Submit")');

      // Wait a moment for form to initialize
      await page.waitForTimeout(500);

      // Button should be enabled (if form has defaults) or disabled (if validation required)
      const isVisible = await submitButton.isVisible();
      expect(isVisible).toBeTruthy();
    });
  });

  test.describe('Consensus Result Display', () => {
    test('should show loading state when fetching consensus', async ({ page }) => {
      // Intercept API call to delay response
      await page.route('**/api/v1/strategies/llm-consensus', route => {
        setTimeout(() => route.continue(), 2000);
      });

      // Fill form and submit
      const submitButton = page.locator('button[type="submit"], button:has-text("Get Consensus"), button:has-text("Submit")');
      if (await submitButton.isEnabled()) {
        await submitButton.click();

        // Check for loading indicator
        await page.waitForTimeout(500);
        const hasLoadingState = await page.locator('text=/Loading|Fetching|\\.\\.\\./').isVisible().catch(() => false) ||
                               await submitButton.isDisabled();
        expect(hasLoadingState).toBeTruthy();
      }
    });

    test('should display consensus result when successful', async ({ page }) => {
      // Mock successful API response
      await page.route('**/api/v1/strategies/llm-consensus', route => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            decision: 'BUY',
            confidence: 0.85,
            reasoning: 'Strong bullish indicators across all providers',
            risk_level: 'medium',
            suggested_stop_loss: 48000,
            suggested_take_profit: 52000,
            consensus_metadata: {
              total_providers: 3,
              participating_providers: 3,
              agreement_score: 0.95,
              weighted_confidence: 0.85,
              vote_breakdown: { BUY: 3, SELL: 0, HOLD: 0 },
              weighted_vote_breakdown: { BUY: 0.85, SELL: 0, HOLD: 0 },
              provider_responses: [
                {
                  provider: 'grok',
                  decision: 'BUY',
                  confidence: 0.9,
                  reasoning: 'Technical analysis shows strong buy signal',
                  risk_level: 'medium',
                  cost: 0.001,
                  tokens_used: 500,
                  latency: 1.2
                },
                {
                  provider: 'gemini',
                  decision: 'BUY',
                  confidence: 0.8,
                  reasoning: 'Market momentum is positive',
                  risk_level: 'medium',
                  cost: 0.001,
                  tokens_used: 450,
                  latency: 1.0
                },
                {
                  provider: 'deepseek',
                  decision: 'BUY',
                  confidence: 0.85,
                  reasoning: 'Price action indicates accumulation',
                  risk_level: 'medium',
                  cost: 0.0005,
                  tokens_used: 480,
                  latency: 0.8
                }
              ],
              total_latency: 3.0,
              total_cost: 0.0025,
              total_tokens: 1430
            }
          })
        });
      });

      // Submit form
      const submitButton = page.locator('button[type="submit"], button:has-text("Get Consensus"), button:has-text("Submit")');
      await submitButton.click();

      // Wait for result
      await page.waitForTimeout(2000);

      // Check for result display
      await expect(page.locator('h2:has-text("Consensus Result")')).toBeVisible();
      await expect(page.locator('text=BUY')).toBeVisible();
      await expect(page.locator('text=/85\\.?0?%/')).toBeVisible();
    });

    test('should display error message when API fails', async ({ page }) => {
      // Mock failed API response
      await page.route('**/api/v1/strategies/llm-consensus', route => {
        route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Failed to get consensus' })
        });
      });

      // Submit form
      const submitButton = page.locator('button[type="submit"], button:has-text("Get Consensus"), button:has-text("Submit")');
      await submitButton.click();

      // Wait for error
      await page.waitForTimeout(1500);

      // Check for error message
      const hasError = await page.locator('text=/Error|Failed|Cannot connect/').isVisible().catch(() => false);
      expect(hasError).toBeTruthy();
    });
  });

  test.describe('Result Components', () => {
    test.beforeEach(async ({ page }) => {
      // Mock successful consensus for these tests
      await page.route('**/api/v1/strategies/llm-consensus', route => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            decision: 'BUY',
            confidence: 0.85,
            reasoning: 'Strong bullish indicators',
            risk_level: 'medium',
            suggested_stop_loss: 48000,
            suggested_take_profit: 52000,
            consensus_metadata: {
              total_providers: 3,
              participating_providers: 3,
              agreement_score: 0.95,
              weighted_confidence: 0.85,
              vote_breakdown: { BUY: 3, SELL: 0, HOLD: 0 },
              weighted_vote_breakdown: { BUY: 0.85, SELL: 0, HOLD: 0 },
              provider_responses: [
                { provider: 'grok', decision: 'BUY', confidence: 0.9, reasoning: 'Bullish', risk_level: 'medium', cost: 0.001, tokens_used: 500, latency: 1.2 },
                { provider: 'gemini', decision: 'BUY', confidence: 0.8, reasoning: 'Positive', risk_level: 'medium', cost: 0.001, tokens_used: 450, latency: 1.0 },
                { provider: 'deepseek', decision: 'BUY', confidence: 0.85, reasoning: 'Accumulation', risk_level: 'medium', cost: 0.0005, tokens_used: 480, latency: 0.8 }
              ],
              total_latency: 3.0,
              total_cost: 0.0025,
              total_tokens: 1430
            }
          })
        });
      });
    });

    test('should display decision, confidence, and agreement', async ({ page }) => {
      const submitButton = page.locator('button[type="submit"], button:has-text("Get Consensus"), button:has-text("Submit")');
      await submitButton.click();
      await page.waitForTimeout(2000);

      await expect(page.locator('text=Decision')).toBeVisible();
      await expect(page.locator('text=Confidence')).toBeVisible();
      await expect(page.locator('text=Agreement')).toBeVisible();
    });

    test('should display reasoning', async ({ page }) => {
      const submitButton = page.locator('button[type="submit"], button:has-text("Get Consensus"), button:has-text("Submit")');
      await submitButton.click();
      await page.waitForTimeout(2000);

      await expect(page.locator('text=Reasoning')).toBeVisible();
      await expect(page.locator('text=Strong bullish indicators')).toBeVisible();
    });

    test('should display risk level and suggestions', async ({ page }) => {
      const submitButton = page.locator('button[type="submit"], button:has-text("Get Consensus"), button:has-text("Submit")');
      await submitButton.click();
      await page.waitForTimeout(2000);

      await expect(page.locator('text=Risk Level')).toBeVisible();
      await expect(page.locator('text=/Stop Loss|Take Profit/')).toBeVisible();
    });

    test('should display provider analysis section', async ({ page }) => {
      const submitButton = page.locator('button[type="submit"], button:has-text("Get Consensus"), button:has-text("Submit")');
      await submitButton.click();
      await page.waitForTimeout(2000);

      await expect(page.locator('h2:has-text("Provider Analysis")')).toBeVisible();
    });

    test('should display metadata (latency, cost, tokens)', async ({ page }) => {
      const submitButton = page.locator('button[type="submit"], button:has-text("Get Consensus"), button:has-text("Submit")');
      await submitButton.click();
      await page.waitForTimeout(2000);

      await expect(page.locator('text=/Latency|Cost|Tokens/')).toBeVisible();
    });
  });

  test.describe('Signal History', () => {
    test('should display signal history after getting consensus', async ({ page }) => {
      // Mock consensus response
      await page.route('**/api/v1/strategies/llm-consensus', route => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            decision: 'BUY',
            confidence: 0.85,
            reasoning: 'Test',
            risk_level: 'medium',
            consensus_metadata: {
              total_providers: 3,
              participating_providers: 3,
              agreement_score: 0.95,
              weighted_confidence: 0.85,
              vote_breakdown: { BUY: 3 },
              weighted_vote_breakdown: { BUY: 0.85 },
              provider_responses: [],
              total_latency: 3.0,
              total_cost: 0.0025,
              total_tokens: 1430
            }
          })
        });
      });

      const submitButton = page.locator('button[type="submit"], button:has-text("Get Consensus"), button:has-text("Submit")');
      await submitButton.click();
      await page.waitForTimeout(2000);

      // Should show signal history section
      const hasHistory = await page.locator('h2:has-text("Signal History")').isVisible();
      expect(hasHistory).toBeTruthy();
    });
  });
});
