"""
Sbobet market adapter.

Sbobet feed format may include markets per event or in a separate structure.
Extend this adapter when feed JSON/API provides market data.
"""

from backend.markets.models import NormalizedMarket
from backend.markets.integration.base import BaseMarketAdapter


class SbobetMarketAdapter(BaseMarketAdapter):
    def extract_markets(self, feed_event: dict, feed_provider: str) -> list[NormalizedMarket]:
        # Stub: no Markets in current sbobet event shape; return empty until we have market payload
        return []
