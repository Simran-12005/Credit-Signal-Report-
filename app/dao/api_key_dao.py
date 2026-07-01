from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import ApiKey


class ApiKeyDAO:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self, supplier_id: UUID, key_prefix: str, key_hash: str, label: str | None
    ) -> ApiKey:
        api_key = ApiKey(
            supplier_id=supplier_id,
            key_prefix=key_prefix,
            key_hash=key_hash,
            label=label,
        )
        self.session.add(api_key)
        await self.session.flush()
        return api_key

    async def get_active_by_hash(self, key_hash: str) -> ApiKey | None:
        result = await self.session.execute(
            select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_active.is_(True))
        )
        return result.scalar_one_or_none()
