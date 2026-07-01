"""Request/response models for the credit signal report API."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateReportRequest(BaseModel):
    gstin: str = Field(..., min_length=15, max_length=15, examples=["27AAPFU0939F1ZV"])


class ManualCompanyRequest(BaseModel):
    """Company/legal facts entered by hand (e.g. looked up free on mca.gov.in).

    Saved onto the report as real MCA signals (provider = 'manual') and the credit
    score is recomputed. All fields optional — fill what you have; blanks are ignored.
    """

    registered_with_mca: bool = True
    company_name: Optional[str] = None
    entity_class: Optional[str] = None          # e.g. "Private Limited Company"
    status: Optional[str] = None                # Active / Dormant / Strike Off / Under Liquidation / Amalgamated
    incorporation_date: Optional[str] = None    # YYYY-MM-DD
    paid_up_capital: Optional[float] = None
    director_count: Optional[int] = Field(None, ge=0)
    open_charges: Optional[int] = Field(None, ge=0)
    satisfied_charges: Optional[int] = Field(None, ge=0)
    total_open_charge_amount: Optional[float] = None
    has_active_insolvency: bool = False
    recovery_case_count: int = Field(0, ge=0)


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    gstin: str
    status: str
    provider: Optional[str] = None
    gst_identity: Optional[dict[str, Any]] = None
    gst_compliance: Optional[dict[str, Any]] = None
    # MCA + legal signal groups (Phase 3).
    mca_provider: Optional[str] = None
    mca_company: Optional[dict[str, Any]] = None
    mca_directors: Optional[dict[str, Any]] = None
    mca_charges: Optional[dict[str, Any]] = None
    mca_legal: Optional[dict[str, Any]] = None
    # Rule-based credit score (Phase 4).
    score: Optional[float] = None
    risk_band: Optional[str] = None
    score_breakdown: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ReportSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    gstin: str
    status: str
    score: Optional[float] = None
    risk_band: Optional[str] = None
    created_at: datetime
