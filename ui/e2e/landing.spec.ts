import { test, expect } from '@playwright/test';

test.describe('Landing Page', () => {
  test('displays hero section with Janus branding', async ({ page }) => {
    await page.goto('/');

    // Verify page title
    await expect(page).toHaveTitle(/Janus/);

    // Verify hero headline
    const heroHeadline = page.locator('h1:has-text("JANUS")');
    await expect(heroHeadline).toBeVisible();

    // Verify tagline (using exact text match to avoid footer duplicate)
    const tagline = page.getByText('The Open Intelligence Rodeo', { exact: true });
    await expect(tagline).toBeVisible();

    // Verify hero image
    const heroImage = page.locator('img[alt="Janus riding an iridescent bull"]');
    await expect(heroImage).toBeVisible();
  });

  test('navigation works correctly', async ({ page }) => {
    await page.goto('/');

    // Verify navigation links exist
    const navLinks = page.locator('nav');
    await expect(navLinks.locator('a:has-text("Home")')).toBeVisible();
    await expect(navLinks.locator('a:has-text("Chat")')).toBeVisible();
    await expect(navLinks.locator('a:has-text("Competition")')).toBeVisible();
    await expect(navLinks.locator('a:has-text("Marketplace")')).toBeVisible();
  });

  test('CTA button navigates to chat page', async ({ page }) => {
    await page.goto('/');

    // Click the primary CTA
    const ctaButton = page.locator('main a:has-text("Janus Chat")').first();
    await expect(ctaButton).toBeVisible();
    await ctaButton.click();

    // Verify navigation to chat page
    await expect(page).toHaveURL('/chat');
  });

  test('API section is visible', async ({ page }) => {
    await page.goto('/');

    const apiSection = page.locator('text=Drop-in API for intelligence builders');
    await expect(apiSection).toBeVisible();

    const codeBlock = page.locator('pre code');
    await expect(codeBlock.first()).toContainText('/v1/chat/completions');
  });

  test('feature cards are displayed', async ({ page }) => {
    await page.goto('/');

    // Verify feature cards section
    const featureSection = page.locator('text=Why Janus?');
    await expect(featureSection).toBeVisible();

    // Verify all three feature cards
    await expect(page.locator('text=Anything In, Anything Out')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Intelligence Rodeo' })).toBeVisible();
    await expect(page.locator('text=Build & Earn')).toBeVisible();
  });

  test('how it works section is displayed', async ({ page }) => {
    await page.goto('/');

    // Verify how it works section
    const howItWorks = page.locator('text=How It Works');
    await expect(howItWorks).toBeVisible();

    // Verify all three steps
    await expect(page.locator('h3:has-text("Submit")')).toBeVisible();
    await expect(page.locator('h3:has-text("Compete")')).toBeVisible();
    await expect(page.locator('h3:has-text("Win")')).toBeVisible();
  });

  test('flexibility and ideals sections are displayed', async ({ page }) => {
    await page.goto('/');

    await expect(page.getByRole('heading', { name: 'Any Stack. Any Approach.' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Built on Bittensor Ideals' })).toBeVisible();
  });

  test('footer is displayed with links', async ({ page }) => {
    await page.goto('/');

    // Verify footer exists
    const footer = page.locator('footer');
    await expect(footer).toBeVisible();

    // Verify powered by section
    await expect(footer.locator('text=Powered by')).toBeVisible();
    await expect(footer.getByText('Chutes', { exact: true })).toBeVisible();
  });

  test('responsive mobile menu works', async ({ page }) => {
    // Set viewport to mobile size
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto('/');

    // Verify hamburger menu button exists on mobile
    const menuButton = page.locator('button[aria-label="Toggle menu"]');
    await expect(menuButton).toBeVisible();

    // Click to open mobile menu
    await menuButton.click();

    // Verify mobile nav links are visible
    const mobileNav = page.locator('nav.flex.flex-col');
    await expect(mobileNav.getByRole('link', { name: 'Chat', exact: true })).toBeVisible();
  });
});
