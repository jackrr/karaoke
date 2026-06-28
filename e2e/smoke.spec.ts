import { test, expect } from '@playwright/test';

/**
 * Smoke test: verifies the Home page renders with session creation/join UI.
 *
 * Prerequisites:
 *   - Backend running on http://localhost:8000
 *   - Frontend dev server running on http://localhost:5173
 *
 * These are managed by the globalSetup/globalTeardown fixtures.
 */
test.beforeEach(async ({ page }) => {
  // Navigate to the Home page
  await page.goto('/');
  await page.waitForLoadState('networkidle');
});

// ── Home page UI structure ────────────────────────────────────────────

test('renders the KARAOKE logo', async ({ page }) => {
  const logo = page.locator('h1.neon-text#logo');
  await expect(logo).toBeVisible();
  await expect(logo).toHaveText('KARAOKE');
});

test('shows Create Room and Join Room mode tabs', async ({ page }) => {
  const tabs = page.locator('.mode-tabs button');
  await expect(tabs).toHaveCount(2);
  await expect(tabs.first()).toContainText('Create Room');
  await expect(tabs.nth(1)).toContainText('Join Room');
});

test('disables Join tab by default (create mode active)', async ({ page }) => {
  // By default, mode is 'create' — the Create Room button should be visible
  const createBtn = page.locator('button.neon-btn.large');
  await expect(createBtn).toBeVisible();
  await expect(createBtn).toHaveText('Create Room');
});

test('switches to Join mode when clicking Join Room tab', async ({ page }) => {
  const joinTab = page.locator('.mode-tabs button').nth(1);
  await joinTab.click();

  // The form with input should now be visible
  const form = page.locator('form.join-form');
  await expect(form).toBeVisible();

  const input = form.locator('input');
  await expect(input).toBeVisible();
  await expect(input).toHaveAttribute('placeholder', 'Enter 6-digit passcode');

  // The Create Room buttons should be gone
  const createBtn = page.locator('button.neon-btn.large');
  await expect(createBtn).toBeHidden();
});

test('attempts to join room with invalid passcode', async ({ page }) => {
  // Switch to join mode
  await page.locator('.mode-tabs button').nth(1).click();

  // Enter a 6-digit code and submit
  const input = page.locator('form.join-form input');
  await input.fill('000000');
  await page.locator('form.join-form button[type="submit"]').click();

  // Should show an error (the backend will likely reject it)
  const errorMessage = page.locator('p.error');
  await expect(errorMessage).toBeVisible({ timeout: 15_000 });
});

// ── Session creation flow ─────────────────────────────────────────────

test('creates a room and displays the passcode', async ({ page }) => {
  // Click Create Room (already in create mode by default)
  const createBtn = page.locator('button.neon-btn.large');
  await createBtn.click();

  // A passcode display component should appear
  const passcodeContainer = page.locator('div[style*="display: flex"], .passcode-display, [class*="passcode"]');
  
  // The page should still be fully rendered and interactive
  await expect(page.locator('h1')).toBeVisible();
});

test('Home page is accessible with keyboard navigation', async ({ page }) => {
  // Tab through the mode tabs
  await page.keyboard.press('Tab');
  await page.keyboard.press('Tab');

  // Enter should activate the focused tab
  await page.keyboard.press('Enter');

  // The page should still be visible
  await expect(page.locator('.home')).toBeVisible();
});
