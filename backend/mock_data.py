from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone

# Use exact path to designs/feed_json_examples
BASE_DIR = Path(__file__).resolve().parent.parent
MOCK_DIR = BASE_DIR / "designs" / "feed_json_examples"

# When feed_data/bet365.json exists (pulled from API), use it instead of feed_json_examples/bet365.json
try:
    from backend import config
    FEED_DATA_DIR = getattr(config, "FEED_DATA_DIR", None)
except Exception:
    FEED_DATA_DIR = None

# We'll use this list to store all loaded events
LOADED_EVENTS = []

def _clear_synthetic_feed_categories(events: list) -> None:
    """Strip legacy COMP:<league_id> values from category fields; unified feeds have no native category."""
    for e in events:
        for key in ("category", "category_id"):
            v = e.get(key)
            if v is None or v == "":
                continue
            s = str(v).strip()
            if s.upper().startswith("COMP:"):
                e[key] = None if key == "category_id" else ""


def _bwin_market_container_is_outright(m: dict) -> bool:
    """Bwin prematch: outright indicators on a market or optionMarket object."""
    mc = (m.get("category") or m.get("Category") or "").strip().lower()
    if mc == "outrights":
        return True
    mtc = m.get("templateCategory") or {}
    mtc_cat = (mtc.get("category") or mtc.get("Category") or "").strip().lower()
    if mtc_cat == "outrights":
        return True
    if any((str(x) or "").strip().lower() == "outrights" for x in (mtc.get("dynamicCategories") or [])):
        return True
    return False


def _bwin_outright_detection(item: dict) -> tuple[bool, str | None, bool]:
    """
    Detect Bwin outright fixture + optional display market name (League Winner, etc.).
    Some payloads put outrights only under optionMarkets with Markets=[].
    """
    is_outright = bool(item.get("IsOutright", False))
    if not is_outright:
        cat = (item.get("category") or item.get("Category") or "").strip()
        if not cat:
            tc = item.get("templateCategory") or {}
            cat = (tc.get("category") or tc.get("Category") or "").strip()
        is_outright = cat.lower() == "outrights"
    if not is_outright:
        for m in item.get("Markets") or []:
            if _bwin_market_container_is_outright(m):
                is_outright = True
                break
    if not is_outright:
        for m in item.get("optionMarkets") or []:
            if _bwin_market_container_is_outright(m):
                is_outright = True
                break

    market_name: str | None = None
    is_mainbook = False
    if not is_outright:
        return False, None, False

    def _name_from_market(market: dict) -> str | None:
        name_obj = market.get("name") or market.get("Name")
        if isinstance(name_obj, dict):
            return (name_obj.get("value") or name_obj.get("Value") or "").strip() or None
        if name_obj is not None:
            s = str(name_obj).strip()
            return s or None
        return market.get("Name") if isinstance(market.get("Name"), str) else None

    for market in item.get("Markets", []) or []:
        if market.get("IsMainbook") or market.get("isMain"):
            market_name = _name_from_market(market) or market.get("Name")
            is_mainbook = True
            break
    if not market_name and item.get("Markets"):
        m0 = item["Markets"][0]
        market_name = _name_from_market(m0) or m0.get("Name")
    if not market_name:
        for market in item.get("optionMarkets", []) or []:
            if market.get("isMain") or market.get("IsMain"):
                market_name = _name_from_market(market)
                is_mainbook = True
                break
    if not market_name and item.get("optionMarkets"):
        m0 = item["optionMarkets"][0]
        market_name = _name_from_market(m0)
    return True, market_name, is_mainbook


