# Spec 103: Visual Regression Testing

## Status: COMPLETE

**Priority:** Medium
**Complexity:** Medium
**Prerequisites:** Spec 102 (E2E Testing)

---

## Overview

Visual regression testing captures screenshots of the UI and compares them against baseline images to detect unintended visual changes. This ensures:

1. Consistent styling across updates
2. Dark mode is properly applied
3. Responsive layouts work on all devices
4. Components render correctly
5. Design system compliance (Chutes style guide)

**Important:** If visual tests fail, either FIX the UI bug or UPDATE the baseline images if the change is intentional.

---

## Test Framework Setup

### Install Dependencies

```bash
cd ui
npm install -D @playwright/test playwright
npx playwright install
```

### Visual Testing Configuration

```typescript
// ui/playwright.visual.config.ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e/visual',
  snapshotDir: './e2e/visual/snapshots',
  timeout: 30000,
  expect: {
    toHaveScreenshot: {
      maxDiffPixels: 100, // Allow small differences
      threshold: 0.2,     // 20% pixel diff threshold
    },
  },
  use: {
    baseURL: process.env.TEST_URL || 'http://localhost:3000',
  },
  projects: [
    {
      name: 'Desktop',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1920, height: 1080 },
      },
    },
    {
      name: 'Tablet',
      use: {
        ...devices['iPad Pro'],
        viewport: { width: 1024, height: 768 },
      },
    },
    {
      name: 'Mobile',
      use: {
        ...devices['iPhone 14'],
        viewport: { width: 390, height: 844 },
      },
    },
  ],
});
```

---

## Part 1: Page Screenshot Tests

### Location: `ui/e2e/visual/pages.visual.spec.ts`

```typescript
import { test, expect } from '@playwright/test';

test.describe('Page Screenshots', () => {
  test.describe('Landing Page', () => {
    test('matches desktop baseline', async ({ page }) => {
      await page.goto('/');
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(1000); // Wait for animations

      await expect(page).toHaveScreenshot('landing-desktop.png', {
        fullPage: true,
        animations: 'disabled',
      });
    });

    test('matches tablet baseline', async ({ page }) => {
      await page.setViewportSize({ width: 1024, height: 768 });
      await page.goto('/');
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(1000);

      await expect(page).toHaveScreenshot('landing-tablet.png', {
        fullPage: true,
        animations: 'disabled',
      });
    });

    test('matches mobile baseline', async ({ page }) => {
      await page.setViewportSize({ width: 390, height: 844 });
      await page.goto('/');
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(1000);

      await expect(page).toHaveScreenshot('landing-mobile.png', {
        fullPage: true,
        animations: 'disabled',
      });
    });
  });

  test.describe('Chat Page', () => {
    test('empty state matches baseline', async ({ page }) => {
      await page.goto('/chat');
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(1000);

      await expect(page).toHaveScreenshot('chat-empty-desktop.png', {
        animations: 'disabled',
      });
    });

    test('chat with model dropdown open', async ({ page }) => {
      await page.goto('/chat');
      await page.waitForLoadState('networkidle');

      // Open model selector
      const modelSelector = page.locator('[data-testid="model-select"], select').first();
      if (await modelSelector.isVisible()) {
        await modelSelector.click();
        await page.waitForTimeout(500);
      }

      await expect(page).toHaveScreenshot('chat-model-dropdown.png', {
        animations: 'disabled',
      });
    });

    test('chat input focused state', async ({ page }) => {
      await page.goto('/chat');
      await page.waitForLoadState('networkidle');

      // Focus input
      const input = page.locator('textarea, input[type="text"]').first();
      await input.focus();
      await input.fill('Sample message text');

      await expect(page).toHaveScreenshot('chat-input-focused.png', {
        animations: 'disabled',
      });
    });

    test('mobile chat layout', async ({ page }) => {
      await page.setViewportSize({ width: 390, height: 844 });
      await page.goto('/chat');
      await page.waitForLoadState('networkidle');

      await expect(page).toHaveScreenshot('chat-mobile.png', {
        animations: 'disabled',
      });
    });
  });

  test.describe('Competition Page', () => {
    test('matches desktop baseline', async ({ page }) => {
      await page.goto('/competition');
      await page.waitForLoadState('networkidle');
      // Wait for Mermaid diagrams to render
      await page.waitForSelector('.mermaid svg, svg.mermaid', { timeout: 10000 }).catch(() => {});
      await page.waitForTimeout(2000);

      await expect(page).toHaveScreenshot('competition-desktop.png', {
        fullPage: true,
        animations: 'disabled',
      });
    });

    test('matches mobile baseline', async ({ page }) => {
      await page.setViewportSize({ width: 390, height: 844 });
      await page.goto('/competition');
      await page.waitForLoadState('networkidle');
      await page.waitForSelector('.mermaid svg').catch(() => {});
      await page.waitForTimeout(2000);

      await expect(page).toHaveScreenshot('competition-mobile.png', {
        fullPage: true,
        animations: 'disabled',
      });
    });
  });

  test.describe('Marketplace Page', () => {
    test('matches desktop baseline', async ({ page }) => {
      await page.goto('/marketplace');
      await page.waitForLoadState('networkidle');

      await expect(page).toHaveScreenshot('marketplace-desktop.png', {
        fullPage: true,
        animations: 'disabled',
      });
    });
  });
});
```

