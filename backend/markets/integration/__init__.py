"""
Per-feed market adapters: parse feed-specific JSON into NormalizedMarket list.
"""

from backend.markets.integration.base import BaseMarketAdapter
from backend.markets.integration.bwin import BwinMarketAdapter
from backend.markets.integration.bet365 import Bet365MarketAdapter

# Registry: feed_provider code -> adapter instance (used by processor)
ADAPTERS = {
    "bwin": BwinMarketAdapter(),
    "bwin_l2": BwinMarketAdapter(),
    "bet365": Bet365MarketAdapter(),
}

__all__ = ["BaseMarketAdapter", "BwinMarketAdapter", "Bet365MarketAdapter", "ADAPTERS"]
