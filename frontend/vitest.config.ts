import { defineConfig, configDefaults } from "vitest/config";
import { svelte } from "@sveltejs/vite-plugin-svelte";
import { svelteTesting } from "@testing-library/svelte/vite";

// SessionCard.svelte imports from the bare `$lib` alias. In the real app
// that's resolved by SvelteKit's vite plugin, which isn't loaded here, so
// resolve it manually for both vitest workspaces. `new URL(...).pathname`
// (rather than `fileURLToPath` from `node:url`) avoids needing `@types/node`
// as a devDependency just for this one path.
export default defineConfig({
  plugins: [svelte()],
  resolve: {
    alias: {
      $lib: new URL("./src/lib", import.meta.url).pathname,
    },
  },
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