def parse_bwin(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    events = []
    for item in data.get("results", []):
        is_outright, market_name, is_mainbook = _bwin_outright_detection(item)
        
        # Parse Date (bwin ISO 8601: "2017-03-17T10:00:00Z")
        dt_str = item.get("Date")
        if dt_str:
            try:
                # Strip trailing Z and parse as UTC
                dt = datetime.fromisoformat(dt_str.rstrip("Z"))
                start_time = dt.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, AttributeError):
                start_time = "—"
        else:
            start_time = "—"

        # Determine Sport (check more specific names first so "Table Tennis" is not collapsed to "Tennis")
        sport_name = item.get("SportName", "Unknown")
        if "Football" in sport_name or "Soccer" in sport_name:
            sport = "Soccer"
        elif "Basketball" in sport_name:
            sport = "Basketball"
        elif "Table Tennis" in sport_name:
            sport = "Table Tennis"
        elif "Tennis" in sport_name:
            sport = "Tennis"
        else:
            sport = sport_name

        # Use HomeTeamId/AwayTeamId when present (updated bwin API); fallback to None for older data or outrights
        home_id = item.get("HomeTeamId")
        away_id = item.get("AwayTeamId")
        events.append({
            "feed_provider": "bwin",
            "valid_id": str(item.get("Id")),
            "domain_id": None,
            "raw_home_name": item.get("HomeTeam", "") if not is_outright else "",
            "raw_away_name": item.get("AwayTeam", "") if not is_outright else "",
            "raw_home_id": str(home_id) if home_id is not None else None,
            "raw_away_id": str(away_id) if away_id is not None else None,
            "raw_league_name": item.get("LeagueName"),
            "raw_league_id": str(item.get("LeagueId")) if item.get("LeagueId") else None,
            "category": item.get("RegionName"),
            "category_id": str(item.get("RegionId")) if item.get("RegionId") else None,
            "start_time": start_time,
            "time_status": "0" if item.get("IsPreMatch") else "1",
            "sport": sport,
            "sport_id": item.get("SportId"),  # only set when feed provides ID; else backend uses sport name for mapping
            "betradar_id": item.get("BetRadarId"),
            "is_outright": is_outright,
            "market_name": market_name,
            "is_mainbook": is_mainbook,
            "updated_at": int(item.get("updated_at")) if item.get("updated_at") else None,
            "mapping_status": "UNMAPPED",
            "status": (item.get("status") or "Open").strip() or "Open",
            "markets_count": item.get("markets_count") if item.get("markets_count") is not None else 0,
        })
    return events

def parse_unified(file_path, provider):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    events = []
    for item in data.get("results", []):
        # time is a unix timestamp string
        ts_str = item.get("time")
        try:
            ts = int(ts_str)
            start_time = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            start_time = "—"
            
        home = item.get("home") or {}
        away = item.get("away") if item.get("away") is not None else {}
        league = item.get("league") or {}
        league_id = league.get("id")
        sport_id = item.get("sport_id")

        # Bet365: outright when away is null (Horse Racing, Greyhounds, etc.); extra.n = Race #
        is_outright = False
        market_name = None
        if provider == "bet365" and item.get("away") is None:
            is_outright = True
            extra = item.get("extra") or {}
            if isinstance(extra, dict):
                n_val = extra.get("n")
                if n_val is not None:
                    market_name = "Race " + str(n_val).strip()

        events.append({
            "feed_provider": provider,
            "valid_id": item.get("id"),
            "domain_id": None,
            "raw_home_name": home.get("name") if isinstance(home, dict) else "",
            "raw_away_name": "" if is_outright else (away.get("name") if isinstance(away, dict) else ""),
            "raw_home_id": str(home["id"]) if isinstance(home, dict) and home.get("id") is not None else None,
            "raw_away_id": None if is_outright else (str(away["id"]) if isinstance(away, dict) and away.get("id") is not None else None),
            "raw_league_name": league.get("name") if isinstance(league, dict) else None,
            "raw_league_id": str(league_id) if league_id is not None else None,
            "category": "",
            "category_id": None,
            "start_time": start_time,
            "time_status": item.get("time_status", "0"),
            "sport": None,
            "sport_id": sport_id if sport_id not in (None, "") else None,
            "betradar_id": None,
            "is_outright": is_outright,
            "market_name": market_name,
            "is_mainbook": False,
            "updated_at": None,
            "mapping_status": "UNMAPPED",
            "status": (item.get("status") or "Open").strip() or "Open",
            "markets_count": item.get("markets_count") if item.get("markets_count") is not None else 0,
        })
    return events


def parse_b365racing(file_path):
    """
    Parse b365racing.json: Bet365 Horse Racing (sport_id 2). Outright-type events.
    Same API shape as bet365/unified but: away is null, extra.n = Race Number.
    Event name for outright display = Race Number (extra.n), e.g. "Race 11".
    """
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    events = []
    for item in data.get("results", []):
        ts_str = item.get("time")
        try:
            ts = int(ts_str)
            start_time = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            start_time = "—"

        league = item.get("league", {}) or {}
        league_id = league.get("id")

        home = item.get("home") or {}
        if isinstance(home, dict):
            raw_home_id = home.get("id")
            raw_home_name = home.get("name") or ""
        else:
            raw_home_id = None
            raw_home_name = ""

        # extra.n = Race Number for this league; use as event name (outright display)
        extra = item.get("extra") or {}
        race_n = extra.get("n") if isinstance(extra, dict) else None
        if race_n is not None:
            race_n = str(race_n).strip()
        market_name = ("Race " + race_n) if race_n else "Race"

        events.append({
            "feed_provider": "bet365",
            "valid_id": item.get("id"),
            "domain_id": None,
            "raw_home_name": raw_home_name,
            "raw_away_name": None,
            "raw_home_id": str(raw_home_id) if raw_home_id is not None else None,
            "raw_away_id": None,
            "raw_league_name": league.get("name"),
            "raw_league_id": str(league_id) if league_id is not None else None,
            "category": "",
            "category_id": None,
            "start_time": start_time,
            "time_status": item.get("time_status", "0"),
            "sport": "Horse Racing",
            "sport_id": "2",
            "betradar_id": None,
            "is_outright": True,
            "market_name": market_name,
            "is_mainbook": False,
            "updated_at": int(item["updated_at"]) if item.get("updated_at") not in (None, "") else None,
            "mapping_status": "UNMAPPED",
            "status": (item.get("status") or "Open").strip() or "Open",
            "markets_count": item.get("markets_count") if item.get("markets_count") is not None else 0,
        })
    return events


