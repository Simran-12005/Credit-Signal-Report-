"""Application settings, loaded from the environment / .env file."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/credit_signal_report"

    # API
    port: int = 8120
    environment: str = "dev"

    # GSTIN validation
    validate_gstin_checksum: bool = True

    # How long a cached GST response stays fresh (GST data changes slowly).
    gst_cache_ttl_days: int = 30

    # GST data provider: "mock", "sandbox", or "perfios"
    gst_provider: str = "mock"

    # MCA + legal (companies / directors / charges / insolvency / recovery) provider.
    # "mock" (offline) or "attestr" (real company data via Attestr CorpX).
    mca_provider: str = "mock"
    # MCA/legal data also changes slowly, so cache responses for this many days.
    mca_cache_ttl_days: int = 30

    # Attestr CorpX (real MCA company data). Self-serve, free trial. Get an Auth Token
    # from dashboard.attestr.com -> Apps -> New App. Sent as `Authorization: Basic <token>`.
    attestr_base_url: str = "https://api.attestr.com/api/v2"
    attestr_auth_token: str = ""

    # Sandbox.co.in (Quicko) — self-serve, free to start. Sign up at sandbox.co.in to
    # get an API key + secret. Auth is a token exchange (valid 24h).
    sandbox_base_url: str = "https://api.sandbox.co.in"
    sandbox_api_key: str = ""
    sandbox_api_secret: str = ""
    sandbox_api_version: str = "1.0.0"
    # Financial year for the returns-tracking (compliance) call, e.g. "FY 2025-26".
    # Empty = auto-detect the current Indian FY (Apr–Mar).
    sandbox_financial_year: str = ""
    perfios_base_url: str = "https://sandbox.perfios.ai"
    perfios_api_key: str = ""
    # Auth header name the provider expects. Perfios/Karza commonly use "x-karza-key"
    # or "x-api-key" — confirm against your sandbox docs and set here.
    perfios_auth_header: str = "x-api-key"
    # Path to the GST search/verification endpoint (appended to perfios_base_url).
    perfios_gst_path: str = "/gst/v1/search"
    # Consent flag many Indian KYC/GST APIs require ("Y").
    perfios_consent: str = "Y"

    @property
    def is_dev(self) -> bool:
        return self.environment == "dev"


@lru_cache
def get_settings() -> Settings:
    return Settings()
