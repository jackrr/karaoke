import { test, expect } from '@playwright/test';
import { createSessionViaUI, waitForWebSocketConnected } from './helpers';

test('create session via UI', async ({ page }) => {
  await page.goto('/');
  await createSessionViaUI(page);
  await expect(page).toHaveURL(/\/session\//);
});

test('list sessions after creation via UI', async ({ page }) => {
  // Create a session first
  await page.goto('/');
  await createSessionViaUI(page);
  await expect(page).toHaveURL(/\/session\//);

  // Navigate back to list
  await page.goto('/');
  // Wait for sessions to load (avoid async state where list is empty)
  await page.waitForLoadState('networkidle');
  // The session we just created should appear (use .first() since parallel tests may duplicate names)
  await expect(
    page.getByRole('button', { name: 'My Session' }).first()
  ).toBeVisible();
});

test('session page shows connected status and chat input', async ({ page }) => {
  // Create via the UI so the browser's identity is registered as the host
  // member (a session created via a bare API call from outside the page
  // would not be a recognized websocket member of its own session).
  await page.goto('/');
  await createSessionViaUI(page, 'My Session');

  // Wait for the session page to fully load (heading should appear)
  await expect(page.getByRole('heading', { name: 'My Session' })).toBeVisible({
    timeout: 10000,
  });

  // Wait for websocket to connect
  await waitForWebSocketConnected(page);

  // Verify chat elements are present
  await expect(page.locator('.chat-input')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Leave Session' })).toBeVisible();
});

test('error handling — invalid session', async ({ page }) => {
  await page.goto('/session/nonexistent-id', { waitUntil: 'commit' });
  // SvelteKit static fallback — URL should not change
  await expect(page).toHaveURL(/\/session\/nonexistent-id/, { timeout: 5000 });
});
