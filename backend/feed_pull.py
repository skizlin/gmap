"""
Pull feed events from live APIs and merge into stored feed data.
Bet365: https://api.b365api.com/v1/bet365/upcoming?sport_id={id}&token=... with pagination.
Betfair: https://api.b365api.com/v1/betfair/sb/upcoming?sport_id={id}&token=... with pagination.
Sbobet: https://api.b365api.com/v1/sbobet/upcoming?sport_id=1&token=... (Soccer only).
1xbet: https://api.b365api.com/v1/1xbet/upcoming?sport_id={id}&token=... with pagination.
Bwin: https://api.b365api.com/v1/bwin/prematch?token=...&sport_id={id} per sport (100 per page).
"""
from __future__ import annotations

import json
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

# Config: set by main on init
FEED_DATA_DIR: Optional[Path] = None
BET365_API_BASE = "https://api.b365api.com/v1/bet365/upcoming"
BET365_PER_PAGE = 50
BETFAIR_API_BASE = "https://api.b365api.com/v1/betfair/sb/upcoming"
BETFAIR_PER_PAGE = 50
SBOBET_API_BASE = "https://api.b365api.com/v1/sbobet/upcoming"
SBOBET_PER_PAGE = 50
ONEXBET_API_BASE = "https://api.b365api.com/v1/1xbet/upcoming"
ONEXBET_PER_PAGE = 50
BWIN_API_BASE = "https://api.b365api.com/v1/bwin/prematch"
BWIN_PER_PAGE = 100


def _get_feed_data_path(feed_code: str) -> Path:
    if not FEED_DATA_DIR:
        raise RuntimeError("FEED_DATA_DIR not set")
    return FEED_DATA_DIR / f"{feed_code.strip().lower()}.json"


def load_stored_feed_events(feed_code: str) -> list[dict]:
    """Load stored events for a feed from feed_data/{feed_code}.json. Returns [] if file missing or invalid."""
    path = _get_feed_data_path(feed_code)
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return list(data) if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_stored_feed_events(feed_code: str, events: list[dict]) -> None:
    """Save events to feed_data/{feed_code}.json."""
    path = _get_feed_data_path(feed_code)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2, ensure_ascii=False)


def _normalize_unified_item(item: dict, sport_id: str, sport_name: str, feed_provider: str) -> dict:
    """Convert one unified API result item (Bet365/Betfair/Sbobet/1xbet) to our event shape.
    Bet365 outrights: away is null in payload; extra.n = Race # (e.g. Horse Racing sport_id 2, Greyhounds sport_id 4).
    """
    raw_id = item.get("id")
    valid_id = str(raw_id) if raw_id is not None else ""
    ts_str = item.get("time")
    try:
        ts = int(ts_str)
        start_time = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        start_time = "—"
    home = item.get("home") or {}
    away = item.get("away") or {}
    league = item.get("league") or {}
    league_id = league.get("id")
    comp_category_id = ("COMP:" + str(league_id)) if league_id is not None and str(league_id).strip() else None
    home_id = home.get("id") if isinstance(home, dict) else None
    away_id = away.get("id") if isinstance(away, dict) else None

    # Bet365: outright when away is null (Horse Racing, Greyhounds, etc.); extra.n = Race #
    is_outright = False
    market_name = None
    if feed_provider == "bet365" and item.get("away") is None:
        is_outright = True
        extra = item.get("extra") or {}
        if isinstance(extra, dict):
            n_val = extra.get("n")
            if n_val is not None:
                market_name = "Race " + str(n_val).strip()

    return {
        "feed_provider": feed_provider,
        "valid_id": valid_id,
        "domain_id": None,
        "raw_home_name": home.get("name") if isinstance(home, dict) else "",
        "raw_away_name": "" if is_outright else (away.get("name") if isinstance(away, dict) else ""),
        "raw_home_id": str(home_id) if home_id is not None else None,
        "raw_away_id": None if is_outright else (str(away_id) if away_id is not None else None),
        "raw_league_name": league.get("name") if isinstance(league, dict) else None,
        "raw_league_id": str(league_id) if league_id is not None else None,
        "category": comp_category_id,
        "category_id": comp_category_id,
        "start_time": start_time,
        "time_status": (str(item.get("time_status")).strip() if item.get("time_status") is not None else ""),
        "sport": sport_name,
        "sport_id": str(sport_id),
        "betradar_id": None,
        "is_outright": is_outright,
        "market_name": market_name,
        "is_mainbook": False,
        "updated_at": None,
        "mapping_status": "UNMAPPED",
        "status": (item.get("status") or "Open").strip() or "Open",
        "markets_count": item.get("markets_count") if item.get("markets_count") is not None else 0,
    }


