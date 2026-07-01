"""Request/response models for the feature dataset + rule-based score (Phase 4)."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BuildFeaturesRequest(BaseModel):
    gstin: str = Field(..., min_length=15, max_length=15, examples=["27AAPFU0939F1ZV"])
    # Optionally pin the buyer whose payment history supplies the label. If omitted, the
    # supplier's buyer with this GSTIN (if any) is used.
    buyer_id: Optional[UUID] = None
    # Defaults to today on the server.
    as_of_date: Optional[date] = None


class FeatureSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    gstin: str
    buyer_id: Optional[UUID] = None
    as_of_date: date
    version: int
    features: dict[str, Any]
    label: Optional[dict[str, Any]] = None
    has_label: bool
    score: Optional[Decimal] = None
    risk_band: Optional[str] = None
    score_breakdown: Optional[dict[str, Any]] = None
    gst_provider: Optional[str] = None
    mca_provider: Optional[str] = None
    created_at: datetime


class FeatureSnapshotSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    gstin: str
    as_of_date: date
    version: int
    score: Optional[Decimal] = None
    risk_band: Optional[str] = None
    has_label: bool
    created_at: datetime
