"""
Legacy shim — forwards to the new backend provider manager.
This file exists for backwards compatibility only. Do not add logic here.
"""
from lmms.backend.providers.manager import ProviderManager

__all__ = ["ProviderManager"]
