import { test, expect, type Page } from '@playwright/test';
import { createSessionViaUI, joinSessionViaUI, waitForWebSocketConnected, leaveSession } from './helpers';

/**
 * Create a session in `hostPage` via the UI and return its id and passcode.
 *
 * Sessions must be created (and joined) through the real UI flow so the
 * browser's own persisted client id is registered as a session member —
 * the websocket endpoint rejects connections from client ids that aren't
 * active members, so a session created out-of-band (e.g. a bare API call)
 * would never be able to connect from a real browser.
 */
async function createSessionAndGetPasscode(
  hostPage: Page,
  name: string
): Promise<{ sessionId: string; passcode: string }> {
  await hostPage.goto('/');
  await createSessionViaUI(hostPage, name);
  const sessionId = new URL(hostPage.url()).pathname.replace('/session/', '');
  const passcodeText = await hostPage.locator('.session-card code').innerText();
  const passcode = passcodeText.replace(/\D/g, '');
  return { sessionId, passcode };
}

test('chat message broadcasts to other clients in the same session', async ({ browser }) => {
  const ctx1 = await browser.newContext();
  const ctx2 = await browser.newContext();
  const page1 = await ctx1.newPage();
  const page2 = await ctx2.newPage();

  const { passcode } = await createSessionAndGetPasscode(page1, 'Broadcast Session');

  await page2.goto('/join');
  await joinSessionViaUI(page2, passcode, 'Guest');

  await Promise.all([waitForWebSocketConnected(page1), waitForWebSocketConnected(page2)]);

  await page1.locator('.chat-input').fill('hello from client 1');
  await page1.getByRole('button', { name: 'Send' }).click();

  // The sender sees its own message immediately...
  await expect(page1.getByText('hello from client 1')).toBeVisible();
  // ...and it's broadcast to the other connected client.
  await expect(page2.getByText('hello from client 1')).toBeVisible();

  await ctx1.close();
  await ctx2.close();
});

test('sessions are isolated — messages do not leak across sessions', async ({ browser }) => {
  const ctxA = await browser.newContext();
  const ctxB = await browser.newContext();
  const pageA = await ctxA.newPage();
  const pageB = await ctxB.newPage();

  await createSessionAndGetPasscode(pageA, 'Session A');
  await createSessionAndGetPasscode(pageB, 'Session B');

  await Promise.all([waitForWebSocketConnected(pageA), waitForWebSocketConnected(pageB)]);

  await pageA.locator('.chat-input').fill('secret to session A');
  await pageA.getByRole('button', { name: 'Send' }).click();
  await expect(pageA.getByText('secret to session A')).toBeVisible();

  // Session B must never receive a message sent in session A.
  await expect(pageB.getByText('secret to session A')).not.toBeVisible();

  await ctxA.close();
  await ctxB.close();
});

test('online count drops after a client leaves the session', async ({ browser, request }) => {
  const ctx1 = await browser.newContext();
  const ctx2 = await browser.newContext();
  const page1 = await ctx1.newPage();
  const page2 = await ctx2.newPage();

  const { sessionId, passcode } = await createSessionAndGetPasscode(page1, 'Leave Session');

  await page2.goto('/join');
  await joinSessionViaUI(page2, passcode, 'Guest');

  await Promise.all([waitForWebSocketConnected(page1), waitForWebSocketConnected(page2)]);

  await leaveSession(page1);

  // Poll the backend directly — the disconnect is processed async server-side,
  // and the frontend only fetches `online` once on mount.
  await expect(async () => {
    const resp = await request.get(`/sessions/${sessionId}`);
    const data = await resp.json();
    expect(data.online).toBe(1);
  }).toPass({ timeout: 5000 });

  await ctx1.close();
  await ctx2.close();
});