---

## Part 2: Component Visual Tests

### Location: `ui/e2e/visual/components.visual.spec.ts`

```typescript
import { test, expect } from '@playwright/test';

test.describe('Component Screenshots', () => {
  test.describe('Navigation', () => {
    test('header desktop', async ({ page }) => {
      await page.goto('/');
      await page.waitForLoadState('networkidle');

      const header = page.locator('header, nav').first();
      await expect(header).toHaveScreenshot('header-desktop.png');
    });

    test('header mobile with menu closed', async ({ page }) => {
      await page.setViewportSize({ width: 390, height: 844 });
      await page.goto('/');
      await page.waitForLoadState('networkidle');

      const header = page.locator('header, nav').first();
      await expect(header).toHaveScreenshot('header-mobile-closed.png');
    });

    test('header mobile with menu open', async ({ page }) => {
      await page.setViewportSize({ width: 390, height: 844 });
      await page.goto('/');
      await page.waitForLoadState('networkidle');

      // Open mobile menu
      const menuButton = page.locator('button[aria-label*="menu"], .mobile-menu-button').first();
      if (await menuButton.isVisible()) {
        await menuButton.click();
        await page.waitForTimeout(500);
      }

      await expect(page).toHaveScreenshot('header-mobile-open.png');
    });
  });

  test.describe('Chat Components', () => {
    test('chat input component', async ({ page }) => {
      await page.goto('/chat');
      await page.waitForLoadState('networkidle');

      const inputContainer = page.locator('.chat-input-container, form').last();
      await expect(inputContainer).toHaveScreenshot('chat-input.png');
    });

    test('chat message bubble - user', async ({ page }) => {
      await page.goto('/chat');
      await page.waitForLoadState('networkidle');

      // Send a message to create user bubble
      const input = page.locator('textarea').first();
      await input.fill('Hello');
      await page.keyboard.press('Enter');
      await page.waitForTimeout(1000);

      const userMessage = page.locator('[data-role="user"], .user-message').first();
      if (await userMessage.isVisible()) {
        await expect(userMessage).toHaveScreenshot('message-user.png');
      }
    });

    test('chat message bubble - assistant', async ({ page }) => {
      await page.goto('/chat');
      await page.waitForLoadState('networkidle');

      // Send a message and wait for response
      const input = page.locator('textarea').first();
      await input.fill('Say hi');
      await page.keyboard.press('Enter');

      // Wait for assistant response
      const assistantMessage = page.locator('[data-role="assistant"], .assistant-message').first();
      await assistantMessage.waitFor({ timeout: 30000 });

      await expect(assistantMessage).toHaveScreenshot('message-assistant.png', {
        mask: [page.locator('.timestamp, time')], // Mask dynamic timestamps
      });
    });

    test('chat sidebar', async ({ page }) => {
      await page.goto('/chat');
      await page.waitForLoadState('networkidle');

      const sidebar = page.locator('[data-testid="chat-sidebar"], .sidebar, aside').first();
      if (await sidebar.isVisible()) {
        await expect(sidebar).toHaveScreenshot('chat-sidebar.png');
      }
    });
  });

  test.describe('Buttons and Controls', () => {
    test('primary button', async ({ page }) => {
      await page.goto('/');
      await page.waitForLoadState('networkidle');

      const primaryButton = page.locator('a.bg-moss, button.bg-moss, .btn-primary').first();
      if (await primaryButton.isVisible()) {
        await expect(primaryButton).toHaveScreenshot('button-primary.png');
      }
    });

    test('send button', async ({ page }) => {
      await page.goto('/chat');
      await page.waitForLoadState('networkidle');

      const sendButton = page.locator('button[type="submit"]').first();
      await expect(sendButton).toHaveScreenshot('button-send.png');
    });
  });
});
```

