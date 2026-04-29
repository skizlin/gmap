"""
Log-base-2 margin mapping from fair (true) decimal odds to displayed book odds.

The trader-facing Excel expression is::

    (margin_pct/100/2) ^ LOG(true_odds, 2)

where ``LOG(x, 2)`` is the base-2 logarithm of ``x``. For typical PM%% (e.g. 108)
that factor is below 1 while ``true_odds`` is above 1, so the raw power is a
*shrink* factor on the probability scale. Here we convert it to **decimal odds**
(the quantity shown in Brand Overview) as::

    margined_odds = 1 / factor

so prices stay above 1 and shorten when margin is applied. If your sheet uses
the raw power directly as something other than odds, swap the return path in
``true_odds_to_margined_odds_log2``.
"""
from __future__ import annotations

import math


def log2_excel_factor(margin_pct: float, true_odds: float) -> float | None:
    """Return ``(margin_pct/100/2) ** log2(true_odds)`` when defined."""
    if true_odds <= 0 or margin_pct <= 0:
        return None
    if true_odds == 1.0:
        return 1.0
    base = (float(margin_pct) / 100.0) / 2.0
    if base <= 0:
        return None
    try:
        return float(base ** math.log(float(true_odds), 2.0))
    except (ValueError, ZeroDivisionError, OverflowError):
        return None


def true_odds_to_margined_odds_log2(
    true_odds: float,
    margin_pct: float,
    *,
    n_outcomes: int | None = None,
) -> float | None:
    """
    Convert fair decimal ``true_odds`` to a margined decimal price using PM%%.

    ``n_outcomes`` is reserved for future dynamic tweaks (per-market selection
    count); currently ignored.
    """
    _ = n_outcomes  # reserved for DYN tuning vs number of selections
    factor = log2_excel_factor(margin_pct, true_odds)
    if factor is None or factor <= 0:
        return None
    # Book-style decimal odds from shrink factor on implied side
    try:
        out = 1.0 / factor
    except ZeroDivisionError:
        return None
    if out < 1.0:
        return None
    return round(out, 2)


