"""MockGstProvider — realistic, deterministic fake GST data (the Phase 0 stub).

Returns identity + compliance signals derived deterministically from the GSTIN, so
the same GSTIN always yields the same data. Lets us build and test the entire
report flow offline with zero API cost. Swap to PerfiosGstProvider for real data.
"""

import hashlib
from datetime import date, timedelta

from app.services.gst.base import GstData, GstProvider

# Subset of GST state codes (first 2 digits of a GSTIN) -> state name.
_STATE_CODES = {
    "01": "Jammu and Kashmir", "02": "Himachal Pradesh", "03": "Punjab",
    "04": "Chandigarh", "05": "Uttarakhand", "06": "Haryana", "07": "Delhi",
    "08": "Rajasthan", "09": "Uttar Pradesh", "10": "Bihar", "19": "West Bengal",
    "21": "Odisha", "23": "Madhya Pradesh", "24": "Gujarat", "27": "Maharashtra",
    "29": "Karnataka", "32": "Kerala", "33": "Tamil Nadu", "36": "Telangana",
    "37": "Andhra Pradesh",
}

_TAXPAYER_TYPES = ["Regular", "Composition", "Regular", "Regular"]


class MockGstProvider(GstProvider):
    name = "mock"
    cost_per_call = 0.0  # free, offline

    async def fetch_gst_data(self, gstin: str) -> GstData:
        # Deterministic pseudo-randomness seeded from the GSTIN.
        seed = int(hashlib.sha256(gstin.encode()).hexdigest(), 16)

        state = _STATE_CODES.get(gstin[:2], "Unknown")
        pan = gstin[2:12]
        taxpayer_type = _TAXPAYER_TYPES[seed % len(_TAXPAYER_TYPES)]

        # Registration 1-12 years ago.
        years_ago = 1 + (seed % 12)
        reg_date = date(2026, 1, 1) - timedelta(days=365 * years_ago + (seed % 365))

        # Active most of the time; occasionally suspended/cancelled.
        status_roll = seed % 100
        if status_roll < 85:
            gst_status = "Active"
        elif status_roll < 95:
            gst_status = "Suspended"
        else:
            gst_status = "Cancelled"

        identity = {
            "gstin": gstin,
            "legal_name": f"Mock Traders {pan[:5]} Pvt Ltd",
            "trade_name": f"Mock {pan[:5]}",
            "pan": pan,
            "taxpayer_type": taxpayer_type,
            "state": state,
            "state_code": gstin[:2],
            "registration_date": reg_date.isoformat(),
            "status": gst_status,
        }

        # Compliance: last 12 monthly filings, with some misses.
        expected_returns = 12
        missed = seed % 4  # 0-3 missed filings
        returns_filed = expected_returns - missed
        last_filed = date(2026, 5, 31) - timedelta(days=30 * (seed % 3))
        on_time_rate = round(returns_filed / expected_returns, 2)

        compliance = {
            "filing_frequency": "Monthly",
            "expected_returns_12m": expected_returns,
            "returns_filed_12m": returns_filed,
            "missed_filings_12m": missed,
            "on_time_filing_rate": on_time_rate,
            "last_return_filed_date": last_filed.isoformat(),
            "is_compliant": gst_status == "Active" and missed <= 1,
        }

        return GstData(identity=identity, compliance=compliance)
