"""Buyer CRUD. GSTIN, when provided, is validated like everywhere else."""

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.dao.buyer_dao import BuyerDAO
from app.models.buyer import Buyer
from app.utils.gstin import validate_gstin


class BuyerConflictError(Exception):
    """Raised when a buyer with the same GSTIN already exists for this supplier."""


class BuyerService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.dao = BuyerDAO(session)

    def _clean(self, data: dict) -> dict:
        if data.get("gstin"):
            # Raises InvalidGstinError on bad input (handled at the router).
            data["gstin"] = validate_gstin(
                data["gstin"], verify_checksum=get_settings().validate_gstin_checksum
            )
        return data

    async def create_buyer(self, supplier_id: UUID, data: dict) -> Buyer:
        data = self._clean(data)
        try:
            buyer = await self.dao.create(supplier_id, data)
            await self.session.flush()
        except IntegrityError as exc:
            raise BuyerConflictError(
                "A buyer with this GSTIN already exists for your account."
            ) from exc
        return buyer

    async def get_buyer(self, buyer_id: UUID, supplier_id: UUID) -> Buyer | None:
        return await self.dao.get_for_supplier(buyer_id, supplier_id)

    async def list_buyers(self, supplier_id: UUID, limit: int, offset: int) -> list[Buyer]:
        return await self.dao.list_for_supplier(supplier_id, limit, offset)

    async def update_buyer(self, buyer: Buyer, data: dict) -> Buyer:
        data = self._clean({k: v for k, v in data.items() if v is not None})
        return await self.dao.update(buyer, data)
