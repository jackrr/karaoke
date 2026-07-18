import { type Page } from '@playwright/test';

/**
 * Create a session via direct API call (bypasses UI).
 * Returns the session created data (including id and passcode).
 */
type CreateSessionResult = {
  id: string;
  name: string;
  passcode: string;
  host_client_id: string;
  client_id: string;
};

export async function createSessionViaApi(
  page: Page,
  name = 'E2E Test Session'
): Promise<CreateSessionResult> {
  const resp = await page.evaluate(
    (sessionName) =>
      fetch('/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: sessionName, display_name: 'Host' }),
      }).then((r) => r.json()) as Promise<CreateSessionResult>,
    name
  );
  return resp;
}

/**
 * Create a session via UI: fill in the session name field and click Create.
 */
export async function createSessionViaUI(page: Page, name = 'My Session'): Promise<void> {
  await page.getByPlaceholder('Session name').fill(name);
  await page.getByRole('button', { name: /Create/i }).click();
  // Wait for navigation to session page
  await page.waitForURL(/\/session\//);
}

/**
 * Join a session via the passcode UI. Assumes the browser is already on `/join`.
 */
export async function joinSessionViaUI(
  page: Page,
  passcode: string,
  displayName = 'Guest'
): Promise<void> {
  await page.getByLabel('Passcode').fill(passcode);
  await page.getByLabel('Display name').fill(displayName);
  await page.getByRole('button', { name: /Join Session/i }).click();
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
  await page.getByText(/Connected/).waitFor({ timeout: 5000 });
}

/**
 * Leave a session page.
 */
export async function leaveSession(page: Page): Promise<void> {
  await page.getByRole('button', { name: 'Leave Session' }).click();
  await page.waitForURL('/');
}
