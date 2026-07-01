"""Fetch MCA + legal data through a cache, logging every call for cost control.

Flow per lookup (identical shape to GstDataService):
  1. Fresh cache entry for (gstin, provider)?  -> log a cache hit (cost 0), return it.
  2. Otherwise call the provider (timed), store the result in the cache, log a live
     call with its cost. Provider failures are logged too, then re-raised.

Cache is shared across suppliers (MCA/legal data is public); the call log is
per-supplier so cost can be attributed.
"""

import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.dao.mca_api_call_dao import McaApiCallDAO
from app.dao.mca_cache_dao import McaCacheDAO
from app.services.mca.base import McaProviderError
from app.services.mca.factory import get_mca_provider


@dataclass
class McaFetchResult:
    company: Optional[dict[str, Any]]
    directors: Optional[dict[str, Any]]
    charges: Optional[dict[str, Any]]
    legal: Optional[dict[str, Any]]
    provider: str
    cache_hit: bool


class McaDataService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.cache_dao = McaCacheDAO(session)
        self.call_dao = McaApiCallDAO(session)

    async def fetch(
        self, supplier_id: UUID, gstin: str, legal_name: str | None = None
    ) -> McaFetchResult:
        provider = get_mca_provider()

        cached = await self.cache_dao.get_fresh(gstin, provider.name)
        if cached is not None:
            await self.call_dao.log(
                supplier_id,
                {
                    "gstin": gstin, "provider": provider.name, "cache_hit": True,
                    "success": True, "cost": 0, "latency_ms": 0,
                },
            )
            return McaFetchResult(
                cached.company, cached.directors, cached.charges, cached.legal,
                provider.name, True,
            )

        t0 = time.perf_counter()
        try:
            data = await provider.fetch_mca_data(gstin, legal_name)
        except McaProviderError as exc:
            await self.call_dao.log(
                supplier_id,
                {
                    "gstin": gstin, "provider": provider.name, "cache_hit": False,
                    "success": False, "cost": provider.cost_per_call,
                    "latency_ms": int((time.perf_counter() - t0) * 1000),
                    "error": str(exc),
                },
            )
            raise

        latency_ms = int((time.perf_counter() - t0) * 1000)
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=get_settings().mca_cache_ttl_days
        )
        await self.cache_dao.upsert(
            gstin,
            provider.name,
            {
                "company": data.company, "directors": data.directors,
                "charges": data.charges, "legal": data.legal,
            },
            expires_at,
        )
        await self.call_dao.log(
            supplier_id,
            {
                "gstin": gstin, "provider": provider.name, "cache_hit": False,
                "success": True, "cost": provider.cost_per_call, "latency_ms": latency_ms,
            },
        )
        return McaFetchResult(
            data.company, data.directors, data.charges, data.legal, provider.name, False
        )
