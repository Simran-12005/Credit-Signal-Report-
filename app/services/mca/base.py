"""The swappable MCA + legal data provider interface (Phase 3).

Every concrete provider (mock, MCA21/Signzy/Probe, NJDG/IBBI scrapers, ...) implements
`fetch_mca_data` and returns the same normalized shape, so the rest of the app never
depends on a specific vendor. Swap providers via the MCA_PROVIDER setting.

Four signal groups, all vendor-independent:
  company    incorporation, age, status (active / strike-off / under liquidation), capital
  directors  count + roster (name, DIN, designation, appointment date), disqualifications
  charges    secured loans registered against the company (open / satisfied, amounts)
  legal      insolvency (IBBI) + recovery (NJDG) cases — applies to ANY entity, not just companies
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class McaData:
    """Normalized MCA + legal signals for one entity, vendor-independent."""

    # company: registered_with_mca, cin, company_name, entity_class, incorporation_date,
    #          age_years, status, roc, authorized_capital, paid_up_capital
    company: dict[str, Any] = field(default_factory=dict)
    # directors: count, directors[], has_disqualified_director
    directors: dict[str, Any] = field(default_factory=dict)
    # charges: open_count, satisfied_count, total_open_amount, charges[]
    charges: dict[str, Any] = field(default_factory=dict)
    # legal: has_active_insolvency, insolvency_cases[], recovery_case_count,
    #        recovery_cases[], total_recovery_amount
    legal: dict[str, Any] = field(default_factory=dict)


class McaProviderError(Exception):
    """Raised when a provider cannot return data (network, auth, not found)."""


class McaProvider(ABC):
    """Interface for an MCA + legal data source."""

    name: str = "base"
    # Approximate cost charged per live call (currency-agnostic units). Used for the
    # cost log; cache hits cost nothing. Override per provider.
    cost_per_call: float = 0.0

    @abstractmethod
    async def fetch_mca_data(self, gstin: str, legal_name: str | None = None) -> McaData:
        """Fetch company / directors / charges / legal signals for a GSTIN.

        `legal_name` (from the GST identity) helps providers that resolve a company by
        name. Raises McaProviderError on failure.
        """
        raise NotImplementedError
