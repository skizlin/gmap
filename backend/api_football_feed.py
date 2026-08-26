"""
API-Football (api-sports.io) helpers.

Phase 1: fixtures → feeder events.
Phase 2: /odds/bets + /odds/bookmakers catalogs (feed-level market map; bookmakers are labels only).

Odds values under fixture (Phase 3+) stay nested by bookmaker; market mappings stay feed-scoped.
See docs/API_FOOTBALL_INTEGRATION.md.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FEED_CODE = "api_football"
# Single sport product for this API family (soccer / football).
DEFAULT_SPORT_ID = "1"
DEFAULT_SPORT_NAME = "Football"

# Catalog filenames under FEED_DATA_DIR (and designs samples).
BETS_CATALOG_FILENAME = "api_football_bets.json"
BOOKMAKERS_CATALOG_FILENAME = "api_football_bookmakers.json"


def is_raw_api_football_item(item: dict) -> bool:
    """True when the row still looks like a native API-Football fixtures response element."""
    if not isinstance(item, dict):
        return False
    return isinstance(item.get("fixture"), dict) and isinstance(item.get("teams"), dict)


def _parse_fixture_start(fixture: dict) -> str:
    """Normalize fixture date/timestamp to 'YYYY-MM-DD HH:MM:SS' display."""
    date_s = (fixture.get("date") or "").strip()
    if date_s:
        # ISO with offset, e.g. 2026-03-07T15:00:00+00:00
        try:
            dt = datetime.fromisoformat(date_s.replace("Z", "+00:00"))
            if dt.tzinfo is not None:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except (TypeError, ValueError):
            pass
        # Fallback: truncate common forms
        if "T" in date_s:
            return date_s.replace("T", " ")[:19]
        return date_s[:19]
    ts = fixture.get("timestamp")
    if ts is not None:
        try:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        except (TypeError, ValueError, OSError):
            pass
    return "—"


def normalize_api_football_item(item: dict) -> dict | None:
    """
    Map one API-Football /fixtures response element to the unified feeder event shape.
    If already normalized, return a shallow copy.
    """
    if not isinstance(item, dict):
        return None

    if (item.get("feed_provider") or "").strip().lower() == FEED_CODE and item.get("valid_id") and not is_raw_api_football_item(item):
        return dict(item)

    fixture = item.get("fixture") if isinstance(item.get("fixture"), dict) else {}
    league = item.get("league") if isinstance(item.get("league"), dict) else {}
    teams = item.get("teams") if isinstance(item.get("teams"), dict) else {}
    home = teams.get("home") if isinstance(teams.get("home"), dict) else {}
    away = teams.get("away") if isinstance(teams.get("away"), dict) else {}
    status = fixture.get("status") if isinstance(fixture.get("status"), dict) else {}

    fid = fixture.get("id")
    if fid is None or str(fid).strip() == "":
        return None
    valid_id = str(fid).strip()

    home_id = home.get("id")
    away_id = away.get("id")
    league_id = league.get("id")
    country = (league.get("country") or "").strip()

    return {
        "feed_provider": FEED_CODE,
        "valid_id": valid_id,
        "domain_id": None,
        "raw_home_name": (home.get("name") or "").strip(),
        "raw_away_name": (away.get("name") or "").strip(),
        "raw_home_id": str(home_id).strip() if home_id is not None and str(home_id).strip() else None,
        "raw_away_id": str(away_id).strip() if away_id is not None and str(away_id).strip() else None,
        "raw_league_name": (league.get("name") or "").strip() or None,
        "raw_league_id": str(league_id).strip() if league_id is not None and str(league_id).strip() else None,
        "category": country,
        "category_id": None,
        "start_time": _parse_fixture_start(fixture),
        "time_status": (status.get("short") or status.get("long") or "").strip(),
        "sport": DEFAULT_SPORT_NAME,
        "sport_id": DEFAULT_SPORT_ID,
        "betradar_id": None,
        "is_outright": False,
        "market_name": None,
        "is_mainbook": False,
        "updated_at": None,
        "mapping_status": "UNMAPPED",
        "status": "Open",
        "markets_count": 0,
        # API-Football extras (ignored by most UI; useful for Phase 2 odds)
        "api_football_league_season": league.get("season"),
        "api_football_league_round": (league.get("round") or "").strip() or None,
        "api_football_status_long": (status.get("long") or "").strip() or None,
    }


def normalize_api_football_events(raw_events: list) -> list[dict]:
    """Normalize a list of raw or stored events; drop invalid; dedupe by valid_id (last wins)."""
    by_id: dict[str, dict] = {}
    for item in raw_events or []:
        if not isinstance(item, dict):
            continue
        ev = normalize_api_football_item(item)
        if not ev:
            continue
        vid = str(ev.get("valid_id") or "").strip()
        if not vid:
            continue
        by_id[vid] = ev
    return list(by_id.values())


def _catalog_dir() -> Path | None:
    from backend import config

    d = getattr(config, "FEED_DATA_DIR", None)
    return Path(d) if d else None


def bets_catalog_path() -> Path | None:
    d = _catalog_dir()
    return (d / BETS_CATALOG_FILENAME) if d else None


def bookmakers_catalog_path() -> Path | None:
    d = _catalog_dir()
    return (d / BOOKMAKERS_CATALOG_FILENAME) if d else None


def normalize_odds_id_name_list(raw: list | dict | None) -> list[dict]:
    """
    Normalize /odds/bets or /odds/bookmakers response into [{id, name}, ...] sorted by id.
    Accepts a bare list or {response: [...]}.
    """
    items: list = []
    if isinstance(raw, dict):
        items = raw.get("response") or raw.get("results") or []
    elif isinstance(raw, list):
        items = raw
    out: list[dict] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        rid = item.get("id")
        if rid is None or str(rid).strip() == "":
            continue
        sid = str(rid).strip()
        if sid in seen:
            continue
        seen.add(sid)
        name = (item.get("name") or "").strip() or sid
        out.append({"id": sid, "name": name})
    def _sort_key(row: dict) -> tuple:
        try:
            return (0, int(row["id"]))
        except (TypeError, ValueError):
            return (1, str(row.get("id") or ""))
    out.sort(key=_sort_key)
    return out


def save_odds_catalog(kind: str, rows: list[dict]) -> Path | None:
    """kind is 'bets' or 'bookmakers'. Returns path written."""
    path = bets_catalog_path() if kind == "bets" else bookmakers_catalog_path()
    if path is None:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "feed_provider": FEED_CODE,
        "kind": kind,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(rows),
        "response": rows,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path


def load_odds_catalog(kind: str) -> list[dict]:
    """Load stored bets or bookmakers catalog (id/name rows). Falls back to designs sample."""
    primary = bets_catalog_path() if kind == "bets" else bookmakers_catalog_path()
    sample_name = (
        "api_football_odds_bets.json" if kind == "bets" else "api_football_odds_bookmakers.json"
    )
    candidates: list[Path] = []
    if primary:
        candidates.append(primary)
    candidates.append(
        Path(__file__).resolve().parent.parent / "designs" / "feed_json_examples" / sample_name
    )
    for path in candidates:
        if not path.exists():
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            rows = normalize_odds_id_name_list(data)
            if rows:
                return rows
        except (json.JSONDecodeError, OSError):
            continue
    return []


def bets_for_market_mapper(*, sport_name: str | None = None) -> list[dict]:
    """
    Catalog for Entities market mapper: feed_market_id = bet.id (shared by all bookmakers).
    Returns {id, name, is_prematch, sport_name}.
    """
    display = (sport_name or "").strip() or DEFAULT_SPORT_NAME
    return [
        {
            "id": row["id"],
            "name": row["name"],
            "is_prematch": True,
            "sport_name": display,
        }
        for row in load_odds_catalog("bets")
    ]


def _api_football_odds_payload_bookmakers(data: dict | list | None) -> list[dict]:
    """Return bookmakers[] from a cached /odds response (response[0] or top-level)."""
    if data is None:
        return []
    if isinstance(data, list):
        # list of response items or already bookmakers
        if data and isinstance(data[0], dict) and "bookmakers" in data[0]:
            books = data[0].get("bookmakers") or []
            return books if isinstance(books, list) else []
        if data and isinstance(data[0], dict) and "bets" in data[0]:
            return data  # already bookmakers list
        return []
    if not isinstance(data, dict):
        return []
    resp = data.get("response")
    if isinstance(resp, list) and resp:
        first = resp[0] if isinstance(resp[0], dict) else {}
        books = first.get("bookmakers") or []
        return books if isinstance(books, list) else []
    books = data.get("bookmakers")
    return books if isinstance(books, list) else []


def _parse_line_from_value_label(label: str) -> str | None:
    """Extract line from labels like 'Over 2.5', 'Under 2,5', 'Home -1.5', 'Away +0.5'."""
    import re

    s = (label or "").strip().replace(",", ".")
    if not s:
        return None
    m = re.search(r"([+-]?\d+(?:\.\d+)?)\s*$", s)
    if not m:
        return None
    return m.group(1)


def _normalize_outcome_label(value: str) -> str:
    """Map API-Football value labels toward Feed Odds headers (1 / X / 2 when possible)."""
    v = (value or "").strip()
    low = v.lower()
    if low in ("home", "1"):
        return "1"
    if low in ("draw", "x", "tie"):
        return "X"
    if low in ("away", "2"):
        return "2"
    return v


def extract_api_football_bookmaker_odds_rows(
    data: dict | list | None,
    feed_market_id: str,
    *,
    all_lines: bool = True,
    line: str | None = None,
    feed_provider_id: int | None = None,
) -> list[dict]:
    """
    From cached /odds JSON, emit one Feed Odds row per bookmaker for the mapped bet id.

    ``feed_name`` is the bookmaker name (Bet365, Pinnacle, …), not \"API-Football\".
    """
    bet_id = str(feed_market_id or "").strip()
    if not bet_id:
        return []
    line_want = (line or "").strip().replace(",", ".") if line else None
    rows: list[dict] = []
    for book in _api_football_odds_payload_bookmakers(data):
        if not isinstance(book, dict):
            continue
        book_id = book.get("id")
        book_name = (book.get("name") or "").strip() or (str(book_id) if book_id is not None else "Bookmaker")
        bets = book.get("bets") or []
        if not isinstance(bets, list):
            continue
        bet = next(
            (b for b in bets if isinstance(b, dict) and str(b.get("id") or "").strip() == bet_id),
            None,
        )
        if not bet:
            continue
        values = bet.get("values") or []
        if not isinstance(values, list) or not values:
            continue

        # Group by parsed line when labels carry a number (O/U, handicap).
        by_line: dict[str, list[dict]] = {}
        plain: list[dict] = []
        for val in values:
            if not isinstance(val, dict):
                continue
            label = (val.get("value") or "").strip()
            odd = val.get("odd")
            if odd is None or str(odd).strip() == "":
                continue
            outcome = {"name": _normalize_outcome_label(label), "price": str(odd).strip()}
            parsed = _parse_line_from_value_label(label)
            # Only treat as multi-line when Over/Under/Home/Away + number pattern
            low = label.lower()
            is_line_mkt = parsed is not None and (
                low.startswith("over")
                or low.startswith("under")
                or low.startswith("home")
                or low.startswith("away")
            )
            if is_line_mkt and parsed is not None:
                by_line.setdefault(parsed, []).append(outcome)
            else:
                plain.append(outcome)

        def _append_row(outcomes: list[dict], row_line: str, *, is_main: bool = False) -> None:
            rows.append({
                "feed_provider_id": feed_provider_id,
                "feed_name": book_name,
                "bookmaker_id": str(book_id).strip() if book_id is not None else "",
                "feed_market_id": bet_id,
                "outcomes": outcomes,
                "line": row_line or "—",
                "is_main_line": is_main,
            })

        if by_line and (all_lines or line_want):
            # Sort lines numerically when possible
            def _line_key(s: str) -> tuple:
                try:
                    return (0, float(s))
                except (TypeError, ValueError):
                    return (1, s)

            items = sorted(by_line.items(), key=lambda kv: _line_key(kv[0]))
            if line_want and not all_lines:
                items = [(ln, outs) for ln, outs in items if ln.replace(",", ".") == line_want]
            for i, (ln, outs) in enumerate(items):
                _append_row(outs, ln, is_main=(i == 0 and len(items) > 1))
            if items:
                continue
        if plain:
            # Prefer 1 / X / 2 column order for Match Winner–style markets
            order = {"1": 0, "X": 1, "2": 2}
            plain.sort(key=lambda o: order.get(str(o.get("name") or ""), 50))
            _append_row(plain, "—")
        elif by_line:
            # Fallback: flatten first line group
            first_ln, first_outs = next(iter(sorted(by_line.items(), key=lambda kv: kv[0])))
            _append_row(first_outs, first_ln)
    return rows
