from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gst_api_call import GstApiCall


class GstApiCallDAO:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def log(self, supplier_id: UUID, data: dict) -> GstApiCall:
        call = GstApiCall(supplier_id=supplier_id, **data)
        self.session.add(call)
        await self.session.flush()
        return call

    async def list_for_supplier(
        self, supplier_id: UUID, limit: int, offset: int
    ) -> list[GstApiCall]:
        result = await self.session.execute(
            select(GstApiCall)
            .where(GstApiCall.supplier_id == supplier_id)
            .order_by(GstApiCall.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def usage_for_supplier(self, supplier_id: UUID) -> dict:
        """Aggregate totals for cost control."""
        result = await self.session.execute(
            select(
                func.count().label("total_calls"),
                func.count().filter(GstApiCall.cache_hit.is_(True)).label("cache_hits"),
                func.count().filter(GstApiCall.success.is_(False)).label("failed_calls"),
                func.coalesce(func.sum(GstApiCall.cost), 0).label("total_cost"),
            ).where(GstApiCall.supplier_id == supplier_id)
        )
        row = result.one()
        total = row.total_calls or 0
        hits = row.cache_hits or 0
        return {
            "total_calls": total,
            "cache_hits": hits,
            "live_calls": total - hits,
            "failed_calls": row.failed_calls or 0,
            "total_cost": Decimal(row.total_cost or 0),
            "cache_hit_rate": round(hits / total, 2) if total else None,
        }
