import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  outputDir: "../output/playwright/test-results",
  use: {
    baseURL: "http://127.0.0.1:4173",
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  webServer: {
    command: "pnpm build && pnpm vite preview --host 127.0.0.1 --port 4173",
    port: 4173,
    reuseExistingServer: true,
  },
});

