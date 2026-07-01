"""MCA + legal API usage + cost endpoints (Phase 3).

    GET /mca/usage   aggregate calls / cache hits / cost for your account
    GET /mca/calls   the recent MCA + legal lookup log
"""

from fastapi import APIRouter, Query

from app.dao.mca_api_call_dao import McaApiCallDAO
from app.deps import SessionDep, SupplierIdDep
from app.schemas.mca import McaApiCallResponse, McaUsageResponse

router = APIRouter(prefix="/mca", tags=["mca-usage"])


@router.get("/usage", response_model=McaUsageResponse)
async def mca_usage(supplier_id: SupplierIdDep, session: SessionDep) -> McaUsageResponse:
    usage = await McaApiCallDAO(session).usage_for_supplier(supplier_id)
    return McaUsageResponse(**usage)


@router.get("/calls", response_model=list[McaApiCallResponse])
async def mca_calls(
    supplier_id: SupplierIdDep,
    session: SessionDep,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[McaApiCallResponse]:
    calls = await McaApiCallDAO(session).list_for_supplier(supplier_id, limit, offset)
    return [McaApiCallResponse.model_validate(c) for c in calls]
