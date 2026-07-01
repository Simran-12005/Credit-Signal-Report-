"""AttestrMcaProvider — real MCA company data via Attestr CorpX.

Flow (fully automatic from the GSTIN):
  GSTIN -> PAN (chars 3-12) -> Attestr company search -> company master data.

Only companies / LLPs have MCA data; the PAN's 4th character tells us the entity type
('C' company, 'F' firm/LLP). For proprietors/individuals we return empty groups without
calling Attestr (there is nothing to fetch).

Auth: `Authorization: Basic <ATTESTR_AUTH_TOKEN>` (get the token from
dashboard.attestr.com -> Apps -> New App). The token is the ready-made Basic value.

NOTE: the exact request/response field names below are from Attestr's documented Company
Search contract; the directors/charges master-data call is finalized against the live API
once the account is provisioned (services are gated behind business onboarding). The
provider fails safe — any unexpected response raises McaProviderError, which the report
service treats as "company data unavailable" (the report and GST data still come through).
"""

import logging

import httpx

from app.config import get_settings
from app.services.mca.base import McaData, McaProvider, McaProviderError
from app.utils.dates import age_years

logger = logging.getLogger(__name__)

# PAN 4th char -> is this an MCA-registered entity (company / LLP)?
_MCA_ENTITY_TYPES = {"C", "F"}


def _iso(ddmmyyyy: str | None) -> str | None:
    """Attestr returns DD-MM-YYYY; normalize to YYYY-MM-DD for our schema."""
    if not ddmmyyyy:
        return None
    parts = ddmmyyyy.split("-")
    if len(parts) == 3 and len(parts[0]) == 2:
        d, m, y = parts
        return f"{y}-{m}-{d}"
    return ddmmyyyy


class AttestrMcaProvider(McaProvider):
    name = "attestr"
    cost_per_call = 1.0  # real per-call cost; adjust to your Attestr plan

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.attestr_auth_token:
            raise McaProviderError(
                "MCA_PROVIDER=attestr but ATTESTR_AUTH_TOKEN is not set. Get a token from "
                "dashboard.attestr.com -> Apps -> New App, add it to .env, or set MCA_PROVIDER=none."
            )
        self._base = settings.attestr_base_url.rstrip("/")
        self._headers = {
            "Authorization": "Basic " + settings.attestr_auth_token,
            "Content-Type": "application/json",
        }

    async def fetch_mca_data(self, gstin: str, legal_name: str | None = None) -> McaData:
        pan = gstin[2:12]
        entity_char = pan[3] if len(pan) >= 4 else ""
        if entity_char not in _MCA_ENTITY_TYPES:
            # Proprietor / individual / HUF / trust — no MCA record exists.
            return McaData(company={"registered_with_mca": False}, directors={}, charges={}, legal={})

        if not legal_name:
            # We search by company name (taken from the GST identity). Without it we
            # can't resolve the company on Attestr; leave company data empty.
            return McaData(company={}, directors={}, charges={}, legal={})

        try:
            async with httpx.AsyncClient(timeout=40.0) as client:
                match = await self._search_company(client, legal_name)
        except httpx.HTTPStatusError as exc:
            raise McaProviderError(
                f"Attestr returned {exc.response.status_code} for {gstin}: {exc.response.text[:160]}"
            ) from exc
        except httpx.HTTPError as exc:
            raise McaProviderError(f"Attestr request failed: {exc}") from exc

        if match is None:
            return McaData(company={}, directors={}, charges={}, legal={})

        inc = _iso(match.get("incorporatedDate"))
        company = {
            "registered_with_mca": True,
            "cin": match.get("indexId"),
            "company_name": match.get("businessName"),
            "entity_class": match.get("type"),
            "status": match.get("status"),
            "incorporation_date": inc,
            "age_years": age_years(inc),
        }
        # Directors + charges come from the master-data call (finalized on live access).
        return McaData(company=company, directors={}, charges={}, legal={})

    async def _search_company(self, client: httpx.AsyncClient, name: str) -> dict | None:
        resp = await client.post(
            f"{self._base}/public/corpx/business/search",
            headers=self._headers,
            json={
                "businessName": {"matchCriteria": "CONTAINS", "matchValue": name, "enableFuzzy": True},
                "active": True,
                "limit": 5,
                "sort": "score",
                "sortOrder": -1,
            },
        )
        resp.raise_for_status()
        body = resp.json()
        # Response is a list of matches (shape confirmed on live access); take the best.
        results = body if isinstance(body, list) else body.get("results") or body.get("data") or []
        return results[0] if results else None
