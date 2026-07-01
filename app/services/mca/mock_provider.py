"""MockMcaProvider — realistic, deterministic fake MCA + legal data (the Phase 3 stub).

Returns company / directors / charges / legal signals derived deterministically from the
GSTIN, so the same GSTIN always yields the same data. Lets us build and test the whole
report + scoring flow offline with zero API cost.

Whether an entity has MCA *company* data depends on its constitution, which the GSTIN
encodes: the 4th character of the embedded PAN (GSTIN position 5) is the PAN holder type
— 'C' = company, 'F' = LLP/firm, others (P/H/A/T/...) are non-corporate (proprietor, HUF,
trust, ...) and have no MCA filing. Legal (insolvency/recovery) cases can hit any entity,
so that group is always populated (usually empty = clean).
"""

import hashlib
from datetime import date, timedelta

from app.services.mca.base import McaData, McaProvider

_COMPANY_STATUSES = [
    "Active", "Active", "Active", "Active", "Active",
    "Active", "Active", "Dormant", "Strike Off", "Under Liquidation",
]

_DESIGNATIONS = ["Director", "Director", "Managing Director", "Whole-time Director"]
_BANKS = [
    "HDFC Bank", "State Bank of India", "ICICI Bank", "Axis Bank",
    "Kotak Mahindra Bank", "Bajaj Finserv",
]
_ROCS = {
    "27": "RoC-Mumbai", "07": "RoC-Delhi", "29": "RoC-Bangalore",
    "24": "RoC-Ahmedabad", "33": "RoC-Chennai", "19": "RoC-Kolkata",
}


def _entity_class(pan_type: str) -> str | None:
    """Map the PAN holder type to an MCA-registered entity class (None = not on MCA)."""
    if pan_type == "C":
        return "Private Limited Company"
    if pan_type == "F":
        return "Limited Liability Partnership"
    return None


class MockMcaProvider(McaProvider):
    name = "mock"
    cost_per_call = 0.0  # free, offline

    async def fetch_mca_data(self, gstin: str, legal_name: str | None = None) -> McaData:
        seed = int(hashlib.sha256(("mca:" + gstin).encode()).hexdigest(), 16)

        pan = gstin[2:12]
        pan_type = pan[3] if len(pan) >= 4 else "P"
        entity_class = _entity_class(pan_type)

        legal = self._legal(seed, gstin)

        if entity_class is None:
            # Non-corporate entity: no MCA filing, but legal cases can still exist.
            company = {"registered_with_mca": False, "entity_class": None}
            return McaData(company=company, directors={}, charges={}, legal=legal)

        company = self._company(seed, gstin, pan, entity_class)
        directors = self._directors(seed, pan)
        charges = self._charges(seed)
        return McaData(company=company, directors=directors, charges=charges, legal=legal)

    def _company(self, seed: int, gstin: str, pan: str, entity_class: str) -> dict:
        years_ago = 1 + (seed % 18)
        inc_date = date(2026, 1, 1) - timedelta(days=365 * years_ago + (seed % 365))
        age_years = round((date(2026, 1, 1) - inc_date).days / 365.25, 1)
        status = _COMPANY_STATUSES[seed % len(_COMPANY_STATUSES)]
        authorized = (1 + seed % 50) * 100_000
        paid_up = int(authorized * (0.3 + (seed % 70) / 100))
        return {
            "registered_with_mca": True,
            "cin": f"U{(seed % 90000) + 10000}{gstin[:2]}{2026 - years_ago}PTC{(seed % 900000) + 100000}",
            "company_name": f"Mock Traders {pan[:5]} Pvt Ltd",
            "entity_class": entity_class,
            "incorporation_date": inc_date.isoformat(),
            "age_years": age_years,
            "status": status,
            "roc": _ROCS.get(gstin[:2], "RoC-Other"),
            "authorized_capital": authorized,
            "paid_up_capital": paid_up,
        }

    def _directors(self, seed: int, pan: str) -> dict:
        count = 2 + (seed % 4)  # 2-5 directors
        directors = []
        for i in range(count):
            dseed = seed >> (i * 8)
            appt_years = 1 + (dseed % 10)
            appt = date(2026, 1, 1) - timedelta(days=365 * appt_years + (dseed % 365))
            directors.append({
                "name": f"Director {pan[:3]}{i + 1}",
                "din": f"{(dseed % 90000000) + 10000000:08d}",
                "designation": _DESIGNATIONS[dseed % len(_DESIGNATIONS)],
                "appointment_date": appt.isoformat(),
            })
        return {
            "count": count,
            "directors": directors,
            # ~6% of mock companies have a disqualified director on the board.
            "has_disqualified_director": (seed % 16) == 0,
        }

    def _charges(self, seed: int) -> dict:
        # 0-3 secured charges; some satisfied (repaid), some still open.
        total_charges = seed % 4
        charges = []
        open_count = 0
        satisfied_count = 0
        total_open = 0
        for i in range(total_charges):
            cseed = seed >> (i * 7)
            amount = (1 + cseed % 200) * 100_000
            is_open = (cseed % 3) != 0
            created = date(2026, 1, 1) - timedelta(days=365 * (1 + cseed % 8))
            charges.append({
                "holder": _BANKS[cseed % len(_BANKS)],
                "amount": amount,
                "status": "open" if is_open else "satisfied",
                "creation_date": created.isoformat(),
            })
            if is_open:
                open_count += 1
                total_open += amount
            else:
                satisfied_count += 1
        return {
            "open_count": open_count,
            "satisfied_count": satisfied_count,
            "total_open_amount": total_open,
            "charges": charges,
        }

    def _legal(self, seed: int, gstin: str) -> dict:
        # ~5% have an active insolvency proceeding (IBBI); recovery suits are a bit
        # more common. Most entities are clean.
        has_insolvency = (seed % 20) == 0
        insolvency_cases = []
        if has_insolvency:
            insolvency_cases.append({
                "case_type": "CIRP",  # Corporate Insolvency Resolution Process
                "authority": "NCLT",
                "status": "Admitted",
                "filed_date": (date(2026, 1, 1) - timedelta(days=30 + seed % 600)).isoformat(),
            })

        recovery_count = 0
        recovery_cases = []
        total_recovery = 0
        if (seed % 7) == 0:
            recovery_count = 1 + (seed % 3)
            for i in range(recovery_count):
                rseed = seed >> (i * 5)
                amount = (1 + rseed % 100) * 100_000
                total_recovery += amount
                recovery_cases.append({
                    "case_type": "Recovery Suit",
                    "court": "DRT" if rseed % 2 else "Civil Court",
                    "status": "Pending" if rseed % 2 else "Decree Passed",
                    "amount": amount,
                    "filed_date": (date(2026, 1, 1) - timedelta(days=60 + rseed % 900)).isoformat(),
                })

        return {
            "has_active_insolvency": has_insolvency,
            "insolvency_cases": insolvency_cases,
            "recovery_case_count": recovery_count,
            "recovery_cases": recovery_cases,
            "total_recovery_amount": total_recovery,
        }
