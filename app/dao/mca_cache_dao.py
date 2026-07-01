from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mca_cache import McaCache


class McaCacheDAO:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_fresh(self, gstin: str, provider: str) -> McaCache | None:
        """Return the cached entry only if it hasn't expired."""
        result = await self.session.execute(
            select(McaCache).where(
                McaCache.gstin == gstin,
                McaCache.provider == provider,
                McaCache.expires_at > datetime.now(timezone.utc),
            )
        )
        return result.scalar_one_or_none()

    async def upsert(
        self, gstin: str, provider: str, data: dict, expires_at: datetime
    ) -> McaCache:
        """Store (or refresh) a cached response for (gstin, provider)."""
        result = await self.session.execute(
            select(McaCache).where(
                McaCache.gstin == gstin, McaCache.provider == provider
            )
        )
        entry = result.scalar_one_or_none()
        if entry is None:
            entry = McaCache(gstin=gstin, provider=provider)
            self.session.add(entry)
        entry.company = data.get("company")
        entry.directors = data.get("directors")
        entry.charges = data.get("charges")
        entry.legal = data.get("legal")
        entry.fetched_at = datetime.now(timezone.utc)
        entry.expires_at = expires_at
        await self.session.flush()
        return entry
