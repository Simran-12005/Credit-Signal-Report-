"""A clean, ML-ready feature row for one business (Phase 4).

Flattens every collected signal (GST + MCA + legal) into `features`, attaches the
supplier's payment outcome as `label`, and records the rule-based score. Versioned and
stamped with `as_of_date` so the training dataset is reproducible as data grows.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import uuid4, UUID

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class FeatureSnapshot(Base):
    __tablename__ = "csr_feature_snapshots"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    supplier_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("csr_suppliers.id", ondelete="CASCADE"), nullable=False
    )
    gstin: Mapped[str] = mapped_column(String(15), nullable=False)
    buyer_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("csr_buyers.id", ondelete="SET NULL"), nullable=True
    )
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    features: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    label: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    has_label: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    risk_band: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    score_breakdown: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    gst_provider: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    mca_provider: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
