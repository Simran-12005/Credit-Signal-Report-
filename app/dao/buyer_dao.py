from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.buyer import Buyer


class BuyerDAO:
    """All reads/writes scoped to a supplier_id."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, supplier_id: UUID, data: dict) -> Buyer:
        buyer = Buyer(supplier_id=supplier_id, **data)
        self.session.add(buyer)
        await self.session.flush()
        return buyer

    async def get_for_supplier(self, buyer_id: UUID, supplier_id: UUID) -> Buyer | None:
        result = await self.session.execute(
            select(Buyer).where(Buyer.id == buyer_id, Buyer.supplier_id == supplier_id)
        )
        return result.scalar_one_or_none()

    async def get_by_gstin(self, supplier_id: UUID, gstin: str) -> Buyer | None:
        result = await self.session.execute(
            select(Buyer).where(Buyer.supplier_id == supplier_id, Buyer.gstin == gstin)
        )
        return result.scalar_one_or_none()

    async def list_for_supplier(
        self, supplier_id: UUID, limit: int, offset: int
    ) -> list[Buyer]:
        result = await self.session.execute(
            select(Buyer)
            .where(Buyer.supplier_id == supplier_id)
            .order_by(Buyer.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def update(self, buyer: Buyer, data: dict) -> Buyer:
        for key, value in data.items():
            setattr(buyer, key, value)
        await self.session.flush()
        # Reload server-side updated_at so serialization doesn't lazy-load it.
        await self.session.refresh(buyer)
        return buyer
