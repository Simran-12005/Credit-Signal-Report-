"""SandboxGstProvider — real GST data via Sandbox.co.in (Quicko).

Self-serve and free to start. Two calls give us both signal groups:
  1. Search GSTIN  -> identity (legal/trade name, type, status, registration date)
  2. Track Returns -> compliance (which GSTR returns were filed, when)

Auth is a token exchange: POST /authenticate with the API key + secret returns a
JWT access token valid ~24h, sent on subsequent calls as the `authorization` header
(no "Bearer" prefix). The token is cached on the provider instance.
"""

import asyncio
import logging
from datetime import datetime, timezone

import httpx

from app.config import get_settings
from app.services.gst.base import GstData, GstProvider, GstProviderError

logger = logging.getLogger(__name__)


def _current_financial_year() -> str:
    """Indian FY (Apr–Mar) for today, formatted like 'FY 2025-26'."""
    now = datetime.now(timezone.utc)
    start = now.year if now.month >= 4 else now.year - 1
    return f"FY {start}-{str(start + 1)[-2:]}"


class SandboxGstProvider(GstProvider):
    name = "sandbox"
    # Two API calls per lookup (search + returns). Adjust to your plan's per-call price.
    cost_per_call = 2.0

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.sandbox_api_key or not settings.sandbox_api_secret:
            raise GstProviderError(
                "GST_PROVIDER=sandbox but SANDBOX_API_KEY / SANDBOX_API_SECRET are not set. "
                "Sign up at sandbox.co.in, add them to .env, or set GST_PROVIDER=mock."
            )
        self._base_url = settings.sandbox_base_url.rstrip("/")
        self._api_key = settings.sandbox_api_key
        self._api_secret = settings.sandbox_api_secret
        self._api_version = settings.sandbox_api_version
        self._financial_year = settings.sandbox_financial_year or _current_financial_year()
        self._token: str | None = None
        self._token_lock = asyncio.Lock()

    async def _get_token(self, client: httpx.AsyncClient) -> str:
        # Cached for the life of the provider instance; re-auth on demand.
        if self._token:
            return self._token
        async with self._token_lock:
            if self._token:
                return self._token
            resp = await client.post(
                f"{self._base_url}/authenticate",
                headers={
                    "x-api-key": self._api_key,
                    "x-api-secret": self._api_secret,
                    "x-api-version": self._api_version,
                },
            )
            resp.raise_for_status()
            body = resp.json()
            token = body.get("access_token") or body.get("data", {}).get("access_token")
            if not token:
                raise GstProviderError("Sandbox authenticate returned no access_token.")
            self._token = token
            return token

    def _auth_headers(self, token: str) -> dict[str, str]:
        return {
            "authorization": token,  # no "Bearer" prefix (per Sandbox docs)
            "x-api-key": self._api_key,
            "x-api-version": self._api_version,
            "Content-Type": "application/json",
        }

    async def fetch_gst_data(self, gstin: str) -> GstData:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                token = await self._get_token(client)
                identity = await self._fetch_identity(client, token, gstin)
                # Compliance is best-effort: a returns lookup can fail without
                # invalidating the identity we already have.
                compliance = await self._fetch_compliance(client, token, gstin)
        except httpx.HTTPStatusError as exc:
            raise GstProviderError(
                f"Sandbox returned {exc.response.status_code} for GSTIN {gstin}"
            ) from exc
        except httpx.HTTPError as exc:
            raise GstProviderError(f"Sandbox request failed: {exc}") from exc

        return GstData(identity=identity, compliance=compliance)

    async def _fetch_identity(
        self, client: httpx.AsyncClient, token: str, gstin: str
    ) -> dict:
        resp = await client.post(
            f"{self._base_url}/gst/compliance/public/gstin/search",
            headers=self._auth_headers(token),
            json={"gstin": gstin},
        )
        resp.raise_for_status()
        d = resp.json().get("data", {}).get("data", {}) or {}
        addr = (d.get("pradr") or {}).get("addr") or {}
        return {
            "gstin": gstin,
            "legal_name": d.get("lgnm"),
            "trade_name": d.get("tradeNam"),
            "pan": gstin[2:12],
            "taxpayer_type": d.get("dty"),
            "constitution": d.get("ctb"),
            "state": d.get("stj"),
            "state_code": addr.get("stcd") or gstin[:2],
            "registration_date": d.get("rgdt"),
            "status": d.get("sts"),
            "cancellation_date": d.get("cxdt"),
        }

    async def _fetch_compliance(
        self, client: httpx.AsyncClient, token: str, gstin: str
    ) -> dict:
        try:
            resp = await client.post(
                f"{self._base_url}/gst/compliance/public/gstrs/track",
                headers=self._auth_headers(token),
                params={"financial_year": self._financial_year},
                json={"gstin": gstin},
            )
            resp.raise_for_status()
            filed = (
                resp.json().get("data", {}).get("data", {}).get("EFiledlist", []) or []
            )
        except httpx.HTTPError as exc:
            logger.warning("Sandbox returns-tracking failed for %s: %s", gstin, exc)
            return {"financial_year": self._financial_year, "available": False}

        filings = [
            {
                "return_type": f.get("rtntype"),
                "period": f.get("ret_prd"),
                "filed_date": f.get("dof"),
                "status": f.get("status"),
                "mode": f.get("mof"),
            }
            for f in filed
        ]
        last_filed = max((f.get("dof") for f in filed if f.get("dof")), default=None)
        return {
            "financial_year": self._financial_year,
            "available": True,
            "returns_filed": len(filings),
            "last_return_filed_date": last_filed,
            "filings": filings,
        }
