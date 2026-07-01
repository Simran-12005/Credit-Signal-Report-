"""The swappable GST data provider interface.

Every concrete provider (mock, Perfios, Clear, ...) implements `fetch_gst_data` and
returns the same normalized shape, so the rest of the app never depends on a specific
vendor. Swap providers via the GST_PROVIDER setting.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class GstData:
    """Normalized GST signals for one GSTIN, vendor-independent."""

    # Identity: legal_name, trade_name, registration_date, taxpayer_type, state, status, ...
    identity: dict[str, Any] = field(default_factory=dict)
    # Compliance: filing_status, returns_filed, last_filed_date, missed_filings, ...
    compliance: dict[str, Any] = field(default_factory=dict)


class GstProviderError(Exception):
    """Raised when a provider cannot return data (network, auth, not found)."""


class GstProvider(ABC):
    """Interface for a GST data source."""

    name: str = "base"
    # Approximate cost charged per live call (currency-agnostic units). Used for the
    # cost log; cache hits cost nothing. Override per provider.
    cost_per_call: float = 0.0

    @abstractmethod
    async def fetch_gst_data(self, gstin: str) -> GstData:
        """Fetch identity + compliance signals for a GSTIN.

        Raises GstProviderError on failure.
        """
        raise NotImplementedError
