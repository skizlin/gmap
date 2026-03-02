"""
Process markets from feed events: run per-feed adapters and return normalized list.
Persistence (markets.csv, entity_feed_mappings) stays in main.py / app layer.
"""

from backend.markets.models import NormalizedMarket
from backend.markets.config import SUPPORTED_MARKET_FEEDS
from backend.markets.integration import ADAPTERS


def get_adapter(feed_provider: str):
    """Return the market adapter for the given feed code, or None if not supported."""
    return ADAPTERS.get((feed_provider or "").strip().lower())


def extract_markets_from_feed_event(feed_event: dict, feed_provider: str) -> list[NormalizedMarket]:
    """
    Extract all markets from a single feed event using the appropriate adapter.
    :param feed_event: One event dict from the feed (e.g. item from results[]).
    :param feed_provider: Feed code (e.g. "bwin", "bet365").
    :return: List of NormalizedMarket; empty if feed has no adapter or no markets.
    """
    adapter = get_adapter(feed_provider)
    if not adapter:
        return []
    return adapter.extract_markets(feed_event, feed_provider.strip())


def process_markets_for_event(feed_event: dict, feed_provider: str) -> list[NormalizedMarket]:
    """
    Alias for extract_markets_from_feed_event. Use this when processing one event
    (e.g. when displaying event details or syncing markets for an event).
    """
    return extract_markets_from_feed_event(feed_event, feed_provider)
