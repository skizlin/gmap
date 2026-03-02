"""
Per-feed market adapters: parse feed-specific JSON into NormalizedMarket list.
"""

from backend.markets.integration.base import BaseMarketAdapter
from backend.markets.integration.bwin import BwinMarketAdapter
from backend.markets.integration.bet365 import Bet365MarketAdapter
from backend.markets.integration.sbobet import SbobetMarketAdapter

# Registry: feed_provider code -> adapter instance (used by processor)
ADAPTERS = {
    "bwin": BwinMarketAdapter(),
    "bet365": Bet365MarketAdapter(),
    "sbobet": SbobetMarketAdapter(),
}

__all__ = ["BaseMarketAdapter", "BwinMarketAdapter", "Bet365MarketAdapter", "SbobetMarketAdapter", "ADAPTERS"]
