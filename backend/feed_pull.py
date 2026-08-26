"""
Pull feed events from live APIs and merge into stored feed data.
Bet365: https://api.b365api.com/v1/bet365/upcoming?sport_id={id}&token=... with pagination.
Betfair: https://api.b365api.com/v1/betfair/sb/upcoming?sport_id={id}&token=... with pagination.
1xbet: https://api.b365api.com/v1/1xbet/upcoming?sport_id={id}&token=... with pagination.
Bwin / Bwin L2: same https://api.b365api.com/v1/bwin/prematch?token=...&sport_id={id}; L2 stores high-id / ``2:`` events in feed_data/bwin_l2.json.

Uses async HTTP (httpx) so pulls can be run in parallel with a concurrency cap.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

import httpx

from backend.mock_data import (
    _bwin_outright_detection,
    bwin_canonical_market_display_name,
    bwin_normalize_outright_stored_event,
)

# Per-feed locks so parallel pulls for the same feed serialize merge/save only (fetch stays parallel).
_feed_locks: dict[str, asyncio.Lock] = {}


def _feed_lock(feed_code: str) -> asyncio.Lock:
    if feed_code not in _feed_locks:
        _feed_locks[feed_code] = asyncio.Lock()
    return _feed_locks[feed_code]

# Config: set by main on init
FEED_DATA_DIR: Optional[Path] = None
BET365_API_BASE = "https://api.b365api.com/v1/bet365/upcoming"
BET365_PER_PAGE = 50
BETFAIR_API_BASE = "https://api.b365api.com/v1/betfair/sb/upcoming"
BETFAIR_PER_PAGE = 50
ONEXBET_API_BASE = "https://api.b365api.com/v1/1xbet/upcoming"
ONEXBET_PER_PAGE = 50
BWIN_API_BASE = "https://api.b365api.com/v1/bwin/prematch"
BWIN_PER_PAGE = 100
# BetsAPI / Bwin: alternate product line uses high numeric event Id (and sometimes "2:" ids). Split into feed "bwin_l2".
BWIN_L2_MIN_NUMERIC_EVENT_ID = 200_000_000


def bwin_event_id_is_layer_l2(raw_id) -> bool:
    """True if this Bwin event Id belongs to the L2 / extended line (stored under feed_provider bwin_l2)."""
    if raw_id is None:
        return False
    s = str(raw_id).strip()
    if not s:
        return False
    if s.lower().startswith("2:"):
        return True
    try:
        return int(float(s)) >= BWIN_L2_MIN_NUMERIC_EVENT_ID
    except (ValueError, TypeError):
        return False


def bwin_event_id_is_layer_l1(raw_id) -> bool:
    """Classic Bwin line (feed_provider bwin)."""
    return not bwin_event_id_is_layer_l2(raw_id)

# Event-details API (BetsAPI): token from .env (BETSAPI_TOKEN). Used when domain event is created or mapped.
# 1xbet: /v1/1xbet/event?token=...&event_id=...   bwin: /v1/bwin/event?token=...&event_id=...   bet365 prematch: /v4/bet365/prematch?token=...&FI=...
ONEXBET_EVENT_DETAILS_BASE = "https://api.b365api.com/v1/1xbet/event"
BWIN_EVENT_DETAILS_BASE = "https://api.b365api.com/v1/bwin/event"
BET365_PREMATCH_DETAILS_BASE = "https://api.b365api.com/v4/bet365/prematch"


def _get_feed_data_path(feed_code: str) -> Path:
    if not FEED_DATA_DIR:
        raise RuntimeError("FEED_DATA_DIR not set")
    return FEED_DATA_DIR / f"{feed_code.strip().lower()}.json"


async def _fetch_json_async(url: str, timeout: float = 60.0) -> tuple[Optional[dict], Optional[str]]:
    """Fetch URL and parse JSON. Returns (data, None) on success or (None, error_message) on failure."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=timeout, headers={"User-Agent": "PTC-Global-Mapper/1.0"})
            resp.raise_for_status()
            data = resp.json()
            return (data, None)
    except httpx.HTTPStatusError as e:
        body = (e.response.text or "")[:500]
        return (None, f"HTTP {e.response.status_code}: {body}")
    except (httpx.RequestError, json.JSONDecodeError, OSError) as e:
        return (None, str(e))


