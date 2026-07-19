import { defineConfig, configDefaults } from "vitest/config";
import { svelte } from "@sveltejs/vite-plugin-svelte";
import { svelteTesting } from "@testing-library/svelte/vite";

export default defineConfig({
  plugins: [svelte()],
  test: {
    workspace: [
      {
        extends: true,
        plugins: [svelte(), svelteTesting()],
        test: {
          name: "components",
          include: ["src/**/?(*.)test.{svelte,html,md,vue,astro}"],
          exclude: [...configDefaults.exclude, "**/*.test.{ts,js}"],
          environment: "jsdom",
          globals: true,
        },
      },
      {
        extends: true,
        plugins: [svelteTesting()],
        test: {
          name: "utils",
          include: ["src/**/*.test.ts", "tests/**/*.test.{ts,js}"],
          exclude: [
            ...configDefaults.exclude,
            "**/*.test.svelte",
            "**/*.test.{html,md,vue,astro}",
          ],
          environment: "jsdom",
          globals: true,
        },
      },
    ],
  },
});
