"""
Logarithmic de-vig / margin adjustment (ported from docs/log_function.py, without console output).

``target_overround`` in ``solve_for_odds`` is the *excess* implied-probability mass over 1.0
(e.g. user enters 107.0 for 7%% margin → pass ``(107 - 100) / 100 == 0.07``).
"""
from __future__ import annotations

import math
from typing import Optional

_MAX_NEWTON_ITER = 500


def _remove_overround_fn(
    odds: list[float],
    overround: float,
    accuracy: int,
) -> tuple[Optional[float], list[float]]:
    """Newton–Raphson: find c so sum((1/o)**c) = 1 + overround; true_odds = o**c."""
    c = 1.0
    max_error = (10 ** (-accuracy)) / 2
    if any(o <= 0 for o in odds):
        return None, []

    current_error = 1000.0
    iteration = 0
    while current_error > max_error and iteration < _MAX_NEWTON_ITER:
        iteration += 1
        error_function = sum((1 / o) ** c for o in odds) - 1 - overround
        error_derivative = sum((1 / o) ** c * -math.log(o) for o in odds)
        if error_derivative == 0:
            break
        newton_step = -error_function / error_derivative
        c += newton_step
        current_error = abs(sum((1 / o) ** c for o in odds) - 1 - overround)

    true_odds = [round(o**c, 6) for o in odds]
    return c, true_odds


def solve_for_odds(
    odds: list[float],
    target_overround: float,
    remove_overround: float,
    accuracy: int,
) -> tuple[Optional[float], list[float], float, list[float]]:
    """
    Returns (remove_overround_result, true_odds, c_final, adjusted_odds).
    ``target_overround`` is the decimal margin on implied prob (e.g. 0.07 for 7%%).
    """
    remove_overround_result, true_odds = _remove_overround_fn(odds, remove_overround, accuracy)
    if remove_overround_result is None or not true_odds:
        return None, [], 1.0, []

    c = 1.0
    max_error = (10 ** (-accuracy)) / 2
    current_error = 1000.0
    iteration = 0
    while current_error > max_error and iteration < _MAX_NEWTON_ITER:
        iteration += 1
        error_function = sum((1 / o) ** c for o in true_odds) - 1 - target_overround
        error_derivative = sum((1 / o) ** c * -math.log(o) for o in true_odds)
        if error_derivative == 0:
            break
        newton_step = -error_function / error_derivative
        c += newton_step
        current_error = abs(sum((1 / o) ** c for o in true_odds) - 1 - target_overround)

    adjusted_odds = [round(o**c, 6) for o in true_odds]
    return remove_overround_result, true_odds, c, adjusted_odds


def true_odds_and_probs_from_decimal_odds(
    odds: list[float],
    accuracy: int = 10,
) -> tuple[list[float], list[float]] | None:
    """
    Remove overround only (fair book: sum of implied probs = 1).
    Returns (true_odds, true_probs) or None if invalid.
    """
    if not odds or any(o <= 0 for o in odds):
        return None
    _c, true_odds = _remove_overround_fn(odds, 0.0, accuracy)
    if not true_odds:
        return None
    true_probs = [round(1.0 / o, 6) for o in true_odds]
    return true_odds, true_probs


def implied_margin_pct(odds: list[float]) -> float | None:
    """Book margin as percentage (e.g. 107.2 for 7.2%% overround). None if invalid."""
    if not odds or any(o <= 0 for o in odds):
        return None
    return round(sum(1.0 / o for o in odds) * 100.0, 1)
