"""API keys authenticate a supplier. Only the SHA-256 hash of a key is stored."""

from datetime import datetime
from typing import Optional
from uuid import uuid4, UUID

from sqlalchemy import Boolean, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ApiKey(Base):
    __tablename__ = "csr_api_keys"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    supplier_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("csr_suppliers.id", ondelete="CASCADE"), nullable=False
    )
    # First few chars of the key (e.g. "csr_AbC1") — shown in listings to identify a key.
    key_prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    # SHA-256 hex digest of the full key. The plaintext key is shown only once, at creation.
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    label: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
