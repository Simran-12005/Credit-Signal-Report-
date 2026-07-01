"""Fetch GST data through a cache, logging every call for cost control.

Flow per lookup:
  1. Fresh cache entry for (gstin, provider)?  -> log a cache hit (cost 0), return it.
  2. Otherwise call the provider (timed), store the result in the cache, log a live
     call with its cost. Provider failures are logged too, then re-raised.

Cache is shared across suppliers (GST data is public); the call log is per-supplier
so cost can be attributed.
"""

import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.dao.gst_api_call_dao import GstApiCallDAO
from app.dao.gst_cache_dao import GstCacheDAO
from app.services.gst.base import GstProviderError
from app.services.gst.factory import get_gst_provider


@dataclass
class GstFetchResult:
    identity: Optional[dict[str, Any]]
    compliance: Optional[dict[str, Any]]
    provider: str
    cache_hit: bool


class GstDataService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.cache_dao = GstCacheDAO(session)
        self.call_dao = GstApiCallDAO(session)

    async def fetch(self, supplier_id: UUID, gstin: str) -> GstFetchResult:
        provider = get_gst_provider()

        cached = await self.cache_dao.get_fresh(gstin, provider.name)
        if cached is not None:
            await self.call_dao.log(
                supplier_id,
                {
                    "gstin": gstin, "provider": provider.name, "cache_hit": True,
                    "success": True, "cost": 0, "latency_ms": 0,
                },
            )
            return GstFetchResult(cached.identity, cached.compliance, provider.name, True)

        t0 = time.perf_counter()
        try:
            data = await provider.fetch_gst_data(gstin)
        except GstProviderError as exc:
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
            days=get_settings().gst_cache_ttl_days
        )
        await self.cache_dao.upsert(
            gstin,
            provider.name,
            {"identity": data.identity, "compliance": data.compliance},
            expires_at,
        )
        await self.call_dao.log(
            supplier_id,
            {
                "gstin": gstin, "provider": provider.name, "cache_hit": False,
                "success": True, "cost": provider.cost_per_call, "latency_ms": latency_ms,
            },
        )
        return GstFetchResult(data.identity, data.compliance, provider.name, False)
