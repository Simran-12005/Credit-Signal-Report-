"""Orders/invoices + payment actions, and the derived payment summary.

The payment summary is the "outcome label" Phase 1 exists to produce — who actually
pays well. It's computed on the fly from the buyer's orders (no stored aggregates to
drift out of sync).
"""

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.buyer_dao import BuyerDAO
from app.dao.order_dao import OrderDAO
from app.models.buyer import Buyer
from app.models.order import Order
from app.schemas.buyer import PaymentSummary


def _delay_days(order: Order) -> int | None:
    """Days a paid order was late (0 if on time). None if not paid."""
    if order.paid_date is None:
        return None
    return max(0, (order.paid_date - order.due_date).days)


class OrderService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.dao = OrderDAO(session)

    async def create_order(self, supplier_id: UUID, buyer_id: UUID, data: dict) -> Order:
        data = {k: v for k, v in data.items() if v is not None}
        data.setdefault("status", "pending")
        data.setdefault("bounce_count", 0)
        return await self.dao.create(supplier_id, buyer_id, data)

    async def get_order(self, order_id: UUID, supplier_id: UUID) -> Order | None:
        return await self.dao.get_for_supplier(order_id, supplier_id)

    async def list_orders(self, buyer_id: UUID, supplier_id: UUID) -> list[Order]:
        return await self.dao.list_for_buyer(buyer_id, supplier_id)

    async def update_order(self, order: Order, data: dict) -> Order:
        return await self.dao.update(order, {k: v for k, v in data.items() if v is not None})

    async def mark_paid(self, order: Order, paid_date: date) -> Order:
        return await self.dao.update(order, {"paid_date": paid_date, "status": "paid"})

    async def flag_bounce(self, order: Order) -> Order:
        """Record a bounced payment: increment the counter and set status."""
        return await self.dao.update(
            order, {"bounce_count": order.bounce_count + 1, "status": "bounced"}
        )

    async def summary_for_buyer(self, supplier_id: UUID, buyer: Buyer) -> PaymentSummary:
        orders = await self.list_orders(buyer.id, supplier_id)
        return self.compute_summary(buyer.id, buyer.gstin, orders)

    async def summary_for_gstin(
        self, supplier_id: UUID, gstin: str
    ) -> PaymentSummary | None:
        """Payment summary for the supplier's buyer with this GSTIN, if one exists.

        Lets a credit report join the supplier's own first-party payment outcomes for
        the same business. Returns None when the supplier has no such buyer.
        """
        buyer = await BuyerDAO(self.session).get_by_gstin(supplier_id, gstin)
        if buyer is None:
            return None
        return await self.summary_for_buyer(supplier_id, buyer)

    def compute_summary(
        self, buyer_id: UUID, gstin: str | None, orders: list[Order]
    ) -> PaymentSummary:
        today = date.today()
        total_amount = sum((o.amount for o in orders), Decimal("0"))
        outstanding = sum(
            (o.amount for o in orders if o.status != "paid"), Decimal("0")
        )

        paid = [o for o in orders if o.status == "paid"]
        pending = [o for o in orders if o.status == "pending"]
        bounced = [o for o in orders if o.status == "bounced"]
        overdue = [o for o in pending if o.due_date < today]

        delays = [d for o in paid if (d := _delay_days(o)) is not None]
        on_time = sum(1 for d in delays if d == 0)
        late = sum(1 for d in delays if d > 0)

        return PaymentSummary(
            buyer_id=buyer_id,
            gstin=gstin,
            total_orders=len(orders),
            total_amount=total_amount,
            paid_orders=len(paid),
            pending_orders=len(pending),
            bounced_orders=len(bounced),
            overdue_orders=len(overdue),
            total_bounces=sum(o.bounce_count for o in orders),
            on_time_payments=on_time,
            late_payments=late,
            on_time_rate=round(on_time / len(paid), 2) if paid else None,
            avg_delay_days=round(sum(delays) / len(delays), 1) if delays else None,
            max_delay_days=max(delays) if delays else None,
            outstanding_amount=outstanding,
        )
