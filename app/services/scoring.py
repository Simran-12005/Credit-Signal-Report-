"""Rule-based credit score (Phase 4) — a transparent, weighted blend of the signals.

This is the "simple rule-based report meanwhile" the plan calls for: usable while the
labelled dataset grows, and later a baseline for the ML model to beat. It is a pure
function of the collected signals — no DB, no I/O — so it's easy to test and explain.

How it works
------------
Each signal group is scored 0–100 where **higher = safer to extend credit**. Groups are
combined as a weighted average, but only over the groups we actually have data for: a
missing group drops out and the remaining weights are renormalised, so missing data
never breaks (or unfairly tanks) the score. Two hard overrides force HIGH risk
regardless of the blend: an active insolvency proceeding, or a cancelled GST
registration — both are near-disqualifying for unsecured credit.

The result carries a per-signal breakdown (weight, sub-score, contribution) so the
report can show *why* it landed where it did.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:  # avoid importing the pydantic schema at runtime (keeps scoring pure)
    from app.schemas.buyer import PaymentSummary

# Weights across all signal groups (sum to 1.0). Renormalised over whatever is present.
WEIGHTS = {
    "payment_history": 0.25,   # our own first-party outcome — most trusted
    "gst_compliance": 0.20,    # filing discipline
    "legal": 0.15,             # insolvency / recovery cases
    "gst_status": 0.12,        # active / suspended / cancelled
    "mca_status": 0.10,        # company alive / strike-off / liquidation
    "mca_charges": 0.10,       # secured-debt load
    "gst_age": 0.08,           # how long established
}

LOW_THRESHOLD = 70.0   # score >= 70 -> Low risk
MED_THRESHOLD = 45.0   # 45–69 -> Medium; below -> High


@dataclass
class SignalScore:
    key: str
    label: str
    weight: float
    sub_score: Optional[float]  # 0–100, or None if the signal is unavailable
    available: bool
    detail: str


@dataclass
class ScoreResult:
    score: Optional[float]          # 0–100, None if no signals at all
    risk_band: str                  # "Low" | "Medium" | "High" | "Unknown"
    signals: list[SignalScore] = field(default_factory=list)
    overrides: list[str] = field(default_factory=list)

    def as_breakdown(self) -> dict[str, Any]:
        """JSON-friendly breakdown for storage / API response."""
        return {
            "score": self.score,
            "risk_band": self.risk_band,
            "overrides": self.overrides,
            "signals": [
                {
                    "key": s.key,
                    "label": s.label,
                    "weight": s.weight,
                    "sub_score": s.sub_score,
                    "available": s.available,
                    # share of the final score this signal contributed (0 if unavailable)
                    "contribution": (
                        round(s.sub_score * s.weight, 2)
                        if (s.available and s.sub_score is not None)
                        else 0.0
                    ),
                    "detail": s.detail,
                }
                for s in self.signals
            ],
        }


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


# --- per-signal sub-scores -------------------------------------------------------

def _score_gst_status(identity: Optional[dict]) -> SignalScore:
    status = (identity or {}).get("status")
    if not status:
        return SignalScore("gst_status", "GST registration status", WEIGHTS["gst_status"], None, False, "No GST status")
    s = str(status).lower()
    if "cancel" in s:
        sub = 0.0
    elif "suspend" in s:
        sub = 40.0
    elif "active" in s:
        sub = 100.0
    else:
        sub = 70.0  # provisional / unknown-but-present
    return SignalScore("gst_status", "GST registration status", WEIGHTS["gst_status"], sub, True, f"Status: {status}")


def _score_gst_compliance(compliance: Optional[dict]) -> SignalScore:
    c = compliance or {}
    rate = c.get("on_time_filing_rate")
    if rate is None:
        # Derive from counts if the provider gave those instead of a rate.
        expected = c.get("expected_returns_12m")
        filed = c.get("returns_filed_12m") or c.get("returns_filed")
        if expected and filed is not None:
            rate = filed / expected
    if rate is None:
        return SignalScore("gst_compliance", "GST filing compliance", WEIGHTS["gst_compliance"], None, False, "No filing data")
    sub = _clamp(float(rate) * 100.0)
    if c.get("is_compliant") is False:
        sub = _clamp(sub - 10.0)
    return SignalScore(
        "gst_compliance", "GST filing compliance", WEIGHTS["gst_compliance"], sub, True,
        f"On-time filing rate {round(float(rate) * 100)}%",
    )


def _score_gst_age(age_years: Optional[float]) -> SignalScore:
    if age_years is None:
        return SignalScore("gst_age", "Years GST-registered", WEIGHTS["gst_age"], None, False, "No registration date")
    # 0 yrs -> 20, ramps to 100 at 5+ years established.
    sub = _clamp(20.0 + (age_years / 5.0) * 80.0)
    return SignalScore("gst_age", "Years GST-registered", WEIGHTS["gst_age"], sub, True, f"{age_years} years registered")


def _score_mca_status(company: Optional[dict]) -> SignalScore:
    c = company or {}
    if not c.get("registered_with_mca"):
        # Not a company/LLP — MCA status simply doesn't apply (don't penalise).
        return SignalScore("mca_status", "Company status (MCA)", WEIGHTS["mca_status"], None, False, "Not registered with MCA")
    status = str(c.get("status") or "").lower()
    if "liquidation" in status or "strike" in status:
        sub = 0.0
    elif "dormant" in status:
        sub = 50.0
    elif "amalgamat" in status:
        sub = 30.0
    elif "active" in status:
        sub = 100.0
    else:
        sub = 60.0
    return SignalScore("mca_status", "Company status (MCA)", WEIGHTS["mca_status"], sub, True, f"Status: {c.get('status')}")


def _score_mca_charges(charges: Optional[dict]) -> SignalScore:
    if not charges:
        return SignalScore("mca_charges", "Secured-debt load (charges)", WEIGHTS["mca_charges"], None, False, "No charge data")
    open_count = charges.get("open_count", 0) or 0
    # No open charges -> 100; each open charge knocks off 25 points.
    sub = _clamp(100.0 - open_count * 25.0)
    return SignalScore(
        "mca_charges", "Secured-debt load (charges)", WEIGHTS["mca_charges"], sub, True,
        f"{open_count} open charge(s)",
    )


def _score_legal(legal: Optional[dict]) -> SignalScore:
    if not legal:
        return SignalScore("legal", "Insolvency / recovery cases", WEIGHTS["legal"], None, False, "No legal data")
    if legal.get("has_active_insolvency"):
        return SignalScore("legal", "Insolvency / recovery cases", WEIGHTS["legal"], 0.0, True, "Active insolvency proceeding")
    recovery = legal.get("recovery_case_count", 0) or 0
    sub = _clamp(100.0 - recovery * 30.0)
    detail = "No cases" if recovery == 0 else f"{recovery} recovery case(s)"
    return SignalScore("legal", "Insolvency / recovery cases", WEIGHTS["legal"], sub, True, detail)


def _score_payment(payment: "Optional[PaymentSummary]") -> SignalScore:
    if payment is None or payment.total_orders == 0 or payment.on_time_rate is None:
        return SignalScore("payment_history", "Own payment history", WEIGHTS["payment_history"], None, False, "No payment history")
    sub = payment.on_time_rate * 100.0
    sub -= (payment.total_bounces or 0) * 10.0      # each bounce is a strong negative
    sub -= (payment.overdue_orders or 0) * 5.0       # currently-overdue invoices
    sub = _clamp(sub)
    return SignalScore(
        "payment_history", "Own payment history", WEIGHTS["payment_history"], sub, True,
        f"On-time {round(payment.on_time_rate * 100)}%, {payment.total_bounces} bounce(s)",
    )


# --- blend -----------------------------------------------------------------------

def _band(score: Optional[float]) -> str:
    if score is None:
        return "Unknown"
    if score >= LOW_THRESHOLD:
        return "Low"
    if score >= MED_THRESHOLD:
        return "Medium"
    return "High"


def compute_score(
    *,
    gst_identity: Optional[dict] = None,
    gst_compliance: Optional[dict] = None,
    gst_age_years: Optional[float] = None,
    mca_company: Optional[dict] = None,
    mca_charges: Optional[dict] = None,
    mca_legal: Optional[dict] = None,
    payment: "Optional[PaymentSummary]" = None,
) -> ScoreResult:
    """Blend the available signals into a 0–100 score + risk band + breakdown."""
    signals = [
        _score_payment(payment),
        _score_gst_compliance(gst_compliance),
        _score_legal(mca_legal),
        _score_gst_status(gst_identity),
        _score_mca_status(mca_company),
        _score_mca_charges(mca_charges),
        _score_gst_age(gst_age_years),
    ]

    available = [s for s in signals if s.available and s.sub_score is not None]
    total_weight = sum(s.weight for s in available)
    if total_weight == 0:
        return ScoreResult(score=None, risk_band="Unknown", signals=signals)

    score = sum(s.sub_score * s.weight for s in available) / total_weight

    # Hard overrides: certain signals disqualify regardless of the weighted blend.
    overrides: list[str] = []
    if (mca_legal or {}).get("has_active_insolvency"):
        overrides.append("Active insolvency proceeding")
    if "cancel" in str((gst_identity or {}).get("status", "")).lower():
        overrides.append("GST registration cancelled")
    mca_status = str((mca_company or {}).get("status", "")).lower()
    if "liquidation" in mca_status or "strike" in mca_status:
        overrides.append("Company under liquidation / struck off")

    if overrides:
        score = min(score, MED_THRESHOLD - 1.0)  # force into the High band

    score = round(_clamp(score), 2)
    return ScoreResult(score=score, risk_band=_band(score), signals=signals, overrides=overrides)
