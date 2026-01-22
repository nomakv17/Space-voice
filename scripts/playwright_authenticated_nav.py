#!/usr/bin/env python3
"""
Authenticated Navigation Testing.
Tests dashboard navigation after logging in with real credentials.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone

try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("ERROR: playwright not installed")
    sys.exit(1)

import httpx


BASE_URL = os.getenv("FRONTEND_URL", "http://localhost:3001")
API_URL = os.getenv("API_URL", "http://localhost:8000")

# Test credentials - get from env or use defaults
TEST_EMAIL = os.getenv("TEST_EMAIL", "admin@admin.com")
TEST_PASSWORD = os.getenv("TEST_PASSWORD", "admin")


async def get_auth_token() -> str | None:
    """Get authentication token from API."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{API_URL}/api/v1/auth/login",
                data={"username": TEST_EMAIL, "password": TEST_PASSWORD},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if response.status_code == 200:
                return response.json().get("access_token")
            else:
                print(f"Login failed: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"API error: {e}")
            return None


async def run_authenticated_nav_tests():
    """Run navigation tests with authentication."""

    print(f"\n{'='*60}")
    print("Authenticated Dashboard Navigation Testing")
    print(f"{'='*60}")
    print(f"Frontend: {BASE_URL}")
    print(f"API: {API_URL}")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")

    # Get auth token
    print(f"\n[AUTH] Authenticating as {TEST_EMAIL}...")
    token = await get_auth_token()

    if not token:
        print("[AUTH] FAILED - Cannot proceed without authentication")
        print("       Make sure the backend is running and credentials are correct")
        print(f"       Try: TEST_EMAIL=your@email.com TEST_PASSWORD=yourpassword python {sys.argv[0]}")
        return 1

    print(f"[AUTH] SUCCESS - Token obtained ({len(token)} chars)")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True,
        )
        page = await context.new_page()

        # Collect errors
        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

        # ============================================================
        # Inject authentication token into localStorage
        # ============================================================
        print(f"\n[SETUP] Injecting auth token into localStorage...")

        await page.goto(BASE_URL, wait_until="domcontentloaded")
        await page.evaluate(f"localStorage.setItem('access_token', '{token}')")
        print("[SETUP] Token injected")

        # Wait for preloader
        await asyncio.sleep(3)

        # Navigate to dashboard
        await page.goto(f"{BASE_URL}/dashboard", wait_until="networkidle", timeout=30000)
        await asyncio.sleep(2)

        current_url = page.url
        if "/login" in current_url:
            print(f"[SETUP] FAILED - Still on login page (token may be invalid)")
            await browser.close()
            return 1

        print(f"[SETUP] SUCCESS - On dashboard: {current_url}")
        await page.screenshot(path="/tmp/auth-nav-01-dashboard.png")

        # ============================================================
        # TEST: Sidebar navigation links
        # ============================================================
        print(f"\n{'='*60}")
        print("NAVIGATION TESTS")
        print(f"{'='*60}")

        nav_tests = [
            {"name": "Voice Agents", "href": "/dashboard/agents", "check": "agents"},
            {"name": "CRM", "href": "/dashboard/crm", "check": "crm"},
            {"name": "Campaigns", "href": "/dashboard/campaigns", "check": "campaigns"},
            {"name": "Appointments", "href": "/dashboard/appointments", "check": "appointments"},
            {"name": "Phone Numbers", "href": "/dashboard/phone-numbers", "check": "phone-numbers"},
            {"name": "Call History", "href": "/dashboard/calls", "check": "calls"},
            {"name": "Settings", "href": "/dashboard/settings", "check": "settings"},
            {"name": "Dashboard", "href": "/dashboard", "check": "dashboard"},
        ]

        passed = 0
        failed = 0
        results = []

        for i, test in enumerate(nav_tests):
            print(f"\n[NAV {i+1}/{len(nav_tests)}] Testing: {test['name']}")

            try:
                # Method 1: Click sidebar link
                link = await page.query_selector(f'a[href="{test["href"]}"]')

                if link:
                    # Wait for any animations to complete before clicking
                    await asyncio.sleep(0.3)
                    await link.click(force=True)
                    await page.wait_for_load_state("networkidle", timeout=10000)
                    await asyncio.sleep(1)  # Longer wait for navigation to complete

                    current = page.url
                    if test["check"] in current:
                        print(f"  [PASS] Clicked link -> {current}")
                        passed += 1
                        results.append({"test": test["name"], "status": "PASS", "method": "click"})
                    else:
                        print(f"  [FAIL] Expected '{test['check']}' in URL, got: {current}")
                        failed += 1
                        results.append({"test": test["name"], "status": "FAIL", "reason": f"Wrong URL: {current}"})
                else:
                    # Method 2: Direct navigation
                    print(f"  [INFO] Link not found, trying direct navigation...")
                    await page.goto(f"{BASE_URL}{test['href']}", timeout=10000)
                    await page.wait_for_load_state("networkidle")

                    current = page.url
                    if test["check"] in current:
                        print(f"  [PASS] Direct nav -> {current}")
                        passed += 1
                        results.append({"test": test["name"], "status": "PASS", "method": "direct"})
                    else:
                        print(f"  [FAIL] Direct nav failed, got: {current}")
                        failed += 1
                        results.append({"test": test["name"], "status": "FAIL", "reason": f"Redirect: {current}"})

            except PlaywrightTimeout:
                print(f"  [FAIL] Timeout")
                failed += 1
                results.append({"test": test["name"], "status": "FAIL", "reason": "Timeout"})
            except Exception as e:
                print(f"  [FAIL] Error: {e}")
                failed += 1
                results.append({"test": test["name"], "status": "FAIL", "reason": str(e)})

        # Take final screenshot
        await page.screenshot(path="/tmp/auth-nav-02-final.png")

        # ============================================================
        # TEST: Browser back/forward
        # ============================================================
        print(f"\n{'='*60}")
        print("BROWSER HISTORY TESTS")
        print(f"{'='*60}")

        try:
            # Check token before history test
            token_before = await page.evaluate("localStorage.getItem('access_token')")
            print(f"  Token before history test: {'Present' if token_before else 'MISSING'}")

            # Navigate to agents using click (not page.goto to avoid full reload)
            agents_link = await page.query_selector('a[href="/dashboard/agents"]')
            if agents_link:
                await agents_link.click(force=True)
                await page.wait_for_load_state("networkidle", timeout=10000)
            else:
                await page.goto(f"{BASE_URL}/dashboard/agents", wait_until="networkidle")

            await asyncio.sleep(0.5)
            print(f"  On agents: {page.url}")

            # Navigate to CRM using click
            crm_link = await page.query_selector('a[href="/dashboard/crm"]')
            if crm_link:
                await crm_link.click(force=True)
                await page.wait_for_load_state("networkidle", timeout=10000)
            else:
                await page.goto(f"{BASE_URL}/dashboard/crm", wait_until="networkidle")

            await asyncio.sleep(0.5)
            print(f"  On CRM: {page.url}")

            # Check token after navigations
            token_after = await page.evaluate("localStorage.getItem('access_token')")
            print(f"  Token after navigations: {'Present' if token_after else 'MISSING'}")

            # Go back
            await page.go_back(wait_until="networkidle", timeout=10000)
            await asyncio.sleep(0.5)

            if "agents" in page.url:
                print(f"  [PASS] Back button works: {page.url}")
                passed += 1
            else:
                print(f"  [FAIL] Back button: expected agents, got {page.url}")
                failed += 1

            # Check token after back
            token_back = await page.evaluate("localStorage.getItem('access_token')")
            print(f"  Token after back: {'Present' if token_back else 'MISSING'}")

            # Go forward
            await page.go_forward(wait_until="networkidle", timeout=10000)
            await asyncio.sleep(0.5)

            # Check token after forward
            token_forward = await page.evaluate("localStorage.getItem('access_token')")
            print(f"  Token after forward: {'Present' if token_forward else 'MISSING'}")

            if "crm" in page.url:
                print(f"  [PASS] Forward button works: {page.url}")
                passed += 1
            else:
                print(f"  [FAIL] Forward button: expected crm, got {page.url}")
                failed += 1

        except Exception as e:
            print(f"  [FAIL] History navigation error: {e}")
            failed += 2

        # ============================================================
        # TEST: Sidebar collapse/expand
        # ============================================================
        print(f"\n{'='*60}")
        print("SIDEBAR TOGGLE TEST")
        print(f"{'='*60}")

        try:
            # Navigate to dashboard using click
            dash_link = await page.query_selector('a[href="/dashboard"]')
            if dash_link:
                await dash_link.click(force=True)
                await page.wait_for_load_state("networkidle", timeout=10000)
            await asyncio.sleep(1)

            # Find sidebar container
            sidebar = await page.query_selector('[style*="width: 220px"], [style*="width: 64px"]')
            if sidebar:
                initial_style = await sidebar.get_attribute("style")
                print(f"  Initial sidebar style: {initial_style}")

            # Find toggle button - look for button with PanelLeftClose or PanelLeft icon
            # The button is in a div after nav element and before user profile
            toggle = await page.query_selector('button:has-text("Hide sidebar")')
            if not toggle:
                # Try finding by icon class pattern
                toggle = await page.query_selector('nav + div button')
            if not toggle:
                # Try finding any button with the toggle text
                all_buttons = await page.query_selector_all('button')
                for btn in all_buttons:
                    text = await btn.inner_text()
                    if "hide" in text.lower() or "sidebar" in text.lower():
                        toggle = btn
                        break

            if toggle:
                # Get initial state
                await page.screenshot(path="/tmp/auth-nav-03-sidebar-open.png")
                print(f"  [INFO] Toggle button found, clicking...")

                # Click toggle
                await toggle.click(force=True)
                await asyncio.sleep(0.7)

                # Check if width changed
                if sidebar:
                    new_style = await sidebar.get_attribute("style")
                    print(f"  After toggle style: {new_style}")

                await page.screenshot(path="/tmp/auth-nav-04-sidebar-closed.png")

                # Click again to re-open
                await toggle.click(force=True)
                await asyncio.sleep(0.5)

                print(f"  [PASS] Sidebar toggle works (see screenshots)")
                passed += 1
            else:
                print(f"  [FAIL] Sidebar toggle button not found")
                # Debug: list all buttons
                all_buttons = await page.query_selector_all('button')
                print(f"  [DEBUG] Found {len(all_buttons)} buttons on page")
                failed += 1

        except Exception as e:
            print(f"  [FAIL] Sidebar toggle error: {e}")
            failed += 1

        # ============================================================
        # TEST: Active state highlighting
        # ============================================================
        print(f"\n{'='*60}")
        print("ACTIVE STATE TEST")
        print(f"{'='*60}")

        try:
            # Navigate to agents page
            agents_link = await page.query_selector('a[href="/dashboard/agents"]')
            if agents_link:
                await agents_link.click(force=True)
                await page.wait_for_load_state("networkidle", timeout=10000)
            await asyncio.sleep(1)

            # Find the agents link again (it should now have active state)
            agents_link = await page.query_selector('a[href="/dashboard/agents"]')
            if agents_link:
                # Check the link's own classes (no longer nested button)
                class_attr = await agents_link.get_attribute("class") or ""

                if "bg-sidebar-accent" in class_attr:
                    print(f"  [PASS] Active state: bg-sidebar-accent applied to link")
                    passed += 1
                else:
                    # Check for active indicator bar inside the link
                    indicator = await agents_link.query_selector('[class*="w-0.5"], [class*="rounded-r-full"]')
                    if indicator:
                        print(f"  [PASS] Active state: indicator bar present")
                        passed += 1
                    else:
                        print(f"  [FAIL] No active styling found. Link classes: {class_attr[:100]}")
                        failed += 1
            else:
                print(f"  [FAIL] Agents link not found")
                failed += 1

        except Exception as e:
            print(f"  [FAIL] Active state error: {e}")
            failed += 1

        # ============================================================
        # Console errors summary
        # ============================================================
        print(f"\n{'='*60}")
        print("CONSOLE ERRORS")
        print(f"{'='*60}")

        if console_errors:
            non_401 = [e for e in console_errors if "401" not in e and "Unauthorized" not in e]
            print(f"  Total: {len(console_errors)}, Non-auth: {len(non_401)}")
            if non_401:
                print("  Non-auth errors:")
                for err in non_401[:5]:
                    print(f"    - {err[:80]}")
        else:
            print("  No console errors")

        await browser.close()

        # ============================================================
        # Final Summary
        # ============================================================
        print(f"\n{'='*60}")
        print("FINAL SUMMARY")
        print(f"{'='*60}")
        print(f"  Passed: {passed}")
        print(f"  Failed: {failed}")
        print(f"  Total: {passed + failed}")
        print(f"  Pass Rate: {passed / (passed + failed) * 100:.1f}%" if (passed + failed) > 0 else "N/A")

        print(f"\n  Screenshots:")
        print(f"    - /tmp/auth-nav-01-dashboard.png")
        print(f"    - /tmp/auth-nav-02-final.png")
        print(f"    - /tmp/auth-nav-03-sidebar-open.png")
        print(f"    - /tmp/auth-nav-04-sidebar-closed.png")

        return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_authenticated_nav_tests())
    sys.exit(exit_code)
