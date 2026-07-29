import { type Page } from '@playwright/test';

/**
 * Create a session via direct API call (bypasses UI).
 * Returns the session created data (including id and code).
 */
type CreateSessionResult = {
  id: string;
  code: string;
  host_client_id: string;
  client_id: string;
};

export async function createSessionViaApi(page: Page): Promise<CreateSessionResult> {
  const resp = await page.evaluate(
    () =>
      fetch('/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ display_name: 'Host' }),
      }).then((r) => r.json()) as Promise<CreateSessionResult>
  );
  return resp;
}

/**
 * Create a session via UI: click Create (no session name to fill in — the
 * server generates the session's display/join code).
 */
export async function createSessionViaUI(page: Page): Promise<void> {
  await page.getByRole('button', { name: /Create/i }).click();
  // Wait for navigation to session page
  await page.waitForURL(/\/session\//);
}

/**
 * Join a session via the session-code UI. Assumes the browser is already on `/join`.
 */
export async function joinSessionViaUI(
  page: Page,
  code: string,
  displayName = 'Guest'
): Promise<void> {
  await page.getByLabel('Session code').fill(code);
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

type CreateTrackResult = {
  id: string;
  status: string;
  source_url: string;
  youtube_video_id: string | null;
};

/**
 * Create a track via direct API call (bypasses the YouTube URL form).
 * `clientId` must belong to an active member of `sessionId` (e.g. the
 * `client_id` returned by `createSessionViaApi`, or the browser's persisted
 * `karaoke_client_id` localStorage value when the session was created via
 * the UI — see `getClientId`).
 */
export async function createTrackViaApi(
  page: Page,
  sessionId: string,
  url: string,
  clientId: string
): Promise<CreateTrackResult> {
  const resp = await page.evaluate(
    ({ sessionId, url, clientId }: { sessionId: string; url: string; clientId: string }) =>
      fetch(`/sessions/${sessionId}/tracks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, client_id: clientId }),
      }).then((r) => r.json()) as Promise<CreateTrackResult>,
    { sessionId, url, clientId }
  );
  return resp;
}

/**
 * Read the browser's persisted client id (set by the app in localStorage
 * under `karaoke_client_id` — see frontend/src/lib/identity.ts).
 */
export async function getClientId(page: Page): Promise<string> {
  const clientId = await page.evaluate(() => localStorage.getItem('karaoke_client_id'));
  if (!clientId) throw new Error('karaoke_client_id not found in localStorage');
  return clientId;
}

/**
 * Wait for WebSocket to be connected by checking the connected text.
 */
export async function waitForWebSocketConnected(page: Page): Promise<void> {
  await page.getByText(/Connected/).waitFor({ timeout: 5000 });
}

/**
 * Open the session menu (a native `<dialog>`) that holds the SessionCard,
 * chat, and the Leave Session button.
 */
export async function openSessionMenu(page: Page): Promise<void> {
  await page.getByRole('button', { name: 'Open menu' }).click();
}

/**
 * Leave a session page. Opens the session menu first (if it isn't already
 * open) since the Leave Session button lives inside it.
 */
export async function leaveSession(page: Page): Promise<void> {
  const leaveButton = page.getByRole('button', { name: 'Leave Session' });
  if (!(await leaveButton.isVisible())) {
    await openSessionMenu(page);
  }
  await leaveButton.click();
  await page.waitForURL('/');
}
