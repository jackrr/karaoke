import { test } from '@playwright/test';
import { createSessionViaUI, waitForWebSocketConnected } from '../tests/helpers';

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
      await createSessionViaUI(page, 'Screenshot Session');
      await waitForWebSocketConnected(page);
      await page.screenshot({ path: `screenshots/03-session-host-${viewport.name}.png` });
    });

    // No load function in the app throws, so the only reliable way to hit
    // SvelteKit's default +error.svelte is a truly unmatched route (404).
    test(`error page — ${viewport.name}`, async ({ page }) => {
      await page.goto('/this-route-does-not-exist');
      await page.screenshot({ path: `screenshots/04-error-${viewport.name}.png` });
    });
  });
}
