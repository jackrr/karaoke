import { sveltekit } from "@sveltejs/kit/vite";
import { defineConfig } from "vite";

const apiTarget = "http://localhost:8000";

export default defineConfig({
  plugins: [sveltekit()],
  server: {
    proxy: {
      "/sessions": apiTarget,
      "/health": apiTarget,
      "/ws": {
        target: apiTarget,
        ws: true,
      },
    },
  },
});
