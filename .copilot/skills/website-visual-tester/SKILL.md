# Website Visual Tester Skill

## Overview
This skill provides comprehensive visual testing capabilities for websites using Playwright's built-in visual regression testing. It enables automated screenshot comparison, baseline management, and cross-browser visual validation.

## When to Use
- Visual regression testing for UI changes
- Cross-browser visual consistency validation
- Design system component verification
- Responsive design testing across viewports
- Automated visual QA in CI/CD pipelines

## Core Concepts

### Visual Regression Testing with Playwright
Playwright Test includes `toHaveScreenshot()` for pixel-perfect visual comparisons:

```typescript
import { test, expect } from '@playwright/test';

test('homepage visual regression', async ({ page }) => {
  await page.goto('https://example.com');
  await expect(page).toHaveScreenshot('homepage.png');
});
```

### Snapshot Management
- **Baseline screenshots**: Generated on first run, stored in `{test-file}-snapshots/` directory
- **Platform-specific**: Separate baselines per browser/OS (chromium-darwin, firefox-linux, etc.)
- **Update workflow**: Use `--update-snapshots` flag to refresh baselines

## Key Commands

### Playwright CLI (Recommended for Agents)
```bash
# Install globally
npm install -g @playwright/cli@latest

# Install visual testing skills
playwright-cli install --skills

# Visual testing workflow
playwright-cli open https://example.com --headed
playwright-cli snapshot --filename=baseline.yaml
playwright-cli screenshot --filename=current.png
```

### Playwright Test Commands
```bash
# Run visual tests
npx playwright test --project=chromium

# Update snapshots when UI changes intentionally
npx playwright test --update-snapshots

# Run with specific browser
npx playwright test --project=firefox

# Generate report
npx playwright show-report
```

## Configuration

### playwright.config.ts for Visual Testing
```typescript
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/visual',
  snapshotDir: './tests/visual/snapshots',
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit', use: { ...devices['Desktop Safari'] } },
    { name: 'mobile-chrome', use: { ...devices['Pixel 5'] } },
    { name: 'mobile-safari', use: { ...devices['iPhone 12'] } },
  ],
  expect: {
    toHaveScreenshot: {
      maxDiffPixels: 100,
      threshold: 0.2,
    },
  },
});
```

### Custom Snapshot Options
```typescript
// Per-test customization
await expect(page).toHaveScreenshot('custom-name.png', {
  maxDiffPixels: 50,
  threshold: 0.1,
  stylePath: './tests/visual/screenshot.css', // Hide dynamic elements
  animations: 'disabled',
});

// Mask dynamic regions
await expect(page).toHaveScreenshot('dashboard.png', {
  mask: [page.locator('.timestamp'), page.locator('.user-avatar')],
});
```

## Advanced Patterns

### Component-Level Visual Testing
```typescript
test('button component states', async ({ page }) => {
  await page.goto('/storybook/iframe.html?id=button--primary');
  
  // Default state
  await expect(page.locator('button')).toHaveScreenshot('button-default.png');
  
  // Hover state
  await page.locator('button').hover();
  await expect(page.locator('button')).toHaveScreenshot('button-hover.png');
  
  // Disabled state
  await page.locator('button[disabled]').toHaveScreenshot('button-disabled.png');
});
```

### Responsive Visual Testing
```typescript
const viewports = [
  { name: 'mobile', width: 375, height: 667 },
  { name: 'tablet', width: 768, height: 1024 },
  { name: 'desktop', width: 1280, height: 720 },
  { name: 'wide', width: 1920, height: 1080 },
];

for (const vp of viewports) {
  test(`homepage at ${vp.name}`, async ({ page }) => {
    await page.setViewportSize({ width: vp.width, height: vp.height });
    await page.goto('/');
    await expect(page).toHaveScreenshot(`homepage-${vp.name}.png`);
  });
}
```

