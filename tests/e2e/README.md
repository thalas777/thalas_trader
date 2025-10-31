# Thalas Trader E2E Tests

End-to-end tests for the Thalas Trader frontend dashboard using Playwright.

## Overview

This test suite provides comprehensive E2E testing for the Next.js frontend, including:

- **Dashboard Tests** (`dashboard.spec.ts`): Portfolio summary, bot status, trades feed, charts
- **Consensus Tests** (`consensus.spec.ts`): LLM consensus visualization, vote breakdown, provider responses
- **Navigation Tests** (`navigation.spec.ts`): Page routing, deep linking, browser navigation
- **Responsive Tests** (`responsive.spec.ts`): Mobile/tablet/desktop layouts, touch interactions

## Setup

### Prerequisites

- Node.js 18+ and npm
- Frontend running at `http://localhost:3000` (or set `FRONTEND_URL` environment variable)

### Installation

```bash
# Install dependencies
npm install

# Install Playwright browsers
npx playwright install

# Install system dependencies (optional, for headed mode)
sudo npx playwright install-deps
```

## Running Tests

### All Tests

```bash
# Run all tests (headless mode)
npm test

# Run with UI mode (recommended for development)
npm run test:ui

# Run in headed mode (see browser)
npm run test:headed

# Run in debug mode
npm run test:debug
```

### Specific Browsers

```bash
# Run only in Chromium
npm run test:chromium

# Run only in Firefox
npm run test:firefox

# Run only in WebKit (Safari)
npm run test:webkit

# Run only mobile tests
npm run test:mobile
```

### Specific Test Files

```bash
# Run only dashboard tests
npx playwright test dashboard

# Run only consensus tests
npx playwright test consensus

# Run only navigation tests
npx playwright test navigation

# Run only responsive tests
npx playwright test responsive
```

## Test Reports

After running tests, view the HTML report:

```bash
npm run report
```

Reports are generated in `playwright-report/` directory.

## Test Configuration

Tests are configured in `playwright.config.ts`:

- **Base URL**: `http://localhost:3000` (configurable via `FRONTEND_URL` env var)
- **Browsers**: Chromium, Firefox, WebKit, Mobile Chrome, Mobile Safari
- **Timeouts**: 30s per test
- **Retries**: 2 retries on CI, 0 locally
- **Screenshots**: On failure
- **Videos**: On first retry

## Environment Variables

```bash
# Frontend URL (default: http://localhost:3000)
export FRONTEND_URL=http://localhost:3000

# CI mode (enables retries and stricter settings)
export CI=true
```

## Test Structure

### Dashboard Tests (10 tests)

- ✓ Dashboard loads successfully
- ✓ Portfolio summary cards display
- ✓ Bot status table displays
- ✓ Recent trades feed displays
- ✓ Performance chart renders
- ✓ Loading states work
- ✓ API errors handled gracefully
- ✓ Manual refresh works
- ✓ Profit/loss formatting correct
- ✓ Bot status indicators work

### Consensus Tests (12 tests)

- ✓ Consensus page loads
- ✓ Generation form displays
- ✓ Signal generation works
- ✓ Vote breakdown visualization
- ✓ Provider responses display
- ✓ Agreement score shows
- ✓ Confidence metrics display
- ✓ Provider health status
- ✓ Consensus reasoning shows
- ✓ Performance metrics display
- ✓ Error handling works
- ✓ Loading states work

### Navigation Tests (13 tests)

- ✓ Navigate to dashboard
- ✓ Navigate to consensus
- ✓ Navigate back to dashboard
- ✓ Browser back button works
- ✓ Browser forward button works
- ✓ Active nav item highlighted
- ✓ Deep linking works
- ✓ Query parameters preserved
- ✓ Nav menu on all pages
- ✓ Invalid routes handled
- ✓ Nav state maintained
- ✓ Keyboard navigation works
- ✓ Scroll position preserved

### Responsive Tests (15+ tests)

- ✓ Mobile layout adapts
- ✓ Hamburger menu on mobile
- ✓ Cards stack vertically on mobile
- ✓ No horizontal scroll on mobile
- ✓ Desktop elements hidden on mobile
- ✓ Tables scrollable on mobile
- ✓ Tablet layout optimized
- ✓ 2-column grid on tablet
- ✓ Tablet navigation works
- ✓ Desktop layout full width
- ✓ Horizontal nav on desktop
- ✓ Mobile menu hidden on desktop
- ✓ Multi-column grid on desktop
- ✓ Touch interactions work
- ✓ Font sizes readable
- ✓ Touch targets sufficient

## Working with Stubs

These tests are designed to work both:

1. **With a real frontend** - Full integration testing against actual Next.js app
2. **As stubs** - Tests use soft assertions and graceful fallbacks when frontend is not implemented

### API Mocking

All tests mock backend API responses using Playwright's route mocking:

```typescript
await page.route('**/api/v1/portfolio/summary', async route => {
  await route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ /* mock data */ })
  });
});
```

This allows tests to run independently of the backend.

### Soft Assertions

Tests use `expect.soft()` for assertions that should pass when frontend is ready but won't fail if elements aren't implemented yet:

```typescript
await expect.soft(element).toBeVisible();
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: 18

      - name: Install dependencies
        run: cd tests/e2e && npm install

      - name: Install Playwright browsers
        run: cd tests/e2e && npx playwright install --with-deps

      - name: Run E2E tests
        run: cd tests/e2e && npm test
        env:
          CI: true

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: tests/e2e/playwright-report/
```

## Debugging Tests

### UI Mode (Recommended)

```bash
npm run test:ui
```

This opens an interactive UI where you can:
- See test execution step-by-step
- Inspect DOM at each step
- View network requests
- Time travel through test execution

### Debug Mode

```bash
npm run test:debug
```

Opens Playwright Inspector for debugging individual tests.

### Codegen Mode

Generate new tests by recording browser interactions:

```bash
npm run codegen
```

## Best Practices

1. **Use data-testid attributes** in frontend components for reliable selectors
2. **Mock API responses** to avoid backend dependencies
3. **Use soft assertions** for progressive enhancement
4. **Test user workflows**, not implementation details
5. **Keep tests isolated** - each test should be independent
6. **Use page objects** for complex interactions (TODO for future enhancement)

## Troubleshooting

### Tests timing out

- Increase timeout in `playwright.config.ts`
- Check if frontend is running at correct URL
- Use `--debug` flag to see what's happening

### Frontend not found

- Ensure frontend is running: `cd frontend && npm run dev`
- Check `FRONTEND_URL` environment variable
- Tests will gracefully skip assertions if frontend not ready

### Browser not installed

```bash
npx playwright install chromium
```

### Permission errors on Linux

```bash
sudo npx playwright install-deps
```

## Future Enhancements

- [ ] Page Object Model for better test organization
- [ ] Visual regression testing with screenshots
- [ ] Performance testing (Lighthouse integration)
- [ ] Accessibility testing (axe-core integration)
- [ ] API contract testing
- [ ] Load testing with multiple concurrent users

## Contributing

When adding new tests:

1. Follow existing test structure
2. Use descriptive test names
3. Mock all API calls
4. Add soft assertions for optional features
5. Test both happy path and error scenarios
6. Update this README with new test descriptions

## Resources

- [Playwright Documentation](https://playwright.dev)
- [Next.js Testing Guide](https://nextjs.org/docs/testing)
- [Testing Best Practices](https://playwright.dev/docs/best-practices)
