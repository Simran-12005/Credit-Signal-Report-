from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.report import Report


class ReportDAO:
    """All reads/writes are scoped to a supplier_id so suppliers only see their own data."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, supplier_id: UUID, gstin: str) -> Report:
        report = Report(supplier_id=supplier_id, gstin=gstin, status="pending")
        self.session.add(report)
        await self.session.flush()
        return report

    async def get_for_supplier(self, report_id: UUID, supplier_id: UUID) -> Report | None:
        """Fetch a report only if it belongs to this supplier."""
        result = await self.session.execute(
            select(Report).where(
                Report.id == report_id, Report.supplier_id == supplier_id
            )
        )
        return result.scalar_one_or_none()

    async def list_for_supplier(
        self, supplier_id: UUID, limit: int, offset: int
    ) -> list[Report]:
        result = await self.session.execute(
            select(Report)
            .where(Report.supplier_id == supplier_id)
            .order_by(Report.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
