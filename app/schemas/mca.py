"""Response models for MCA + legal usage / cost tracking (Phase 3)."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class McaUsageResponse(BaseModel):
    total_calls: int
    cache_hits: int
    live_calls: int
    failed_calls: int
    total_cost: Decimal
    cache_hit_rate: Optional[float] = None


class McaApiCallResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    gstin: str
    provider: str
    cache_hit: bool
    success: bool
    cost: Decimal
    latency_ms: Optional[int] = None
    error: Optional[str] = None
    created_at: datetime
