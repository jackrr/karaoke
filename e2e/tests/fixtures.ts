import { test as base } from '@playwright/test';

/**
 * Fixtures available to e2e tests.
 * In CI, `webServer` in playwright.config.ts starts both backend and frontend.
 */
export const test = base.extend<{
  /** Create a session via API and return the session ID. */
  sessionUrl: string;
}>({
  sessionUrl: async ({ baseURL }, use) => {
    const resp = await fetch(`${baseURL}/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: 'Fixture Session' }),
    });
    const data = await resp.json();
    await use(`${baseURL}/session/${data.id}`);
  },
});
