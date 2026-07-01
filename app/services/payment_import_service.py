"""Bulk entry of payment history: CSV upload and a sample-data generator.

Both let a supplier populate realistic payment behaviour quickly so there's data to
work with (and, later, to train on).
"""

import csv
import io
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.dao.buyer_dao import BuyerDAO
from app.dao.order_dao import OrderDAO
from app.schemas.order import CsvImportResult
from app.utils.gstin import InvalidGstinError, validate_gstin

CSV_COLUMNS = [
    "buyer_name", "buyer_gstin", "invoice_number", "amount",
    "order_date", "due_date", "paid_date", "status", "bounce_count",
]


def _parse_date(value: str | None) -> date | None:
    value = (value or "").strip()
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


class PaymentImportService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.buyer_dao = BuyerDAO(session)
        self.order_dao = OrderDAO(session)

    async def _get_or_create_buyer(
        self, supplier_id: UUID, name: str, gstin: str | None, cache: dict
    ):
        key = gstin or f"name:{name.lower()}"
        if key in cache:
            return cache[key]
        buyer = None
        if gstin:
            buyer = await self.buyer_dao.get_by_gstin(supplier_id, gstin)
        if buyer is None:
            buyer = await self.buyer_dao.create(
                supplier_id, {"name": name, "gstin": gstin}
            )
        cache[key] = buyer
        return buyer

    async def import_csv(self, supplier_id: UUID, content: bytes) -> CsvImportResult:
        verify = get_settings().validate_gstin_checksum
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))

        errors: list[str] = []
        buyer_cache: dict = {}
        buyers_before = len(buyer_cache)
        orders_created = 0
        rows = 0

        for i, row in enumerate(reader, start=2):  # row 1 is the header
            rows += 1
            try:
                name = (row.get("buyer_name") or "").strip()
                gstin = (row.get("buyer_gstin") or "").strip() or None
                if not name and not gstin:
                    raise ValueError("buyer_name or buyer_gstin is required")
                if gstin:
                    gstin = validate_gstin(gstin, verify_checksum=verify)
                if not name:
                    name = gstin  # fall back to the GSTIN as a label

                try:
                    amount = Decimal((row.get("amount") or "0").strip())
                except InvalidOperation:
                    raise ValueError(f"invalid amount {row.get('amount')!r}")

                order_date = _parse_date(row.get("order_date")) or date.today()
                due_date = _parse_date(row.get("due_date")) or order_date
                paid_date = _parse_date(row.get("paid_date"))
                status = (row.get("status") or "").strip().lower() or (
                    "paid" if paid_date else "pending"
                )
                if status not in ("pending", "paid", "bounced"):
                    raise ValueError(f"invalid status {status!r}")
                bounce_count = int((row.get("bounce_count") or "0").strip() or 0)

                buyer = await self._get_or_create_buyer(
                    supplier_id, name, gstin, buyer_cache
                )
                await self.order_dao.create(
                    supplier_id,
                    buyer.id,
                    {
                        "invoice_number": (row.get("invoice_number") or "").strip() or None,
                        "amount": amount,
                        "order_date": order_date,
                        "due_date": due_date,
                        "paid_date": paid_date,
                        "status": status,
                        "bounce_count": bounce_count,
                    },
                )
                orders_created += 1
            except (ValueError, InvalidGstinError) as exc:
                errors.append(f"row {i}: {exc}")

        await self.session.flush()
        return CsvImportResult(
            buyers_created=len(buyer_cache) - buyers_before,
            orders_created=orders_created,
            rows_processed=rows,
            errors=errors,
        )

    async def seed_sample(self, supplier_id: UUID) -> CsvImportResult:
        """Create three buyers with distinct payment profiles, for quick testing."""
        today = date.today()
        cache: dict = {}

        # (name, gstin, [(days_ago_ordered, term_days, paid_offset_or_None, status, bounces)])
        profiles = [
            ("Reliable Retail",  "27AAPFU0939F1ZV", [
                (120, 30, 28, "paid", 0), (90, 30, 25, "paid", 0),
                (60, 30, 30, "paid", 0), (30, 30, None, "pending", 0),
            ]),
            ("Slowpay Stores",   "29AABCU9603R1ZJ", [
                (150, 45, 70, "paid", 0), (100, 45, 80, "paid", 0),
                (50, 45, None, "pending", 0),
            ]),
            ("Risky Traders",    "07AAGFF2194N1Z1", [
                (200, 30, 95, "paid", 2), (120, 30, None, "bounced", 1),
                (40, 30, None, "pending", 0),
            ]),
        ]

        orders_created = 0
        for name, gstin, orders in profiles:
            buyer = await self._get_or_create_buyer(supplier_id, name, gstin, cache)
            for ordered_ago, term, paid_offset, status, bounces in orders:
                order_date = today - timedelta(days=ordered_ago)
                due_date = order_date + timedelta(days=term)
                paid_date = (
                    order_date + timedelta(days=paid_offset)
                    if paid_offset is not None
                    else None
                )
                await self.order_dao.create(
                    supplier_id,
                    buyer.id,
                    {
                        "amount": Decimal("50000.00"),
                        "order_date": order_date,
                        "due_date": due_date,
                        "paid_date": paid_date,
                        "status": status,
                        "bounce_count": bounces,
                    },
                )
                orders_created += 1

        await self.session.flush()
        return CsvImportResult(
            buyers_created=len(cache),
            orders_created=orders_created,
            rows_processed=orders_created,
            errors=[],
        )