def pull_bet365_sport(sport_id: str, sport_name: str, token: str) -> dict:
    """
    Pull all upcoming events for one Bet365 sport from the API (with pagination), merge into stored bet365.json.
    - If event id already stored: skip.
    - If new: add.
    Returns {"ok": bool, "added": int, "skipped": int, "total": int, "error": str | None}.
    """
    token = (token or "").strip()
    if not token:
        return {"ok": False, "added": 0, "skipped": 0, "total": 0, "error": "BET365_API_TOKEN not set"}

    existing = load_stored_feed_events("bet365")
    existing_ids = {str(e.get("valid_id") or "").strip() for e in existing if (e.get("valid_id") or "").strip()}
    added = 0
    skipped = 0
    total_from_api = 0
    page = 1
    all_new_events = []

    while True:
        url = f"{BET365_API_BASE}?sport_id={sport_id}&token={token}&page={page}&per_page={BET365_PER_PAGE}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "PTC-Global-Mapper/1.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", errors="replace")[:500]
            except Exception:
                pass
            return {"ok": False, "added": added, "skipped": skipped, "total": total_from_api, "error": f"HTTP {e.code}: {body}"}
        except urllib.error.URLError as e:
            return {"ok": False, "added": added, "skipped": skipped, "total": total_from_api, "error": str(e.reason)}
        except (json.JSONDecodeError, OSError) as e:
            return {"ok": False, "added": added, "skipped": skipped, "total": total_from_api, "error": str(e)}

        if not data.get("success"):
            return {"ok": False, "added": added, "skipped": skipped, "total": total_from_api, "error": data.get("message", "API returned success=0")}

        pager = data.get("pager") or {}
        total_from_api = int(pager.get("total") or 0)
        per_page = int(pager.get("per_page") or BET365_PER_PAGE)
        results = data.get("results") or []

        for item in results:
            raw_id = item.get("id")
            eid = str(raw_id).strip() if raw_id is not None else ""
            if not eid:
                continue
            if eid in existing_ids:
                skipped += 1
                continue
            normalized = _normalize_unified_item(item, sport_id, sport_name, "bet365")
            all_new_events.append(normalized)
            existing_ids.add(eid)
            added += 1

        if not results or len(results) < per_page or page * per_page >= total_from_api:
            break
        page += 1

    if all_new_events:
        merged = existing + all_new_events
        save_stored_feed_events("bet365", merged)

    return {"ok": True, "added": added, "skipped": skipped, "total": total_from_api, "error": None}


def pull_betfair_sport(sport_id: str, sport_name: str, token: str) -> dict:
    """
    Pull all upcoming events for one Betfair sport from the API (with pagination), merge into stored betfair.json.
    - If event id already stored: skip.
    - If new: add.
    Returns {"ok": bool, "added": int, "skipped": int, "total": int, "error": str | None}.
    """
    token = (token or "").strip()
    if not token:
        return {"ok": False, "added": 0, "skipped": 0, "total": 0, "error": "API key required"}

    existing = load_stored_feed_events("betfair")
    existing_ids = {str(e.get("valid_id") or "").strip() for e in existing if (e.get("valid_id") or "").strip()}
    added = 0
    skipped = 0
    total_from_api = 0
    page = 1
    all_new_events = []

    while True:
        url = f"{BETFAIR_API_BASE}?sport_id={sport_id}&token={token}&page={page}&per_page={BETFAIR_PER_PAGE}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "PTC-Global-Mapper/1.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", errors="replace")[:500]
            except Exception:
                pass
            return {"ok": False, "added": added, "skipped": skipped, "total": total_from_api, "error": f"HTTP {e.code}: {body}"}
        except urllib.error.URLError as e:
            return {"ok": False, "added": added, "skipped": skipped, "total": total_from_api, "error": str(e.reason)}
        except (json.JSONDecodeError, OSError) as e:
            return {"ok": False, "added": added, "skipped": skipped, "total": total_from_api, "error": str(e)}

        if not data.get("success"):
            return {"ok": False, "added": added, "skipped": skipped, "total": total_from_api, "error": data.get("message", "API returned success=0")}

        pager = data.get("pager") or {}
        total_from_api = int(pager.get("total") or 0)
        per_page = int(pager.get("per_page") or BETFAIR_PER_PAGE)
        results = data.get("results") or []

        for item in results:
            raw_id = item.get("id")
            eid = str(raw_id).strip() if raw_id is not None else ""
            if not eid:
                continue
            if eid in existing_ids:
                skipped += 1
                continue
            normalized = _normalize_unified_item(item, sport_id, sport_name, "betfair")
            all_new_events.append(normalized)
            existing_ids.add(eid)
            added += 1

        if not results or len(results) < per_page or page * per_page >= total_from_api:
            break
        page += 1

    if all_new_events:
        merged = existing + all_new_events
        save_stored_feed_events("betfair", merged)

    return {"ok": True, "added": added, "skipped": skipped, "total": total_from_api, "error": None}


