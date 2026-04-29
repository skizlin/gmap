"""
IMLog (internal model logarithmic) synthetic feed: Bwin-shaped event JSON under
``feed_event_details/imlog/{feed_valid_id}.json``.

Convention for Configuration → Event mapping (recommended; Feed Odds also picks up IMLog when
``feed_event_details/imlog/{domain_event_id}.json`` exists even if the CSV row is missing):
  - Map domain event to feed ``imlog`` with ``feed_valid_id`` equal to the domain event id (e.g. ``E-12``).
  - Map domain markets (Correct Set Score, Match Winner, Set Handicap, …) to these feed market ids:
      ``IMLOG_CORRECT_SET_SCORE``, ``IMLOG_MATCH_WINNER``, ``IMLOG_SET_HANDICAP_M15``
  - Add a ``sport_feed_mappings`` row for IMLog + your domain sport: ``feed_id`` is the feed sport id written as
    ``SportId`` on the synthetic JSON. Use any id you like; Configuration resolves IMLog markets from that mapping
    (same mechanism as Bet365/Bwin/1xbet — no need to match another feed).

After mapping, Feed Odds on Event Details reads this file like any other feed (Bwin parser).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from backend.internal_pricing.sports.volleyball.correct_set_score import (
    compute_correct_set_score_internal,
    is_volleyball_sport,
)
from backend.internal_pricing.transforms.log_function import true_odds_and_probs_from_decimal_odds

# Feed market ids (map domain markets to these in market_type_mappings.csv)
IMLOG_MARKET_CORRECT_SET_SCORE = "IMLOG_CORRECT_SET_SCORE"
IMLOG_MARKET_MATCH_WINNER = "IMLOG_MATCH_WINNER"
IMLOG_MARKET_SET_HANDICAP_M15 = "IMLOG_SET_HANDICAP_M15"


def imlog_markets_for_configuration_mapper() -> list[dict]:
    """
    Stable market list for Configuration → Markets when cached ``feed_event_details/imlog/*.json``
    does not match ``sport_feed_mappings`` ``feed_id`` (e.g. legacy files used ``SportId`` 18 fallback).
    IDs must match ``templateId`` on written JSON.
    """
    return [
        {"id": IMLOG_MARKET_CORRECT_SET_SCORE, "name": "Correct Set Score (IMLog)", "is_prematch": True, "line": None},
        {"id": IMLOG_MARKET_MATCH_WINNER, "name": "Match Winner (IMLog)", "is_prematch": True, "line": None},
        {"id": IMLOG_MARKET_SET_HANDICAP_M15, "name": "Set Handicap -1.5 (IMLog)", "is_prematch": True, "line": None},
    ]


def _decimal_odds_two_places(x: Any) -> float:
    try:
        return round(float(x), 2)
    except (TypeError, ValueError):
        return 1.0


def _bwin_result(name: str, odds: float) -> dict[str, Any]:
    return {
        "name": {"value": name},
        "odds": _decimal_odds_two_places(odds),
        "visibility": "Visible",
    }


def _bwin_market(template_id: str, display_name: str, results: list[dict[str, Any]], attr: str = "") -> dict[str, Any]:
    m: dict[str, Any] = {
        "templateId": template_id,
        "name": {"value": display_name},
        "category": "Other",
        "results": results,
        "isMain": True,
    }
    if attr:
        m["attr"] = attr
    return m


def _find_volleyball_correct_set_score_market(
    markets: list[dict],
    sport_id: Any,
    entity_ids_equal_fn: Callable[[Any, Any], bool],
) -> dict | None:
    for m in markets or []:
        if not entity_ids_equal_fn(m.get("sport_id"), sport_id):
            continue
        tpl = (m.get("template") or "").strip().upper()
        nm = (m.get("name") or "").strip().lower()
        if tpl == "CORRECT_SCORE" or "correct set score" in nm:
            return m
    return None


def _two_way_odds_from_probs(p_a: float, p_b: float) -> tuple[float, float]:
    """Fair decimal odds (no extra margin) from two probabilities that sum to ~1."""
    if p_a <= 0 or p_b <= 0:
        return 2.0, 2.0
    o1, o2 = 1.0 / p_a, 1.0 / p_b
    tp = true_odds_and_probs_from_decimal_odds([o1, o2], accuracy=8)
    if tp:
        return round(float(tp[0][0]), 2), round(float(tp[0][1]), 2)
    return round(o1, 2), round(o2, 2)


def build_imlog_event_payload(
    *,
    domain_event_id: str,
    home_name: str,
    away_name: str,
    declared_feed_sport_id: int | str | None,
    correct_score_labels: list[str],
    averaged_css: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build ``{ success, results: [ bwin-shaped event ] }`` for one domain event."""
    by_l = {(r.get("name") or "").strip(): float(r.get("true_prob") or 0) for r in averaged_css}
    n = len(correct_score_labels)
    if n < 2:
        n = 6
        correct_score_labels = ["3:0", "3:1", "3:2", "2:3", "1:3", "0:3"]
        by_l = {k: 1.0 / n for k in correct_score_labels}

    def p(label: str) -> float:
        return float(by_l.get(label, 0.0))

    p_home = p("3:0") + p("3:1") + p("3:2")
    p_away = p("2:3") + p("1:3") + p("0:3")
    if p_home <= 0 and p_away <= 0:
        p_home = p_away = 0.5
    s = p_home + p_away
    if s > 0:
        p_home, p_away = p_home / s, p_away / s
    mw_h, mw_a = _two_way_odds_from_probs(p_home, p_away)

    p_h_m15 = p("3:0") + p("3:1")
    p_a_p15 = 1.0 - p_h_m15
    if p_h_m15 <= 0 or p_a_p15 <= 0:
        p_h_m15, p_a_p15 = 0.5, 0.5
    sh_h, sh_a = _two_way_odds_from_probs(p_h_m15, p_a_p15)

    css_results = []
    for lbl in correct_score_labels:
        row_avg = next((r for r in averaged_css if (r.get("name") or "").strip() == lbl), None)
        if row_avg is not None and row_avg.get("true_odds") is not None:
            try:
                od = float(row_avg["true_odds"])
            except (TypeError, ValueError):
                pr = p(lbl)
                od = round(1.0 / pr, 2) if pr > 0 else 50.0
        else:
            pr = p(lbl)
            od = round(1.0 / pr, 2) if pr > 0 else 50.0
        css_results.append(_bwin_result(lbl, od))

    markets = [
        _bwin_market(IMLOG_MARKET_CORRECT_SET_SCORE, "Correct Set Score (IMLog)", css_results),
        _bwin_market(
            IMLOG_MARKET_MATCH_WINNER,
            "Match Winner (IMLog)",
            [_bwin_result(home_name or "Home", mw_h), _bwin_result(away_name or "Away", mw_a)],
        ),
        _bwin_market(
            IMLOG_MARKET_SET_HANDICAP_M15,
            "Set Handicap -1.5 (IMLog)",
            [
                _bwin_result(f"{home_name or 'Home'} -1.5", sh_h),
                _bwin_result(f"{away_name or 'Away'} +1.5", sh_a),
            ],
            attr="-1.5",
        ),
    ]

    ev_block: dict[str, Any] = {
        "Id": str(domain_event_id).strip(),
        "SportId": 18 if declared_feed_sport_id is None else declared_feed_sport_id,
        "SportName": "Volleyball",
        "HomeTeam": home_name or "",
        "AwayTeam": away_name or "",
        "Markets": markets,
    }
    return {"success": 1, "results": [ev_block]}


def sync_imlog_event_json(
    *,
    domain_event_id: str,
    domain_event: dict | None,
    markets_bucket: list[dict],
    get_feed_odds_fn: Callable[..., list[dict]],
    get_outcome_labels_fn: Callable[..., tuple[list[str], str]],
    entity_ids_equal_fn: Callable[[Any, Any], bool],
    sport_id: Any,
    out_path: Path,
    declared_feed_sport_id: Any | None = None,
) -> bool:
    """
    Build and write IMLog Bwin-shaped JSON for ``domain_event_id``.
    ``get_feed_odds_fn`` must exclude imlog (e.g. wrap _get_feed_odds_for_event_market with exclude_feed_codes).
    Returns True if file was written.
    """
    eid = str(domain_event_id).strip()
    if not domain_event or not is_volleyball_sport(domain_event.get("sport")):
        return False
    css_mkt = _find_volleyball_correct_set_score_market(markets_bucket, sport_id, entity_ids_equal_fn)
    if not css_mkt:
        return False
    css_mid = css_mkt.get("domain_id")
    rows = get_feed_odds_fn(eid, css_mid, None, True)
    labels, _ = get_outcome_labels_fn(css_mkt, sport_id)
    comp = compute_correct_set_score_internal(rows, None, labels)
    averaged = comp.get("averaged_outcomes") or []
    if not averaged:
        labels = labels or ["3:0", "3:1", "3:2", "2:3", "1:3", "0:3"]
        averaged = [{"name": lbl, "true_prob": 1.0 / len(labels), "true_odds": float(len(labels))} for lbl in labels]

    sid_payload: Any | None = declared_feed_sport_id
    if sid_payload is None and sport_id is not None:
        try:
            sid_payload = int(sport_id)
        except (TypeError, ValueError):
            sid_payload = None

    payload = build_imlog_event_payload(
        domain_event_id=eid,
        home_name=(domain_event.get("home") or "").strip(),
        away_name=(domain_event.get("away") or "").strip(),
        declared_feed_sport_id=sid_payload,
        correct_score_labels=labels,
        averaged_css=averaged,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return True


def imlog_event_file_path(feed_details_dir: Path, feed_valid_id: str) -> Path:
    return feed_details_dir / "imlog" / f"{str(feed_valid_id).strip()}.json"
