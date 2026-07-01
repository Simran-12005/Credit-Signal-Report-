"""Buyer + per-buyer order endpoints (Phase 1).

    POST  /buyers                          create a buyer
    GET   /buyers                          list your buyers
    GET   /buyers/{id}                     read a buyer
    PATCH /buyers/{id}                     edit a buyer
    GET   /buyers/{id}/payment-summary     derived payment-behaviour signals
    GET   /buyers/{id}/orders              list a buyer's orders
    POST  /buyers/{id}/orders              add an order
    POST  /buyers/{id}/orders/bulk         add many orders at once

All scoped to the authenticated supplier.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.deps import SessionDep, SupplierIdDep
from app.schemas.buyer import (
    BuyerResponse,
    CreateBuyerRequest,
    PaymentSummary,
    UpdateBuyerRequest,
)
from app.schemas.order import BulkOrdersRequest, CreateOrderRequest, OrderResponse
from app.services.buyer_service import BuyerConflictError, BuyerService
from app.services.order_service import OrderService
from app.utils.gstin import InvalidGstinError

router = APIRouter(prefix="/buyers", tags=["buyers"])


async def _load_buyer(buyer_id: UUID, supplier_id: UUID, session):
    buyer = await BuyerService(session).get_buyer(buyer_id, supplier_id)
    if buyer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Buyer not found.")
    return buyer


@router.post("", response_model=BuyerResponse, status_code=status.HTTP_201_CREATED)
async def create_buyer(
    body: CreateBuyerRequest, supplier_id: SupplierIdDep, session: SessionDep
) -> BuyerResponse:
    try:
        buyer = await BuyerService(session).create_buyer(supplier_id, body.model_dump())
    except InvalidGstinError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except BuyerConflictError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc))
    return BuyerResponse.model_validate(buyer)


@router.get("", response_model=list[BuyerResponse])
async def list_buyers(
    supplier_id: SupplierIdDep,
    session: SessionDep,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[BuyerResponse]:
    buyers = await BuyerService(session).list_buyers(supplier_id, limit, offset)
    return [BuyerResponse.model_validate(b) for b in buyers]


@router.get("/{buyer_id}", response_model=BuyerResponse)
async def get_buyer(
    buyer_id: UUID, supplier_id: SupplierIdDep, session: SessionDep
) -> BuyerResponse:
    return BuyerResponse.model_validate(await _load_buyer(buyer_id, supplier_id, session))


@router.patch("/{buyer_id}", response_model=BuyerResponse)
async def update_buyer(
    buyer_id: UUID,
    body: UpdateBuyerRequest,
    supplier_id: SupplierIdDep,
    session: SessionDep,
) -> BuyerResponse:
    buyer = await _load_buyer(buyer_id, supplier_id, session)
    try:
        buyer = await BuyerService(session).update_buyer(buyer, body.model_dump())
    except InvalidGstinError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return BuyerResponse.model_validate(buyer)


@router.get("/{buyer_id}/payment-summary", response_model=PaymentSummary)
async def buyer_payment_summary(
    buyer_id: UUID, supplier_id: SupplierIdDep, session: SessionDep
) -> PaymentSummary:
    buyer = await _load_buyer(buyer_id, supplier_id, session)
    svc = OrderService(session)
    orders = await svc.list_orders(buyer.id, supplier_id)
    return svc.compute_summary(buyer.id, buyer.gstin, orders)


@router.get("/{buyer_id}/orders", response_model=list[OrderResponse])
async def list_buyer_orders(
    buyer_id: UUID, supplier_id: SupplierIdDep, session: SessionDep
) -> list[OrderResponse]:
    buyer = await _load_buyer(buyer_id, supplier_id, session)
    orders = await OrderService(session).list_orders(buyer.id, supplier_id)
    return [OrderResponse.model_validate(o) for o in orders]


@router.post(
    "/{buyer_id}/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED
)
async def create_order(
    buyer_id: UUID,
    body: CreateOrderRequest,
    supplier_id: SupplierIdDep,
    session: SessionDep,
) -> OrderResponse:
    buyer = await _load_buyer(buyer_id, supplier_id, session)
    order = await OrderService(session).create_order(
        supplier_id, buyer.id, body.model_dump()
    )
    return OrderResponse.model_validate(order)


@router.post(
    "/{buyer_id}/orders/bulk",
    response_model=list[OrderResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_orders_bulk(
    buyer_id: UUID,
    body: BulkOrdersRequest,
    supplier_id: SupplierIdDep,
    session: SessionDep,
) -> list[OrderResponse]:
    buyer = await _load_buyer(buyer_id, supplier_id, session)
    svc = OrderService(session)
    created = [
        await svc.create_order(supplier_id, buyer.id, o.model_dump()) for o in body.orders
    ]
    return [OrderResponse.model_validate(o) for o in created]