def pull_sbobet_sport(sport_id: str, sport_name: str, token: str) -> dict:
    """
    Pull all upcoming events for one Sbobet sport from the API (with pagination), merge into stored sbobet.json.
    Sbobet only supports Soccer (sport_id=1).
    Returns {"ok": bool, "added": int, "skipped": int, "total": int, "error": str | None}.
    """
    token = (token or "").strip()
    if not token:
        return {"ok": False, "added": 0, "skipped": 0, "total": 0, "error": "API key required"}

    existing = load_stored_feed_events("sbobet")
    existing_ids = {str(e.get("valid_id") or "").strip() for e in existing if (e.get("valid_id") or "").strip()}
    added = 0
    skipped = 0
    total_from_api = 0
    page = 1
    all_new_events = []

    while True:
        url = f"{SBOBET_API_BASE}?sport_id={sport_id}&token={token}&page={page}&per_page={SBOBET_PER_PAGE}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "PTC-Global-Mapper/1.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", errors="replace")[:500]
            except Exception:
                pass
            return {"ok": False, "added": added, "skipped": skipped, "total": total_from_api, "error": f"HTTP {e.code}: {body}"}
        except urllib.error.URLError as e:
            return {"ok": False, "added": added, "skipped": skipped, "total": total_from_api, "error": str(e.reason)}
        except (json.JSONDecodeError, OSError) as e:
            return {"ok": False, "added": added, "skipped": skipped, "total": total_from_api, "error": str(e)}

        if not data.get("success"):
            return {"ok": False, "added": added, "skipped": skipped, "total": total_from_api, "error": data.get("message", "API returned success=0")}

        pager = data.get("pager") or {}
        total_from_api = int(pager.get("total") or 0)
        per_page = int(pager.get("per_page") or SBOBET_PER_PAGE)
        results = data.get("results") or []

        for item in results:
            raw_id = item.get("id")
            eid = str(raw_id).strip() if raw_id is not None else ""
            if not eid:
                continue
            if eid in existing_ids:
                skipped += 1
                continue
            normalized = _normalize_unified_item(item, sport_id, sport_name, "sbobet")
            all_new_events.append(normalized)
            existing_ids.add(eid)
            added += 1

        if not results or len(results) < per_page or page * per_page >= total_from_api:
            break
        page += 1

    if all_new_events:
        merged = existing + all_new_events
        save_stored_feed_events("sbobet", merged)

    return {"ok": True, "added": added, "skipped": skipped, "total": total_from_api, "error": None}


