"""Cached MCA + legal responses, keyed by (gstin, provider). Shared across suppliers."""

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4, UUID

from sqlalchemy import String, func
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class McaCache(Base):
    __tablename__ = "csr_mca_cache"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    gstin: Mapped[str] = mapped_column(String(15), nullable=False)
    provider: Mapped[str] = mapped_column(String(30), nullable=False)
    company: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    directors: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    charges: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    legal: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
