import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
  {
    rules: {
      // React 19's strict rule flags common initialization patterns (mount, theme, modal).
      // Downgrade to warning so builds pass while keeping visibility.
      "react-hooks/set-state-in-effect": "warn",
      // Allow img tags for inline preview thumbnails (Image component is overkill here).
      "@next/next/no-img-element": "warn",
    },
  },
]);

export default eslintConfig;
