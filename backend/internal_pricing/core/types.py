"""Shared types for pricing inputs and outputs (expand per your spec)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class OutcomeKey:
    """Stable identifier for a priced outcome within a market."""

    key: str


@dataclass(frozen=True)
class MarketKey:
    """Stable identifier for a market (e.g. match winner, set handicap)."""

    key: str
