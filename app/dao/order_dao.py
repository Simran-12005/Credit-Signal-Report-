from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order


class OrderDAO:
    """All reads/writes scoped to a supplier_id."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, supplier_id: UUID, buyer_id: UUID, data: dict) -> Order:
        order = Order(supplier_id=supplier_id, buyer_id=buyer_id, **data)
        self.session.add(order)
        await self.session.flush()
        return order

    async def get_for_supplier(self, order_id: UUID, supplier_id: UUID) -> Order | None:
        result = await self.session.execute(
            select(Order).where(Order.id == order_id, Order.supplier_id == supplier_id)
        )
        return result.scalar_one_or_none()

    async def list_for_buyer(self, buyer_id: UUID, supplier_id: UUID) -> list[Order]:
        result = await self.session.execute(
            select(Order)
            .where(Order.buyer_id == buyer_id, Order.supplier_id == supplier_id)
            .order_by(Order.order_date.desc())
        )
        return list(result.scalars().all())

    async def update(self, order: Order, data: dict) -> Order:
        for key, value in data.items():
            setattr(order, key, value)
        await self.session.flush()
        # Reload server-side updated_at so serialization doesn't lazy-load it.
        await self.session.refresh(order)
        return order