def _sanitize_feed_valid_id_for_path(feed_valid_id: str) -> str:
    """Safe filename from feed_valid_id (no path separators or reserved chars)."""
    s = (feed_valid_id or "").strip()
    for c in ("/", "\\", ":", "*", "?", '"', "<", ">", "|"):
        s = s.replace(c, "_")
    return s or "unknown"


async def fetch_event_details_async(
    feed_code: str, feed_valid_id: str, token: str
) -> Optional[dict]:
    """
    Fetch event details from BetsAPI (b365api.com). Used when a domain event is created or mapped.
    - 1xbet: event_id param (prematch + inplay).
    - bwin: event_id param (prematch + inplay).
    - bet365: FI param (prematch only; inplay out of scope for now).
    Returns full API response dict or None on failure. Accepts 1 id for now (up to 10 later).
    """
    feed = (feed_code or "").strip().lower()
    fid = (feed_valid_id or "").strip()
    if not fid or not token:
        return None
    if feed == "1xbet":
        url = f"{ONEXBET_EVENT_DETAILS_BASE}?token={token}&event_id={fid}"
    elif feed in ("bwin", "bwin_l2"):
        url = f"{BWIN_EVENT_DETAILS_BASE}?token={token}&event_id={fid}"
    elif feed == "bet365":
        url = f"{BET365_PREMATCH_DETAILS_BASE}?token={token}&FI={fid}"
    else:
        return None
    data, err = await _fetch_json_async(url, timeout=30.0)
    return data


def save_event_details(feed_code: str, feed_valid_id: str, data: dict) -> None:
    """Persist event-details API response under feed_event_details/{feed_code}/{feed_valid_id}.json."""
    from backend import config
    base = config.FEED_EVENT_DETAILS_DIR
    feed = (feed_code or "").strip().lower()
    safe_id = _sanitize_feed_valid_id_for_path(feed_valid_id)
    if not feed:
        return
    path = base / feed / f"{safe_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


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
    from backend.mock_data import _clear_synthetic_feed_categories

    _clear_synthetic_feed_categories(events)
    path = _get_feed_data_path(feed_code)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2, ensure_ascii=False)


