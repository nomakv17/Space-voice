import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright configuration for SpaceVoice dashboard E2E tests
 * @see https://playwright.dev/docs/test-configuration
 *
 * Environments:
 *   - Local: http://localhost:3001 (default)
 *   - Production: https://dashboard.spacevoice.ai
 *
 * Usage:
 *   npm run test:e2e                                    # Local with dev server
 *   PLAYWRIGHT_BASE_URL=https://dashboard.spacevoice.ai npm run test:e2e  # Production
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [["html", { open: "never" }], ["list"]],

  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || "http://localhost:3001",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    // Increase timeout for production testing
    actionTimeout: 15000,
    navigationTimeout: 30000,
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "firefox",
      use: { ...devices["Desktop Firefox"] },
    },
    {
      name: "webkit",
      use: { ...devices["Desktop Safari"] },
    },
    // Mobile viewports
    {
      name: "Mobile Chrome",
      use: { ...devices["Pixel 5"] },
    },
  ],

  // Run local dev server before starting tests if needed
  webServer: process.env.PLAYWRIGHT_SKIP_WEBSERVER
    ? undefined
    : {
        command: "npm run dev",
        url: "http://localhost:3001",
        reuseExistingServer: !process.env.CI,
        timeout: 120000,
      },
});
