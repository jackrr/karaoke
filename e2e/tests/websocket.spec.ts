import { test, expect, type APIRequestContext } from '@playwright/test';
import { waitForWebSocketConnected, leaveSession } from './helpers';

async function createSession(request: APIRequestContext, name: string): Promise<string> {
  const resp = await request.post('/sessions', { data: { name } });
  const data = await resp.json();
  return data.id;
}

test('chat message broadcasts to other clients in the same session', async ({
  browser,
  request,
}) => {
  const sessionId = await createSession(request, 'Broadcast Session');

  const ctx1 = await browser.newContext();
  const ctx2 = await browser.newContext();
  const page1 = await ctx1.newPage();
  const page2 = await ctx2.newPage();

  await Promise.all([
    page1.goto(`/session/${sessionId}`),
    page2.goto(`/session/${sessionId}`),
  ]);
  await Promise.all([
    waitForWebSocketConnected(page1),
    waitForWebSocketConnected(page2),
  ]);

  await page1.locator('.chat-input').fill('hello from client 1');
  await page1.getByRole('button', { name: 'Send' }).click();

  // The sender sees its own message immediately...
  await expect(page1.getByText('hello from client 1')).toBeVisible();
  // ...and it's broadcast to the other connected client.
  await expect(page2.getByText('hello from client 1')).toBeVisible();

  await ctx1.close();
  await ctx2.close();
});

test('sessions are isolated — messages do not leak across sessions', async ({
  browser,
  request,
}) => {
  const sessionA = await createSession(request, 'Session A');
  const sessionB = await createSession(request, 'Session B');

  const ctxA = await browser.newContext();
  const ctxB = await browser.newContext();
  const pageA = await ctxA.newPage();
  const pageB = await ctxB.newPage();

  await Promise.all([pageA.goto(`/session/${sessionA}`), pageB.goto(`/session/${sessionB}`)]);
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
  const sessionId = await createSession(request, 'Leave Session');

  const ctx1 = await browser.newContext();
  const ctx2 = await browser.newContext();
  const page1 = await ctx1.newPage();
  const page2 = await ctx2.newPage();

  await Promise.all([
    page1.goto(`/session/${sessionId}`),
    page2.goto(`/session/${sessionId}`),
  ]);
  await Promise.all([
    waitForWebSocketConnected(page1),
    waitForWebSocketConnected(page2),
  ]);

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
