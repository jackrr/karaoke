import { test, expect, type Page } from '@playwright/test';
import { createSessionViaUI, waitForWebSocketConnected } from './helpers';

/**
 * Regression tests for a mobile disconnect that never recovers: once the
 * session WebSocket drops (network loss, tab backgrounded by the OS, etc.),
 * nothing brings it back — neither resuming a backgrounded tab nor a full
 * page refresh reconnects to the backend. Both are expected to reconnect;
 * today neither does (the frontend has no retry/resume logic, and the
 * backend also marks the dropped member as "left" and rejects the next
 * handshake from that client_id — see `_mark_member_left` /
 * `_is_active_member` in `backend/app/websocket_manager.py`).
 *
 * `context.setOffline()` alone doesn't reliably tear down an already-open
 * WebSocket in Chromium, so these tests force the drop directly by closing
 * the page's live socket — indistinguishable, from the app's perspective,
 * from the server or network killing the connection out from under it.
 */

async function dropConnection(page: Page): Promise<void> {
  await page.evaluate(() => {
    (window as unknown as { __lastWs: WebSocket }).__lastWs.close();
  });
  await expect(page.getByText(/Disconnected/)).toBeVisible();
}

test.beforeEach(async ({ page }) => {
  // Stash every WebSocket the app creates so tests can force-close the live
  // one to simulate a dropped connection.
  await page.addInitScript(() => {
    const NativeWebSocket = window.WebSocket;
    class TrackedWebSocket extends NativeWebSocket {
      constructor(...args: ConstructorParameters<typeof NativeWebSocket>) {
        super(...args);
        (window as unknown as { __lastWs: WebSocket }).__lastWs = this;
      }
    }
    window.WebSocket = TrackedWebSocket as unknown as typeof WebSocket;
  });
});

test('reconnects when the tab regains foreground after losing connectivity', async ({ page }) => {
  await page.goto('/');
  await createSessionViaUI(page);
  await waitForWebSocketConnected(page);

  await dropConnection(page);

  // Tab goes to the background, then resumes — the browser fires
  // `visibilitychange` in both directions.
  await page.evaluate(() => {
    Object.defineProperty(document, 'visibilityState', { value: 'hidden', configurable: true });
    document.dispatchEvent(new Event('visibilitychange'));
  });
  await page.evaluate(() => {
    Object.defineProperty(document, 'visibilityState', { value: 'visible', configurable: true });
    document.dispatchEvent(new Event('visibilitychange'));
  });

  await expect(page.getByText(/Connected/)).toBeVisible({ timeout: 5000 });
});

test('reconnects after a page refresh following a lost connection', async ({ page }) => {
  await page.goto('/');
  await createSessionViaUI(page);
  await waitForWebSocketConnected(page);

  await dropConnection(page);

  await page.reload();

  await expect(page.getByText(/Connected/)).toBeVisible({ timeout: 5000 });
});