def pull_1xbet_sport(sport_id: str, sport_name: str, token: str) -> dict:
    """
    Pull all upcoming events for one 1xbet sport from the API (with pagination), merge into stored 1xbet.json.
    Returns {"ok": bool, "added": int, "skipped": int, "total": int, "error": str | None}.
    """
    token = (token or "").strip()
    if not token:
        return {"ok": False, "added": 0, "skipped": 0, "total": 0, "error": "API key required"}

    existing = load_stored_feed_events("1xbet")
    existing_ids = {str(e.get("valid_id") or "").strip() for e in existing if (e.get("valid_id") or "").strip()}
    added = 0
    skipped = 0
    total_from_api = 0
    page = 1
    all_new_events = []

    while True:
        url = f"{ONEXBET_API_BASE}?sport_id={sport_id}&token={token}&page={page}&per_page={ONEXBET_PER_PAGE}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "PTC-Global-Mapper/1.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", errors="replace")[:500]
            except Exception:
                pass
            return {"ok": False, "added": added, "skipped": skipped, "total": total_from_api, "error": f"HTTP {e.code}: {body}"}
        except urllib.error.URLError as e:
            return {"ok": False, "added": added, "skipped": skipped, "total": total_from_api, "error": str(e.reason)}
        except (json.JSONDecodeError, OSError) as e:
            return {"ok": False, "added": added, "skipped": skipped, "total": total_from_api, "error": str(e)}

        if not data.get("success"):
            return {"ok": False, "added": added, "skipped": skipped, "total": total_from_api, "error": data.get("message", "API returned success=0")}

        pager = data.get("pager") or {}
        total_from_api = int(pager.get("total") or 0)
        per_page = int(pager.get("per_page") or ONEXBET_PER_PAGE)
        results = data.get("results") or []

        for item in results:
            raw_id = item.get("id")
            eid = str(raw_id).strip() if raw_id is not None else ""
            if not eid:
                continue
            if eid in existing_ids:
                skipped += 1
                continue
            normalized = _normalize_unified_item(item, sport_id, sport_name, "1xbet")
            all_new_events.append(normalized)
            existing_ids.add(eid)
            added += 1

        if not results or len(results) < per_page or page * per_page >= total_from_api:
            break
        page += 1

    if all_new_events:
        merged = existing + all_new_events
        save_stored_feed_events("1xbet", merged)

    return {"ok": True, "added": added, "skipped": skipped, "total": total_from_api, "error": None}


def _normalize_bwin_item(item: dict, sport_name_override: str | None = None) -> dict:
    """Convert one Bwin prematch API result item to our bwin event shape.
    sport_name_override: when pulling by sport, use this (from feed_sports.csv) so sport_id 11 -> American Football etc.
    """
    raw_id = item.get("Id") or item.get("id")
    valid_id = str(raw_id) if raw_id is not None else ""
    # Bwin: outright from (1) IsOutright, (2) event-level category/templateCategory "Outrights",
    # or (3) any Market having category/templateCategory "Outrights" (see bwincategoryoutrights.json)
    is_outright = item.get("IsOutright", False)
    if not is_outright:
        cat = (item.get("category") or item.get("Category") or "").strip()
        if not cat:
            tc = item.get("templateCategory") or {}
            cat = (tc.get("category") or tc.get("Category") or "").strip()
        is_outright = cat.lower() == "outrights"
    if not is_outright:
        for m in item.get("Markets") or []:
            mc = (m.get("category") or m.get("Category") or "").strip().lower()
            if mc == "outrights":
                is_outright = True
                break
            mtc = m.get("templateCategory") or {}
            mtc_cat = (mtc.get("category") or mtc.get("Category") or "").strip().lower()
            if mtc_cat == "outrights":
                is_outright = True
                break
            if any((str(x) or "").strip().lower() == "outrights" for x in (mtc.get("dynamicCategories") or [])):
                is_outright = True
                break
    market_name = None
    is_mainbook = False
    if is_outright:
        for market in item.get("Markets") or []:
            if market.get("IsMainbook") or market.get("isMain"):
                name_obj = market.get("name") or market.get("Name")
                if isinstance(name_obj, dict) and "value" in name_obj:
                    market_name = name_obj.get("value")
                else:
                    market_name = name_obj
                is_mainbook = True
                break
        if not market_name and (item.get("Markets") or []):
            m = item["Markets"][0]
            name_obj = m.get("name") or m.get("Name")
            market_name = name_obj.get("value") if isinstance(name_obj, dict) else name_obj
    dt_str = item.get("Date")
    if dt_str:
        try:
            dt = datetime.fromisoformat(dt_str.rstrip("Z").replace("Z", "+00:00"))
            start_time = dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, AttributeError, TypeError):
            start_time = "—"
    else:
        start_time = "—"
    # Use feed_sports name when provided (pull_bwin_sport passes it) so sport_id 11 -> American Football
    if sport_name_override:
        sport = sport_name_override
    else:
        sport_name = item.get("SportName", "Unknown") or "Unknown"
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
    home_id = item.get("HomeTeamId")
    away_id = item.get("AwayTeamId")
    updated_at = item.get("updated_at")
    if isinstance(updated_at, str) and updated_at.isdigit():
        updated_at = int(updated_at)
    elif not isinstance(updated_at, int):
        updated_at = None
    return {
        "feed_provider": "bwin",
        "valid_id": valid_id,
        "domain_id": None,
        "raw_home_name": (item.get("HomeTeam") or "") if not is_outright else "",
        "raw_away_name": (item.get("AwayTeam") or "") if not is_outright else "",
        "raw_home_id": str(home_id) if home_id is not None else None,
        "raw_away_id": str(away_id) if away_id is not None else None,
        "raw_league_name": item.get("LeagueName"),
        "raw_league_id": str(item.get("LeagueId")) if item.get("LeagueId") else None,
        "category": item.get("RegionName"),
        "category_id": str(item.get("RegionId")) if item.get("RegionId") else None,
        "start_time": start_time,
        # Bwin: IsPreMatch true → Not Started (0); false → InPlay (1). Results link later will provide other statuses.
        "time_status": "0" if item.get("IsPreMatch") else "1",
        "sport": sport,
        "sport_id": str(item.get("SportId")) if item.get("SportId") is not None else None,
        "betradar_id": item.get("BetRadarId"),
        "is_outright": is_outright,
        "market_name": market_name,
        "is_mainbook": is_mainbook,
        "updated_at": updated_at,
        "mapping_status": "UNMAPPED",
        "status": (item.get("status") or "Open").strip() or "Open",
        "markets_count": item.get("markets_count") if item.get("markets_count") is not None else (len(item.get("Markets") or [])),
    }