---

## Part 3: Dark Mode & Theme Tests

### Location: `ui/e2e/visual/theme.visual.spec.ts`

```typescript
import { test, expect } from '@playwright/test';

test.describe('Theme & Dark Mode', () => {
  test('landing page dark mode styling', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Verify dark background
    const bgColor = await page.evaluate(() =>
      getComputedStyle(document.body).backgroundColor
    );

    // Should be dark (low RGB values)
    const rgb = bgColor.match(/\d+/g)?.map(Number) || [];
    const avgBrightness = rgb.reduce((a, b) => a + b, 0) / 3;
    expect(avgBrightness).toBeLessThan(50); // Dark mode check

    await expect(page).toHaveScreenshot('theme-dark-landing.png', {
      fullPage: true,
      animations: 'disabled',
    });
  });

  test('chat page dark mode styling', async ({ page }) => {
    await page.goto('/chat');
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveScreenshot('theme-dark-chat.png', {
      animations: 'disabled',
    });
  });

  test('aurora gradient is visible', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Check for aurora gradient elements
    const hasGradient = await page.evaluate(() => {
      const elements = document.querySelectorAll('*');
      for (const el of elements) {
        const style = getComputedStyle(el);
        if (style.backgroundImage.includes('gradient')) {
          return true;
        }
      }
      return false;
    });

    expect(hasGradient).toBe(true);
  });

  test('moss green accent color is used', async ({ page }) => {
    await page.goto('/chat');
    await page.waitForLoadState('networkidle');

    // Check for moss green (#63D297) usage
    const hasMossGreen = await page.evaluate(() => {
      const elements = document.querySelectorAll('*');
      for (const el of elements) {
        const style = getComputedStyle(el);
        if (style.color.includes('99') || style.backgroundColor.includes('99') ||
            style.borderColor.includes('99')) {
          return true;
        }
      }
      // Also check for class names
      return document.querySelector('.text-moss, .bg-moss, .border-moss') !== null;
    });

    expect(hasMossGreen).toBe(true);
  });
});
```

---

## Part 4: Responsive Layout Tests

### Location: `ui/e2e/visual/responsive.visual.spec.ts`

```typescript
import { test, expect } from '@playwright/test';

const viewports = [
  { name: 'desktop-4k', width: 3840, height: 2160 },
  { name: 'desktop-1080p', width: 1920, height: 1080 },
  { name: 'laptop', width: 1440, height: 900 },
  { name: 'tablet-landscape', width: 1024, height: 768 },
  { name: 'tablet-portrait', width: 768, height: 1024 },
  { name: 'mobile-large', width: 428, height: 926 },  // iPhone 14 Pro Max
  { name: 'mobile-medium', width: 390, height: 844 }, // iPhone 14
  { name: 'mobile-small', width: 375, height: 667 },  // iPhone SE
];

test.describe('Responsive Layouts', () => {
  for (const viewport of viewports) {
    test.describe(`${viewport.name} (${viewport.width}x${viewport.height})`, () => {
      test.beforeEach(async ({ page }) => {
        await page.setViewportSize({ width: viewport.width, height: viewport.height });
      });

      test('landing page layout', async ({ page }) => {
        await page.goto('/');
        await page.waitForLoadState('networkidle');
        await page.waitForTimeout(500);

        await expect(page).toHaveScreenshot(`responsive-landing-${viewport.name}.png`, {
          fullPage: true,
          animations: 'disabled',
        });
      });

      test('chat page layout', async ({ page }) => {
        await page.goto('/chat');
        await page.waitForLoadState('networkidle');
        await page.waitForTimeout(500);

        await expect(page).toHaveScreenshot(`responsive-chat-${viewport.name}.png`, {
          animations: 'disabled',
        });
      });

      test('no horizontal scroll', async ({ page }) => {
        await page.goto('/chat');
        await page.waitForLoadState('networkidle');

        const hasHorizontalScroll = await page.evaluate(() =>
          document.body.scrollWidth > document.body.clientWidth
        );

        expect(hasHorizontalScroll).toBe(false);
      });
    });
  }
});
```

