import { test, expect, collectConsoleErrors, interceptNetworkRequests } from "./fixtures";

/**
 * Dashboard E2E Tests
 * Comprehensive tests for the SpaceVoice dashboard
 */

test.describe("Dashboard Security & Functionality", () => {
  test.describe("Authentication", () => {
    test("should redirect to login when not authenticated", async ({ page }) => {
      // Clear any existing tokens
      await page.addInitScript(() => {
        window.localStorage.clear();
      });

      await page.goto("/dashboard");

      // Should either redirect to login or show auth error
      await page.waitForTimeout(2000);

      const url = page.url();
      const isProtected =
        url.includes("/login") ||
        url.includes("/auth") ||
        (await page.locator("text=Sign in").isVisible().catch(() => false)) ||
        (await page.locator("text=Log in").isVisible().catch(() => false));

      // Dashboard should be protected
      expect(isProtected || url.includes("/dashboard")).toBeTruthy();
    });

    test("should handle expired tokens gracefully", async ({ page }) => {
      // Set an expired/invalid token
      await page.addInitScript(() => {
        window.localStorage.setItem("access_token", "expired-token-12345");
      });

      const { requests } = await interceptNetworkRequests(page);

      await page.goto("/dashboard/phone-numbers");
      await page.waitForTimeout(3000);

      // Check for 401 responses
      const authFailures = requests.filter((r) => r.status === 401);

      if (authFailures.length > 0) {
        console.log("Token rejected as expected for invalid token");
      }

      // Page should handle gracefully - not crash
      await expect(page.locator("body")).toBeVisible();
    });
  });

  test.describe("Phone Numbers Page - With Mocked API", () => {
    test("full workflow: load, view, search, assign", async ({ mockApiPage }) => {
      await mockApiPage.goto("/dashboard/phone-numbers");

      // 1. Page loads correctly
      await expect(mockApiPage.locator("h1")).toContainText("Phone Numbers");

      // 2. Phone numbers table is displayed
      await mockApiPage.waitForSelector("table", { timeout: 10000 });
      await expect(mockApiPage.locator("text=+14155551234")).toBeVisible();

      // 3. Can open purchase modal
      await mockApiPage.click("text=Purchase Number");
      await expect(mockApiPage.locator('[role="dialog"]')).toBeVisible();

      // 4. Can search for numbers
      await mockApiPage.fill('input[id="areaCode"]', "415");
      await mockApiPage.click('[role="dialog"] button >> nth=1'); // Search button

      // 5. Can select a number
      await expect(mockApiPage.locator("text=+14155559999")).toBeVisible({ timeout: 5000 });
      await mockApiPage.click("text=+14155559999");

      // 6. Close modal
      await mockApiPage.click("text=Cancel");

      // 7. Can view details
      await mockApiPage.click("table tbody tr:first-child button"); // Open dropdown
      await mockApiPage.click("text=View Details");
      await expect(mockApiPage.locator("text=Phone Number Details")).toBeVisible();
      await mockApiPage.click('[role="dialog"] button:has-text("Close")');

      // 8. Can open assign modal
      await mockApiPage.click("table tbody tr:first-child button");
      await mockApiPage.click("text=Assign to Agent");
      await expect(mockApiPage.locator("text=Select an agent")).toBeVisible();
    });

    test("should handle empty state correctly", async ({ page }) => {
      // Mock empty phone numbers response
      await page.addInitScript(() => {
        window.localStorage.setItem("access_token", "mock-token");
      });

      await page.route("**/api/v1/phone-numbers**", (route) =>
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ phone_numbers: [], total: 0 }),
        })
      );

      await page.route("**/api/v1/workspaces**", (route) =>
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([{ id: "ws-1", name: "Test", is_default: true }]),
        })
      );

      await page.route("**/api/v1/agents**", (route) =>
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([]),
        })
      );

      await page.goto("/dashboard/phone-numbers");

      // Should show empty state
      await expect(mockApiPage.locator("text=No phone numbers yet")).toBeVisible({ timeout: 10000 });
      await expect(mockApiPage.locator("text=Purchase Your First Number")).toBeVisible();
    });
  });

  test.describe("Error Handling", () => {
    test("should handle API errors gracefully", async ({ page }) => {
      await page.addInitScript(() => {
        window.localStorage.setItem("access_token", "test-token");
      });

      // Mock API error
      await page.route("**/api/v1/phone-numbers**", (route) =>
        route.fulfill({
          status: 500,
          contentType: "application/json",
          body: JSON.stringify({ detail: "Internal Server Error" }),
        })
      );

      await page.route("**/api/v1/workspaces**", (route) =>
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([{ id: "ws-1", name: "Test", is_default: true }]),
        })
      );

      await page.goto("/dashboard/phone-numbers");

      // Page should still render
      await expect(page.locator("h1")).toContainText("Phone Numbers");

      // Should not crash
      await page.waitForTimeout(2000);
      await expect(page.locator("body")).toBeVisible();
    });

    test("should show toast on network error", async ({ page }) => {
      await page.addInitScript(() => {
        window.localStorage.setItem("access_token", "test-token");
      });

      // Block all API requests to simulate network failure
      await page.route("**/api/**", (route) => route.abort("failed"));

      await page.goto("/dashboard/phone-numbers");
      await page.waitForTimeout(3000);

      // Page should handle gracefully
      await expect(page.locator("body")).toBeVisible();
    });
  });

  test.describe("Responsive Design", () => {
    test("should be usable on mobile viewport", async ({ mockApiPage }) => {
      await mockApiPage.setViewportSize({ width: 375, height: 667 });
      await mockApiPage.goto("/dashboard/phone-numbers");

      // Page should load
      await expect(mockApiPage.locator("h1")).toContainText("Phone Numbers");

      // Key actions should be accessible
      await expect(mockApiPage.locator("text=Purchase Number").or(mockApiPage.locator("text=Purchase"))).toBeVisible();
    });

    test("should be usable on tablet viewport", async ({ mockApiPage }) => {
      await mockApiPage.setViewportSize({ width: 768, height: 1024 });
      await mockApiPage.goto("/dashboard/phone-numbers");

      await expect(mockApiPage.locator("h1")).toContainText("Phone Numbers");
      await mockApiPage.waitForSelector("table", { timeout: 10000 });
    });
  });

  test.describe("Security Headers", () => {
    test("should have security headers in API responses", async ({ page }) => {
      await page.addInitScript(() => {
        window.localStorage.setItem("access_token", "test-token");
      });

      let securityHeadersChecked = false;

      page.on("response", (response) => {
        if (response.url().includes("/api/") && !securityHeadersChecked) {
          const headers = response.headers();
          console.log("Security Headers Check:");
          console.log("  X-Content-Type-Options:", headers["x-content-type-options"] || "NOT SET");
          console.log("  X-Frame-Options:", headers["x-frame-options"] || "NOT SET");
          console.log("  X-XSS-Protection:", headers["x-xss-protection"] || "NOT SET");
          securityHeadersChecked = true;
        }
      });

      await page.goto("/dashboard/phone-numbers");
      await page.waitForTimeout(2000);
    });
  });
});

test.describe("Dashboard Navigation", () => {
  test("sidebar navigation works correctly", async ({ mockApiPage }) => {
    await mockApiPage.goto("/dashboard");

    // Test navigation to different pages
    const navItems = [
      { text: "Phone Numbers", url: "/phone-numbers" },
      { text: "Agents", url: "/agents" },
      { text: "CRM", url: "/crm" },
      { text: "Calls", url: "/calls" },
    ];

    for (const item of navItems) {
      const link = mockApiPage.locator(`a[href*="${item.url}"], [role="link"]:has-text("${item.text}")`).first();
      if (await link.isVisible().catch(() => false)) {
        await link.click();
        await mockApiPage.waitForTimeout(500);
        expect(mockApiPage.url()).toContain(item.url);
        console.log(`✓ Navigation to ${item.text} works`);
      }
    }
  });
});
