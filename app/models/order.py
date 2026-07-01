"""An order/invoice and its payment outcome. The raw material for the credit label."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import uuid4, UUID

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Order(Base):
    __tablename__ = "csr_orders"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    supplier_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("csr_suppliers.id", ondelete="CASCADE"), nullable=False
    )
    buyer_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("csr_buyers.id", ondelete="CASCADE"), nullable=False
    )
    invoice_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    order_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    paid_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    # 'pending' | 'paid' | 'bounced'. 'overdue' is derived, never stored.
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    bounce_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
