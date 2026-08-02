import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { resolve } from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./test/setup.ts"],
    // Vitest picks up *.test.{ts,tsx}; Playwright owns *.spec.ts under e2e/.
    include: ["**/*.test.{ts,tsx}"],
    exclude: [
      "**/node_modules/**",
      "**/.next/**",
      "**/playwright-report/**",
      "**/test-results/**",
      "e2e/**",
    ],
  },
  resolve: {
    alias: {
      // Mirror the tsconfig "@/*" → "./*" path alias so component imports resolve.
      "@": resolve(__dirname, "."),
    },
  },
});
