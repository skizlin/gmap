import json
from pathlib import Path
from datetime import datetime, timezone

# Use exact path to designs/feed_json_examples
BASE_DIR = Path(__file__).resolve().parent.parent
MOCK_DIR = BASE_DIR / "designs" / "feed_json_examples"

# We'll use this list to store all loaded events
LOADED_EVENTS = []

# Multi-word country name prefixes that appear in bet365 league names
_MULTI_WORD_PREFIXES = {
    "Bosnia Herzegovina", "Bosnia-Herzegovina",
    "Czech Republic",
    "El Salvador",
    "Hong Kong",
    "Ivory Coast",
    "New Zealand",
    "North Macedonia",
    "Papua New Guinea",
    "Saudi Arabia",
    "Sierra Leone",
    "South Africa",
    "South Korea",
    "Trinidad Tobago",
    "Trinidad And Tobago",
    "United Arab Emirates",
}

# International organisations / regions → display name
_ORG_PREFIXES = {
    "UEFA": "UEFA",
    "FIFA": "FIFA",
    "CONMEBOL": "CONMEBOL",
    "CONCACAF": "CONCACAF",
    "CAF": "CAF",
    "AFC": "AFC",
    "Europe": "Europe",
    "International": "International",
    "World": "World",
}

def extract_category_from_league_name(league_name: str) -> str | None:
    """
    Parse the category (country or organisation) from a bet365/sbobet league name.
    League names follow the pattern: '<Country/Org> <Competition Name>'
    e.g. 'Germany Bundesliga' → 'Germany'
         'UEFA Champions League Women' → 'UEFA'
         'Europe Friendlies' → 'Europe'
         'Ivory Coast Premier Division' → 'Ivory Coast'
    The competition name itself is left untouched.
    """
    if not league_name:
        return None

    # Skip known acronym-only league names that have no country prefix
    # e.g. 'MLB (Major League Baseball)', 'NBA (PLAYOFF)', '3x3 Asia Cup'
    _no_country_prefixes = {"MLB", "NBA", "NFL", "NHL", "MLS", "3x3"}
    first_word = league_name.split()[0].rstrip("(")
    if first_word in _no_country_prefixes:
        return None

    # Check multi-word prefixes first (longest match wins)
    for prefix in sorted(_MULTI_WORD_PREFIXES, key=len, reverse=True):
        if league_name.startswith(prefix + " ") or league_name == prefix:
            return prefix

    # Check single-word organisation prefixes
    if first_word in _ORG_PREFIXES:
        return _ORG_PREFIXES[first_word]

    # Assume first word is a country name if it looks like a proper noun
    _generic_skip = {"La", "Le", "Die", "Der", "El", "Cup", "League", "Super", "Premier"}
    if first_word[0].isupper() and first_word not in _generic_skip:
        return first_word

    return None


def extract_category_1xbet(league_name: str) -> str | None:
    """
    Parse the category from a 1xbet league name.
    1xbet uses dot-separated format: '<Country>. <Competition>'
    e.g. 'Belarus. Reserve League' → 'Belarus'
         'Czech Republic. Youth League' → 'Czech Republic'
         'Australia. QBL. Women' → 'Australia'
    Some 1xbet leagues lack dots — fall back to the space-prefix extractor.
    """
    if not league_name:
        return None

    if "." in league_name:
        first_part = league_name.split(".")[0].strip()
        if not first_part:
            return None

        # Check for known multi-word countries in 1xbet
        for prefix in sorted(_MULTI_WORD_PREFIXES, key=len, reverse=True):
            if first_part == prefix:
                return prefix

        # Check org prefixes
        first_word = first_part.split()[0]
        if first_word in _ORG_PREFIXES:
            return _ORG_PREFIXES[first_word]

        # Return the whole first segment (works for "Belarus", "Czech Republic", etc.)
        if first_part[0].isupper():
            return first_part

        return None
    else:
        # No dot: fall back to space-prefix extractor (same as bet365/sbobet)
        return extract_category_from_league_name(league_name)

