"""Request/response models for buyers and their payment summary."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateBuyerRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    gstin: Optional[str] = Field(None, min_length=15, max_length=15)
    notes: Optional[str] = None


class UpdateBuyerRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    gstin: Optional[str] = Field(None, min_length=15, max_length=15)
    notes: Optional[str] = None


class BuyerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    gstin: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PaymentSummary(BaseModel):
    """Derived payment-behaviour signals for a buyer — the outcome label."""

    buyer_id: UUID
    gstin: Optional[str] = None
    total_orders: int
    total_amount: Decimal
    paid_orders: int
    pending_orders: int
    bounced_orders: int
    overdue_orders: int
    total_bounces: int
    on_time_payments: int
    late_payments: int
    on_time_rate: Optional[float] = None       # on-time / paid; None if nothing paid yet
    avg_delay_days: Optional[float] = None      # avg days late over paid orders
    max_delay_days: Optional[int] = None
    outstanding_amount: Decimal                 # amount not yet paid (pending + bounced)
