import { test, expect } from '@playwright/test';
import { createSessionViaUI, joinSessionViaUI, waitForWebSocketConnected } from './helpers';

test('joining by passcode adds a second participant and shows real display names in chat', async ({
  browser,
}) => {
  const ctxA = await browser.newContext();
  const ctxB = await browser.newContext();
  const pageA = await ctxA.newPage();
  const pageB = await ctxB.newPage();

  // Context A creates the session via the UI.
  await pageA.goto('/');
  await createSessionViaUI(pageA, 'Join Flow Session');
  await waitForWebSocketConnected(pageA);

  // Read the passcode straight from the rendered SessionCard.
  const passcodeText = await pageA.locator('.session-card code').innerText();
  const passcode = passcodeText.replace(/\D/g, '');
  expect(passcode).toMatch(/^\d{6}$/);

  // Context B joins using only the passcode from the UI.
  await pageB.goto('/join');
  await joinSessionViaUI(pageB, passcode, 'Bob');
  await waitForWebSocketConnected(pageB);

  // Both contexts should now see 2 participants.
  await expect(pageA.locator('.participants li')).toHaveCount(2);
  await expect(pageB.locator('.participants li')).toHaveCount(2);

  // A chat message from context B should show B's real display name in
  // context A's view, not a hardcoded placeholder like "you".
  await pageB.locator('.chat-input').fill('hi from bob');
  await pageB.getByRole('button', { name: 'Send' }).click();

  await expect(pageA.getByText('Bob:')).toBeVisible();
  await expect(pageA.getByText('hi from bob')).toBeVisible();
  await expect(pageA.getByText('you:', { exact: false })).not.toBeVisible();

  await ctxA.close();
  await ctxB.close();
});
