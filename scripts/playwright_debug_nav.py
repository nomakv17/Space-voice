#!/usr/bin/env python3
"""
Debug Navigation - Detailed click analysis.
"""

import asyncio
import os
import sys

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("ERROR: playwright not installed")
    sys.exit(1)

import httpx

BASE_URL = os.getenv("FRONTEND_URL", "http://localhost:3001")
API_URL = os.getenv("API_URL", "http://localhost:8000")
TEST_EMAIL = os.getenv("TEST_EMAIL", "test@playwright.local")
TEST_PASSWORD = os.getenv("TEST_PASSWORD", "testpass123")


async def get_auth_token() -> str | None:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_URL}/api/v1/auth/login",
            data={"username": TEST_EMAIL, "password": TEST_PASSWORD},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if response.status_code == 200:
            return response.json().get("access_token")
        return None


async def debug_navigation():
    """Debug navigation click behavior."""

    print("\n=== Navigation Debug Test ===\n")

    token = await get_auth_token()
    if not token:
        print("AUTH FAILED")
        return

    print(f"Token obtained: {len(token)} chars")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()

        # Inject token
        await page.goto(BASE_URL)
        await page.evaluate(f"localStorage.setItem('access_token', '{token}')")

        # Wait for preloader (3 seconds)
        await asyncio.sleep(3.5)

        # Go to dashboard
        await page.goto(f"{BASE_URL}/dashboard", wait_until="networkidle", timeout=30000)
        await asyncio.sleep(2)

        print(f"Initial URL: {page.url}")

        # Analyze navigation link structure
        print("\n--- Analyzing navigation link structure ---")

        links_info = await page.evaluate("""() => {
            const links = document.querySelectorAll('a[href*="/dashboard"]');
            return Array.from(links).map(link => ({
                href: link.getAttribute('href'),
                text: link.textContent.trim().substring(0, 30),
                hasButton: link.querySelector('button') !== null,
                buttonClasses: link.querySelector('button')?.className || 'N/A',
                isVisible: link.offsetParent !== null,
                rect: link.getBoundingClientRect()
            }));
        }""")

        print(f"\nFound {len(links_info)} navigation links:")
        for info in links_info[:12]:
            print(f"  - {info['href']}: visible={info['isVisible']}, hasButton={info['hasButton']}")

        # Test clicking different navigation items
        print("\n--- Testing navigation clicks ---")

        routes_to_test = [
            "/dashboard/campaigns",
            "/dashboard/appointments",
            "/dashboard/phone-numbers",
        ]

        for route in routes_to_test:
            print(f"\n[Testing {route}]")

            # Method 1: Click the link directly
            link = await page.query_selector(f'a[href="{route}"]')
            if link:
                # Check if link is visible and clickable
                is_visible = await link.is_visible()
                box = await link.bounding_box()
                print(f"  Link found: visible={is_visible}, box={box}")

                if is_visible and box:
                    # Try clicking the link element directly
                    await link.click(force=True)
                    await asyncio.sleep(1)
                    print(f"  After click: {page.url}")

                    # Check if we actually navigated
                    if route not in page.url:
                        print(f"  [BUG] Navigation failed! Still on: {page.url}")

                        # Try method 2: Click the button inside
                        button = await link.query_selector("button")
                        if button:
                            print(f"  Trying button click...")
                            await button.click(force=True)
                            await asyncio.sleep(1)
                            print(f"  After button click: {page.url}")

                        # Method 3: Direct navigation
                        if route not in page.url:
                            print(f"  Trying direct navigation...")
                            await page.goto(f"{BASE_URL}{route}", wait_until="networkidle")
                            await asyncio.sleep(1)
                            print(f"  After direct nav: {page.url}")
            else:
                print(f"  Link NOT FOUND for {route}")

        # Check localStorage token persistence
        print("\n--- Checking token persistence ---")
        token_check = await page.evaluate("localStorage.getItem('access_token')")
        print(f"Token in localStorage: {'Present' if token_check else 'MISSING!'}")

        # Screenshot final state
        await page.screenshot(path="/tmp/nav-debug-final.png")
        print("\nScreenshot saved: /tmp/nav-debug-final.png")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(debug_navigation())
