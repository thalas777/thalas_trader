import { test, expect } from '@playwright/test';

test.describe('Home Page', () => {
  test('should load home page successfully', async ({ page }) => {
    await page.goto('/');

    // Check title
    await expect(page).toHaveTitle(/Thalas Trader/);

    // Check main heading
    const heading = page.locator('h1');
    await expect(heading).toContainText('Welcome to Thalas Trader');
  });

  test('should display system information', async ({ page }) => {
    await page.goto('/');

    // Check subtitle
    await expect(page.locator('text=Multi-LLM Consensus Trading System')).toBeVisible();
    await expect(page.locator('text=Powered by Grok, Gemini, and DeepSeek')).toBeVisible();

    // Check system status indicator
    await expect(page.locator('text=System Online')).toBeVisible();
    await expect(page.locator('text=3 LLM Providers Active')).toBeVisible();
  });

  test('should have navigation cards', async ({ page }) => {
    await page.goto('/');

    // Check Dashboard card
    const dashboardCard = page.locator('text=Trading Dashboard').locator('..');
    await expect(dashboardCard).toBeVisible();
    await expect(page.locator('text=Monitor your bots, view performance metrics')).toBeVisible();

    // Check Consensus card
    const consensusCard = page.locator('text=Consensus Signals').locator('..');
    await expect(consensusCard).toBeVisible();
    await expect(page.locator('text=Request trading signals with multi-LLM consensus')).toBeVisible();
  });

  test('should navigate to dashboard page', async ({ page }) => {
    await page.goto('/');

    // Click dashboard card
    await page.locator('a[href="/dashboard"]').first().click();

    // Verify navigation
    await expect(page).toHaveURL('/dashboard');
    await expect(page.locator('text=Trading Dashboard')).toBeVisible();
  });

  test('should navigate to consensus page', async ({ page }) => {
    await page.goto('/');

    // Click consensus card
    await page.locator('a[href="/consensus"]').first().click();

    // Verify navigation
    await expect(page).toHaveURL('/consensus');
    await expect(page.locator('text=Multi-LLM Consensus Trading Signals')).toBeVisible();
  });

  test('should have working navigation bar', async ({ page }) => {
    await page.goto('/');

    // Check nav bar exists
    const nav = page.locator('nav');
    await expect(nav).toBeVisible();

    // Check Thalas Trader logo/link
    await expect(nav.locator('text=Thalas Trader')).toBeVisible();

    // Check navigation links
    await expect(nav.locator('a[href="/"]')).toBeVisible();
    await expect(nav.locator('a[href="/consensus"]')).toBeVisible();
  });
});