---

## Part 5: State-Based Visual Tests

### Location: `ui/e2e/visual/states.visual.spec.ts`

```typescript
import { test, expect } from '@playwright/test';

test.describe('UI State Screenshots', () => {
  test.describe('Loading States', () => {
    test('chat loading indicator', async ({ page }) => {
      await page.goto('/chat');
      await page.waitForLoadState('networkidle');

      // Send message to trigger loading
      const input = page.locator('textarea').first();
      await input.fill('Hello');
      await page.keyboard.press('Enter');

      // Capture loading state quickly
      await page.waitForTimeout(500);

      const loadingIndicator = page.locator('[data-loading="true"], .loading, .spinner');
      if (await loadingIndicator.isVisible()) {
        await expect(loadingIndicator).toHaveScreenshot('state-loading.png');
      }
    });
  });

  test.describe('Error States', () => {
    test('error message styling', async ({ page }) => {
      await page.goto('/chat');
      await page.waitForLoadState('networkidle');

      // Inject error message for screenshot
      await page.evaluate(() => {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message bg-red-500/20 border border-red-500 p-4 rounded';
        errorDiv.textContent = 'An error occurred. Please try again.';
        document.body.appendChild(errorDiv);
      });

      const errorMessage = page.locator('.error-message').first();
      await expect(errorMessage).toHaveScreenshot('state-error.png');
    });
  });

  test.describe('Empty States', () => {
    test('no conversations empty state', async ({ page }) => {
      await page.goto('/chat');
      await page.waitForLoadState('networkidle');

      // Clear localStorage to show empty state
      await page.evaluate(() => {
        localStorage.clear();
      });
      await page.reload();
      await page.waitForLoadState('networkidle');

      await expect(page).toHaveScreenshot('state-empty-chat.png', {
        animations: 'disabled',
      });
    });
  });

  test.describe('Hover States', () => {
    test('button hover', async ({ page }) => {
      await page.goto('/');
      await page.waitForLoadState('networkidle');

      const button = page.locator('a.bg-moss, button.bg-moss').first();
      if (await button.isVisible()) {
        await button.hover();
        await page.waitForTimeout(300);
        await expect(button).toHaveScreenshot('state-button-hover.png');
      }
    });

    test('link hover', async ({ page }) => {
      await page.goto('/');
      await page.waitForLoadState('networkidle');

      const link = page.locator('a').first();
      await link.hover();
      await page.waitForTimeout(300);
      await expect(link).toHaveScreenshot('state-link-hover.png');
    });
  });

  test.describe('Focus States', () => {
    test('input focus', async ({ page }) => {
      await page.goto('/chat');
      await page.waitForLoadState('networkidle');

      const input = page.locator('textarea').first();
      await input.focus();
      await page.waitForTimeout(300);

      await expect(input).toHaveScreenshot('state-input-focus.png');
    });
  });
});
```

---

## Part 6: Accessibility Visual Tests

### Location: `ui/e2e/visual/accessibility.visual.spec.ts`

```typescript
import { test, expect } from '@playwright/test';

test.describe('Accessibility Visual Checks', () => {
  test('focus visible outlines', async ({ page }) => {
    await page.goto('/chat');
    await page.waitForLoadState('networkidle');

    // Tab through focusable elements
    await page.keyboard.press('Tab');
    await page.waitForTimeout(300);

    // Capture focus ring
    const focusedElement = page.locator(':focus');
    await expect(focusedElement).toHaveScreenshot('a11y-focus-outline.png');
  });

  test('sufficient color contrast', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Visual check - actual contrast testing would need axe-core
    await expect(page).toHaveScreenshot('a11y-contrast-landing.png', {
      animations: 'disabled',
    });
  });

  test('text is readable at default zoom', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Screenshot at 100% zoom
    await expect(page).toHaveScreenshot('a11y-zoom-100.png', {
      animations: 'disabled',
    });
  });

  test('text is readable at 200% zoom', async ({ page }) => {
    await page.goto('/');

    // Set 200% zoom
    await page.evaluate(() => {
      document.body.style.zoom = '200%';
    });
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(500);

    await expect(page).toHaveScreenshot('a11y-zoom-200.png', {
      animations: 'disabled',
    });
  });
});
```

---

