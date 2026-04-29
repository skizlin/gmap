"""Volleyball Correct Set Score: aggregate feed odds → true odds / probs (averaged across feeds)."""

from __future__ import annotations

import re
from typing import Any

from backend.internal_pricing.transforms.log_function import true_odds_and_probs_from_decimal_odds

_CORRECT_SET_SCORE_PHRASE = "correct set score"


def is_volleyball_sport(sport_name: str | None) -> bool:
    return (sport_name or "").strip().lower() == "volleyball"


def is_correct_set_score_market(market_name: str | None) -> bool:
    return _CORRECT_SET_SCORE_PHRASE in (market_name or "").strip().lower()


def _normalize_line(val: Any) -> str:
    s = "" if val is None else str(val).strip()
    s = re.sub(r"\s*★\s*$", "", s).strip()
    return s


def _parse_price(cell: Any) -> float | None:
    if cell is None:
        return None
    s = str(cell).strip().replace(",", ".")
    if not s or s == "—":
        return None
    try:
        x = float(s)
        return x if x > 0 else None
    except (TypeError, ValueError):
        return None


def _outcome_name_key(name: Any) -> str:
    return ("" if name is None else str(name)).strip()


def _normalize_score_label(s: str) -> str:
    """Canonical key for set-score outcomes so feed labels match domain (3-0 vs 3:0, spacing)."""
    t = (s or "").strip().lower()
    t = re.sub(r"\s+", "", t)
    t = t.replace("\u2013", "-").replace("\u2014", "-")
    t = t.replace("-", ":")
    return t


def _pick_rows_per_feed(
    feed_rows: list[dict],
    line: str | None,
) -> list[dict]:
    """One row per feed: match line if provided, else prefer main line then first usable row."""
    line_norm = _normalize_line(line) if line else ""
    by_feed: dict[str, list[dict]] = {}
    for r in feed_rows:
        fn = (r.get("feed_name") or "").strip() or "—"
        by_feed.setdefault(fn, []).append(r)

    picked: list[dict] = []
    for _fname, rows in by_feed.items():
        candidates = rows
        if line_norm:
            matched = [x for x in candidates if _normalize_line(x.get("line")) == line_norm]
            if matched:
                candidates = matched
        main = [x for x in candidates if x.get("is_main_line")]
        use = main[0] if main else None
        if use is None:
            for x in candidates:
                outs = x.get("outcomes") or []
                if len(outs) >= 2 and all(_parse_price(o.get("price")) for o in outs):
                    use = x
                    break
        if use is None and candidates:
            use = candidates[0]
        if use is not None:
            picked.append(use)
    return picked


def _row_norm_to_prices(row: dict) -> dict[str, float]:
    """Map normalized score label -> decimal price (last wins if duplicates)."""
    out: dict[str, float] = {}
    for o in row.get("outcomes") or []:
        k = _outcome_name_key(o.get("name"))
        p = _parse_price(o.get("price"))
        if k and p is not None:
            out[_normalize_score_label(k)] = p
    return out


def compute_correct_set_score_internal(
    feed_rows: list[dict],
    line: str | None,
    column_order: list[str],
    accuracy: int = 10,
) -> dict[str, Any]:
    """
    For each feed with a full price vector, compute true odds & probs (de-vig).
    Average by outcome name across feeds. ``column_order`` is domain outcome labels (order of columns).
    """
    per_feed: list[dict[str, Any]] = []
    picked = _pick_rows_per_feed(feed_rows, line)

    # name -> list of (true_odd, true_prob)
    accum: dict[str, list[tuple[float, float]]] = {}

    required = [(k or "").strip() for k in column_order if (k or "").strip()]
    if not required:
        first_map: dict[str, float] = {}
        for row in picked:
            first_map = _row_norm_to_prices(row)
            if len(first_map) >= 2:
                break
        required = list(first_map.keys())

    for row in picked:
        n2p = _row_norm_to_prices(row)
        odds: list[float] = []
        keys: list[str] = []
        for k in required:
            nk = _normalize_score_label(k)
            if nk not in n2p:
                odds = []
                keys = []
                break
            keys.append(k)
            odds.append(n2p[nk])
        if len(keys) != len(required) or len(odds) < 2:
            continue
        tp = true_odds_and_probs_from_decimal_odds(odds, accuracy=accuracy)
        if not tp:
            continue
        true_odds, true_probs = tp
        per_feed.append(
            {
                "feed_name": row.get("feed_name"),
                "line": row.get("line"),
                "outcomes": [{"name": keys[i], "decimal_odds": odds[i], "true_odds": true_odds[i], "true_prob": true_probs[i]} for i in range(len(keys))],
            }
        )
        for i, k in enumerate(keys):
            accum.setdefault(k, []).append((true_odds[i], true_probs[i]))

    averaged: list[dict[str, Any]] = []
    for label in required:
        if label not in accum:
            continue
        pairs = accum[label]
        n = len(pairs)
        if n == 0:
            continue
        avg_o = round(sum(p[0] for p in pairs) / n, 4)
        avg_p = round(sum(p[1] for p in pairs) / n, 6)
        averaged.append({"name": label, "true_odds": avg_o, "true_prob": avg_p})

    return {
        "per_feed": per_feed,
        "averaged_outcomes": averaged,
        "feeds_used": len(per_feed),
    }
