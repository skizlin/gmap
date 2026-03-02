"""
Bet365 market adapter.

Unified/BetsAPI-style bet365 events (e.g. designs/feed_json_examples/bet365.json)
typically do not include a Markets array per event. When the feed provides
market-level data (e.g. from a separate odds/markets endpoint), extend this
adapter to parse it and return NormalizedMarket list.
"""

from backend.markets.models import NormalizedMarket
from backend.markets.integration.base import BaseMarketAdapter


class Bet365MarketAdapter(BaseMarketAdapter):
    def extract_markets(self, feed_event: dict, feed_provider: str) -> list[NormalizedMarket]:
        # bet365 results[] in current JSON have no Markets array; return empty until we have market payload
        return []
