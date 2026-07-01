"""Report service: create a credit signal report and gather signals.

Collection per report (all synchronous today; can move to a worker later):
  - GST identity + compliance (Phase 0/2) — primary; a failure marks the report failed.
  - MCA + legal: company / directors / charges / insolvency / recovery (Phase 3) —
    best-effort; a failure leaves those groups null but never fails the report.
  - The supplier's own payment history for the same GSTIN, if it has a buyer on record.
  - A rule-based credit score over whatever signals came back (Phase 4).
"""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.dao.report_dao import ReportDAO
from app.models.report import Report
from app.services.gst.base import GstProviderError
from app.services.gst.factory import get_gst_provider
from app.services.gst_data_service import GstDataService
from app.services.mca.base import McaProviderError
from app.services.mca_data_service import McaDataService
from app.services.order_service import OrderService
from app.services.scoring import compute_score
from app.utils.dates import age_years
from app.utils.gstin import validate_gstin

logger = logging.getLogger(__name__)


class ReportService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.dao = ReportDAO(session)

    async def create_report(self, supplier_id: UUID, gstin_input: str) -> Report:
        """Validate the GSTIN, persist a report, and collect signals + score into it."""
        settings = get_settings()
        # Raises InvalidGstinError (handled at the router) on bad input.
        gstin = validate_gstin(
            gstin_input, verify_checksum=settings.validate_gstin_checksum
        )

        report = await self.dao.create(supplier_id=supplier_id, gstin=gstin)

        # GST is the primary signal source. Goes through the cache + cost log (Phase 2);
        # a repeat lookup of the same GSTIN is served from cache without paying again.
        try:
            gst = await GstDataService(self.session).fetch(supplier_id, gstin)
            report.provider = gst.provider
            report.gst_identity = gst.identity
            report.gst_compliance = gst.compliance
            report.status = "ready"
        except GstProviderError as exc:
            logger.warning("GST fetch failed for %s: %s", gstin, exc)
            report.provider = get_gst_provider().name
            report.status = "failed"
            report.error = str(exc)

        # MCA + legal: best-effort. Missing data must never break the report.
        # Pass the GST legal name so name-based providers (e.g. Attestr) can resolve it.
        legal_name = (report.gst_identity or {}).get("legal_name")
        try:
            mca = await McaDataService(self.session).fetch(supplier_id, gstin, legal_name)
            report.mca_provider = mca.provider
            report.mca_company = mca.company
            report.mca_directors = mca.directors
            report.mca_charges = mca.charges
            report.mca_legal = mca.legal
        except McaProviderError as exc:
            logger.warning("MCA fetch failed for %s: %s", gstin, exc)

        # Join the supplier's own payment history for this GSTIN, if any.
        payment = await OrderService(self.session).summary_for_gstin(supplier_id, gstin)

        self._apply_score(report, payment)

        await self.session.flush()
        # Reload server-populated columns (created_at/updated_at) before serialization,
        # so accessing them later doesn't trigger a lazy load outside the async context.
        await self.session.refresh(report)
        return report

    def _apply_score(self, report: Report, payment) -> None:
        """(Re)compute the rule-based score onto the report. GST is the backbone: if it
        failed, we publish no score rather than a misleading number from other signals."""
        if report.status == "failed":
            report.score = None
            report.risk_band = "Unknown"
            report.score_breakdown = {
                "score": None,
                "risk_band": "Unknown",
                "note": "No score: GST lookup failed, so there is no reliable data to score.",
                "overrides": [],
                "signals": [],
            }
            return
        reg_date = (report.gst_identity or {}).get("registration_date")
        result = compute_score(
            gst_identity=report.gst_identity,
            gst_compliance=report.gst_compliance,
            gst_age_years=age_years(reg_date),
            mca_company=report.mca_company,
            mca_charges=report.mca_charges,
            mca_legal=report.mca_legal,
            payment=payment,
        )
        report.score = result.score
        report.risk_band = result.risk_band
        report.score_breakdown = result.as_breakdown()

    async def set_manual_company_data(
        self, report_id: UUID, supplier_id: UUID, data: dict
    ) -> Report | None:
        """Save hand-entered company/legal facts (e.g. from mca.gov.in) onto a report
        as real MCA signals (provider 'manual'), then recompute the score."""
        report = await self.dao.get_for_supplier(report_id, supplier_id)
        if report is None:
            return None

        inc = data.get("incorporation_date")
        report.mca_provider = "manual"
        report.mca_company = {
            "registered_with_mca": data.get("registered_with_mca", True),
            "company_name": data.get("company_name"),
            "entity_class": data.get("entity_class"),
            "status": data.get("status"),
            "incorporation_date": inc,
            "age_years": age_years(inc),
            "paid_up_capital": data.get("paid_up_capital"),
        }
        report.mca_directors = {"count": data.get("director_count")}
        report.mca_charges = {
            "open_count": data.get("open_charges"),
            "satisfied_count": data.get("satisfied_charges"),
            "total_open_amount": data.get("total_open_charge_amount"),
        }
        report.mca_legal = {
            "has_active_insolvency": data.get("has_active_insolvency", False),
            "recovery_case_count": data.get("recovery_case_count", 0),
        }

        payment = await OrderService(self.session).summary_for_gstin(
            supplier_id, report.gstin
        )
        self._apply_score(report, payment)

        await self.session.flush()
        await self.session.refresh(report)
        return report

    async def get_report(self, report_id: UUID, supplier_id: UUID) -> Report | None:
        return await self.dao.get_for_supplier(report_id, supplier_id)

    async def list_reports(
        self, supplier_id: UUID, limit: int, offset: int
    ) -> list[Report]:
        return await self.dao.list_for_supplier(supplier_id, limit, offset)
