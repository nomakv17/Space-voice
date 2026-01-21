#!/usr/bin/env python3
"""
SpaceVoice API Handshake Test Script
Tests connectivity to external APIs: Retell AI and Telnyx.
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add backend to path for config
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

try:
    import httpx
except ImportError:
    print("ERROR: httpx not installed. Run: pip install httpx")
    sys.exit(1)


class APIHandshakeResult:
    def __init__(self, name: str):
        self.name = name
        self.status = "NOT_TESTED"
        self.latency_ms = None
        self.error = None
        self.details = {}

    def passed(self):
        return self.status == "PASS"


async def test_retell_api(api_key: str) -> APIHandshakeResult:
    """Test Retell AI API connectivity."""
    result = APIHandshakeResult("Retell AI")

    if not api_key:
        result.status = "SKIP"
        result.error = "RETELL_API_KEY not configured"
        return result

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            start = datetime.now(timezone.utc)

            # Test the agents list endpoint (lightweight)
            response = await client.get(
                "https://api.retellai.com/list-agents",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )

            latency = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            result.latency_ms = round(latency, 2)

            if response.status_code == 200:
                result.status = "PASS"
                data = response.json()
                result.details["agent_count"] = len(data) if isinstance(data, list) else "unknown"
            elif response.status_code == 401:
                result.status = "FAIL"
                result.error = "Invalid API key (401 Unauthorized)"
            elif response.status_code == 403:
                result.status = "FAIL"
                result.error = "API key lacks permission (403 Forbidden)"
            else:
                result.status = "FAIL"
                result.error = f"Unexpected status: {response.status_code}"
                try:
                    result.details["response"] = response.json()
                except Exception:
                    result.details["response"] = response.text[:200]

        except httpx.TimeoutException:
            result.status = "FAIL"
            result.error = "Connection timeout (>15s)"
        except httpx.ConnectError as e:
            result.status = "FAIL"
            result.error = f"Connection error: {str(e)}"
        except Exception as e:
            result.status = "FAIL"
            result.error = f"Unexpected error: {str(e)}"

    return result


async def test_telnyx_api(api_key: str) -> APIHandshakeResult:
    """Test Telnyx API connectivity."""
    result = APIHandshakeResult("Telnyx")

    if not api_key:
        result.status = "SKIP"
        result.error = "TELNYX_API_KEY not configured"
        return result

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            start = datetime.now(timezone.utc)

            # Test the balance endpoint (lightweight, verifies auth)
            response = await client.get(
                "https://api.telnyx.com/v2/balance",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )

            latency = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            result.latency_ms = round(latency, 2)

            if response.status_code == 200:
                result.status = "PASS"
                data = response.json()
                if "data" in data:
                    balance = data["data"].get("balance", "unknown")
                    currency = data["data"].get("currency", "USD")
                    result.details["balance"] = f"{balance} {currency}"
            elif response.status_code == 401:
                result.status = "FAIL"
                result.error = "Invalid API key (401 Unauthorized)"
            elif response.status_code == 403:
                result.status = "FAIL"
                result.error = "API key lacks permission (403 Forbidden)"
            else:
                result.status = "FAIL"
                result.error = f"Unexpected status: {response.status_code}"

        except httpx.TimeoutException:
            result.status = "FAIL"
            result.error = "Connection timeout (>15s)"
        except httpx.ConnectError as e:
            result.status = "FAIL"
            result.error = f"Connection error: {str(e)}"
        except Exception as e:
            result.status = "FAIL"
            result.error = f"Unexpected error: {str(e)}"

    return result


async def test_openai_api(api_key: str) -> APIHandshakeResult:
    """Test OpenAI API connectivity."""
    result = APIHandshakeResult("OpenAI")

    if not api_key:
        result.status = "SKIP"
        result.error = "OPENAI_API_KEY not configured"
        return result

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            start = datetime.now(timezone.utc)

            # Test models endpoint (lightweight)
            response = await client.get(
                "https://api.openai.com/v1/models",
                headers={
                    "Authorization": f"Bearer {api_key}",
                },
            )

            latency = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            result.latency_ms = round(latency, 2)

            if response.status_code == 200:
                result.status = "PASS"
                data = response.json()
                result.details["model_count"] = len(data.get("data", []))
            elif response.status_code == 401:
                result.status = "FAIL"
                result.error = "Invalid API key (401 Unauthorized)"
            else:
                result.status = "FAIL"
                result.error = f"Unexpected status: {response.status_code}"

        except httpx.TimeoutException:
            result.status = "FAIL"
            result.error = "Connection timeout (>15s)"
        except Exception as e:
            result.status = "FAIL"
            result.error = f"Unexpected error: {str(e)}"

    return result


async def test_anthropic_api(api_key: str) -> APIHandshakeResult:
    """Test Anthropic Claude API connectivity."""
    result = APIHandshakeResult("Anthropic Claude")

    if not api_key:
        result.status = "SKIP"
        result.error = "ANTHROPIC_API_KEY not configured"
        return result

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            start = datetime.now(timezone.utc)

            # Send a minimal test message
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "claude-3-haiku-20240307",
                    "max_tokens": 10,
                    "messages": [{"role": "user", "content": "Hi"}],
                },
            )

            latency = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            result.latency_ms = round(latency, 2)

            if response.status_code == 200:
                result.status = "PASS"
                result.details["model"] = "claude-3-haiku (test)"
            elif response.status_code == 401:
                result.status = "FAIL"
                result.error = "Invalid API key (401 Unauthorized)"
            elif response.status_code == 400:
                # 400 with valid auth often means model/format issue - still shows auth works
                result.status = "PASS"
                result.details["note"] = "Auth verified (400 likely model access)"
            else:
                result.status = "FAIL"
                result.error = f"Unexpected status: {response.status_code}"

        except httpx.TimeoutException:
            result.status = "FAIL"
            result.error = "Connection timeout (>15s)"
        except Exception as e:
            result.status = "FAIL"
            result.error = f"Unexpected error: {str(e)}"

    return result


async def test_backend_health(base_url: str = "http://localhost:8080") -> APIHandshakeResult:
    """Test SpaceVoice backend health."""
    result = APIHandshakeResult("SpaceVoice Backend")

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            start = datetime.now(timezone.utc)
            response = await client.get(f"{base_url}/health")
            latency = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            result.latency_ms = round(latency, 2)

            if response.status_code == 200:
                result.status = "PASS"
                try:
                    data = response.json()
                    result.details = data
                except Exception:
                    pass
            else:
                result.status = "FAIL"
                result.error = f"Status {response.status_code}"

        except httpx.ConnectError:
            result.status = "FAIL"
            result.error = f"Cannot connect to {base_url}"
        except Exception as e:
            result.status = "FAIL"
            result.error = str(e)

    return result


def load_env_file(env_path: str) -> dict:
    """Load environment variables from .env file."""
    env_vars = {}
    path = Path(env_path)
    if not path.exists():
        return env_vars

    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                # Remove quotes
                value = value.strip().strip('"').strip("'")
                env_vars[key.strip()] = value

    return env_vars


async def main():
    """Run all API handshake tests."""
    print("=" * 60)
    print("SpaceVoice API Handshake Tests")
    print("=" * 60)
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")

    # Load env vars
    env_path = Path(__file__).parent.parent / "backend" / ".env"
    env_vars = load_env_file(str(env_path))

    # Get API keys
    retell_key = env_vars.get("RETELL_API_KEY") or os.environ.get("RETELL_API_KEY")
    telnyx_key = env_vars.get("TELNYX_API_KEY") or os.environ.get("TELNYX_API_KEY")
    openai_key = env_vars.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    anthropic_key = env_vars.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")

    print("\n" + "-" * 60)
    print("Running Tests...")
    print("-" * 60)

    # Run tests
    results = await asyncio.gather(
        test_backend_health(),
        test_retell_api(retell_key),
        test_telnyx_api(telnyx_key),
        test_openai_api(openai_key),
        test_anthropic_api(anthropic_key),
    )

    # Print results
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)

    total_latency = 0
    latency_count = 0
    passed = 0
    failed = 0
    skipped = 0

    for result in results:
        status_icon = {
            "PASS": "[OK]",
            "FAIL": "[FAIL]",
            "SKIP": "[SKIP]",
            "NOT_TESTED": "[?]",
        }.get(result.status, "[?]")

        latency_str = f"{result.latency_ms}ms" if result.latency_ms else "N/A"

        print(f"\n{status_icon} {result.name}")
        print(f"    Status: {result.status}")
        print(f"    Latency: {latency_str}")

        if result.error:
            print(f"    Error: {result.error}")

        if result.details:
            for key, value in result.details.items():
                print(f"    {key}: {value}")

        if result.status == "PASS":
            passed += 1
            if result.latency_ms:
                total_latency += result.latency_ms
                latency_count += 1
        elif result.status == "FAIL":
            failed += 1
        elif result.status == "SKIP":
            skipped += 1

    avg_latency = round(total_latency / latency_count, 2) if latency_count > 0 else 0

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Skipped: {skipped}")
    print(f"Average Latency: {avg_latency}ms")

    # Return results for certificate
    return {
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "avg_latency_ms": avg_latency,
        "results": [
            {
                "name": r.name,
                "status": r.status,
                "latency_ms": r.latency_ms,
                "error": r.error,
            }
            for r in results
        ],
    }


if __name__ == "__main__":
    result = asyncio.run(main())
    # Exit with error code if any critical services failed
    critical_failed = any(
        r["status"] == "FAIL" and r["name"] in ["SpaceVoice Backend", "Retell AI"]
        for r in result["results"]
    )
    sys.exit(1 if critical_failed else 0)
