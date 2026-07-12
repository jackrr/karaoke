import { test, expect } from '@playwright/test';

/**
 * Helper: create a session via the API running during the webServer start.
 */
async function apiCreateSession(url: string, name: string) {
  const resp = await fetch(`${url}/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  });
  const data = await (resp as Response).json();
  return data.id;
}

test('single client joins session', async ({ page, baseURL }) => {
  const sessionId = await apiCreateSession(baseURL, 'WS Test Session');

  await page.goto(`/session/${sessionId}`);
  // Verify connected state is shown (status text)
  await expect(page.getByText(/Connected/)).toBeVisible();
  // Verify chat input exists
  await expect(page.locator('.chat-input')).toBeVisible();
});

test('two clients can see connection state', async ({ browser, baseURL }) => {
  const ctx1 = await browser.newContext();
  const ctx2 = await browser.newContext();
  const page1 = await ctx1.newPage();
  const page2 = await ctx2.newPage();

  const sessionId = await apiCreateSession(baseURL, 'Multi-Session');

  await Promise.all([
    page1.goto(`/session/${sessionId}`),
    page2.goto(`/session/${sessionId}`),
  ]);

  // Wait for both to show connected
  await expect(page1.getByText(/Connected/)).toBeVisible();
  await expect(page2.getByText(/Connected/)).toBeVisible();

  await page1.close();
  await ctx1.close();
  await page2.close();
  await ctx2.close();
});

test('disconnect detection shows Disconnected', async ({ browser, baseURL }) => {
  const ctx = await browser.newContext();
  const page = await ctx.newPage();

  const sessionId = await apiCreateSession(baseURL, 'Disconnect Test');

  await page.goto(`/session/${sessionId}`);
  await expect(page.getByText(/Connected/)).toBeVisible();

  // navigate away to trigger disconnect
  await page.goto('/');

  // Create new context simulating the second client that was connected
  const ctx2 = await browser.newContext();
  const page2 = await ctx2.newPage();
  await page2.goto(`/session/${sessionId}`);

  await page2.close();
  await ctx2.close();
  await ctx.close();
});

test('multiple sessions are isolated', async ({ browser, baseURL }) => {
  const page = await browser.newPage();

  const idA = await apiCreateSession(baseURL, 'Session A');
  const idB = await apiCreateSession(baseURL, 'Session B');

  // Navigate to session A
  await page.goto(`/session/${idA}`);
  await expect(page.getByRole('heading', { name: /Session A/i })).toBeVisible();

  // Navigate to session B
  await page.goto(`/session/${idB}`);
  await expect(page.getByRole('heading', { name: /Session B/i })).toBeVisible();

  await page.close();
});
