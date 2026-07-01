"""Resolve the configured MCA + legal provider (MCA_PROVIDER setting).

Only the offline `mock` provider ships today. A real provider (MCA21 via an aggregator
such as Signzy / Probe42 / SurePass for company + charges, plus NJDG / IBBI for legal
cases) drops in here behind the same `McaProvider` interface — add the class, wire its
name below, and set MCA_PROVIDER in .env. The rest of the app is unaffected.
"""

from functools import lru_cache

from app.config import get_settings
from app.services.mca.attestr_provider import AttestrMcaProvider
from app.services.mca.base import McaProvider, McaProviderError
from app.services.mca.mock_provider import MockMcaProvider
from app.services.mca.none_provider import NoneMcaProvider


@lru_cache
def get_mca_provider() -> McaProvider:
    name = get_settings().mca_provider.lower()
    if name == "mock":
        return MockMcaProvider()
    if name in ("none", "off", "manual"):
        # No automated company data — filled in by hand via the manual entry form.
        return NoneMcaProvider()
    if name == "attestr":
        return AttestrMcaProvider()
    raise McaProviderError(
        f"Unknown MCA_PROVIDER '{name}' (expected 'mock', 'none', or 'attestr')."
    )
