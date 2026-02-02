"""
Deal sources module - pluggable sources for deal ingestion.
Currently contains stubs for future implementation.
"""
from .base import DealSource
from .sec_edgar import SECEdgarSource
from .press_releases import PressReleaseSource

__all__ = ["DealSource", "SECEdgarSource", "PressReleaseSource"]
