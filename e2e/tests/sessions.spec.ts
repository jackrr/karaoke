import { test, expect } from '@playwright/test';
import { createSessionViaUI, waitForWebSocketConnected } from './helpers';

test('create session via UI', async ({ page }) => {
  await page.goto('/');
  await createSessionViaUI(page);
  await expect(page).toHaveURL(/\/session\//);
});

test('homepage shows an active session count, not a list of sessions', async ({ page }) => {
  // Create a session first
  await page.goto('/');
  await createSessionViaUI(page);
  await expect(page).toHaveURL(/\/session\//);

  // Navigate back to the homepage
  await page.goto('/');
  // Wait for the count to load (avoid async state where it hasn't populated yet)
  await page.waitForLoadState('networkidle');
  await expect(page.getByText(/active session/)).toBeVisible();
  // The homepage must never enumerate individual sessions — the only button
  // present should be "Create Session", not a per-session join button.
  await expect(page.getByRole('button')).toHaveCount(1);
});

test('session page shows the session code, connected status, and chat input', async ({
  page,
}) => {
  // Create via the UI so the browser's identity is registered as the host
  // member (a session created via a bare API call from outside the page
  // would not be a recognized websocket member of its own session).
  await page.goto('/');
  await createSessionViaUI(page);

  // Wait for the session page to fully load — the SessionCard header shows
  // the formatted 6-digit code, e.g. "123 456".
  await expect(page.locator('.session-card h2')).toHaveText(/^\d{3} \d{3}$/, {
    timeout: 10000,
  });

  // Wait for websocket to connect
  await waitForWebSocketConnected(page);

  // Verify chat elements are present
  await expect(page.locator('.chat-input')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Leave Session' })).toBeVisible();
});

test('creating a session lets the host set their display name and shows them connected', async ({
  page,
}) => {
  await page.goto('/');
  await page.getByLabel('Display name').fill('Hostina');
  await createSessionViaUI(page);

  // The host's chosen name — not an auto-generated "Guest-XXXX" — should
  // appear in the participants list.
  await expect(page.locator('.participants li')).toHaveText('Hostina (host)');

  // The websocket should connect for the session's creator.
  await waitForWebSocketConnected(page);
});

test('error handling — invalid session redirects home with a message', async ({ page }) => {
  await page.goto('/session/nonexistent-id');
  await expect(page).toHaveURL('/', { timeout: 5000 });
  await expect(page.locator('.error')).toBeVisible();
  await expect(page.locator('.error')).toHaveText(/session/i);
});
