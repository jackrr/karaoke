import { expect, test } from '@playwright/test';
import {
  createSessionViaUI,
  createTrackViaApi,
  getClientId,
  openSessionMenu,
  waitForWebSocketConnected,
} from '../tests/helpers';

const VIEWPORTS = [
  { name: 'desktop', width: 1280, height: 800 },
  { name: 'mobile', width: 390, height: 844 },
];

for (const viewport of VIEWPORTS) {
  test.describe(`${viewport.name} viewport`, () => {
    test.beforeEach(async ({ page }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
    });

    test(`home page — ${viewport.name}`, async ({ page }) => {
      await page.goto('/');
      await page.waitForLoadState('networkidle');
      await page.screenshot({ path: `screenshots/01-home-${viewport.name}.png` });
    });

    test(`join page — ${viewport.name}`, async ({ page }) => {
      await page.goto('/join');
      await page.screenshot({ path: `screenshots/02-join-${viewport.name}.png` });
    });

    test(`session page as host — ${viewport.name}`, async ({ page }) => {
      await page.goto('/');
      await createSessionViaUI(page);
      await waitForWebSocketConnected(page);
      await page.screenshot({ path: `screenshots/03-session-host-${viewport.name}.png` });
    });

    // No load function in the app throws, so the only reliable way to hit
    // SvelteKit's default +error.svelte is a truly unmatched route (404).
    test(`error page — ${viewport.name}`, async ({ page }) => {
      await page.goto('/this-route-does-not-exist');
      await page.screenshot({ path: `screenshots/04-error-${viewport.name}.png` });
    });

    // Requires SKIP_TRACK_DOWNLOAD=1 (set on this config's webServer) so a
    // seeded track reaches "ready" without hitting yt-dlp/demucs.
    test(`session menu open — ${viewport.name}`, async ({ page }) => {
      await page.goto('/');
      await createSessionViaUI(page);
      await waitForWebSocketConnected(page);
      await openSessionMenu(page);
      await page.screenshot({ path: `screenshots/05-session-menu-${viewport.name}.png` });
    });

    test(`now playing — ${viewport.name}`, async ({ page }) => {
      await page.goto('/');
      await createSessionViaUI(page);
      await waitForWebSocketConnected(page);

      const match = page.url().match(/\/session\/([^/?#]+)/);
      if (!match) throw new Error(`Could not extract session id from URL: ${page.url()}`);
      const clientId = await getClientId(page);
      await createTrackViaApi(
        page,
        match[1],
        'https://www.youtube.com/watch?v=aaaaaaaaaaa',
        clientId
      );

      await expect(page.locator('.status-ready')).toHaveCount(1, { timeout: 10_000 });
      await page.getByRole('button', { name: 'Play' }).click();
      await page.screenshot({ path: `screenshots/06-now-playing-${viewport.name}.png` });
    });
  });
}
