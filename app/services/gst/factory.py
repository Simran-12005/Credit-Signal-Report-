"""Resolve the configured GST provider (GST_PROVIDER setting)."""

from functools import lru_cache

from app.config import get_settings
from app.services.gst.base import GstProvider, GstProviderError
from app.services.gst.mock_provider import MockGstProvider
from app.services.gst.perfios_provider import PerfiosGstProvider
from app.services.gst.sandbox_provider import SandboxGstProvider


@lru_cache
def get_gst_provider() -> GstProvider:
    name = get_settings().gst_provider.lower()
    if name == "mock":
        return MockGstProvider()
    if name == "sandbox":
        return SandboxGstProvider()
    if name == "perfios":
        return PerfiosGstProvider()
    raise GstProviderError(
        f"Unknown GST_PROVIDER '{name}' (expected 'mock', 'sandbox', or 'perfios')."
    )