### Full Page vs Element Screenshots
```typescript
// Full page
await expect(page).toHaveScreenshot('full-page.png', { fullPage: true });

// Specific element
await expect(page.locator('#main-content')).toHaveScreenshot('main-content.png');

// Element with padding
await expect(page.locator('.card')).toHaveScreenshot('card.png', {
  clip: { x: 0, y: 0, width: 400, height: 300 },
});
```

## CI/CD Integration

### GitHub Actions Workflow
```yaml
# .github/workflows/visual-tests.yml
name: Visual Regression Tests

on: [push, pull_request]

jobs:
  visual-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: npm ci
      - run: npx playwright install --with-deps
      - run: npx playwright test --project=chromium
      - uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: visual-test-screenshots
          path: test-results/
```

### Baseline Management Strategy
1. **Commit baselines** to repository (snapshots directory)
2. **Review changes** in PR diffs for screenshot updates
3. **Approve intentional changes** via `--update-snapshots` in CI
4. **Separate baselines** per browser/OS combination

## Best Practices

### Deterministic Screenshots
- Disable animations: `animations: 'disabled'`
- Mask dynamic content: timestamps, user data, ads
- Use consistent test data and seeded randomness
- Run in identical environments (CI containers)

### Performance Optimization
- Use `--depth=N` for partial snapshots
- Target specific elements instead of full pages
- Reuse browser contexts across tests
- Parallelize across browsers/projects

### Maintenance
- Regular baseline review and cleanup
- Document visual testing strategy
- Train team on snapshot update workflow
- Monitor flaky visual tests

## Troubleshooting

### Common Issues
| Issue | Solution |
|-------|----------|
| Font rendering differences | Use same OS/container for baseline and test |
| Anti-aliasing variations | Set `threshold` and `maxDiffPixels` appropriately |
| Dynamic content | Use `mask` or `stylePath` to hide volatile elements |
| Timing issues | Wait for network idle, animations, fonts loaded |

### Debug Commands
```bash
# Debug specific test
npx playwright test --debug visual/homepage.spec.ts

# Show trace viewer
npx playwright show-trace trace.zip

# Visual diff locally
npx playwright test --update-snapshots --project=chromium
```

## Cleanup & Maintenance

### Automatic Cleanup (Recommended)
Configure Playwright to automatically clean up test artifacts after runs:

```typescript
// playwright.config.ts
import { existsSync, rmSync } from 'fs';
import { join } from 'path';

const TEST_ARTIFACTS_DIRS = [
  'test-results',
  'playwright-report',
];

function cleanupTestArtifacts() {
  for (const dir of TEST_ARTIFACTS_DIRS) {
    const fullPath = join(process.cwd(), dir);
    if (existsSync(fullPath)) {
      rmSync(fullPath, { recursive: true, force: true });
      console.log(`Cleaned up: ${dir}`);
    }
  }
}

export default defineConfig({
  // ... other config
  globalTeardown: async () => {
    cleanupTestArtifacts();
  },
});
```

### Manual Cleanup Commands
```bash
# Clean up test artifacts
rm -rf test-results playwright-report

# Clean up and regenerate baselines
npx playwright test --update-snapshots

# Clean node_modules and reinstall (if needed)
rm -rf node_modules package-lock.json && npm install
```

### CI/CD Integration
```yaml
# .github/workflows/visual-tests.yml
- name: Run visual tests
  run: npx playwright test

- name: Cleanup artifacts
  if: always()
  run: |
    rm -rf test-results playwright-report
```

## Resources
- [Playwright Visual Comparisons](https://playwright.dev/docs/test-snapshots)
- [Playwright CLI with Skills](https://github.com/microsoft/playwright-cli)
- [Playwright MCP Server](https://github.com/microsoft/playwright-mcp)
- [Pixelmatch Library](https://github.com/mapbox/pixelmatch)

## Related Skills
- `playwright-cli` - CLI-based browser automation
- `playwright-mcp` - MCP server for persistent browser sessions
- `building-data-apps` - For visual dashboard testing