"""
Abstract base for feed-specific market adapters.
"""

from abc import ABC, abstractmethod
from backend.markets.models import NormalizedMarket


class BaseMarketAdapter(ABC):
    """
    Parse a single feed event (raw dict from feed JSON) and return a list of normalized markets.
    """

    @abstractmethod
    def extract_markets(self, feed_event: dict, feed_provider: str) -> list[NormalizedMarket]:
        """
        Extract all markets from one feed event.
        :param feed_event: One event object from the feed (e.g. item from results[]).
        :param feed_provider: Feed code (e.g. "bwin", "bet365") for NormalizedMarket.feed_provider.
        :return: List of NormalizedMarket; may be empty if event has no markets or feed format is unknown.
        """
        pass