def pull_bwin_sport(sport_id: str, sport_name: str, token: str) -> dict:
    """
    Pull prematch events for one Bwin sport from the API (sport_id param, 100 per page).
    Replaces/updates only this sport's events in stored bwin.json; other sports unchanged.
    Returns {"ok": bool, "added": int, "updated": int, "total": int, "error": str | None}.
    """
    token = (token or "").strip()
    if not token:
        return {"ok": False, "added": 0, "updated": 0, "total": 0, "error": "API key required"}

    existing = load_stored_feed_events("bwin")
    sport_id_str = str(sport_id or "").strip()
    existing_for_sport = {str(e.get("valid_id") or "").strip() for e in existing if str(e.get("sport_id") or "").strip() == sport_id_str}
    added = 0
    updated = 0
    total_from_api = 0
    page = 1
    api_by_id: dict[str, dict] = {}
    api_order: list[str] = []

    while True:
        url = f"{BWIN_API_BASE}?token={token}&sport_id={sport_id}&page={page}&per_page={BWIN_PER_PAGE}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "PTC-Global-Mapper/1.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", errors="replace")[:500]
            except Exception:
                pass
            return {"ok": False, "added": added, "updated": updated, "total": total_from_api, "error": f"HTTP {e.code}: {body}"}
        except urllib.error.URLError as e:
            return {"ok": False, "added": added, "updated": updated, "total": total_from_api, "error": str(e.reason)}
        except (json.JSONDecodeError, OSError) as e:
            return {"ok": False, "added": added, "updated": updated, "total": total_from_api, "error": str(e)}

        if not data.get("success"):
            return {"ok": False, "added": added, "updated": updated, "total": total_from_api, "error": data.get("message", "API returned success=0")}

        pager = data.get("pager") or {}
        total_from_api = int(pager.get("total") or 0)
        per_page = int(pager.get("per_page") or BWIN_PER_PAGE)
        results = data.get("results") or []

        for item in results:
            raw_id = item.get("Id") or item.get("id")
            eid = str(raw_id).strip() if raw_id is not None else ""
            if not eid:
                continue
            normalized = _normalize_bwin_item(item, sport_name_override=sport_name)
            if eid not in api_by_id:
                api_order.append(eid)
                api_by_id[eid] = normalized
                if eid in existing_for_sport:
                    updated += 1
                else:
                    added += 1
            else:
                api_by_id[eid] = normalized

        if not results or len(results) < per_page or page * per_page >= total_from_api:
            break
        page += 1

    if api_by_id or sport_id_str:
        other_sports = [e for e in existing if str(e.get("sport_id") or "").strip() != sport_id_str]
        merged = other_sports + [api_by_id[eid] for eid in api_order]
        save_stored_feed_events("bwin", merged)

    return {"ok": True, "added": added, "updated": updated, "total": total_from_api, "error": None}