def _normalize_unified_item(item: dict, sport_id: str, sport_name: str, feed_provider: str) -> dict:
    """Convert one unified API result item (Bet365/Betfair/1xbet) to our event shape.
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
        "category": "",
        "category_id": None,
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


async def pull_bet365_sport(sport_id: str, sport_name: str, token: str) -> dict:
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
        data, err = await _fetch_json_async(url)
        if err:
            return {"ok": False, "added": added, "skipped": skipped, "total": total_from_api, "error": err}

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
        async with _feed_lock("bet365"):
            current = load_stored_feed_events("bet365")
            current_ids = {str(e.get("valid_id") or "").strip() for e in current}
            for ev in all_new_events:
                eid = str(ev.get("valid_id") or "").strip()
                if eid and eid not in current_ids:
                    current.append(ev)
                    current_ids.add(eid)
            save_stored_feed_events("bet365", current)

    return {"ok": True, "added": added, "skipped": skipped, "total": total_from_api, "error": None}


async def pull_betfair_sport(sport_id: str, sport_name: str, token: str) -> dict:
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
        data, err = await _fetch_json_async(url)
        if err:
            return {"ok": False, "added": added, "skipped": skipped, "total": total_from_api, "error": err}

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
        async with _feed_lock("betfair"):
            current = load_stored_feed_events("betfair")
            current_ids = {str(e.get("valid_id") or "").strip() for e in current}
            for ev in all_new_events:
                eid = str(ev.get("valid_id") or "").strip()
                if eid and eid not in current_ids:
                    current.append(ev)
                    current_ids.add(eid)
            save_stored_feed_events("betfair", current)

    return {"ok": True, "added": added, "skipped": skipped, "total": total_from_api, "error": None}


async def pull_1xbet_sport(sport_id: str, sport_name: str, token: str) -> dict:
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
        data, err = await _fetch_json_async(url)
        if err:
            return {"ok": False, "added": added, "skipped": skipped, "total": total_from_api, "error": err}

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
        async with _feed_lock("1xbet"):
            current = load_stored_feed_events("1xbet")
            current_ids = {str(e.get("valid_id") or "").strip() for e in current}
            for ev in all_new_events:
                eid = str(ev.get("valid_id") or "").strip()
                if eid and eid not in current_ids:
                    current.append(ev)
                    current_ids.add(eid)
            save_stored_feed_events("1xbet", current)

    return {"ok": True, "added": added, "skipped": skipped, "total": total_from_api, "error": None}


def _bwin_template_id_placeholder(template_id: object) -> bool:
    if template_id is None:
        return True
    try:
        return int(template_id) == 0
    except (TypeError, ValueError):
        s = str(template_id).strip()
        return s == "" or s == "0"


def _bwin_market_row_display_name(m: dict, *, canonical: bool = False) -> str:
    n = m.get("name")
    if isinstance(n, dict):
        raw = (n.get("value") or "").strip()
    elif isinstance(n, str):
        raw = n.strip()
    else:
        raw = ""
    if canonical and raw:
        return bwin_canonical_market_display_name(raw)
    return raw


def _bwin_market_identity_key(m: dict, *, l2_dedupe_by_name: bool) -> tuple[str, str]:
    """One key per logical market type for counting; L2 grid uses display name so multi-line handicaps count as one type."""
    tc = m.get("templateCategory") or {}
    tid = m.get("templateId")
    if tid is None:
        tid = tc.get("id")
    placeholder = _bwin_template_id_placeholder(tid)
    if l2_dedupe_by_name and placeholder:
        nm = _bwin_market_row_display_name(m, canonical=True)
        if not nm and isinstance(tc.get("name"), dict):
            nm = bwin_canonical_market_display_name((tc["name"].get("value") or "").strip())
        if nm:
            return ("name", nm.casefold())
        rid = m.get("id")
        return ("row", str(rid) if rid is not None else "")
    if not placeholder:
        return ("tid", str(tid).strip())
    rid = m.get("id")
    return ("row", str(rid) if rid is not None else "")


def _bwin_distinct_market_types_count(item: dict, *, l2_dedupe_by_name: bool) -> int:
    keys: set[tuple[str, str]] = set()
    for m in (item.get("Markets") or []) + (item.get("optionMarkets") or []):
        if isinstance(m, dict):
            keys.add(_bwin_market_identity_key(m, l2_dedupe_by_name=l2_dedupe_by_name))
    return len(keys)


def _normalize_bwin_item(
    item: dict, sport_name_override: str | None = None, *, feed_provider: str = "bwin"
) -> dict:
    """Convert one Bwin prematch API result item to our stored event shape.
    sport_name_override: when pulling by sport, use this (from feed_sports.csv) so sport_id 11 -> American Football etc.
    feed_provider: "bwin" (L1 ids) or "bwin_l2" (L2 ids); same API payload shape.
    """
    raw_id = item.get("Id") or item.get("id")
    valid_id = str(raw_id) if raw_id is not None else ""
    is_outright, market_name, is_mainbook = _bwin_outright_detection(item)
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
    fp = (feed_provider or "bwin").strip().lower()
    if fp not in ("bwin", "bwin_l2"):
        fp = "bwin"
    out = {
        "feed_provider": fp,
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
        "markets_count": (
            _bwin_distinct_market_types_count(item, l2_dedupe_by_name=True)
            if fp == "bwin_l2"
            else (
                item.get("markets_count")
                if item.get("markets_count") is not None
                else (len(item.get("Markets") or []) + len(item.get("optionMarkets") or []))
            )
        ),
        # Keep prematch market payloads for Configuration → Markets mapper. L2 ids often have no /v1/bwin/event body.
        "SportId": item.get("SportId"),
        "Markets": list(item.get("Markets") or []),
        "optionMarkets": list(item.get("optionMarkets") or []),
    }
    if is_outright:
        bwin_normalize_outright_stored_event(out)
        if fp == "bwin_l2":
            out["markets_count"] = _bwin_distinct_market_types_count(out, l2_dedupe_by_name=True)
    return out


async def _pull_bwin_prematch_layer(
    sport_id: str,
    sport_name: str,
    token: str,
    *,
    store_feed_code: str,
    for_l2_layer: bool,
) -> dict:
    """
    Pull prematch from BetsAPI bwin/prematch; filter rows into L1 (bwin) or L2 (bwin_l2) by event Id rule.
    Replaces/updates only this sport's events in feed_data/{store_feed_code}.json.
    """
    token = (token or "").strip()
    if not token:
        return {"ok": False, "added": 0, "updated": 0, "total": 0, "error": "API key required"}

    store_feed_code = (store_feed_code or "bwin").strip().lower()
    existing = load_stored_feed_events(store_feed_code)
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
        data, err = await _fetch_json_async(url)
        if err:
            return {"ok": False, "added": added, "updated": updated, "total": total_from_api, "error": err}

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
            if for_l2_layer:
                if not bwin_event_id_is_layer_l2(raw_id):
                    continue
            else:
                if not bwin_event_id_is_layer_l1(raw_id):
                    continue
            normalized = _normalize_bwin_item(
                item, sport_name_override=sport_name, feed_provider=store_feed_code
            )
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
        async with _feed_lock(store_feed_code):
            current = load_stored_feed_events(store_feed_code)
            other_sports = [e for e in current if str(e.get("sport_id") or "").strip() != sport_id_str]
            merged = other_sports + [api_by_id[eid] for eid in api_order]
            save_stored_feed_events(store_feed_code, merged)

    return {"ok": True, "added": added, "updated": updated, "total": total_from_api, "error": None}


async def pull_bwin_sport(sport_id: str, sport_name: str, token: str) -> dict:
    """Bwin L1: prematch ids below BWIN_L2_MIN_NUMERIC_EVENT_ID and not ``2:``-prefixed."""
    return await _pull_bwin_prematch_layer(sport_id, sport_name, token, store_feed_code="bwin", for_l2_layer=False)


async def pull_bwin_l2_sport(sport_id: str, sport_name: str, token: str) -> dict:
    """Bwin L2: same API as bwin; high numeric ids (>= 200M) or ``2:``-prefixed ids → feed_data/bwin_l2.json."""
    return await _pull_bwin_prematch_layer(sport_id, sport_name, token, store_feed_code="bwin_l2", for_l2_layer=True)


# Map feed code to its async pull-one-sport function (sport_id, sport_name, token) -> result dict.
_PULL_ONE_SPORT: dict[str, Callable[..., object]] = {
    "bet365": pull_bet365_sport,
    "betfair": pull_betfair_sport,
    "1xbet": pull_1xbet_sport,
    "bwin": pull_bwin_sport,
    "bwin_l2": pull_bwin_l2_sport,
}


async def pull_feed_all_sports_async(
    feed_provider: str,
    sports: list[tuple[str, str]],
    token: str,
    concurrency: int = 5,
) -> dict:
    """
    Pull all sports for one feed in parallel, with a concurrency cap.
    sports: list of (sport_id, sport_name).
    Returns {"ok": bool, "results": [per-sport result dicts], "error": str | None}.
    If any sport fails, ok is False and error is the first error message; results still contain all outcomes.
    """
    feed = (feed_provider or "").strip().lower()
    pull_one = _PULL_ONE_SPORT.get(feed)
    if not pull_one or not sports:
        return {"ok": False, "results": [], "error": "Unsupported feed or no sports"}

    sem = asyncio.Semaphore(concurrency)

    async def run_one(sport_id: str, sport_name: str):
        async with sem:
            return await pull_one(sport_id, sport_name, token)

    results = await asyncio.gather(
        *[run_one(sid, name) for sid, name in sports],
        return_exceptions=True,
    )
    out = []
    first_error = None
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            out.append({"ok": False, "error": str(r), "sport_id": sports[i][0], "sport_name": sports[i][1]})
            if first_error is None:
                first_error = str(r)
        else:
            out.append(r)
    return {
        "ok": first_error is None,
        "results": out,
        "error": first_error,
    }


def ingest_pinnacle_raw_events(
    raw_events: list,
    *,
    sport_id_filter: str | None = None,
    replace: bool = False,
) -> dict:
    """
    Normalize native Pinnacle rows and merge into feed_data/pinnacle.json by valid_id.
    Existing ids are skipped unless replace=True (then stored events for the filter scope are cleared first).
    Optional sport_id_filter limits which rows are considered (e.g. \"29\").
    Does not call APIs. Callers should upsert feed_sports from returned sports_seen.
    """
    global FEED_DATA_DIR
    from backend.pinnacle_feed import FEED_CODE, collect_sports_from_events, normalize_pinnacle_events
    from backend import config as _cfg

    if not FEED_DATA_DIR:
        FEED_DATA_DIR = getattr(_cfg, "FEED_DATA_DIR", None)

    sports_seen = collect_sports_from_events(raw_events)
    normalized = normalize_pinnacle_events(raw_events)
    if sport_id_filter is not None and str(sport_id_filter).strip():
        want = str(sport_id_filter).strip()
        try:
            want = str(int(float(want)))
        except (TypeError, ValueError):
            pass
        normalized = [e for e in normalized if str(e.get("sport_id") or "").strip() == want]
        sports_seen = {k: v for k, v in sports_seen.items() if k == want}

    existing = load_stored_feed_events(FEED_CODE)
    if replace:
        if sport_id_filter is not None and str(sport_id_filter).strip():
            want = str(sport_id_filter).strip()
            try:
                want = str(int(float(want)))
            except (TypeError, ValueError):
                pass
            existing = [e for e in existing if str(e.get("sport_id") or "").strip() != want]
        else:
            existing = []
        save_stored_feed_events(FEED_CODE, existing)

    existing_ids = {str(e.get("valid_id") or "").strip() for e in existing if (e.get("valid_id") or "").strip()}
    added = 0
    skipped = 0
    new_rows: list[dict] = []
    for ev in normalized:
        vid = str(ev.get("valid_id") or "").strip()
        if not vid:
            continue
        if vid in existing_ids:
            skipped += 1
            continue
        new_rows.append(ev)
        existing_ids.add(vid)
        added += 1
    if new_rows:
        merged = list(existing) + new_rows
        save_stored_feed_events(FEED_CODE, merged)
    return {
        "ok": True,
        "added": added,
        "skipped": skipped,
        "total": len(normalized),
        "error": None,
        "feed_provider": FEED_CODE,
        "sports_seen": sports_seen,
        "replaced": bool(replace),
    }


def load_pinnacle_raw_file() -> list:
    """
    Load native Pinnacle JSON for ingest.
    Prefers feed_data/pinnacle_raw.json, else designs/feed_json_examples/pinnacle_raw.json.
    """
    from backend import config

    candidates = []
    feed_data = getattr(config, "FEED_DATA_DIR", None)
    if feed_data:
        candidates.append(Path(feed_data) / "pinnacle_raw.json")
    # Project designs examples (same layout as other feed samples)
    candidates.append(Path(__file__).resolve().parent.parent / "designs" / "feed_json_examples" / "pinnacle_raw.json")
    for path in candidates:
        if not path.exists():
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and isinstance(data.get("events"), list):
                return data["events"]
            if isinstance(data, dict) and isinstance(data.get("results"), list):
                return data["results"]
        except (json.JSONDecodeError, OSError):
            continue
    return []


# ── API-Football (fixtures Phase 1) ─────────────────────────────────────────

API_FOOTBALL_DEFAULT_DAYS_AHEAD = 365
API_FOOTBALL_DATE_CHUNK_DAYS = 14  # from/to window size per request (quota-friendly)


async def _fetch_api_football_json(
    path: str,
    api_key: str,
    params: dict | None = None,
    *,
    base_url: str | None = None,
    timeout: float = 60.0,
) -> tuple[Optional[dict], Optional[str]]:
    """GET path on API-Football with x-apisports-key. Returns (data, error)."""
    from backend import config as _cfg

    key = (api_key or "").strip()
    if not key:
        return (None, "API_FOOTBALL_KEY not set")
    root = (base_url or getattr(_cfg, "API_FOOTBALL_BASE_URL", None) or "https://v3.football.api-sports.io").rstrip("/")
    url = f"{root}/{path.lstrip('/')}"
    headers = {
        "x-apisports-key": key,
        "User-Agent": "PTC-Global-Mapper/1.0",
    }
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params or {}, headers=headers, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            return (data, None)
    except httpx.HTTPStatusError as e:
        body = (e.response.text or "")[:500]
        return (None, f"HTTP {e.response.status_code}: {body}")
    except (httpx.RequestError, json.JSONDecodeError, OSError) as e:
        return (None, str(e))


def _api_football_errors_message(data: dict) -> str | None:
    errs = data.get("errors")
    if not errs:
        return None
    if isinstance(errs, dict) and errs:
        parts = [f"{k}: {v}" for k, v in errs.items()]
        return "; ".join(parts)
    if isinstance(errs, list) and errs:
        return "; ".join(str(x) for x in errs)
    return None


async def _api_football_fetch_all_pages(
    api_key: str, params: dict, *, max_pages: int = 50
) -> tuple[list, Optional[str], int]:
    """Fetch /fixtures for one param set, following paging. Returns (raw items, error, request_count)."""
    raw_items: list = []
    page = 1
    total_pages = 1
    request_count = 0
    while page <= total_pages and page <= max_pages:
        page_params = dict(params)
        if page > 1:
            page_params["page"] = page
        data, err = await _fetch_api_football_json("fixtures", api_key, page_params)
        request_count += 1
        if err:
            return ([], err, request_count)
        if not isinstance(data, dict):
            return ([], "Invalid API response", request_count)
        msg = _api_football_errors_message(data)
        if msg:
            return ([], msg, request_count)
        batch = data.get("response") or []
        if isinstance(batch, list):
            raw_items.extend(batch)
        paging = data.get("paging") or {}
        try:
            total_pages = max(1, int(paging.get("total") or 1))
        except (TypeError, ValueError):
            total_pages = 1
        if not batch:
            break
        page += 1
    return (raw_items, None, request_count)


def _api_football_fixture_is_upcoming(item: dict, *, not_before_date: str) -> bool:
    """Keep fixtures on/after YYYY-MM-DD (UTC date from fixture.date or timestamp)."""
    fixture = item.get("fixture") if isinstance(item.get("fixture"), dict) else {}
    date_s = (fixture.get("date") or "").strip()
    day = ""
    if date_s:
        day = date_s[:10]
    else:
        ts = fixture.get("timestamp")
        if ts is not None:
            try:
                day = datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d")
            except (TypeError, ValueError, OSError):
                day = ""
    if not day:
        return True
    return day >= not_before_date


async def pull_api_football_fixtures(
    api_key: str,
    *,
    days_ahead: int | None = None,
    league_id: str | None = None,
    season: str | None = None,
    replace: bool = False,
) -> dict:
    """
    Pull fixtures from API-Football /fixtures and merge into feed_data/api_football.json.

    Default (no league): from **today (UTC)** through **today + days_ahead** (default 365),
    walking the calendar in from/to chunks so you get all offered future fixtures in that window.

    Optional: league_id + season → that competition season, filtered to from today onward.

    Does not fetch odds. Skips existing valid_ids unless replace=True.
    """
    global FEED_DATA_DIR
    from backend.api_football_feed import FEED_CODE, normalize_api_football_events
    from backend import config as _cfg

    if not FEED_DATA_DIR:
        FEED_DATA_DIR = getattr(_cfg, "FEED_DATA_DIR", None)

    key = (api_key or "").strip()
    if not key:
        return {"ok": False, "added": 0, "skipped": 0, "total": 0, "error": "Please enter API key (or set API_FOOTBALL_KEY in .env)"}

    lid = (league_id or "").strip()
    seas = (season or "").strip()
    today = datetime.now(timezone.utc).date()
    today_s = today.isoformat()

    try:
        horizon = int(days_ahead) if days_ahead is not None else API_FOOTBALL_DEFAULT_DAYS_AHEAD
    except (TypeError, ValueError):
        horizon = API_FOOTBALL_DEFAULT_DAYS_AHEAD
    horizon = max(1, min(horizon, 730))

    raw_items: list = []
    mode = "upcoming"
    requests_used = 0

    if lid and seas:
        mode = "league+season"
        end_s = (today + timedelta(days=horizon)).isoformat()
        params = {"league": lid, "season": seas, "from": today_s, "to": end_s}
        batch, err, n_req = await _api_football_fetch_all_pages(key, params)
        requests_used += n_req
        if err:
            # Some plans reject from/to with league — fall back to full season, filter client-side
            batch, err2, n_req2 = await _api_football_fetch_all_pages(key, {"league": lid, "season": seas})
            requests_used += n_req2
            if err2:
                return {"ok": False, "added": 0, "skipped": 0, "total": 0, "error": err2 or err, "requests_used": requests_used}
            batch = [x for x in batch if isinstance(x, dict) and _api_football_fixture_is_upcoming(x, not_before_date=today_s)]
        raw_items.extend(batch)
    else:
        mode = f"upcoming ({horizon}d)"
        end = today + timedelta(days=horizon)
        chunk = timedelta(days=API_FOOTBALL_DATE_CHUNK_DAYS - 1)
        cursor = today
        while cursor <= end:
            chunk_end = min(cursor + chunk, end)
            params = {"from": cursor.isoformat(), "to": chunk_end.isoformat()}
            batch, err, n_req = await _api_football_fetch_all_pages(key, params)
            requests_used += n_req
            if err:
                # Fallback: day-by-day for this chunk if from/to rejected
                day = cursor
                while day <= chunk_end:
                    day_batch, day_err, n_day = await _api_football_fetch_all_pages(key, {"date": day.isoformat()})
                    requests_used += n_day
                    if day_err:
                        return {
                            "ok": False,
                            "added": 0,
                            "skipped": 0,
                            "total": 0,
                            "error": f"{day_err} (while fetching {day.isoformat()}; earlier: {err})",
                            "requests_used": requests_used,
                        }
                    raw_items.extend(day_batch)
                    day += timedelta(days=1)
            else:
                raw_items.extend(batch)
            cursor = chunk_end + timedelta(days=1)

        raw_items = [
            x for x in raw_items
            if isinstance(x, dict) and _api_football_fixture_is_upcoming(x, not_before_date=today_s)
        ]

    normalized = normalize_api_football_events(raw_items)
    existing = load_stored_feed_events(FEED_CODE)
    if replace:
        existing = []
        save_stored_feed_events(FEED_CODE, existing)

    existing_ids = {str(e.get("valid_id") or "").strip() for e in existing if (e.get("valid_id") or "").strip()}
    added = 0
    skipped = 0
    new_rows: list[dict] = []
    for ev in normalized:
        vid = str(ev.get("valid_id") or "").strip()
        if not vid:
            continue
        if vid in existing_ids:
            skipped += 1
            continue
        new_rows.append(ev)
        existing_ids.add(vid)
        added += 1

    if new_rows:
        async with _feed_lock(FEED_CODE):
            current = load_stored_feed_events(FEED_CODE)
            if replace:
                current = []
            current_ids = {str(e.get("valid_id") or "").strip() for e in current}
            for ev in new_rows:
                eid = str(ev.get("valid_id") or "").strip()
                if eid and eid not in current_ids:
                    current.append(ev)
                    current_ids.add(eid)
            save_stored_feed_events(FEED_CODE, current)

    to_date = (today + timedelta(days=horizon)).isoformat()
    return {
        "ok": True,
        "added": added,
        "skipped": skipped,
        "total": len(normalized),
        "error": None,
        "feed_provider": FEED_CODE,
        "mode": mode,
        "replaced": bool(replace),
        "from_date": today_s,
        "to_date": to_date,
        "requests_used": requests_used,
        "days_ahead": horizon,
    }


def load_api_football_raw_file() -> list:
    """Load native fixtures JSON for offline ingest (array or {response: []})."""
    from backend import config

    candidates = []
    feed_data = getattr(config, "FEED_DATA_DIR", None)
    if feed_data:
        candidates.append(Path(feed_data) / "api_football_raw.json")
    candidates.append(
        Path(__file__).resolve().parent.parent / "designs" / "feed_json_examples" / "api_football_fixtures.json"
    )
    for path in candidates:
        if not path.exists():
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and isinstance(data.get("response"), list):
                return data["response"]
            if isinstance(data, dict) and isinstance(data.get("results"), list):
                return data["results"]
        except (json.JSONDecodeError, OSError):
            continue
    return []


def ingest_api_football_raw_events(raw_events: list, *, replace: bool = False) -> dict:
    """Normalize offline fixtures dump into feed_data/api_football.json (no HTTP)."""
    global FEED_DATA_DIR
    from backend.api_football_feed import FEED_CODE, normalize_api_football_events
    from backend import config as _cfg

    if not FEED_DATA_DIR:
        FEED_DATA_DIR = getattr(_cfg, "FEED_DATA_DIR", None)

    normalized = normalize_api_football_events(raw_events)
    existing = load_stored_feed_events(FEED_CODE)
    if replace:
        existing = []
        save_stored_feed_events(FEED_CODE, existing)
    existing_ids = {str(e.get("valid_id") or "").strip() for e in existing if (e.get("valid_id") or "").strip()}
    added = 0
    skipped = 0
    new_rows: list[dict] = []
    for ev in normalized:
        vid = str(ev.get("valid_id") or "").strip()
        if not vid:
            continue
        if vid in existing_ids:
            skipped += 1
            continue
        new_rows.append(ev)
        existing_ids.add(vid)
        added += 1
    if new_rows:
        merged = list(existing) + new_rows
        save_stored_feed_events(FEED_CODE, merged)
    return {
        "ok": True,
        "added": added,
        "skipped": skipped,
        "total": len(normalized),
        "error": None,
        "feed_provider": FEED_CODE,
        "replaced": bool(replace),
    }


async def pull_api_football_odds_catalogs(api_key: str) -> dict:
    """
    Phase 2: pull /odds/bets and /odds/bookmakers into feed_data catalogs.

    Bets → market mapper (feed_market_id = bet.id, once for whole feed).
    Bookmakers → reference labels for nested odds later (not separate feeds).
    """
    from backend.api_football_feed import (
        FEED_CODE,
        normalize_odds_id_name_list,
        save_odds_catalog,
    )

    key = (api_key or "").strip()
    if not key:
        return {
            "ok": False,
            "error": "Please enter API key (or set API_FOOTBALL_KEY in .env)",
            "bets_count": 0,
            "bookmakers_count": 0,
            "requests_used": 0,
        }

    requests_used = 0
    bets_data, bets_err = await _fetch_api_football_json("odds/bets", key)
    requests_used += 1
    if bets_err:
        return {
            "ok": False,
            "error": f"odds/bets: {bets_err}",
            "bets_count": 0,
            "bookmakers_count": 0,
            "requests_used": requests_used,
        }
    if isinstance(bets_data, dict):
        msg = _api_football_errors_message(bets_data)
        if msg:
            return {
                "ok": False,
                "error": f"odds/bets: {msg}",
                "bets_count": 0,
                "bookmakers_count": 0,
                "requests_used": requests_used,
            }

    books_data, books_err = await _fetch_api_football_json("odds/bookmakers", key)
    requests_used += 1
    if books_err:
        return {
            "ok": False,
            "error": f"odds/bookmakers: {books_err}",
            "bets_count": 0,
            "bookmakers_count": 0,
            "requests_used": requests_used,
        }
    if isinstance(books_data, dict):
        msg = _api_football_errors_message(books_data)
        if msg:
            return {
                "ok": False,
                "error": f"odds/bookmakers: {msg}",
                "bets_count": 0,
                "bookmakers_count": 0,
                "requests_used": requests_used,
            }

    bets = normalize_odds_id_name_list(bets_data if isinstance(bets_data, (dict, list)) else [])
    books = normalize_odds_id_name_list(books_data if isinstance(books_data, (dict, list)) else [])
    if not bets:
        return {
            "ok": False,
            "error": "odds/bets returned no markets",
            "bets_count": 0,
            "bookmakers_count": len(books),
            "requests_used": requests_used,
        }

    save_odds_catalog("bets", bets)
    save_odds_catalog("bookmakers", books)
    return {
        "ok": True,
        "error": None,
        "feed_provider": FEED_CODE,
        "bets_count": len(bets),
        "bookmakers_count": len(books),
        "requests_used": requests_used,
        "mode": "odds catalogs",
    }


async def fetch_api_football_fixture_odds(api_key: str, fixture_id: str) -> Optional[dict]:
    """
    GET /odds?fixture={id} — nested bookmakers → bets → values.
    Returns full API JSON on success, else None. Prefer fetch_api_football_fixture_odds_result for errors.
    """
    data, err = await fetch_api_football_fixture_odds_result(api_key, fixture_id)
    return data if not err else None


async def fetch_api_football_fixture_odds_result(api_key: str, fixture_id: str) -> tuple[Optional[dict], Optional[str]]:
    """GET /odds?fixture={id}. Returns (data, error_message)."""
    key = (api_key or "").strip()
    fid = str(fixture_id or "").strip()
    if not key:
        return (None, "API_FOOTBALL_KEY not set (add to .env or pass api_token)")
    if not fid:
        return (None, "fixture id missing")
    data, err = await _fetch_api_football_json("odds", key, {"fixture": fid})
    if err:
        return (None, err)
    if not isinstance(data, dict):
        return (None, "Invalid API response")
    msg = _api_football_errors_message(data)
    if msg:
        return (None, msg)
    resp = data.get("response")
    if not isinstance(resp, list) or not resp:
        return (None, "API returned no odds for this fixture (may not be published yet)")
    books = (resp[0] or {}).get("bookmakers") if isinstance(resp[0], dict) else None
    if not books:
        return (None, "API returned no bookmakers for this fixture (may not be published yet)")
    return (data, None)


