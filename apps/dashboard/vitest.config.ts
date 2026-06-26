import { fileURLToPath } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const root = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": root } },
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest-setup.ts"],
    exclude: ["e2e/**", "node_modules/**", ".next/**"],
  },
});
