#!/usr/bin/env python3
"""
SpaceVoice UI Stability Audit Script
Uses Playwright to test the frontend dashboard.
"""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

# Check for playwright
try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("ERROR: playwright not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(1)


class UIAuditResult:
    def __init__(self):
        self.score = 10  # Start with perfect score
        self.issues = []
        self.warnings = []
        self.passed = []
        self.screenshots = []

    def deduct(self, points: int, reason: str):
        self.score = max(0, self.score - points)
        self.issues.append(reason)

    def warn(self, message: str):
        self.warnings.append(message)

    def passed_check(self, message: str):
        self.passed.append(message)


async def run_ui_audit(base_url: str = "http://localhost:3000") -> UIAuditResult:
    """Run comprehensive UI audit using Playwright."""
    result = UIAuditResult()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True,
        )
        page = await context.new_page()

        print(f"\n[{datetime.now(timezone.utc).isoformat()}] Starting UI Audit...")
        print(f"Target: {base_url}")
        print("-" * 60)

        # Test 1: Homepage loads
        print("\n[TEST 1] Homepage accessibility...")
        try:
            response = await page.goto(base_url, wait_until="networkidle", timeout=30000)
            if response and response.ok:
                result.passed_check("Homepage loads successfully")
                print("  PASS: Homepage accessible")
            else:
                result.deduct(2, f"Homepage returned status {response.status if response else 'no response'}")
                print(f"  FAIL: Homepage returned {response.status if response else 'no response'}")
        except PlaywrightTimeout:
            result.deduct(3, "Homepage timeout (>30s)")
            print("  FAIL: Homepage timeout")
        except Exception as e:
            result.deduct(3, f"Homepage error: {str(e)}")
            print(f"  FAIL: {e}")

        # Test 2: Check if redirected to login (expected behavior)
        print("\n[TEST 2] Authentication redirect...")
        current_url = page.url
        if "login" in current_url.lower():
            result.passed_check("Redirects to login page (authentication working)")
            print("  PASS: Properly redirects to login")
        else:
            result.warn("Did not redirect to login - may be unauthenticated access")
            print("  WARN: No redirect to login")

        # Test 3: Login page elements
        print("\n[TEST 3] Login page elements...")
        try:
            # Wait for page to stabilize
            await page.wait_for_load_state("networkidle", timeout=10000)

            # Check for login form elements
            email_input = await page.query_selector('input[type="email"], input[name="email"], input[placeholder*="email" i]')
            password_input = await page.query_selector('input[type="password"]')
            submit_button = await page.query_selector('button[type="submit"], button:has-text("Sign"), button:has-text("Login"), button:has-text("Log in")')

            if email_input and password_input:
                result.passed_check("Login form has email and password fields")
                print("  PASS: Email and password inputs found")
            else:
                result.deduct(1, "Login form missing required fields")
                print("  FAIL: Missing login form fields")

            if submit_button:
                result.passed_check("Login submit button present")
                print("  PASS: Submit button found")
            else:
                result.warn("Login submit button not found")
                print("  WARN: Submit button not found")

        except Exception as e:
            result.deduct(1, f"Login page check error: {str(e)}")
            print(f"  FAIL: {e}")

        # Test 4: Take screenshot of current state
        print("\n[TEST 4] Screenshot capture...")
        try:
            screenshot_path = Path("/tmp/ui-audit.png")
            await page.screenshot(path=str(screenshot_path), full_page=True)
            result.screenshots.append(str(screenshot_path))
            result.passed_check(f"Screenshot saved to {screenshot_path}")
            print(f"  PASS: Screenshot saved to {screenshot_path}")
        except Exception as e:
            result.warn(f"Screenshot failed: {str(e)}")
            print(f"  WARN: Screenshot failed: {e}")

        # Test 5: Check for console errors
        print("\n[TEST 5] Console errors check...")
        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

        # Navigate again to capture console messages
        try:
            await page.reload(wait_until="networkidle", timeout=15000)
            await asyncio.sleep(2)  # Wait for any delayed errors

            if console_errors:
                for err in console_errors[:5]:  # Limit to first 5
                    result.warn(f"Console error: {err[:100]}")
                print(f"  WARN: {len(console_errors)} console error(s) detected")
            else:
                result.passed_check("No console errors detected")
                print("  PASS: No console errors")
        except Exception as e:
            result.warn(f"Console check error: {str(e)}")
            print(f"  WARN: {e}")

        # Test 6: Performance metrics
        print("\n[TEST 6] Performance metrics...")
        try:
            metrics = await page.evaluate("""() => {
                const timing = performance.timing;
                return {
                    loadTime: timing.loadEventEnd - timing.navigationStart,
                    domContentLoaded: timing.domContentLoadedEventEnd - timing.navigationStart,
                    firstPaint: performance.getEntriesByType('paint')[0]?.startTime || 0
                };
            }""")

            load_time = metrics.get('loadTime', 0)
            if load_time > 0 and load_time < 5000:
                result.passed_check(f"Page load time: {load_time}ms")
                print(f"  PASS: Load time {load_time}ms")
            elif load_time > 5000:
                result.deduct(1, f"Slow page load: {load_time}ms (>5s)")
                print(f"  WARN: Slow load time {load_time}ms")
            else:
                print(f"  INFO: Load time metrics: {metrics}")

        except Exception as e:
            result.warn(f"Performance check error: {str(e)}")
            print(f"  WARN: {e}")

        # Test 7: Accessibility basics
        print("\n[TEST 7] Basic accessibility...")
        try:
            # Check for basic accessibility attributes
            html_lang = await page.evaluate("document.documentElement.lang")
            title = await page.title()

            if html_lang:
                result.passed_check(f"HTML lang attribute set: {html_lang}")
                print(f"  PASS: HTML lang='{html_lang}'")
            else:
                result.warn("HTML lang attribute not set")
                print("  WARN: Missing HTML lang attribute")

            if title and title.strip():
                result.passed_check(f"Page title set: {title}")
                print(f"  PASS: Title='{title}'")
            else:
                result.deduct(1, "Page title not set")
                print("  FAIL: Missing page title")

        except Exception as e:
            result.warn(f"Accessibility check error: {str(e)}")
            print(f"  WARN: {e}")

        # Test 8: Mobile responsiveness check
        print("\n[TEST 8] Mobile viewport test...")
        try:
            await page.set_viewport_size({"width": 375, "height": 667})  # iPhone SE
            await page.reload(wait_until="networkidle", timeout=15000)

            mobile_screenshot = Path("/tmp/ui-audit-mobile.png")
            await page.screenshot(path=str(mobile_screenshot), full_page=True)
            result.screenshots.append(str(mobile_screenshot))
            result.passed_check("Mobile viewport renders without crash")
            print(f"  PASS: Mobile screenshot saved to {mobile_screenshot}")

        except Exception as e:
            result.warn(f"Mobile test error: {str(e)}")
            print(f"  WARN: {e}")

        await browser.close()

    return result


async def main():
    """Main entry point."""
    print("=" * 60)
    print("SpaceVoice UI Stability Audit")
    print("=" * 60)

    result = await run_ui_audit()

    print("\n" + "=" * 60)
    print("AUDIT RESULTS")
    print("=" * 60)
    print(f"\nUI STABILITY SCORE: {result.score}/10")

    if result.passed:
        print(f"\nPASSED CHECKS ({len(result.passed)}):")
        for item in result.passed:
            print(f"  [OK] {item}")

    if result.issues:
        print(f"\nISSUES ({len(result.issues)}):")
        for item in result.issues:
            print(f"  [CRITICAL] {item}")

    if result.warnings:
        print(f"\nWARNINGS ({len(result.warnings)}):")
        for item in result.warnings:
            print(f"  [WARN] {item}")

    if result.screenshots:
        print(f"\nSCREENSHOTS:")
        for ss in result.screenshots:
            print(f"  - {ss}")

    print("\n" + "=" * 60)

    # Return score for scripting
    return result.score


if __name__ == "__main__":
    score = asyncio.run(main())
    sys.exit(0 if score >= 7 else 1)
