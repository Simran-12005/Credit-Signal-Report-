"""Test the configured GST provider connection end-to-end and explain the result.

One command to answer "is real GST data working yet?":

    uv run python scripts/test_gst_connection.py                # uses a sample GSTIN
    uv run python scripts/test_gst_connection.py 27AAPFU0939F1ZV  # test a specific one

It shows the active config, authenticates, does one GSTIN lookup, and prints a clear
PASS/FAIL with the exact server message and a suggested fix on failure. For the Sandbox
provider it knows the common gotchas (live keys on the test endpoint, and vice versa).
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx  # noqa: E402

from app.config import get_settings  # noqa: E402

SAMPLE_GSTIN = "27AAPFU0939F1ZV"


def _hint_for_403(message: str, key_prefix: str, base_url: str) -> str:
    msg = message.lower()
    on_test_endpoint = "test-api" in base_url
    if "test api key" in msg:
        return (
            "Your keys are LIVE keys but the endpoint is TEST. Either:\n"
            "   - paste your key_test_/secret_test_ pair into .env (stays free), or\n"
            "   - set SANDBOX_BASE_URL=https://api.sandbox.co.in to go live (costs credits)."
        )
    if "live api key" in msg or (key_prefix.startswith("key_test") and not on_test_endpoint):
        return (
            "Your keys are TEST keys but the endpoint is LIVE. Either:\n"
            "   - set SANDBOX_BASE_URL=https://test-api.sandbox.co.in (free test data), or\n"
            "   - paste your key_live_/secret_live_ pair into .env to go live."
        )
    return "403 Forbidden — the GST API may not be enabled on this account/plan, or the key/endpoint pair is wrong."


async def _test_sandbox(s, gstin: str) -> None:
    base = s.sandbox_base_url.rstrip("/")
    key_prefix = s.sandbox_api_key[:9]
    print(f"Provider     : sandbox")
    print(f"Endpoint     : {base}  ({'TEST/free' if 'test-api' in base else 'LIVE/credits'})")
    print(f"Key type     : {key_prefix}...  ({'LIVE keys' if key_prefix.startswith('key_live') else 'TEST keys' if key_prefix.startswith('key_test') else 'unknown'})")
    print(f"Test GSTIN   : {gstin}")
    print("-" * 60)

    if not s.sandbox_api_key or not s.sandbox_api_secret:
        print("FAIL: SANDBOX_API_KEY / SANDBOX_API_SECRET are empty in .env.")
        return

    async with httpx.AsyncClient(timeout=30.0) as c:
        # 1) authenticate
        a = await c.post(
            base + "/authenticate",
            headers={
                "x-api-key": s.sandbox_api_key,
                "x-api-secret": s.sandbox_api_secret,
                "x-api-version": s.sandbox_api_version,
            },
        )
        if a.status_code != 200:
            print(f"FAIL at authenticate: HTTP {a.status_code}")
            print("  " + a.text[:300])
            return
        token = a.json().get("access_token") or a.json().get("data", {}).get("access_token")
        print("Step 1/2 authenticate : OK (token received)")

        # 2) GSTIN identity lookup
        r = await c.post(
            base + "/gst/compliance/public/gstin/search",
            headers={
                "authorization": token,
                "x-api-key": s.sandbox_api_key,
                "x-api-version": s.sandbox_api_version,
                "Content-Type": "application/json",
            },
            json={"gstin": gstin},
        )
        if r.status_code != 200:
            print(f"Step 2/2 GSTIN lookup  : FAIL (HTTP {r.status_code})")
            try:
                message = r.json().get("message", r.text[:200])
            except Exception:
                message = r.text[:200]
            print(f"  server says: {message}")
            print("\nHOW TO FIX:\n   " + _hint_for_403(str(message), key_prefix, base))
            return

        d = r.json().get("data", {}).get("data", {}) or {}
        print("Step 2/2 GSTIN lookup  : OK")
        print("-" * 60)
        print("PASS — real GST data is flowing. Sample fields:")
        print(f"  legal name : {d.get('lgnm')}")
        print(f"  trade name : {d.get('tradeNam')}")
        print(f"  status     : {d.get('sts')}")
        print(f"  reg date   : {d.get('rgdt')}")


async def main() -> None:
    gstin = sys.argv[1] if len(sys.argv) > 1 else SAMPLE_GSTIN
    s = get_settings()
    if s.gst_provider == "mock":
        print("GST_PROVIDER=mock — this is fake offline data (no connection to test).")
        print("Set GST_PROVIDER=sandbox in .env to test real data.")
        return
    if s.gst_provider == "sandbox":
        await _test_sandbox(s, gstin)
    else:
        print(f"No connection test wired for GST_PROVIDER={s.gst_provider}.")


if __name__ == "__main__":
    asyncio.run(main())
