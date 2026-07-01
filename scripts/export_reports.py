"""Export the credit reports already saved in the database to a shareable file.

Reads what's stored (no API calls, no credits spent) and writes it out. Use a .csv
extension for a flat spreadsheet (one row per report) or .json for the full detail
(every GST / MCA / legal field + score breakdown).

Usage:
    uv run python scripts/export_reports.py reports.csv                 # all suppliers
    uv run python scripts/export_reports.py reports.json               # full detail
    uv run python scripts/export_reports.py reports.csv "Dashboard User"  # one supplier
"""

import asyncio
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.models.report import Report  # noqa: E402
from app.models.supplier import Supplier  # noqa: E402


def _flat_row(rep: Report, supplier_name: str) -> dict:
    gi = rep.gst_identity or {}
    gc = rep.gst_compliance or {}
    co = rep.mca_company or {}
    ch = rep.mca_charges or {}
    lg = rep.mca_legal or {}
    return {
        "supplier": supplier_name,
        "gstin": rep.gstin,
        "score": float(rep.score) if rep.score is not None else None,
        "risk_band": rep.risk_band,
        "status": rep.status,
        "gst_provider": rep.provider,
        "mca_provider": rep.mca_provider,
        "gst_legal_name": gi.get("legal_name"),
        "gst_trade_name": gi.get("trade_name"),
        "gst_status": gi.get("status"),
        "gst_type": gi.get("taxpayer_type"),
        "gst_state": gi.get("state"),
        "gst_registration_date": gi.get("registration_date"),
        "gst_pan": gi.get("pan"),
        "gst_returns_filed": gc.get("returns_filed_12m") or gc.get("returns_filed"),
        "gst_last_filed": gc.get("last_return_filed_date"),
        "mca_registered": co.get("registered_with_mca"),
        "mca_company_status": co.get("status"),
        "mca_open_charges": ch.get("open_count"),
        "legal_active_insolvency": lg.get("has_active_insolvency"),
        "legal_recovery_cases": lg.get("recovery_case_count"),
        "created_at": rep.created_at.isoformat() if rep.created_at else None,
    }


def _full_row(rep: Report, supplier_name: str) -> dict:
    return {
        "supplier": supplier_name,
        "gstin": rep.gstin,
        "score": float(rep.score) if rep.score is not None else None,
        "risk_band": rep.risk_band,
        "status": rep.status,
        "gst_provider": rep.provider,
        "mca_provider": rep.mca_provider,
        "gst_identity": rep.gst_identity,
        "gst_compliance": rep.gst_compliance,
        "mca_company": rep.mca_company,
        "mca_directors": rep.mca_directors,
        "mca_charges": rep.mca_charges,
        "mca_legal": rep.mca_legal,
        "score_breakdown": rep.score_breakdown,
        "created_at": rep.created_at.isoformat() if rep.created_at else None,
    }


async def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    out_path = Path(sys.argv[1])
    supplier_filter = sys.argv[2] if len(sys.argv) > 2 else None

    async with SessionLocal() as session:
        names = {s.id: s.name for s in (await session.execute(select(Supplier))).scalars()}
        query = select(Report).order_by(Report.created_at.desc())
        reports = list((await session.execute(query)).scalars())
        if supplier_filter:
            wanted = {sid for sid, n in names.items() if n == supplier_filter}
            reports = [r for r in reports if r.supplier_id in wanted]

        # Keep only the latest report per (supplier, GSTIN) so re-runs don't duplicate.
        seen: set = set()
        deduped = []
        for r in reports:  # already newest-first
            key = (r.supplier_id, r.gstin)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(r)
        reports = deduped

    if not reports:
        print("No saved reports found" + (f" for supplier '{supplier_filter}'." if supplier_filter else "."))
        sys.exit(1)

    if out_path.suffix.lower() == ".json":
        rows = [_full_row(r, names.get(r.supplier_id, "?")) for r in reports]
        out_path.write_text(json.dumps({"count": len(rows), "reports": rows}, indent=2, default=str), encoding="utf-8")
    else:
        rows = [_flat_row(r, names.get(r.supplier_id, "?")) for r in reports]
        cols = list(rows[0].keys())
        with out_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=cols)
            writer.writeheader()
            writer.writerows(rows)

    print(f"Wrote {len(reports)} report(s) to {out_path.resolve()}")


if __name__ == "__main__":
    asyncio.run(main())
