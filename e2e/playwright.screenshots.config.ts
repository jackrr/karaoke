import { defineConfig } from "@playwright/test";
import { baseConfig } from "./playwright.config";

/** @type {import('@playwright/test').PlaywrightTestConfig} */
export default defineConfig({
  ...baseConfig,
  testDir: "./tests-screenshots",
  projects: [{ name: "chromium" }],
});
