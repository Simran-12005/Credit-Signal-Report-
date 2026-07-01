"""Feature dataset + rule-based score endpoints (Phase 4).

    POST /credit-signal/features/build   build (or rebuild) a snapshot for a GSTIN
    GET  /credit-signal/features         list your snapshots (optional ?gstin= filter)
    GET  /credit-signal/features/{id}    read one snapshot
    GET  /credit-signal/dataset          export the labelled dataset (JSON or CSV)

All scoped to the authenticated supplier.
"""

import csv
import io
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.deps import SessionDep, SupplierIdDep
from app.models.feature_snapshot import FeatureSnapshot
from app.schemas.feature import (
    BuildFeaturesRequest,
    FeatureSnapshotResponse,
    FeatureSnapshotSummary,
)
from app.services.feature_builder_service import FeatureBuildError, FeatureBuilderService
from app.utils.gstin import InvalidGstinError

router = APIRouter(prefix="/credit-signal", tags=["features"])


def _dataset_row(s: FeatureSnapshot) -> dict:
    """One flat dataset row: identifiers + score + features + label_* columns."""
    row: dict = {
        "gstin": s.gstin,
        "as_of_date": s.as_of_date.isoformat(),
        "version": s.version,
        "score": float(s.score) if s.score is not None else None,
        "risk_band": s.risk_band,
        "has_label": s.has_label,
    }
    row.update(s.features or {})
    for key, value in (s.label or {}).items():
        row[f"label_{key}"] = value
    return row


@router.post(
    "/features/build",
    response_model=FeatureSnapshotResponse,
    status_code=status.HTTP_201_CREATED,
)
async def build_features(
    body: BuildFeaturesRequest,
    supplier_id: SupplierIdDep,
    session: SessionDep,
) -> FeatureSnapshotResponse:
    try:
        snapshot = await FeatureBuilderService(session).build(
            supplier_id, body.gstin, body.buyer_id, body.as_of_date
        )
    except InvalidGstinError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except FeatureBuildError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return FeatureSnapshotResponse.model_validate(snapshot)


@router.get("/features", response_model=list[FeatureSnapshotSummary])
async def list_features(
    supplier_id: SupplierIdDep,
    session: SessionDep,
    gstin: str | None = Query(None, min_length=15, max_length=15),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[FeatureSnapshotSummary]:
    snapshots = await FeatureBuilderService(session).list_snapshots(
        supplier_id, gstin, limit, offset
    )
    return [FeatureSnapshotSummary.model_validate(s) for s in snapshots]


@router.get("/features/{snapshot_id}", response_model=FeatureSnapshotResponse)
async def get_feature_snapshot(
    snapshot_id: UUID,
    supplier_id: SupplierIdDep,
    session: SessionDep,
) -> FeatureSnapshotResponse:
    snapshot = await FeatureBuilderService(session).get(snapshot_id, supplier_id)
    if snapshot is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Snapshot not found.")
    return FeatureSnapshotResponse.model_validate(snapshot)


@router.get("/dataset")
async def export_dataset(
    supplier_id: SupplierIdDep,
    session: SessionDep,
    format: str = Query("json", pattern="^(json|csv)$"),
):
    """The ML-ready dataset: the latest snapshot per business, one flat row each."""
    snapshots = await FeatureBuilderService(session).dataset(supplier_id)
    rows = [_dataset_row(s) for s in snapshots]

    if format == "json":
        return {"count": len(rows), "rows": rows}

    # CSV: union of all keys (snapshots can differ in which signals were available).
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=credit_signal_dataset.csv"},
    )