def load_all_mock_data():
    all_events = []

    # Bwin: use only feed_data/bwin.json when feed_data dir exists (no fallback to examples if file missing/empty)
    bwin_loaded_from_stored = False
    if FEED_DATA_DIR:
        if (FEED_DATA_DIR / "bwin.json").exists():
            try:
                with open(FEED_DATA_DIR / "bwin.json", "r", encoding="utf-8") as f:
                    bwin_stored = json.load(f)
                if isinstance(bwin_stored, list):
                    all_events.extend(bwin_stored)
                bwin_loaded_from_stored = True
            except (json.JSONDecodeError, OSError):
                pass
        else:
            # feed_data exists but bwin.json missing (e.g. user deleted it) -> no Bwin events, no fallback
            bwin_loaded_from_stored = True
    if not bwin_loaded_from_stored:
        bwin_path = MOCK_DIR / "bwin.json"
        if bwin_path.exists():
            all_events.extend(parse_bwin(bwin_path))

    # Bet365: use only feed_data/bet365.json when feed_data dir exists (no fallback if file missing/empty)
    bet365_loaded_from_stored = False
    if FEED_DATA_DIR:
        if (FEED_DATA_DIR / "bet365.json").exists():
            try:
                with open(FEED_DATA_DIR / "bet365.json", "r", encoding="utf-8") as f:
                    bet365_stored = json.load(f)
                if isinstance(bet365_stored, list):
                    all_events.extend(bet365_stored)
                bet365_loaded_from_stored = True
            except (json.JSONDecodeError, OSError):
                bet365_loaded_from_stored = True
        else:
            bet365_loaded_from_stored = True  # file missing -> no Bet365 events, no fallback
    if not bet365_loaded_from_stored:
        if (MOCK_DIR / "bet365.json").exists():
            all_events.extend(parse_unified(MOCK_DIR / "bet365.json", "bet365"))
        b365racing_path = MOCK_DIR / "b365racing.json"
        if b365racing_path.exists():
            all_events.extend(parse_b365racing(b365racing_path))

    # Betfair: use pulled data from feed_data/betfair.json when present, else feed_json_examples
    betfair_loaded_from_stored = False
    if FEED_DATA_DIR and (FEED_DATA_DIR / "betfair.json").exists():
        try:
            with open(FEED_DATA_DIR / "betfair.json", "r", encoding="utf-8") as f:
                betfair_stored = json.load(f)
            if isinstance(betfair_stored, list):
                all_events.extend(betfair_stored)
                betfair_loaded_from_stored = True
        except (json.JSONDecodeError, OSError):
            pass
    if not betfair_loaded_from_stored:
        if (MOCK_DIR / "betfair.json").exists():
            all_events.extend(parse_unified(MOCK_DIR / "betfair.json", "betfair"))

    # 1xbet: use pulled data from feed_data/1xbet.json when present, else feed_json_examples
    onexbet_loaded_from_stored = False
    if FEED_DATA_DIR and (FEED_DATA_DIR / "1xbet.json").exists():
        try:
            with open(FEED_DATA_DIR / "1xbet.json", "r", encoding="utf-8") as f:
                onexbet_stored = json.load(f)
            if isinstance(onexbet_stored, list):
                all_events.extend(onexbet_stored)
                onexbet_loaded_from_stored = True
        except (json.JSONDecodeError, OSError):
            pass
    if not onexbet_loaded_from_stored:
        if (MOCK_DIR / "1xbet.json").exists():
            all_events.extend(parse_unified(MOCK_DIR / "1xbet.json", "1xbet"))

    _clear_synthetic_feed_categories(all_events)
    return all_events
