"""GST API usage + cost endpoints (Phase 2).

    GET /gst/usage   aggregate calls / cache hits / cost for your account
    GET /gst/calls   the recent GST lookup log
"""

from fastapi import APIRouter, Query

from app.dao.gst_api_call_dao import GstApiCallDAO
from app.deps import SessionDep, SupplierIdDep
from app.schemas.gst import GstApiCallResponse, GstUsageResponse

router = APIRouter(prefix="/gst", tags=["gst-usage"])


@router.get("/usage", response_model=GstUsageResponse)
async def gst_usage(supplier_id: SupplierIdDep, session: SessionDep) -> GstUsageResponse:
    usage = await GstApiCallDAO(session).usage_for_supplier(supplier_id)
    return GstUsageResponse(**usage)


@router.get("/calls", response_model=list[GstApiCallResponse])
async def gst_calls(
    supplier_id: SupplierIdDep,
    session: SessionDep,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[GstApiCallResponse]:
    calls = await GstApiCallDAO(session).list_for_supplier(supplier_id, limit, offset)
    return [GstApiCallResponse.model_validate(c) for c in calls]
