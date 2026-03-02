"""
Markets module: integrate and process markets from all feeds for use in the system.
"""

from backend.markets.models import NormalizedMarket, FeedMarketRaw
from backend.markets.config import SUPPORTED_MARKET_FEEDS
from backend.markets.processor import (
    process_markets_for_event,
    extract_markets_from_feed_event,
)

__all__ = [
    "NormalizedMarket",
    "FeedMarketRaw",
    "SUPPORTED_MARKET_FEEDS",
    "process_markets_for_event",
    "extract_markets_from_feed_event",
]
