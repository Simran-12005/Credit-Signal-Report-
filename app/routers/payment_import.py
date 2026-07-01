"""Bulk payment-history entry (Phase 1).

    POST /payment-history/import-csv   upload a CSV of buyers + orders
    POST /payment-history/seed-sample  generate three sample buyers with varied behaviour

CSV columns (header row required):
    buyer_name, buyer_gstin, invoice_number, amount,
    order_date, due_date, paid_date, status, bounce_count
Dates are YYYY-MM-DD. status is pending|paid|bounced (defaults from paid_date).
"""

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.deps import SessionDep, SupplierIdDep
from app.schemas.order import CsvImportResult
from app.services.payment_import_service import PaymentImportService

router = APIRouter(prefix="/payment-history", tags=["payment-history"])


@router.post("/import-csv", response_model=CsvImportResult)
async def import_csv(
    supplier_id: SupplierIdDep,
    session: SessionDep,
    file: UploadFile = File(...),
) -> CsvImportResult:
    content = await file.read()
    try:
        return await PaymentImportService(session).import_csv(supplier_id, content)
    except UnicodeDecodeError:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File is not valid UTF-8 text. Upload a plain CSV.",
        )


@router.post("/seed-sample", response_model=CsvImportResult)
async def seed_sample(
    supplier_id: SupplierIdDep, session: SessionDep
) -> CsvImportResult:
    return await PaymentImportService(session).seed_sample(supplier_id)