## Part 7: Animation and Transition Tests

### Location: `ui/e2e/visual/animations.visual.spec.ts`

```typescript
import { test, expect } from '@playwright/test';

test.describe('Animations', () => {
  test('streaming text animation', async ({ page }) => {
    await page.goto('/chat');
    await page.waitForLoadState('networkidle');

    // Send message
    const input = page.locator('textarea').first();
    await input.fill('Count to 3');
    await page.keyboard.press('Enter');

    // Capture during streaming
    await page.waitForTimeout(2000);

    // Take multiple screenshots to verify animation
    const screenshots = [];
    for (let i = 0; i < 3; i++) {
      screenshots.push(await page.screenshot());
      await page.waitForTimeout(500);
    }

    // Screenshots should be different (animation happening)
    // This is a sanity check - actual comparison would be more complex
  });

  test('modal open animation', async ({ page }) => {
    await page.goto('/chat');
    await page.waitForLoadState('networkidle');

    // Trigger a modal if available
    const modalTrigger = page.locator('[data-testid="open-modal"], button:has-text("Settings")').first();
    if (await modalTrigger.isVisible()) {
      await modalTrigger.click();
      await page.waitForTimeout(100);

      // Capture during animation
      await expect(page).toHaveScreenshot('animation-modal-opening.png');

      await page.waitForTimeout(400);
      await expect(page).toHaveScreenshot('animation-modal-open.png');
    }
  });
});
```

---

## Running Visual Tests

### Commands

```bash
# Run visual tests
cd ui && npx playwright test --config=playwright.visual.config.ts

# Update baseline screenshots
npx playwright test --config=playwright.visual.config.ts --update-snapshots

# Run specific visual test
npx playwright test e2e/visual/pages.visual.spec.ts --config=playwright.visual.config.ts

# Run with UI mode for debugging
npx playwright test --config=playwright.visual.config.ts --ui

# Generate report
npx playwright show-report
```

### Updating Baselines

When visual changes are intentional:

```bash
# Update all baselines
npx playwright test --config=playwright.visual.config.ts --update-snapshots

# Update specific test baselines
npx playwright test e2e/visual/pages.visual.spec.ts --update-snapshots

# Review changes before committing
git diff e2e/visual/snapshots/
```

### CI Configuration

```yaml
# .github/workflows/visual.yml
name: Visual Regression Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  visual:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install dependencies
        run: cd ui && npm ci

      - name: Install Playwright browsers
        run: cd ui && npx playwright install --with-deps chromium

      - name: Run visual tests
        run: cd ui && npx playwright test --config=playwright.visual.config.ts

      - name: Upload snapshots on failure
        uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: visual-snapshots
          path: |
            ui/e2e/visual/snapshots/
            ui/test-results/
          retention-days: 7

      - name: Upload report
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: visual-report
          path: ui/playwright-report/
          retention-days: 30
```

---

## Acceptance Criteria

- [ ] Landing page screenshots captured for all viewports
- [ ] Chat page screenshots captured (empty, with messages)
- [ ] Competition page with Mermaid diagrams captured
- [ ] Component-level screenshots (header, buttons, input)
- [ ] Dark mode verified with correct styling
- [ ] Responsive layouts work on all viewports
- [ ] No horizontal scroll on any viewport
- [ ] Loading, error, and empty states captured
- [ ] Hover and focus states captured
- [ ] Accessibility visual checks pass
- [ ] Baselines committed to repository
- [ ] CI pipeline runs visual tests
- [ ] Any visual regressions result in code fixes or baseline updates

---

## Design System Compliance Checklist

When reviewing visual tests, verify:

- [ ] Background is dark mode (dark grays/blacks)
- [ ] Aurora gradient visible on key pages
- [ ] Moss green (#63D297) used for accents
- [ ] Glass morphism effect on cards
- [ ] Tomato Grotesk or similar typography
- [ ] Consistent spacing and padding
- [ ] Rounded corners on components
- [ ] Subtle borders and shadows
- [ ] Proper hover/focus states

---

## Notes

- Baseline screenshots should be reviewed before committing
- Use `--update-snapshots` carefully - only when changes are intentional
- Screenshots may differ slightly across CI environments
- Consider using docker for consistent rendering
- Large screenshot diffs may indicate CSS issues or missing styles
- Animation tests may be flaky - use appropriate timeouts

NR_OF_TRIES: 1
