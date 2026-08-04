import { defineConfig, devices, type PlaywrightTestConfig } from "@playwright/test";

/** @type {import('@playwright/test').PlaywrightTestConfig} */
export const baseConfig: PlaywrightTestConfig = {
  testDir: "./tests",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  timeout: 30000,
  expect: { timeout: 5000 },
  reporter: process.env.CI ? "html" : "list",
  use: {
    baseURL: process.env.BASE_URL ?? "http://localhost:8765",
  },
  webServer: [
    {
      command: "cd .. && ./scripts/serve",
      port: 8765,
      timeout: 30_000,
      name: "app",
      // Stub the yt-dlp/demucs pipeline so tracks reach "ready" instantly
      // with placeholder audio — tests need real playback state (ready
      // tracks, audio elements), not real downloads/separation.
      env: { ...process.env, SKIP_TRACK_DOWNLOAD: "1" },
    },
  ],

  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
};

export default defineConfig(baseConfig);
