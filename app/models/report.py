"""A credit signal report for one buyer GSTIN, owned by one supplier.

Phase 0 stores the GST identity + compliance signals fetched from the configured
GST provider. Later phases add more signal groups (payment history, MCA, legal) and
a computed score onto this same row.
"""

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4, UUID

from sqlalchemy import ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Report(Base):
    __tablename__ = "csr_reports"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    supplier_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("csr_suppliers.id", ondelete="CASCADE"), nullable=False
    )
    gstin: Mapped[str] = mapped_column(String(15), nullable=False)

    # 'pending' -> 'ready' | 'failed'. Phase 0 fills this synchronously.
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    # Which GstProvider produced the signals ("mock" / "perfios").
    provider: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    # GST signal groups (nullable until fetched).
    gst_identity: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    gst_compliance: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # MCA + legal signal groups (Phase 3; nullable, best-effort — never fail the report).
    mca_provider: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    mca_company: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    mca_directors: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    mca_charges: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    mca_legal: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # Rule-based credit score (Phase 4; computed from the signals above).
    score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    risk_band: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    score_breakdown: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
