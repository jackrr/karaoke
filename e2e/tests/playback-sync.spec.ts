import { test, expect, type Page } from '@playwright/test';
import {
  createSessionViaUI,
  createTrackViaApi,
  getClientId,
  joinSessionViaUI,
  waitForWebSocketConnected,
} from './helpers';

/**
 * Create a session in `hostPage` via the UI and return its id and code.
 *
 * Sessions must be created (and joined) through the real UI flow so the
 * browser's own persisted client id is registered as a session member — see
 * websocket.spec.ts's identical helper for why.
 */
async function createSessionAndGetCode(hostPage: Page): Promise<{ sessionId: string; code: string }> {
  await hostPage.goto('/');
  await createSessionViaUI(hostPage);
  const sessionId = new URL(hostPage.url()).pathname.replace('/session/', '');
  const codeText = await hostPage.locator('.session-card h2').innerText();
  const code = codeText.replace(/\D/g, '');
  return { sessionId, code };
}

test('host playback state syncs to a guest, and a guest can request playback on the host', async ({
  browser,
}) => {
  const hostCtx = await browser.newContext();
  const guestCtx = await browser.newContext();
  const hostPage = await hostCtx.newPage();
  const guestPage = await guestCtx.newPage();

  const { sessionId, code } = await createSessionAndGetCode(hostPage);
  const hostClientId = await getClientId(hostPage);

  await guestPage.goto('/join');
  await joinSessionViaUI(guestPage, code, 'Guest');

  await Promise.all([
    waitForWebSocketConnected(hostPage),
    waitForWebSocketConnected(guestPage),
  ]);

  // Seed two ready tracks (SKIP_TRACK_DOWNLOAD=1 on this config's webServer
  // makes each settle into "ready" almost instantly with placeholder audio).
  // Both stub out to the same title, so track identity below is established
  // by queue position (insertion order), not text content.
  await createTrackViaApi(hostPage, sessionId, 'https://www.youtube.com/watch?v=aaaaaaaaaaa', hostClientId);
  await createTrackViaApi(hostPage, sessionId, 'https://www.youtube.com/watch?v=bbbbbbbbbbb', hostClientId);

  await expect(hostPage.locator('.status-ready')).toHaveCount(2, { timeout: 10_000 });
  await expect(guestPage.locator('.status-ready')).toHaveCount(2, { timeout: 10_000 });

  // Host plays the first track locally. Clicking "Play" in the queue opens
  // the local TrackPlayer and immediately syncs is_playing=true to the
  // server (independent of whether the underlying <audio> element has
  // actually started decoding).
  await hostPage.locator('.track').first().getByRole('button', { name: 'Play' }).click();
  await expect(hostPage.locator('.playback-controls')).toBeVisible();

  // The guest never opens a local player — it just sees the queue update to
  // reflect a "Now Playing" badge on whichever track the host started.
  const guestNowPlaying = guestPage.locator('.track', { has: guestPage.locator('.now-playing') });
  await expect(guestNowPlaying).toHaveCount(1, { timeout: 5000 });
  await expect(guestNowPlaying.locator('.now-playing')).toHaveAttribute('aria-label', 'Now playing');
  await expect(guestPage.locator('.playback-controls')).toHaveCount(0);

  // Actually start local playback on the host (the play/pause toggle inside
  // the full-screen player), then pause it — the guest's badge should
  // reflect the paused state via the playback_state_changed broadcast.
  await hostPage.getByRole('button', { name: 'Play' }).click();
  await hostPage.getByRole('button', { name: 'Pause' }).click();
  await expect(guestNowPlaying.locator('.now-playing')).toHaveAttribute('aria-label', 'Now paused', {
    timeout: 5000,
  });

  // Guest requests playback of the second track, from their own device.
  await guestPage.locator('.track').nth(1).getByRole('button', { name: 'Play on host' }).click();

  // The host's player switches to (and starts) that track; the guest still
  // never gets a local player of their own.
  await expect(hostPage.locator('.playback-controls')).toBeVisible({ timeout: 5000 });
  await expect(guestPage.locator('.playback-controls')).toHaveCount(0);

  await hostCtx.close();
  await guestCtx.close();
});
