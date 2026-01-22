#!/usr/bin/env python3
"""
SpaceVoice Navigation Bug Testing Script
Uses Playwright to test sidebar navigation and route transitions.
"""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("ERROR: playwright not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(1)


# Navigation routes to test (from app-sidebar.tsx)
NAVIGATION_ROUTES = [
    {"name": "Dashboard", "href": "/dashboard", "exact": True},
    {"name": "Voice Agents", "href": "/dashboard/agents", "exact": False},
    {"name": "Workspaces", "href": "/dashboard/workspaces", "exact": False},
    {"name": "CRM", "href": "/dashboard/crm", "exact": False},
    {"name": "Campaigns", "href": "/dashboard/campaigns", "exact": False},
    {"name": "Appointments", "href": "/dashboard/appointments", "exact": False},
    {"name": "Integrations", "href": "/dashboard/integrations", "exact": False},
    {"name": "Phone Numbers", "href": "/dashboard/phone-numbers", "exact": False},
    {"name": "Call History", "href": "/dashboard/calls", "exact": False},
    {"name": "Test Agent", "href": "/dashboard/test", "exact": False},
]


class NavigationTestResult:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failures = []
        self.console_errors = []
        self.screenshots = []

    def pass_test(self, name: str, message: str = ""):
        self.tests_run += 1
        self.tests_passed += 1
        print(f"  [PASS] {name}: {message}")

    def fail_test(self, name: str, reason: str):
        self.tests_run += 1
        self.tests_failed += 1
        self.failures.append({"test": name, "reason": reason})
        print(f"  [FAIL] {name}: {reason}")

    def add_console_error(self, error: str):
        self.console_errors.append(error)


async def run_navigation_tests(base_url: str = "http://localhost:3001") -> NavigationTestResult:
    """Run comprehensive navigation tests."""
    result = NavigationTestResult()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True,
        )
        page = await context.new_page()

        # Collect console errors
        page.on("console", lambda msg: result.add_console_error(msg.text) if msg.type == "error" else None)

        print(f"\n{'='*60}")
        print(f"SpaceVoice Navigation Bug Testing")
        print(f"{'='*60}")
        print(f"Target: {base_url}")
        print(f"Time: {datetime.now(timezone.utc).isoformat()}")
        print(f"{'='*60}")

        # ============================================================
        # TEST 1: Initial page load and redirect
        # ============================================================
        print("\n[TEST GROUP 1] Initial Page Load & Authentication")
        print("-" * 40)

        try:
            response = await page.goto(base_url, wait_until="networkidle", timeout=30000)
            if response and response.ok:
                result.pass_test("Homepage loads", f"Status {response.status}")
            else:
                result.fail_test("Homepage loads", f"Status {response.status if response else 'None'}")
        except PlaywrightTimeout:
            result.fail_test("Homepage loads", "Timeout after 30s")
        except Exception as e:
            result.fail_test("Homepage loads", str(e))

        # Check for redirect to login
        await asyncio.sleep(1)
        current_url = page.url
        if "/login" in current_url or "/auth" in current_url:
            result.pass_test("Auth redirect", f"Redirected to {current_url}")
        else:
            result.pass_test("No auth redirect", f"Stayed at {current_url}")

        # ============================================================
        # TEST 2: Login form (if on login page)
        # ============================================================
        print("\n[TEST GROUP 2] Login Page Testing")
        print("-" * 40)

        if "/login" in page.url or "/auth" in page.url:
            try:
                email_input = await page.wait_for_selector(
                    'input[type="email"], input[name="email"], input[placeholder*="email" i]',
                    timeout=5000
                )
                password_input = await page.query_selector('input[type="password"]')
                submit_btn = await page.query_selector('button[type="submit"]')

                if email_input and password_input:
                    result.pass_test("Login form elements", "Email and password fields found")
                else:
                    result.fail_test("Login form elements", "Missing email or password field")

                if submit_btn:
                    result.pass_test("Submit button", "Found")
                else:
                    result.fail_test("Submit button", "Not found")

                # Take screenshot of login page
                await page.screenshot(path="/tmp/nav-test-login.png", full_page=True)
                result.screenshots.append("/tmp/nav-test-login.png")

            except Exception as e:
                result.fail_test("Login page", str(e))

            # Try to bypass auth for navigation testing (direct URL access)
            print("\n[INFO] Attempting direct dashboard access for navigation testing...")

        # ============================================================
        # TEST 3: Navigation sidebar presence
        # ============================================================
        print("\n[TEST GROUP 3] Navigation Sidebar")
        print("-" * 40)

        try:
            # Try direct dashboard access
            await page.goto(f"{base_url}/dashboard", wait_until="networkidle", timeout=20000)
            await asyncio.sleep(2)

            # Check if redirected back to login
            if "/login" in page.url or "/auth" in page.url:
                print("  [INFO] Redirected to login - authentication required")
                print("  [INFO] Navigation tests will be limited without auth")
            else:
                # Look for sidebar elements
                sidebar = await page.query_selector('[class*="sidebar"], nav, aside')
                if sidebar:
                    result.pass_test("Sidebar present", "Navigation sidebar found")
                else:
                    result.fail_test("Sidebar present", "No sidebar element found")

                # Check for navigation links
                nav_links = await page.query_selector_all('a[href*="/dashboard"]')
                if len(nav_links) >= 5:
                    result.pass_test("Navigation links", f"Found {len(nav_links)} dashboard links")
                else:
                    result.fail_test("Navigation links", f"Only found {len(nav_links)} links, expected 5+")

        except Exception as e:
            result.fail_test("Sidebar check", str(e))

        # ============================================================
        # TEST 4: Route navigation tests (client-side)
        # ============================================================
        print("\n[TEST GROUP 4] Route Navigation Tests")
        print("-" * 40)

        if "/login" not in page.url and "/auth" not in page.url:
            for route in NAVIGATION_ROUTES:
                try:
                    # Find and click the navigation link
                    link = await page.query_selector(f'a[href="{route["href"]}"]')

                    if link:
                        await link.click()
                        await page.wait_for_load_state("networkidle", timeout=10000)
                        await asyncio.sleep(0.5)

                        current = page.url
                        if route["href"] in current:
                            result.pass_test(f"Nav to {route['name']}", f"URL: {current}")
                        else:
                            result.fail_test(f"Nav to {route['name']}", f"Expected {route['href']}, got {current}")
                    else:
                        # Try direct navigation
                        await page.goto(f"{base_url}{route['href']}", timeout=10000)
                        await page.wait_for_load_state("networkidle")

                        if route["href"] in page.url:
                            result.pass_test(f"Direct nav to {route['name']}", f"URL loaded")
                        else:
                            result.fail_test(f"Nav to {route['name']}", f"Link not found and redirect occurred")

                except PlaywrightTimeout:
                    result.fail_test(f"Nav to {route['name']}", "Navigation timeout")
                except Exception as e:
                    result.fail_test(f"Nav to {route['name']}", str(e))
        else:
            print("  [SKIP] Navigation tests skipped - auth required")

        # ============================================================
        # TEST 5: Browser back/forward navigation
        # ============================================================
        print("\n[TEST GROUP 5] Browser History Navigation")
        print("-" * 40)

        if "/login" not in page.url and "/auth" not in page.url:
            try:
                # Navigate to a known page first
                await page.goto(f"{base_url}/dashboard/agents", wait_until="networkidle", timeout=10000)
                initial_url = page.url

                # Navigate to another page
                await page.goto(f"{base_url}/dashboard/crm", wait_until="networkidle", timeout=10000)

                # Go back
                await page.go_back(wait_until="networkidle", timeout=10000)
                await asyncio.sleep(0.5)

                if "/agents" in page.url:
                    result.pass_test("Browser back", f"Returned to {page.url}")
                else:
                    result.fail_test("Browser back", f"Expected agents, got {page.url}")

                # Go forward
                await page.go_forward(wait_until="networkidle", timeout=10000)
                await asyncio.sleep(0.5)

                if "/crm" in page.url:
                    result.pass_test("Browser forward", f"Forward to {page.url}")
                else:
                    result.fail_test("Browser forward", f"Expected crm, got {page.url}")

            except Exception as e:
                result.fail_test("Browser history", str(e))
        else:
            print("  [SKIP] History tests skipped - auth required")

        # ============================================================
        # TEST 6: Sidebar collapse/expand
        # ============================================================
        print("\n[TEST GROUP 6] Sidebar Toggle")
        print("-" * 40)

        if "/login" not in page.url and "/auth" not in page.url:
            try:
                # Find sidebar toggle button
                toggle_btn = await page.query_selector('button:has-text("Hide sidebar"), button:has([class*="PanelLeft"])')

                if toggle_btn:
                    # Get initial sidebar width
                    sidebar = await page.query_selector('[class*="sidebar"]')
                    if sidebar:
                        initial_box = await sidebar.bounding_box()
                        initial_width = initial_box["width"] if initial_box else 0

                        # Click toggle
                        await toggle_btn.click()
                        await asyncio.sleep(0.5)

                        # Get new width
                        new_box = await sidebar.bounding_box()
                        new_width = new_box["width"] if new_box else 0

                        if new_width != initial_width:
                            result.pass_test("Sidebar toggle", f"Width changed: {initial_width} -> {new_width}")
                        else:
                            result.fail_test("Sidebar toggle", f"Width unchanged: {new_width}")
                    else:
                        result.fail_test("Sidebar toggle", "Sidebar element not found")
                else:
                    result.fail_test("Sidebar toggle", "Toggle button not found")

            except Exception as e:
                result.fail_test("Sidebar toggle", str(e))
        else:
            print("  [SKIP] Sidebar toggle skipped - auth required")

        # ============================================================
        # TEST 7: Active state highlighting
        # ============================================================
        print("\n[TEST GROUP 7] Active State Highlighting")
        print("-" * 40)

        if "/login" not in page.url and "/auth" not in page.url:
            try:
                await page.goto(f"{base_url}/dashboard/agents", wait_until="networkidle", timeout=10000)

                # Find the agents link and check for active styling
                agents_link = await page.query_selector('a[href="/dashboard/agents"]')
                if agents_link:
                    # Check for active indicator (the vertical bar)
                    active_indicator = await agents_link.query_selector('[class*="bg-sidebar-foreground"], [class*="w-0.5"]')

                    # Or check for active class on the button
                    button = await agents_link.query_selector('button')
                    if button:
                        class_attr = await button.get_attribute("class")
                        if "bg-sidebar-accent" in (class_attr or ""):
                            result.pass_test("Active state", "Active styling applied to current route")
                        elif active_indicator:
                            result.pass_test("Active state", "Active indicator present")
                        else:
                            result.fail_test("Active state", f"No active styling found. Classes: {class_attr}")
                    else:
                        result.fail_test("Active state", "Button not found in link")
                else:
                    result.fail_test("Active state", "Agents link not found")

            except Exception as e:
                result.fail_test("Active state", str(e))
        else:
            print("  [SKIP] Active state tests skipped - auth required")

        # ============================================================
        # Final screenshot
        # ============================================================
        try:
            await page.screenshot(path="/tmp/nav-test-final.png", full_page=True)
            result.screenshots.append("/tmp/nav-test-final.png")
        except:
            pass

        await browser.close()

    return result


async def main():
    """Main entry point."""
    result = await run_navigation_tests()

    # Print summary
    print(f"\n{'='*60}")
    print("NAVIGATION TEST RESULTS")
    print(f"{'='*60}")
    print(f"\nTotal tests: {result.tests_run}")
    print(f"Passed: {result.tests_passed}")
    print(f"Failed: {result.tests_failed}")
    print(f"Pass rate: {result.tests_passed/result.tests_run*100:.1f}%" if result.tests_run > 0 else "N/A")

    if result.failures:
        print(f"\n{'='*60}")
        print("FAILURES:")
        print(f"{'='*60}")
        for f in result.failures:
            print(f"  - {f['test']}: {f['reason']}")

    if result.console_errors:
        print(f"\n{'='*60}")
        print(f"CONSOLE ERRORS ({len(result.console_errors)}):")
        print(f"{'='*60}")
        for err in result.console_errors[:10]:
            print(f"  - {err[:100]}")

    if result.screenshots:
        print(f"\nScreenshots saved:")
        for ss in result.screenshots:
            print(f"  - {ss}")

    print(f"\n{'='*60}")

    return 0 if result.tests_failed == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
