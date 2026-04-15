"""
Acceptance criteria — feeder auto-map to existing domain events (E-*)

AC-1  Given a feeder row whose sport/category/competition/teams resolve to domain entity ids (via
      entity_feed_mappings) and whose home/away P-* ids and kickoff match exactly one domain event,
      `_find_domain_event_for_auto_map` MUST return that domain event.

AC-2  If the domain event already has another valid_id from the same feed mapped (duplicate feed rows),
      the matcher MUST still return that domain event so we do not create a second E-*.

AC-3  Kickoff: if date is the same and both sides are naive `YYYY-MM-DD HH:MM(:SS)?`, a difference
      within the configured slack MUST still match (covers listing vs domain clock skew).

AC-4  Kickoff: if the difference exceeds the slack, the matcher MUST NOT treat the rows as the same fixture.

AC-5  `_explain_auto_map_feed_vs_domain_row` MUST report which dimension fails (sport, category,
      competition, time, team ids) for debugging.

AC-6  If more than one domain event matches, the implementation MUST pick the one with the **lowest
      numeric** E-* suffix (E-97 before E-200), not lexicographic string order.

Run (from repository root):
  pip install -r tests/requirements-unit.txt
  pytest tests/unit/test_feeder_auto_map.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Repository root (…/tests/unit/file.py -> parents[2])
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import backend.main as main


def _minimal_feeds() -> list[dict]:
    return [{"domain_id": 4, "code": "1xbet", "name": "1xBet"}]


def _minimal_domain_entities() -> dict:
    return {
        "sports": [{"domain_id": "S-1", "name": "Football"}],
        "categories": [{"domain_id": "G-23", "name": "Germany", "sport_id": "S-1"}],
        "competitions": [
            {
                "domain_id": "C-30",
                "name": "Bundesliga",
                "sport_id": "S-1",
                "category_id": "G-23",
            }
        ],
        "teams": [
            {"domain_id": "P-135", "name": "1. FC Cologne", "sport_id": "S-1"},
            {"domain_id": "P-5", "name": "Bayer Leverkusen", "sport_id": "S-1"},
        ],
    }


def _mappings_1xbet_bundesliga() -> list[dict]:
    """Minimal entity_feed_mappings rows (in-memory shape used by main)."""
    return [
        {"entity_type": "sports", "domain_id": "S-1", "feed_provider_id": 4, "feed_id": "1", "domain_name": "Football"},
        {
            "entity_type": "competitions",
            "domain_id": "C-30",
            "feed_provider_id": 4,
            "feed_id": "COMP:96463",
            "domain_name": "Bundesliga",
        },
        {"entity_type": "teams", "domain_id": "P-135", "feed_provider_id": 4, "feed_id": "1001", "domain_name": "1. FC Cologne"},
        {"entity_type": "teams", "domain_id": "P-5", "feed_provider_id": 4, "feed_id": "1002", "domain_name": "Bayer Leverkusen"},
    ]


def _feeder_row_koln_leverkusen(**overrides) -> dict:
    row = {
        "feed_provider": "1xbet",
        "valid_id": "712007124",
        "sport": "Soccer",
        "sport_id": "1",
        "category": "COMP:96463",
        "raw_league_name": "Germany. Bundesliga",
        "raw_home_id": "1001",
        "raw_away_id": "1002",
        "raw_home_name": "1. Koln",
        "raw_away_name": "Bayer 04 Leverkusen",
        "start_time": "2026-04-25 13:30:00",
        "mapping_status": "UNMAPPED",
    }
    row.update(overrides)
    return row


def _domain_e97(**time_kw) -> dict:
    t = time_kw.get("start_time", "2026-04-25 13:30:00")
    return {
        "id": "E-97",
        "sport": "Football",
        "category": "Germany",
        "competition": "Bundesliga",
        "home": "1. FC Cologne",
        "home_id": "P-135",
        "away": "Bayer Leverkusen",
        "away_id": "P-5",
        "start_time": t,
        "sport_id": "S-1",
        "category_id": "G-23",
        "competition_id": "C-30",
    }


@pytest.fixture
def isolated_matcher(monkeypatch: pytest.MonkeyPatch):
    """Replace globals on backend.main so matcher tests do not depend on local CSV."""
    monkeypatch.setattr(main, "FEEDS", _minimal_feeds())
    monkeypatch.setattr(main, "DOMAIN_ENTITIES", _minimal_domain_entities())
    monkeypatch.setattr(main, "ENTITY_FEED_MAPPINGS", _mappings_1xbet_bundesliga())
    monkeypatch.setattr(main, "DOMAIN_EVENTS", [_domain_e97()])
    yield


def test_ac1_find_returns_e97_when_ids_and_time_align(isolated_matcher):
    feeder = _feeder_row_koln_leverkusen()
    got = main._find_domain_event_for_auto_map(feeder, 4, "1xbet")
    assert got is not None
    assert got["id"] == "E-97"


def test_ac2_domain_still_candidate_if_same_feed_has_other_mapping(monkeypatch, isolated_matcher):
    """Regression: do not exclude domain row only because this feed already mapped another valid_id to it."""

    def fake_load():
        return [
            {"domain_event_id": "E-97", "feed_provider": "1xbet", "feed_valid_id": "999999999"},
        ]

    monkeypatch.setattr(main, "_load_event_mappings", fake_load)
    feeder = _feeder_row_koln_leverkusen(valid_id="712007124")
    got = main._find_domain_event_for_auto_map(feeder, 4, "1xbet")
    assert got is not None and got["id"] == "E-97"


def test_ac3_same_date_within_slack_matches(isolated_matcher, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(main, "DOMAIN_EVENTS", [_domain_e97(start_time="2026-04-25 14:00:00")])
    feeder = _feeder_row_koln_leverkusen(start_time="2026-04-25 13:30:00")
    assert main._event_start_times_match_auto_map(feeder["start_time"], "2026-04-25 14:00:00")
    got = main._find_domain_event_for_auto_map(feeder, 4, "1xbet")
    assert got is not None and got["id"] == "E-97"


def test_ac4_beyond_slack_no_match(monkeypatch):
    monkeypatch.setattr(main, "FEEDS", _minimal_feeds())
    monkeypatch.setattr(main, "DOMAIN_ENTITIES", _minimal_domain_entities())
    monkeypatch.setattr(main, "ENTITY_FEED_MAPPINGS", _mappings_1xbet_bundesliga())
    monkeypatch.setattr(main, "DOMAIN_EVENTS", [_domain_e97(start_time="2026-04-25 08:00:00")])
    feeder = _feeder_row_koln_leverkusen(start_time="2026-04-25 13:30:00")
    got = main._find_domain_event_for_auto_map(feeder, 4, "1xbet")
    assert got is None


def test_ac5_explain_flags_wrong_team_pair(isolated_matcher):
    feeder = _feeder_row_koln_leverkusen(raw_home_id="1002", raw_away_id="1001")  # swapped feed ids
    dom = main.DOMAIN_EVENTS[0]
    ex = main._explain_auto_map_feed_vs_domain_row(feeder, 4, dom, swapped=False)
    assert ex["sport_ok"] is True
    assert ex["teams_resolved"] is True
    assert ex["team_pair_ok"] is False
    assert ex["match"] is False
    ex_sw = main._explain_auto_map_feed_vs_domain_row(feeder, 4, dom, swapped=True)
    assert ex_sw["team_pair_ok"] is True
    assert ex_sw["match"] is True


def test_plain_numeric_comp_mapping_matches_comp_category_cell(monkeypatch: pytest.MonkeyPatch):
    """Entities UI often saves Bet365 league id as 10041282; feed rows use COMP:10041282 on the category cell."""
    maps = []
    for m in _mappings_1xbet_bundesliga():
        row = dict(m)
        if row.get("entity_type") == "competitions":
            row["feed_id"] = "96463"
        maps.append(row)
    monkeypatch.setattr(main, "FEEDS", _minimal_feeds())
    monkeypatch.setattr(main, "DOMAIN_ENTITIES", _minimal_domain_entities())
    monkeypatch.setattr(main, "ENTITY_FEED_MAPPINGS", maps)
    monkeypatch.setattr(main, "DOMAIN_EVENTS", [_domain_e97()])
    row = _feeder_row_koln_leverkusen()
    assert main._resolve_entity("competitions", "COMP:96463", 4, domain_sport_id="S-1") is not None
    assert main._feeder_event_feed_category_mapped(row, 4) is True
    assert main._feeder_event_feed_competition_mapped(row, 4) is True


def test_lowest_e_id_when_two_domain_rows_match(isolated_matcher, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        main,
        "DOMAIN_EVENTS",
        [
            _domain_e97(),
            {
                "id": "E-200",
                "sport": "Football",
                "category": "Germany",
                "competition": "Bundesliga",
                "home": "1. FC Cologne",
                "home_id": "P-135",
                "away": "Bayer Leverkusen",
                "away_id": "P-5",
                "start_time": "2026-04-25 13:30:00",
                "sport_id": "S-1",
                "category_id": "G-23",
                "competition_id": "C-30",
            },
        ],
    )
    feeder = _feeder_row_koln_leverkusen()
    got = main._find_domain_event_for_auto_map(feeder, 4, "1xbet")
    assert got["id"] == "E-97"