def parse_bwin(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    events = []
    for item in data.get("results", []):
        is_outright = item.get("IsOutright", False)
        market_name = None
        is_mainbook = False
        
        # If outright, search for the mainbook market
        if is_outright:
            for market in item.get("Markets", []):
                if market.get("IsMainbook"):
                    market_name = market.get("Name")
                    is_mainbook = True
                    break
            # Fallback if no mainbook found
            if not market_name and item.get("Markets"):
                market_name = item["Markets"][0].get("Name")
        
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

        # Determine Sport
        sport_name = item.get("SportName", "Unknown")
        if "Football" in sport_name or "Soccer" in sport_name:
            sport = "Soccer"
        elif "Basketball" in sport_name:
            sport = "Basketball"
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
            "mapping_status": "UNMAPPED"
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
            
        home = item.get("home", {})
        away = item.get("away", {})
        league = item.get("league", {})
        league_id = league.get("id")
        # Category for unified feeds: use league id, present/store as COMP:<league_id>
        comp_category_id = ("COMP:" + str(league_id)) if league_id is not None and str(league_id).strip() else None

        # Feed (e.g. bet365.json) sends only sport_id, not sport name. We derive "sport" for display only.
        # sport_id 1=Soccer, 2=Horse Racing, 13=Tennis, 18=Basketball
        sport_id = item.get("sport_id")
        if sport_id == "1":
            sport = "Soccer"
        elif sport_id == "2":
            sport = "Horse Racing"
        elif sport_id == "13":
            sport = "Tennis"
        elif sport_id == "18":
            sport = "Basketball"
        else:
            sport = "Soccer"  # default for display when unknown
        # Pass through feed's sport_id so entity_feed_mappings stores ID (e.g. "1"), not our display name
        events.append({
            "feed_provider": provider,
            "valid_id": item.get("id"),
            "domain_id": None,
            "raw_home_name": home.get("name"),
            "raw_away_name": away.get("name"),
            "raw_home_id": home.get("id"),
            "raw_away_id": away.get("id"),
            "raw_league_name": league.get("name"),
            "raw_league_id": league.get("id"),
            "category": comp_category_id,
            "category_id": comp_category_id,
            "start_time": start_time,
            "time_status": item.get("time_status", "0"),
            "sport": sport,  # display only (we derive from sport_id; feed does not send sport name)
            "sport_id": sport_id if sport_id not in (None, "") else None,  # from feed (e.g. bet365 "1"); used as mapped feed id
            "betradar_id": None,
            "is_outright": False,
            "market_name": None,
            "is_mainbook": False,
            "updated_at": None,
            "mapping_status": "UNMAPPED"
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
        comp_category_id = ("COMP:" + str(league_id)) if league_id is not None and str(league_id).strip() else None

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
            "category": comp_category_id,
            "category_id": comp_category_id,
            "start_time": start_time,
            "time_status": item.get("time_status", "0"),
            "sport": "Horse Racing",
            "sport_id": "2",
            "betradar_id": None,
            "is_outright": True,
            "market_name": market_name,
            "is_mainbook": False,
            "updated_at": int(item["updated_at"]) if item.get("updated_at") not in (None, "") else None,
            "mapping_status": "UNMAPPED"
        })
    return events


def load_all_mock_data():
    all_events = []
    
    # Load bwin
    bwin_path = MOCK_DIR / "bwin.json"
    if bwin_path.exists():
        all_events.extend(parse_bwin(bwin_path))
        
    # Load unified feeds
    unified_feeds = ["bet365", "betfair", "sbobet", "1xbet"]
    for provider in unified_feeds:
        provider_path = MOCK_DIR / f"{provider}.json"
        if provider_path.exists():
            all_events.extend(parse_unified(provider_path, provider))

    # Bet365 Horse Racing (sport_id 2): outright events; extra.n = Race Number = event name
    b365racing_path = MOCK_DIR / "b365racing.json"
    if b365racing_path.exists():
        all_events.extend(parse_b365racing(b365racing_path))

    return all_events
