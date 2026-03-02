"""
Domain and feed DTOs for markets.
"""

from dataclasses import dataclass, field
from typing import Optional, Any


@dataclass
class NormalizedMarket:
    """
    Common representation of a market after feed-specific parsing.
    Used across the system for display, mapping, and persistence.
    """
    feed_provider: str           # e.g. "bet365", "bwin", "sbobet"
    feed_market_id: str          # Native ID from the feed (string)
    name: str                    # Display name, e.g. "Match Winner", "Total goals"
    code: Optional[str] = None   # Optional domain-style code (e.g. "MATCH_WINNER")
    is_main: bool = False        # Main/premain market (e.g. bwin isMain, IsMainbook)
    raw: Optional[dict] = None  # Optional original feed payload for debugging


@dataclass
class FeedMarketRaw:
    """
    Raw market slice from a feed event (e.g. one item from bwin Markets array).
    Adapters can use this internally before converting to NormalizedMarket.
    """
    feed_provider: str
    data: dict[str, Any]  # Feed-specific structure
    event_context: Optional[dict] = None  # Parent event fields if needed (e.g. feed_event_id)
    is_main: bool = False
    name: Optional[str] = None  # Extracted name if already known
