import { test, expect, type Page } from '@playwright/test';
import { mockServiceHealth, onlyForProjects } from './utils';

async function waitForMermaid(page: Page) {
  await page.waitForSelector('.mermaid-container svg', { timeout: 10000 });
  await page.waitForTimeout(1500);
}

test.beforeEach(async ({ page }) => {
  await mockServiceHealth(page);
});

test.describe('Mermaid Diagram Edge Labels', () => {
  test('sequence diagram labels are fully visible', async ({ page }, testInfo) => {
    onlyForProjects(testInfo, ['Desktop']);
    test.setTimeout(60000);

    await page.goto('/competition');
    await page.waitForLoadState('networkidle');
    await waitForMermaid(page);

    const sequenceDiagram = page.getByRole('img', {
      name: 'Platform services sequence diagram',
    });

    await expect(sequenceDiagram.locator('svg')).toBeVisible();
    await expect(sequenceDiagram).toHaveScreenshot('sequence-diagram-labels.png', {
      maxDiffPixels: 150,
    });

    const messageTexts = sequenceDiagram.locator('.messageText');
    const count = await messageTexts.count();
    expect(count).toBeGreaterThan(0);

    const checks = Math.min(count, 12);
    for (let i = 0; i < checks; i += 1) {
      const text = messageTexts.nth(i);
      const box = await text.boundingBox();
      if (box) {
        expect(box.width).toBeGreaterThan(30);
      }
    }
  });

  test('flowchart edge labels are visible', async ({ page }, testInfo) => {
    onlyForProjects(testInfo, ['Desktop']);
    test.setTimeout(60000);

    await page.goto('/competition');
    await page.waitForLoadState('networkidle');
    await waitForMermaid(page);

    const flowchart = page.getByRole('img', { name: 'Janus architecture diagram' });

    await expect(flowchart.locator('svg')).toBeVisible();
    await expect(flowchart).toHaveScreenshot('flowchart-labels.png', {
      maxDiffPixels: 150,
    });

    await flowchart.locator('.edgeLabel, .edgePath').first().isVisible();
  });

  test('egress diagram blocked labels are visible', async ({ page }, testInfo) => {
    onlyForProjects(testInfo, ['Desktop']);
    test.setTimeout(60000);

    await page.goto('/competition');
    await page.waitForLoadState('networkidle');
    await waitForMermaid(page);

    const egressDiagram = page.getByRole('img', { name: 'Network egress control diagram' });

    await egressDiagram.scrollIntoViewIfNeeded();
    await expect(egressDiagram).toHaveScreenshot('egress-diagram-labels.png', {
      maxDiffPixels: 150,
    });

    const svgText = await egressDiagram.locator('svg').textContent();
    expect(svgText ?? '').toContain('Blocked');
  });

  test('modal view shows full diagram', async ({ page }, testInfo) => {
    onlyForProjects(testInfo, ['Desktop']);
    test.setTimeout(60000);

    await page.goto('/competition');
    await page.waitForLoadState('networkidle');
    await waitForMermaid(page);

    const sequenceDiagram = page.getByRole('img', {
      name: 'Platform services sequence diagram',
    });

    await sequenceDiagram.scrollIntoViewIfNeeded();
    await sequenceDiagram.click();

    const modal = page.getByRole('dialog', {
      name: 'Platform services sequence diagram',
    });

    await expect(modal).toBeVisible();
    await expect(modal).toHaveScreenshot('sequence-diagram-modal.png', {
      maxDiffPixels: 150,
    });
  });

  test('mobile diagrams scroll without page overflow', async ({ page }, testInfo) => {
    onlyForProjects(testInfo, ['Mobile']);
    test.setTimeout(60000);

    await page.goto('/competition');
    await page.waitForLoadState('networkidle');
    await waitForMermaid(page);

    const sequenceDiagram = page.getByRole('img', {
      name: 'Platform services sequence diagram',
    });

    await sequenceDiagram.scrollIntoViewIfNeeded();

    const wrapper = sequenceDiagram.locator('xpath=..');
    const overflowX = await wrapper.evaluate((element) =>
      getComputedStyle(element).overflowX,
    );

    expect(['auto', 'scroll']).toContain(overflowX);

    const bodyOverflowX = await page.evaluate(
      () => getComputedStyle(document.body).overflowX,
    );

    expect(bodyOverflowX).toBe('hidden');
  });
});
