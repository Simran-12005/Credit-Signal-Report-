"""NoneMcaProvider — returns no company/legal data (empty groups).

Used when MCA_PROVIDER=none: reports come back with the company section blank instead
of fabricated mock data, so it can be filled in by hand (e.g. from mca.gov.in) via the
manual entry form. Costs nothing and never errors.
"""

from app.services.mca.base import McaData, McaProvider


class NoneMcaProvider(McaProvider):
    name = "none"
    cost_per_call = 0.0

    async def fetch_mca_data(self, gstin: str, legal_name: str | None = None) -> McaData:
        return McaData(company={}, directors={}, charges={}, legal={})
