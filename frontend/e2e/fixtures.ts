import { test as base, expect, Page } from "@playwright/test";

/**
 * Custom test fixtures for SpaceVoice E2E tests
 * Provides authentication helpers and API mocking
 */

// Test user credentials (use test env or mock)
const TEST_USER = {
  email: process.env.TEST_USER_EMAIL || "test@example.com",
  password: process.env.TEST_USER_PASSWORD || "testpassword123",
};

// API base URL
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Extended test with authentication
 */
export const test = base.extend<{
  authenticatedPage: Page;
  mockApiPage: Page;
}>({
  /**
   * Page with real authentication (for integration tests)
   */
  authenticatedPage: async ({ page }, use) => {
    // Try to login via the API
    try {
      const response = await page.request.post(`${API_BASE}/api/v1/auth/login`, {
        form: {
          username: TEST_USER.email,
          password: TEST_USER.password,
        },
      });

      if (response.ok()) {
        const data = await response.json();
        // Set the token in localStorage before navigating
        await page.addInitScript((token: string) => {
          window.localStorage.setItem("access_token", token);
        }, data.access_token);
      }
    } catch {
      // If login fails, tests will handle unauthenticated state
      console.log("Auth failed - running in unauthenticated mode");
    }

    await use(page);
  },

  /**
   * Page with mocked API responses (for isolated testing)
   */
  mockApiPage: async ({ page }, use) => {
    // Mock authentication
    await page.addInitScript(() => {
      window.localStorage.setItem("access_token", "mock-token-for-testing");
    });

    // Set up API route mocking
    await page.route(`${API_BASE}/**`, async (route) => {
      const url = route.request().url();

      // Mock workspaces endpoint
      if (url.includes("/api/v1/workspaces")) {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([
            {
              id: "workspace-1",
              name: "Test Workspace",
              description: "Default workspace for testing",
              is_default: true,
            },
          ]),
        });
      }

      // Mock phone numbers list
      if (url.includes("/api/v1/phone-numbers") && !url.includes("/search") && !url.includes("/purchase")) {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            phone_numbers: [
              {
                id: "pn-1",
                phone_number: "+14155551234",
                friendly_name: "Test Number 1",
                provider: "telnyx",
                capabilities: { voice: true, sms: true },
                assigned_agent_id: null,
              },
              {
                id: "pn-2",
                phone_number: "+14155555678",
                friendly_name: "Test Number 2",
                provider: "twilio",
                capabilities: { voice: true, sms: true },
                assigned_agent_id: "agent-1",
              },
            ],
            total: 2,
          }),
        });
      }

      // Mock agents list
      if (url.includes("/api/v1/agents")) {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([
            {
              id: "agent-1",
              name: "Sales Agent",
              status: "active",
              phone_number_id: "pn-2",
            },
            {
              id: "agent-2",
              name: "Support Agent",
              status: "active",
              phone_number_id: null,
            },
          ]),
        });
      }

      // Mock phone number search
      if (url.includes("/telephony/phone-numbers/search")) {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([
            { phone_number: "+14155559999", friendly_name: "Available 1" },
            { phone_number: "+14155558888", friendly_name: "Available 2" },
          ]),
        });
      }

      // Default: pass through to actual API
      return route.continue();
    });

    await use(page);
  },
});

export { expect };

/**
 * Helper to check for fetch errors in the console
 */
export async function collectConsoleErrors(page: Page): Promise<string[]> {
  const errors: string[] = [];

  page.on("console", (msg) => {
    if (msg.type() === "error") {
      errors.push(msg.text());
    }
  });

  page.on("pageerror", (err) => {
    errors.push(err.message);
  });

  return errors;
}

/**
 * Helper to intercept and log network requests
 */
export async function interceptNetworkRequests(
  page: Page
): Promise<{ requests: { url: string; status: number; error?: string }[] }> {
  const requests: { url: string; status: number; error?: string }[] = [];

  page.on("requestfailed", (request) => {
    requests.push({
      url: request.url(),
      status: 0,
      error: request.failure()?.errorText || "Unknown error",
    });
  });

  page.on("response", (response) => {
    if (response.url().includes("/api/")) {
      requests.push({
        url: response.url(),
        status: response.status(),
      });
    }
  });

  return { requests };
}
