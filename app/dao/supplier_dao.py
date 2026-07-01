from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.supplier import Supplier


class SupplierDAO:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, name: str) -> Supplier:
        supplier = Supplier(name=name)
        self.session.add(supplier)
        await self.session.flush()
        return supplier

    async def get(self, supplier_id: UUID) -> Supplier | None:
        result = await self.session.execute(
            select(Supplier).where(Supplier.id == supplier_id)
        )
        return result.scalar_one_or_none()
