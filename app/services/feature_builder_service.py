"""Feature builder (Phase 4): turn collected signals into one clean dataset row.

For a (supplier, GSTIN) it gathers GST + MCA/legal signals (through the same caches as
the report) and the supplier's own payment outcome, then:
  - flattens everything into a flat `features` dict (scalar, ML-ready),
  - records the payment outcome as the `label`,
  - computes the rule-based score over the signals,
  - persists a versioned, as_of_date-stamped snapshot.

This is the "labelled dataset ready for training" the plan's Part A builds toward;
Part B (the model) trains on exactly these rows.
"""

import logging
from datetime import date
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.dao.buyer_dao import BuyerDAO
from app.dao.feature_snapshot_dao import FeatureSnapshotDAO
from app.models.feature_snapshot import FeatureSnapshot
from app.schemas.buyer import PaymentSummary
from app.services.gst.base import GstProviderError
from app.services.gst_data_service import GstDataService
from app.services.mca.base import McaProviderError
from app.services.mca_data_service import McaDataService
from app.services.order_service import OrderService
from app.services.scoring import compute_score
from app.utils.dates import age_years
from app.utils.gstin import validate_gstin

logger = logging.getLogger(__name__)


class FeatureBuildError(Exception):
    """Raised when no signals at all could be gathered (nothing worth a snapshot)."""


def _flatten_features(
    *,
    gst_identity: Optional[dict],
    gst_compliance: Optional[dict],
    gst_age: Optional[float],
    mca_company: Optional[dict],
    mca_directors: Optional[dict],
    mca_charges: Optional[dict],
    mca_legal: Optional[dict],
    payment: Optional[PaymentSummary],
) -> dict[str, Any]:
    """Flatten the nested signal groups into a flat, scalar feature dict."""
    gi, gc = gst_identity or {}, gst_compliance or {}
    co, di = mca_company or {}, mca_directors or {}
    ch, lg = mca_charges or {}, mca_legal or {}
    return {
        # GST identity
        "gst_status": gi.get("status"),
        "gst_taxpayer_type": gi.get("taxpayer_type"),
        "gst_state": gi.get("state"),
        "gst_registration_age_years": gst_age,
        # GST compliance
        "gst_on_time_filing_rate": gc.get("on_time_filing_rate"),
        "gst_missed_filings_12m": gc.get("missed_filings_12m"),
        "gst_returns_filed": gc.get("returns_filed_12m") or gc.get("returns_filed"),
        "gst_is_compliant": gc.get("is_compliant"),
        # MCA company
        "mca_registered": bool(co.get("registered_with_mca")),
        "mca_entity_class": co.get("entity_class"),
        "mca_company_status": co.get("status"),
        "mca_age_years": co.get("age_years"),
        "mca_paid_up_capital": co.get("paid_up_capital"),
        "mca_director_count": di.get("count"),
        "mca_has_disqualified_director": di.get("has_disqualified_director"),
        # MCA charges
        "mca_open_charges": ch.get("open_count"),
        "mca_total_open_charge_amount": ch.get("total_open_amount"),
        # Legal
        "legal_has_active_insolvency": lg.get("has_active_insolvency"),
        "legal_recovery_case_count": lg.get("recovery_case_count"),
        "legal_total_recovery_amount": lg.get("total_recovery_amount"),
        # Payment history (also the basis of the label)
        "pay_total_orders": payment.total_orders if payment else None,
        "pay_on_time_rate": payment.on_time_rate if payment else None,
        "pay_avg_delay_days": payment.avg_delay_days if payment else None,
        "pay_total_bounces": payment.total_bounces if payment else None,
        "pay_overdue_orders": payment.overdue_orders if payment else None,
    }


def _label(payment: Optional[PaymentSummary]) -> Optional[dict[str, Any]]:
    """The payment outcome we train against — None until the supplier has orders."""
    if payment is None or payment.total_orders == 0:
        return None
    return {
        "on_time_rate": payment.on_time_rate,
        "avg_delay_days": payment.avg_delay_days,
        "max_delay_days": payment.max_delay_days,
        "total_bounces": payment.total_bounces,
        "outstanding_amount": float(payment.outstanding_amount),
        # A coarse, model-ready class: did this buyer pay reliably?
        "good_payer": (
            payment.on_time_rate is not None
            and payment.on_time_rate >= 0.8
            and payment.total_bounces == 0
        ),
    }


