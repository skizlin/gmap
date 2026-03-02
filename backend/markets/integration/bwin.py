"""
Bwin market adapter: parse Markets and optionMarkets from bwin feed events.
"""

from backend.markets.models import NormalizedMarket
from backend.markets.integration.base import BaseMarketAdapter


class BwinMarketAdapter(BaseMarketAdapter):
    """
    Bwin events have "Markets" (list of market objects) and optionally "optionMarkets".
    Each market has name.value, id, and isMain (or isMainbook).
    """

    def extract_markets(self, feed_event: dict, feed_provider: str) -> list[NormalizedMarket]:
        out: list[NormalizedMarket] = []
        feed_id = str(feed_event.get("Id", ""))

        for m in feed_event.get("Markets", []):
            nm = self._one_market(m, feed_provider, feed_id)
            if nm:
                out.append(nm)

        # optionMarkets: often outright/antepost markets with different structure
        for m in feed_event.get("optionMarkets", []):
            nm = self._one_option_market(m, feed_provider, feed_id)
            if nm:
                out.append(nm)

        return out

    def _one_market(self, m: dict, feed_provider: str, event_id: str) -> NormalizedMarket | None:
        name_obj = m.get("name") or {}
        name = name_obj.get("value") if isinstance(name_obj, dict) else str(name_obj or "")
        if not name:
            return None
        mid = m.get("id") or m.get("marketGroupItemId") or ""
        is_main = m.get("isMain", m.get("IsMainbook", False))
        return NormalizedMarket(
            feed_provider=feed_provider,
            feed_market_id=str(mid) if mid else f"event:{event_id}:{name[:32]}",
            name=name.strip(),
            code=None,
            is_main=bool(is_main),
            raw=m,
        )

    def _one_option_market(self, m: dict, feed_provider: str, event_id: str) -> NormalizedMarket | None:
        # optionMarkets may have marketHelpPath or similar for name
        name = (m.get("marketHelpPath") or "").split("/")[-1].strip()
        if not name and isinstance(m.get("name"), dict):
            name = (m.get("name") or {}).get("value") or ""
        if not name:
            name = m.get("name") if isinstance(m.get("name"), str) else "Outright market"
        name_str = (name.strip() if isinstance(name, str) else str(name)) or "Outright market"
        mid = m.get("marketGroupItemId") or m.get("id") or ""
        return NormalizedMarket(
            feed_provider=feed_provider,
            feed_market_id=str(mid) if mid else f"opt:{event_id}:{name_str[:24]}",
            name=name_str,
            code=None,
            is_main=False,
            raw=m,
        )
