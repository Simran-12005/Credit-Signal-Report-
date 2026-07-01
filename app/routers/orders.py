"""Single-order actions (Phase 1).

    PATCH /orders/{id}          edit amount/dates/invoice number
    POST  /orders/{id}/pay      mark paid (with a paid date)
    POST  /orders/{id}/bounce   flag a bounced payment
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.deps import SessionDep, SupplierIdDep
from app.schemas.order import MarkPaidRequest, OrderResponse, UpdateOrderRequest
from app.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["orders"])


async def _load_order(order_id: UUID, supplier_id: UUID, session) -> object:
    order = await OrderService(session).get_order(order_id, supplier_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
    return order


@router.patch("/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: UUID,
    body: UpdateOrderRequest,
    supplier_id: SupplierIdDep,
    session: SessionDep,
) -> OrderResponse:
    order = await _load_order(order_id, supplier_id, session)
    order = await OrderService(session).update_order(order, body.model_dump())
    return OrderResponse.model_validate(order)


@router.post("/{order_id}/pay", response_model=OrderResponse)
async def mark_order_paid(
    order_id: UUID,
    body: MarkPaidRequest,
    supplier_id: SupplierIdDep,
    session: SessionDep,
) -> OrderResponse:
    order = await _load_order(order_id, supplier_id, session)
    order = await OrderService(session).mark_paid(order, body.paid_date)
    return OrderResponse.model_validate(order)


@router.post("/{order_id}/bounce", response_model=OrderResponse)
async def flag_order_bounce(
    order_id: UUID, supplier_id: SupplierIdDep, session: SessionDep
) -> OrderResponse:
    order = await _load_order(order_id, supplier_id, session)
    order = await OrderService(session).flag_bounce(order)
    return OrderResponse.model_validate(order)
