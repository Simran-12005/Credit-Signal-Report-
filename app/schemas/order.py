"""Request/response models for orders/invoices and bulk operations."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateOrderRequest(BaseModel):
    amount: Decimal = Field(..., ge=0)
    order_date: date
    due_date: date
    invoice_number: Optional[str] = Field(None, max_length=50)
    # Optionally create an already-resolved order in one shot (useful for bulk/sample).
    paid_date: Optional[date] = None
    status: Optional[str] = Field(None, pattern="^(pending|paid|bounced)$")
    bounce_count: Optional[int] = Field(None, ge=0)


class UpdateOrderRequest(BaseModel):
    amount: Optional[Decimal] = Field(None, ge=0)
    order_date: Optional[date] = None
    due_date: Optional[date] = None
    invoice_number: Optional[str] = Field(None, max_length=50)


class MarkPaidRequest(BaseModel):
    paid_date: date


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    buyer_id: UUID
    invoice_number: Optional[str] = None
    amount: Decimal
    order_date: date
    due_date: date
    paid_date: Optional[date] = None
    status: str
    bounce_count: int
    created_at: datetime
    updated_at: datetime


class BulkOrdersRequest(BaseModel):
    orders: list[CreateOrderRequest]


class CsvImportResult(BaseModel):
    buyers_created: int
    orders_created: int
    rows_processed: int
    errors: list[str]
