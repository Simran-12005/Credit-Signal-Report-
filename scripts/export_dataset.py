"""Build credit-signal data for a list of GSTINs and export it to a file.

The simple way to produce a shareable dataset: no running server, no API key, no curl.
Runs through whatever GST/MCA provider is configured in .env — so it gives mock data by
default, and REAL GST data automatically once GST_PROVIDER=sandbox + keys are set.

Usage:
    uv run python scripts/export_dataset.py "Supplier Name" gstins.txt out.csv
    uv run python scripts/export_dataset.py "Supplier Name" gstins.txt out.json

  - "Supplier Name"  the account the data is built under (created if it doesn't exist).
  - gstins.txt       one GSTIN per line (blank lines and #comments ignored).
  - out.csv/out.json output file; format chosen by the .csv / .json extension.

Each GSTIN gets a fresh feature snapshot (GST + MCA + legal signals, payment history if
the supplier has a matching buyer, and the rule-based score). The file then contains the
latest snapshot per business — one flat row each.
"""

import asyncio
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.models.supplier import Supplier  # noqa: E402
from app.routers.features import _dataset_row  # noqa: E402
from app.services.feature_builder_service import (  # noqa: E402
    FeatureBuildError,
    FeatureBuilderService,
)
from app.utils.gstin import InvalidGstinError  # noqa: E402


def _read_gstins(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    out = []
    for line in lines:
        token = line.strip()
        if token and not token.startswith("#"):
            out.append(token)
    return out


async def _get_or_create_supplier(session, name: str) -> Supplier:
    result = await session.execute(select(Supplier).where(Supplier.name == name))
    supplier = result.scalar_one_or_none()
    if supplier is None:
        supplier = Supplier(name=name)
        session.add(supplier)
        await session.flush()
        print(f"Created supplier '{name}'.")
    else:
        print(f"Using existing supplier '{name}'.")
    return supplier


def _write_csv(rows: list[dict], out_path: Path) -> None:
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


async def main() -> None:
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)

    supplier_name, gstins_file, out_file = sys.argv[1], sys.argv[2], sys.argv[3]
    gstins = _read_gstins(Path(gstins_file))
    out_path = Path(out_file)
    if not gstins:
        print(f"No GSTINs found in {gstins_file}.")
        sys.exit(1)

    async with SessionLocal() as session:
        supplier = await _get_or_create_supplier(session, supplier_name)
        builder = FeatureBuilderService(session)

        ok, failed = 0, 0
        for gstin in gstins:
            try:
                snap = await builder.build(supplier.id, gstin)
                print(f"  {gstin}  -> score {snap.score} ({snap.risk_band})")
                ok += 1
            except (InvalidGstinError, FeatureBuildError) as exc:
                print(f"  {gstin}  -> SKIPPED: {exc}")
                failed += 1
        await session.commit()

        # Latest snapshot per business -> flat rows.
        snapshots = await builder.dataset(supplier.id)
        rows = [_dataset_row(s) for s in snapshots]

    if out_path.suffix.lower() == ".json":
        out_path.write_text(
            json.dumps({"count": len(rows), "rows": rows}, indent=2, default=str),
            encoding="utf-8",
        )
    else:
        _write_csv(rows, out_path)

    print(f"\nBuilt {ok} GSTIN(s), skipped {failed}.")
    print(f"Wrote {len(rows)} row(s) to {out_path.resolve()}")


if __name__ == "__main__":
    asyncio.run(main())
