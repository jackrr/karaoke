import { type Page } from '@playwright/test';

/**
 * Create a session via direct API call (bypasses UI).
 * Returns the session created URL.
 */
export async function createSessionViaApi(page: Page): Promise<string> {
  const resp = await page.evaluate(() =>
    fetch('/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: 'E2E Test Session' }),
    })
  );
  const data = await resp.json();
  return data.id;
}

/**
 * Create a session via UI click.
 */
export async function createSessionViaUI(page: Page): Promise<void> {
  await page.getByRole('button', { name: /Create/i }).click();
  // Wait for navigation to session page
  await page.waitForURL(/\/session\//);
}

/**
 * Navigate directly to a session page.
 */
export async function navigateToSession(page: Page, sessionId: string): Promise<Page> {
  await page.goto(`/session/${sessionId}`);
  return page;
}

/**
 * Wait for WebSocket to be connected by checking the connected text.
 */
export async function waitForWebSocketConnected(page: Page): Promise<void> {
  await page.getByText(/Connected/, { timeout: 5000 }).waitFor();
}

/**
 * Leave a session page.
 */
export async function leaveSession(page: Page): Promise<void> {
  await page.getByRole('button', { name: 'Leave Session' }).click();
  await page.waitForURL('/');
}
