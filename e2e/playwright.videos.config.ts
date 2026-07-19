import { defineConfig } from "@playwright/test";
import { baseConfig } from "./playwright.config";

const baseWebServers = Array.isArray(baseConfig.webServer)
  ? baseConfig.webServer
  : baseConfig.webServer
    ? [baseConfig.webServer]
    : [];

/** @type {import('@playwright/test').PlaywrightTestConfig} */
export default defineConfig({
  ...baseConfig,
  testDir: "./tests-videos",
  use: {
    ...baseConfig.use,
    video: { mode: "on", size: { width: 1280, height: 800 } },
  },
  webServer: baseWebServers.map((server) => ({
    ...server,
    env: { ...process.env, SKIP_TRACK_DOWNLOAD: "1" },
  })),
  projects: [{ name: "chromium" }],
});
