"""PerfiosGstProvider — real GST data via the Perfios (Karza) API.

Perfios offers 10,000+ free sandbox credits and underwriting-grade GST signals
(filing history, compliance), which is exactly what the credit report needs.

This is a scaffold: the HTTP plumbing, auth, and error handling are real, but the
exact request path and response field names must be confirmed against the Perfios
sandbox docs you get with your key. Field mappings flagged with TODO below are the
only thing to adjust — the rest of the app is already provider-agnostic.
"""

from typing import Any

import httpx

from app.config import get_settings
from app.services.gst.base import GstData, GstProvider, GstProviderError


class PerfiosGstProvider(GstProvider):
    name = "perfios"
    cost_per_call = 5.0  # placeholder; set to your contracted per-call price

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.perfios_api_key:
            raise GstProviderError(
                "GST_PROVIDER=perfios but PERFIOS_API_KEY is not set. "
                "Add your sandbox key to .env, or set GST_PROVIDER=mock."
            )
        self._base_url = settings.perfios_base_url.rstrip("/")
        self._api_key = settings.perfios_api_key
        self._auth_header = settings.perfios_auth_header
        self._path = settings.perfios_gst_path
        self._consent = settings.perfios_consent

    async def fetch_gst_data(self, gstin: str) -> GstData:
        # Endpoint path + auth header are configurable in .env — confirm against
        # your Perfios sandbox docs (PERFIOS_GST_PATH / PERFIOS_AUTH_HEADER).
        url = f"{self._base_url}{self._path}"
        headers = {self._auth_header: self._api_key, "Content-Type": "application/json"}
        payload = {"gstin": gstin, "consent": self._consent}

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                body = resp.json()
        except httpx.HTTPStatusError as exc:
            raise GstProviderError(
                f"Perfios returned {exc.response.status_code} for GSTIN {gstin}"
            ) from exc
        except httpx.HTTPError as exc:
            raise GstProviderError(f"Perfios request failed: {exc}") from exc

        return self._map_response(gstin, body)

    @staticmethod
    def _map_response(gstin: str, body: dict[str, Any]) -> GstData:
        """Map the Perfios response into our normalized GstData.

        TODO(perfios): align these keys with the actual sandbox response schema.
        """
        data = body.get("data", body)

        identity = {
            "gstin": gstin,
            "legal_name": data.get("legalName") or data.get("lgnm"),
            "trade_name": data.get("tradeName") or data.get("tradeNam"),
            "pan": data.get("pan") or gstin[2:12],
            "taxpayer_type": data.get("taxpayerType") or data.get("dty"),
            "state": data.get("state") or data.get("stj"),
            "state_code": gstin[:2],
            "registration_date": data.get("registrationDate") or data.get("rgdt"),
            "status": data.get("gstinStatus") or data.get("sts"),
        }
        compliance = {
            "filing_frequency": data.get("filingFrequency"),
            "returns_filed_12m": data.get("returnsFiled"),
            "missed_filings_12m": data.get("missedFilings"),
            "last_return_filed_date": data.get("lastReturnFiledDate"),
            "is_compliant": data.get("isCompliant"),
            "raw_filings": data.get("filings"),
        }
        return GstData(identity=identity, compliance=compliance)
