#!/usr/bin/env python3
"""
Detailed Navigation Bug Testing - with preloader wait and direct route access.
"""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("ERROR: playwright not installed")
    sys.exit(1)


async def run_detailed_tests(base_url: str = "http://localhost:3001"):
    """Run detailed navigation tests."""

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True,
        )
        page = await context.new_page()

        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

        print(f"\n{'='*60}")
        print("Detailed Navigation Bug Testing")
        print(f"{'='*60}")
        print(f"Target: {base_url}")
        print(f"Time: {datetime.now(timezone.utc).isoformat()}")

        # ============================================================
        # TEST 1: Wait for preloader to fully disappear
        # ============================================================
        print("\n[TEST 1] Preloader behavior test")
        print("-" * 40)

        await page.goto(base_url, wait_until="domcontentloaded", timeout=30000)

        # Take screenshot immediately
        await page.screenshot(path="/tmp/nav-1-immediate.png")
        print(f"  [Screenshot] /tmp/nav-1-immediate.png (immediate)")

        # Wait 1 second
        await asyncio.sleep(1)
        await page.screenshot(path="/tmp/nav-2-1second.png")
        print(f"  [Screenshot] /tmp/nav-2-1second.png (1s)")

        # Wait 2 more seconds (preloader should be gone by now)
        await asyncio.sleep(2)
        await page.screenshot(path="/tmp/nav-3-3seconds.png")
        print(f"  [Screenshot] /tmp/nav-3-3seconds.png (3s)")

        # Check if preloader is still visible
        preloader = await page.query_selector('[class*="z-[9999]"]')
        if preloader:
            is_visible = await preloader.is_visible()
            print(f"  [WARNING] Preloader element exists, visible: {is_visible}")
        else:
            print(f"  [PASS] Preloader no longer in DOM")

        # ============================================================
        # TEST 2: Login form interaction
        # ============================================================
        print("\n[TEST 2] Login form interaction")
        print("-" * 40)

        await page.wait_for_load_state("networkidle", timeout=10000)

        # Check current URL
        print(f"  Current URL: {page.url}")

        # Find the Client ID input (not type="email" but has "client" in id/name)
        client_input = await page.query_selector('#clientId, input[name="clientId"]')
        password_input = await page.query_selector('input[type="password"]')
        submit_btn = await page.query_selector('button[type="submit"]')

        if client_input:
            print(f"  [PASS] Client ID input found")
            input_type = await client_input.get_attribute("type")
            print(f"         Input type: {input_type}")
        else:
            print(f"  [FAIL] Client ID input NOT found")

        if password_input:
            print(f"  [PASS] Password input found")
        else:
            print(f"  [FAIL] Password input NOT found")

        if submit_btn:
            print(f"  [PASS] Submit button found")
            btn_text = await submit_btn.inner_text()
            print(f"         Button text: {btn_text}")
        else:
            print(f"  [FAIL] Submit button NOT found")

        # ============================================================
        # TEST 3: Attempt login with test credentials
        # ============================================================
        print("\n[TEST 3] Test login flow")
        print("-" * 40)

        if client_input and password_input and submit_btn:
            # Try a test login
            await client_input.fill("admin@test.com")
            await password_input.fill("wrongpassword")

            await page.screenshot(path="/tmp/nav-4-filled-form.png")
            print(f"  [Screenshot] /tmp/nav-4-filled-form.png (form filled)")

            await submit_btn.click()

            # Wait for response
            await asyncio.sleep(2)
            await page.screenshot(path="/tmp/nav-5-after-submit.png")
            print(f"  [Screenshot] /tmp/nav-5-after-submit.png (after submit)")

            # Check for error message or redirect
            error_msg = await page.query_selector('[class*="destructive"], [role="alert"]')
            if error_msg:
                error_text = await error_msg.inner_text()
                print(f"  [INFO] Error message displayed: {error_text[:50]}...")

            if page.url != f"{base_url}/login":
                print(f"  [INFO] Page changed to: {page.url}")

        # ============================================================
        # TEST 4: Direct route access test (bypassing login)
        # ============================================================
        print("\n[TEST 4] Direct route access test")
        print("-" * 40)

        routes_to_test = [
            "/dashboard",
            "/dashboard/agents",
            "/dashboard/crm",
            "/dashboard/settings",
        ]

        for route in routes_to_test:
            try:
                await page.goto(f"{base_url}{route}", wait_until="networkidle", timeout=10000)
                await asyncio.sleep(0.5)

                final_url = page.url
                if "/login" in final_url:
                    print(f"  {route} -> Redirected to login (auth required)")
                else:
                    print(f"  {route} -> {final_url} (accessible)")
            except Exception as e:
                print(f"  {route} -> Error: {e}")

        # ============================================================
        # TEST 5: Check for JS errors during navigation
        # ============================================================
        print("\n[TEST 5] Console errors check")
        print("-" * 40)

        if console_errors:
            # Filter out common 401 errors
            non_401_errors = [e for e in console_errors if "401" not in e]

            print(f"  Total console errors: {len(console_errors)}")
            print(f"  401 errors (expected when not logged in): {len(console_errors) - len(non_401_errors)}")
            print(f"  Other errors: {len(non_401_errors)}")

            if non_401_errors:
                print("\n  Non-401 errors:")
                for err in non_401_errors[:5]:
                    print(f"    - {err[:100]}")
        else:
            print(f"  [PASS] No console errors detected")

        # ============================================================
        # TEST 6: Page performance metrics
        # ============================================================
        print("\n[TEST 6] Performance metrics")
        print("-" * 40)

        try:
            metrics = await page.evaluate("""() => {
                const navigation = performance.getEntriesByType('navigation')[0];
                return {
                    loadComplete: navigation ? navigation.loadEventEnd : 0,
                    domComplete: navigation ? navigation.domComplete : 0,
                    firstPaint: performance.getEntriesByName('first-paint')[0]?.startTime || 0,
                    firstContentfulPaint: performance.getEntriesByName('first-contentful-paint')[0]?.startTime || 0
                };
            }""")

            print(f"  DOM Complete: {metrics.get('domComplete', 0):.0f}ms")
            print(f"  Load Complete: {metrics.get('loadComplete', 0):.0f}ms")
            print(f"  First Paint: {metrics.get('firstPaint', 0):.0f}ms")
            print(f"  First Contentful Paint: {metrics.get('firstContentfulPaint', 0):.0f}ms")

        except Exception as e:
            print(f"  Could not get metrics: {e}")

        await browser.close()

    print(f"\n{'='*60}")
    print("Screenshots saved in /tmp/nav-*.png")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(run_detailed_tests())
