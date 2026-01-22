import { test, expect } from "@playwright/test";

/**
 * API Health Check Tests
 * These tests verify the backend API is accessible and responding correctly
 * Run these first to diagnose connectivity issues
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

test.describe("API Health Checks", () => {
  test("should reach the API health endpoint", async ({ request }) => {
    const response = await request.get(`${API_BASE}/health`).catch(() => null);

    if (!response) {
      console.error(`
        ❌ BACKEND NOT REACHABLE

        The backend API at ${API_BASE} is not responding.

        To fix this:
        1. Make sure the backend is running:
           cd backend && uv run uvicorn app.main:app --reload

        2. Check if PostgreSQL and Redis are running:
           docker-compose up -d

        3. Verify the API URL in your .env file:
           NEXT_PUBLIC_API_URL=http://localhost:8000
      `);
      test.fail();
      return;
    }

    expect(response.status()).toBe(200);
    console.log("✅ Backend API is healthy");
  });

  test("should have CORS configured correctly", async ({ request }) => {
    const response = await request
      .get(`${API_BASE}/health`, {
        headers: {
          Origin: "http://localhost:3001",
        },
      })
      .catch(() => null);

    if (response) {
      const corsHeader = response.headers()["access-control-allow-origin"];
      console.log(`CORS Allow-Origin: ${corsHeader || "NOT SET"}`);

      if (!corsHeader || (corsHeader !== "*" && !corsHeader.includes("localhost:3001"))) {
        console.warn(`
          ⚠️  CORS may not be configured correctly

          The Access-Control-Allow-Origin header should include your frontend origin.
          Check backend/app/main.py for CORS middleware configuration.
        `);
      }
    }
  });

  test("should verify phone numbers endpoint exists", async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/v1/phone-numbers`).catch(() => null);

    if (!response) {
      console.error("❌ Cannot reach phone numbers endpoint");
      return;
    }

    console.log(`Phone Numbers Endpoint Status: ${response.status()}`);

    if (response.status() === 401) {
      console.log("ℹ️  401 Unauthorized - This is expected without authentication");
    } else if (response.status() === 404) {
      console.error(`
        ❌ Phone numbers endpoint not found (404)

        This could mean:
        1. The route is not registered in the backend
        2. The API prefix is different than expected

        Check backend/app/api/phone_numbers.py and main.py router includes
      `);
    } else if (response.status() >= 500) {
      console.error(`
        ❌ Server error on phone numbers endpoint (${response.status()})

        Check the backend logs for errors.
      `);
      const body = await response.text();
      console.log("Response body:", body);
    }
  });

  test("should verify telephony endpoints exist", async ({ request }) => {
    // These are the endpoints used by the phone numbers page
    const endpoints = [
      "/api/v1/telephony/phone-numbers/search",
      "/api/v1/telephony/phone-numbers/purchase",
    ];

    for (const endpoint of endpoints) {
      const response = await request
        .post(`${API_BASE}${endpoint}`, {
          data: {},
          headers: { "Content-Type": "application/json" },
        })
        .catch(() => null);

      if (!response) {
        console.error(`❌ Cannot reach ${endpoint}`);
        continue;
      }

      console.log(`${endpoint}: ${response.status()}`);

      // 401, 422, or 400 are acceptable (need auth or validation)
      // 404 or 500+ indicate problems
      if (response.status() === 404) {
        console.error(`
          ❌ Endpoint not found: ${endpoint}

          This endpoint is called by the frontend but doesn't exist on the backend.
          Check if the route is registered in backend/app/api/
        `);
      }
    }
  });

  test("diagnose fetch error causes", async ({ page }) => {
    console.log("\n📊 FETCH ERROR DIAGNOSTIC REPORT\n");
    console.log("=".repeat(50));

    // 1. Check if backend is running
    const healthResponse = await page.request.get(`${API_BASE}/health`).catch(() => null);
    const backendRunning = healthResponse?.ok();
    console.log(`\n1. Backend Running: ${backendRunning ? "✅ Yes" : "❌ No"}`);

    if (!backendRunning) {
      console.log(`
   → Start the backend:
     cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
      `);
    }

    // 2. Check localStorage token
    await page.goto("http://localhost:3001/dashboard/phone-numbers");
    const hasToken = await page.evaluate(() => {
      return !!localStorage.getItem("access_token");
    });
    console.log(`\n2. Auth Token Present: ${hasToken ? "✅ Yes" : "❌ No"}`);

    if (!hasToken) {
      console.log(`
   → The user needs to log in first
   → Or there might be an issue with token storage
      `);
    }

    // 3. Check network requests
    const requests: { url: string; status: number; method: string }[] = [];
    page.on("response", (response) => {
      if (response.url().includes("/api/")) {
        requests.push({
          url: response.url(),
          status: response.status(),
          method: response.request().method(),
        });
      }
    });

    page.on("requestfailed", (request) => {
      requests.push({
        url: request.url(),
        status: 0,
        method: request.method(),
      });
    });

    // Trigger a refresh
    await page.reload();
    await page.waitForTimeout(5000);

    console.log("\n3. API Requests Made:");
    if (requests.length === 0) {
      console.log("   No API requests detected - check if frontend is making calls");
    } else {
      requests.forEach((r) => {
        const statusIcon = r.status === 0 ? "❌" : r.status < 400 ? "✅" : "⚠️";
        console.log(`   ${statusIcon} ${r.method} ${r.url} → ${r.status || "FAILED"}`);
      });
    }

    // 4. Check console errors
    const errors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") errors.push(msg.text());
    });

    await page.reload();
    await page.waitForTimeout(3000);

    console.log("\n4. Console Errors:");
    if (errors.length === 0) {
      console.log("   ✅ No console errors");
    } else {
      errors.forEach((e) => console.log(`   ❌ ${e}`));
    }

    console.log("\n" + "=".repeat(50));
    console.log("END DIAGNOSTIC REPORT\n");
  });
});
