from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feature_snapshot import FeatureSnapshot


class FeatureSnapshotDAO:
    """All reads/writes scoped to a supplier_id."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def next_version(self, supplier_id: UUID, gstin: str) -> int:
        """The next version number for this (supplier, business)."""
        result = await self.session.execute(
            select(func.coalesce(func.max(FeatureSnapshot.version), 0)).where(
                FeatureSnapshot.supplier_id == supplier_id,
                FeatureSnapshot.gstin == gstin,
            )
        )
        return int(result.scalar_one()) + 1

    async def create(self, data: dict) -> FeatureSnapshot:
        snapshot = FeatureSnapshot(**data)
        self.session.add(snapshot)
        await self.session.flush()
        await self.session.refresh(snapshot)
        return snapshot

    async def get_for_supplier(
        self, snapshot_id: UUID, supplier_id: UUID
    ) -> FeatureSnapshot | None:
        result = await self.session.execute(
            select(FeatureSnapshot).where(
                FeatureSnapshot.id == snapshot_id,
                FeatureSnapshot.supplier_id == supplier_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_supplier(
        self,
        supplier_id: UUID,
        gstin: str | None,
        limit: int,
        offset: int,
    ) -> list[FeatureSnapshot]:
        query = select(FeatureSnapshot).where(
            FeatureSnapshot.supplier_id == supplier_id
        )
        if gstin:
            query = query.where(FeatureSnapshot.gstin == gstin)
        query = (
            query.order_by(FeatureSnapshot.created_at.desc()).limit(limit).offset(offset)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def latest_per_gstin(self, supplier_id: UUID) -> list[FeatureSnapshot]:
        """The newest snapshot version for each business — the exportable dataset."""
        result = await self.session.execute(
            select(FeatureSnapshot)
            .where(FeatureSnapshot.supplier_id == supplier_id)
            # DISTINCT ON keeps the first row per gstin given this ordering.
            .distinct(FeatureSnapshot.gstin)
            .order_by(FeatureSnapshot.gstin, FeatureSnapshot.version.desc())
        )
        return list(result.scalars().all())
