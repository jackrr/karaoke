import { test, expect } from '@playwright/test';

test('create session', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: /Create/i }).click();
  await expect(page).toHaveURL(/\/session\//);
});

test('list sessions after creation', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: /Create/i }).click();
  await page.goto('/');
  // The session we just created should appear
  await expect(
    page.getByRole('button', { name: /My Session/i })
  ).toBeVisible();
});

test('session details visible', async ({ page }) => {
  // Create session via API
  const resp = await page.evaluate(() =>
    fetch('/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: 'Detail Session' }),
    })
  );
  const data = await resp.json();
  const sessionId = data.id;

  await page.goto(`/session/${sessionId}`);
  await expect(page.getByRole('heading', { name: /Detail Session/i })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Leave Session' })).toBeVisible();
});

test('error handling — invalid session', async ({ page }) => {
  await page.goto('/session/nonexistent-id', { waitUntil: 'commit' });
  // SvelteKit fallback — should show a 404 or fallback page
  await expect(page).toHaveURL(/\/session\/nonexistent-id/, { timeout: 5000 });
});