class FeatureBuilderService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.dao = FeatureSnapshotDAO(session)

    async def build(
        self,
        supplier_id: UUID,
        gstin_input: str,
        buyer_id: UUID | None = None,
        as_of: date | None = None,
    ) -> FeatureSnapshot:
        settings = get_settings()
        gstin = validate_gstin(
            gstin_input, verify_checksum=settings.validate_gstin_checksum
        )
        as_of = as_of or date.today()

        # GST (best-effort here — a snapshot is still useful from MCA + payments alone).
        gst_identity = gst_compliance = None
        gst_provider = None
        try:
            gst = await GstDataService(self.session).fetch(supplier_id, gstin)
            gst_identity, gst_compliance, gst_provider = gst.identity, gst.compliance, gst.provider
        except GstProviderError as exc:
            logger.warning("GST fetch failed for %s: %s", gstin, exc)

        # MCA + legal (best-effort). Pass GST legal name for name-based providers.
        mca_company = mca_directors = mca_charges = mca_legal = None
        mca_provider = None
        legal_name = (gst_identity or {}).get("legal_name")
        try:
            mca = await McaDataService(self.session).fetch(supplier_id, gstin, legal_name)
            mca_company, mca_directors = mca.company, mca.directors
            mca_charges, mca_legal, mca_provider = mca.charges, mca.legal, mca.provider
        except McaProviderError as exc:
            logger.warning("MCA fetch failed for %s: %s", gstin, exc)

        # Payment label: explicit buyer if given, else the supplier's buyer for this GSTIN.
        payment, used_buyer_id = await self._payment_label(supplier_id, gstin, buyer_id)

        if not any([gst_identity, gst_compliance, mca_company, mca_legal, payment]):
            raise FeatureBuildError(
                f"No signals available for {gstin} — nothing to snapshot."
            )

        reg_date = (gst_identity or {}).get("registration_date")
        gst_age = age_years(reg_date, as_of=as_of)

        result = compute_score(
            gst_identity=gst_identity,
            gst_compliance=gst_compliance,
            gst_age_years=gst_age,
            mca_company=mca_company,
            mca_charges=mca_charges,
            mca_legal=mca_legal,
            payment=payment,
        )

        features = _flatten_features(
            gst_identity=gst_identity,
            gst_compliance=gst_compliance,
            gst_age=gst_age,
            mca_company=mca_company,
            mca_directors=mca_directors,
            mca_charges=mca_charges,
            mca_legal=mca_legal,
            payment=payment,
        )
        label = _label(payment)

        version = await self.dao.next_version(supplier_id, gstin)
        return await self.dao.create({
            "supplier_id": supplier_id,
            "gstin": gstin,
            "buyer_id": used_buyer_id,
            "as_of_date": as_of,
            "version": version,
            "features": features,
            "label": label,
            "has_label": label is not None,
            "score": Decimal(str(result.score)) if result.score is not None else None,
            "risk_band": result.risk_band,
            "score_breakdown": result.as_breakdown(),
            "gst_provider": gst_provider,
            "mca_provider": mca_provider,
        })

    async def _payment_label(
        self, supplier_id: UUID, gstin: str, buyer_id: UUID | None
    ) -> tuple[Optional[PaymentSummary], Optional[UUID]]:
        order_svc = OrderService(self.session)
        if buyer_id is not None:
            buyer = await BuyerDAO(self.session).get_for_supplier(buyer_id, supplier_id)
            if buyer is None:
                return None, None
            return await order_svc.summary_for_buyer(supplier_id, buyer), buyer.id

        buyer = await BuyerDAO(self.session).get_by_gstin(supplier_id, gstin)
        if buyer is None:
            return None, None
        return await order_svc.summary_for_buyer(supplier_id, buyer), buyer.id

    async def get(self, snapshot_id: UUID, supplier_id: UUID) -> FeatureSnapshot | None:
        return await self.dao.get_for_supplier(snapshot_id, supplier_id)

    async def list_snapshots(
        self, supplier_id: UUID, gstin: str | None, limit: int, offset: int
    ) -> list[FeatureSnapshot]:
        return await self.dao.list_for_supplier(supplier_id, gstin, limit, offset)

    async def dataset(self, supplier_id: UUID) -> list[FeatureSnapshot]:
        return await self.dao.latest_per_gstin(supplier_id)
