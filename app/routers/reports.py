"""Credit signal report endpoints (Phase 0).

    POST /credit-signal/reports        create a report from a GSTIN
    GET  /credit-signal/reports/{id}   read one of your reports
    GET  /credit-signal/reports        list your reports

All endpoints are scoped to the authenticated supplier via the X-API-Key header.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.deps import SessionDep, SupplierIdDep
from app.schemas.report import (
    CreateReportRequest,
    ManualCompanyRequest,
    ReportResponse,
    ReportSummary,
)
from app.services.report_service import ReportService
from app.utils.gstin import InvalidGstinError

router = APIRouter(prefix="/credit-signal/reports", tags=["reports"])


@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    body: CreateReportRequest,
    supplier_id: SupplierIdDep,
    session: SessionDep,
) -> ReportResponse:
    service = ReportService(session)
    try:
        report = await service.create_report(supplier_id, body.gstin)
    except InvalidGstinError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return ReportResponse.model_validate(report)


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: UUID,
    supplier_id: SupplierIdDep,
    session: SessionDep,
) -> ReportResponse:
    report = await ReportService(session).get_report(report_id, supplier_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")
    return ReportResponse.model_validate(report)


@router.patch("/{report_id}/company", response_model=ReportResponse)
async def set_company_data(
    report_id: UUID,
    body: ManualCompanyRequest,
    supplier_id: SupplierIdDep,
    session: SessionDep,
) -> ReportResponse:
    """Enter company/legal facts by hand (e.g. looked up free on mca.gov.in)."""
    report = await ReportService(session).set_manual_company_data(
        report_id, supplier_id, body.model_dump()
    )
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")
    return ReportResponse.model_validate(report)


@router.get("", response_model=list[ReportSummary])
async def list_reports(
    supplier_id: SupplierIdDep,
    session: SessionDep,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[ReportSummary]:
    reports = await ReportService(session).list_reports(supplier_id, limit, offset)
    return [ReportSummary.model_validate(r) for r in reports]
