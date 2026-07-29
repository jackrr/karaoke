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
  testDir: "./tests-screenshots",
  webServer: baseWebServers.map((server) => ({
    ...server,
    env: { ...process.env, SKIP_TRACK_DOWNLOAD: "1" },
  })),
  projects: [{ name: "chromium" }],
});
