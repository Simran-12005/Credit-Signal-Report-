from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gst_cache import GstCache


class GstCacheDAO:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_fresh(self, gstin: str, provider: str) -> GstCache | None:
        """Return the cached entry only if it hasn't expired."""
        result = await self.session.execute(
            select(GstCache).where(
                GstCache.gstin == gstin,
                GstCache.provider == provider,
                GstCache.expires_at > datetime.now(timezone.utc),
            )
        )
        return result.scalar_one_or_none()

    async def upsert(
        self, gstin: str, provider: str, data: dict, expires_at: datetime
    ) -> GstCache:
        """Store (or refresh) a cached response for (gstin, provider)."""
        result = await self.session.execute(
            select(GstCache).where(
                GstCache.gstin == gstin, GstCache.provider == provider
            )
        )
        entry = result.scalar_one_or_none()
        if entry is None:
            entry = GstCache(gstin=gstin, provider=provider)
            self.session.add(entry)
        entry.identity = data.get("identity")
        entry.compliance = data.get("compliance")
        entry.fetched_at = datetime.now(timezone.utc)
        entry.expires_at = expires_at
        await self.session.flush()
        return entry
