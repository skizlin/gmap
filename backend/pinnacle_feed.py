"""
Pinnacle feed helpers (Phase 1).

Sport + competition + event use real IDs from the feed.
Teams have no IDs: synthetic feed keys include underage scope so senior and U19
clubs with the same runner name do not collide.

Team feed_id format:
  {normalized_runner}|u:{underage}|s:{sport_id}
  underage 0 = senior / none; 19 = U19, etc.

Event valid_id: parent_id when set (inplay → prematch), else event_id.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from typing import Any

FEED_CODE = "pinnacle"

# Native Pinnacle sport_id → display name (official / commonly documented ids).
# Ingest also auto-adds any sport_id seen in a dump that is missing here.
KNOWN_PINNACLE_SPORTS: dict[str, str] = {
    "1": "Badminton",
    "2": "Bandy",
    "3": "Baseball",
    "4": "Basketball",
    "5": "Beach Volleyball",
    "6": "Boxing",
    "8": "Cricket",
    "9": "Curling",
    "10": "Darts",
    "12": "E Sports",
    "13": "Field Hockey",
    "14": "Floorball",
    "15": "Football",  # American football in Pinnacle naming
    "16": "Futsal",
    "17": "Golf",
    "18": "Handball",
    "19": "Hockey",
    "20": "Horse Racing",
    "22": "Mixed Martial Arts",
    "26": "Rugby League",
    "27": "Rugby Union",
    "28": "Snooker",
    "29": "Soccer",
    "30": "Softball",
    "31": "Squash",
    "32": "Table Tennis",
    "33": "Tennis",
    "34": "Volleyball",
    "35": "Water Polo",
    "36": "Aussie Rules",
    "37": "Alpine Skiing",
    "39": "Biathlon",
    "40": "Cycling",
    "41": "Formula 1",
    "44": "Chess",
    "45": "Entertainment",
}

# Pinnacle sport_name (or KNOWN name) → our domain sports.csv name
PINNACLE_TO_DOMAIN_SPORT_NAME: dict[str, str] = {
    "soccer": "Football",
    "football": "American Football",  # Pinnacle "Football" = NFL/NCAA
    "hockey": "Ice Hockey",
    "ice hockey": "Ice Hockey",
    "e sports": "Esports",
    "esports": "Esports",
    "mixed martial arts": "MMA/UFC",
    "mma": "MMA/UFC",
    "aussie rules": "Australian Rules",
    "australian rules": "Australian Rules",
    "formula 1": "Formula 1",
    "f1": "Formula 1",
}

_U_AGE_RE = re.compile(r"\bU\s*[-.]?\s*(\d{1,2})\b", re.IGNORECASE)


def domain_sport_name_for_pinnacle(sport_name: str | None, sport_id: Any = None) -> str | None:
    """Best domain sports.csv name for a Pinnacle sport label / id."""
    sid = str(sport_id).strip() if sport_id is not None else ""
    label = (sport_name or "").strip() or KNOWN_PINNACLE_SPORTS.get(sid, "")
    if not label:
        return None
    key = label.casefold()
    if key in PINNACLE_TO_DOMAIN_SPORT_NAME:
        return PINNACLE_TO_DOMAIN_SPORT_NAME[key]
    return label


def collect_sports_from_events(events: list) -> dict[str, str]:
    """sport_id → sport_name from raw or normalized event rows."""
    out: dict[str, str] = {}
    for item in events or []:
        if not isinstance(item, dict):
            continue
        sid_raw = item.get("sport_id")
        if sid_raw is None or str(sid_raw).strip() == "":
            continue
        try:
            sid = str(int(float(sid_raw)))
        except (TypeError, ValueError):
            sid = str(sid_raw).strip()
        name = (item.get("sport_name") or item.get("sport") or "").strip()
        if not name:
            name = KNOWN_PINNACLE_SPORTS.get(sid, f"Sport {sid}")
        if sid not in out or (name and not out[sid].startswith("Sport ")):
            out[sid] = name
    return out


def normalize_match_text(s: str | None) -> str:
    """Case-fold and strip diacritics for stable name keys."""
    s = (s or "").strip()
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return " ".join(s.casefold().split())


def detect_underage_code(*texts: str | None) -> int:
    """
    First Uxx found in the given texts (runner preferred before league).
    Returns 0 when no underage marker.
    """
    for text in texts:
        if not text:
            continue
        m = _U_AGE_RE.search(str(text))
        if not m:
            continue
        try:
            n = int(m.group(1))
        except (TypeError, ValueError):
            continue
        if 7 <= n <= 30:
            return n
    return 0


def team_feed_id(runner_name: str | None, sport_id: Any, underage: int | None = None) -> str | None:
    """Synthetic team key for entity_feed_mappings (name-only Pinnacle runners)."""
    nm = normalize_match_text(runner_name)
    if not nm:
        return None
    sid = str(sport_id).strip() if sport_id is not None else ""
    if not sid:
        return None
    try:
        u = int(underage) if underage is not None else 0
    except (TypeError, ValueError):
        u = 0
    if u < 0:
        u = 0
    return f"{nm}|u:{u}|s:{sid}"


def suggested_team_display_name(runner_name: str | None, underage: int) -> str:
    """Display / create suggestion: append Uxx when underage and not already in the name."""
    name = (runner_name or "").strip()
    if not name:
        return ""
    if underage and underage > 0:
        if not _U_AGE_RE.search(name):
            return f"{name} U{underage}"
    return name


def canonical_event_id(item: dict) -> str:
    """Prefer parent_id (prematch) when inplay row references it."""
    parent = item.get("parent_id")
    if parent is not None and str(parent).strip() not in ("", "0", "null", "None"):
        return str(parent).strip()
    eid = item.get("event_id")
    return str(eid).strip() if eid is not None else ""


def _parse_starts(starts: Any) -> str:
    """Normalize starts to 'YYYY-MM-DD HH:MM:SS' UTC display used by feeder events."""
    if starts is None:
        return "—"
    s = str(starts).strip()
    if not s:
        return "—"
    # ISO with Z or offset
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        pass
    # Already space-separated
    if len(s) >= 19 and s[10] == " ":
        return s[:19]
    if len(s) >= 16 and "T" in s:
        return s.replace("T", " ")[:19]
    return s


def is_raw_pinnacle_item(item: dict) -> bool:
    """True when payload looks like native Pinnacle row (not yet our feeder shape)."""
    if not isinstance(item, dict):
        return False
    if (item.get("feed_provider") or "").strip().lower() == FEED_CODE and item.get("valid_id") is not None:
        if "runner_home" not in item and "runner_away" not in item:
            return False
    return "event_id" in item and ("runner_home" in item or "league_id" in item)


def normalize_pinnacle_item(item: dict) -> dict | None:
    """
    Convert one native Pinnacle event object to the shared feeder event shape.
    Returns None if event_id / sport cannot be resolved.
    """
    if not isinstance(item, dict):
        return None
    # Already normalized stored row: keep as-is (ensure feed_provider)
    if (item.get("feed_provider") or "").strip().lower() == FEED_CODE and item.get("valid_id") and not is_raw_pinnacle_item(item):
        out = dict(item)
        out["feed_provider"] = FEED_CODE
        return out

    sport_id = item.get("sport_id")
    if sport_id is None or str(sport_id).strip() == "":
        return None
    sport_id_s = str(sport_id).strip()
    try:
        sport_id_s = str(int(float(sport_id_s)))
    except (TypeError, ValueError):
        pass

    valid_id = canonical_event_id(item)
    if not valid_id:
        return None

    league_id = item.get("league_id")
    league_name = (item.get("league_name") or "").strip()
    home = (item.get("runner_home") or "").strip()
    away = (item.get("runner_away") or "").strip()

    u_home = detect_underage_code(home, league_name)
    u_away = detect_underage_code(away, league_name)
    # Same competition underage applies to both sides when runners lack Uxx
    if u_home == 0 and u_away == 0:
        u_comp = detect_underage_code(league_name)
        u_home = u_comp
        u_away = u_comp
    elif u_home == 0:
        u_home = detect_underage_code(league_name)
    elif u_away == 0:
        u_away = detect_underage_code(league_name)

    home_id = team_feed_id(home, sport_id_s, u_home)
    away_id = team_feed_id(away, sport_id_s, u_away)

    source_event_id = item.get("event_id")
    parent_id = item.get("parent_id")
    live_status = item.get("live_status")

    return {
        "feed_provider": FEED_CODE,
        "valid_id": valid_id,
        "domain_id": None,
        "raw_home_name": home,
        "raw_away_name": away,
        "raw_home_id": home_id,
        "raw_away_id": away_id,
        "raw_league_name": league_name or None,
        "raw_league_id": str(league_id).strip() if league_id is not None and str(league_id).strip() else None,
        "category": "",
        "category_id": None,
        "start_time": _parse_starts(item.get("starts")),
        "time_status": str(live_status).strip() if live_status is not None else "",
        "sport": (item.get("sport_name") or "").strip() or f"Sport {sport_id_s}",
        "sport_id": sport_id_s,
        "betradar_id": None,
        "is_outright": False,
        "market_name": None,
        "is_mainbook": False,
        "updated_at": (item.get("timestamp") or None),
        "mapping_status": "UNMAPPED",
        "status": "Open",
        "markets_count": 0,
        # Pinnacle-specific (kept for Phase 2 / debugging; ignored by most UI)
        "pinnacle_source_event_id": str(source_event_id).strip() if source_event_id is not None else valid_id,
        "pinnacle_parent_id": str(parent_id).strip() if parent_id is not None and str(parent_id).strip() not in ("", "0") else None,
        "home_underage_id": u_home or None,
        "away_underage_id": u_away or None,
        "suggested_home_name": suggested_team_display_name(home, u_home),
        "suggested_away_name": suggested_team_display_name(away, u_away),
    }


def normalize_pinnacle_events(raw_events: list) -> list[dict]:
    """Normalize a list of raw or stored events; drop invalid rows; dedupe by valid_id.

    When prematch and inplay share a canonical id, keep the prematch row (no parent_id).
    """
    by_id: dict[str, dict] = {}
    for item in raw_events or []:
        if not isinstance(item, dict):
            continue
        ev = normalize_pinnacle_item(item)
        if not ev:
            continue
        vid = str(ev.get("valid_id") or "").strip()
        if not vid:
            continue
        existing = by_id.get(vid)
        if existing is None:
            by_id[vid] = ev
            continue
        # Prefer prematch (no parent) over inplay child when both collapse to same id
        new_is_child = bool(ev.get("pinnacle_parent_id"))
        old_is_child = bool(existing.get("pinnacle_parent_id"))
        if old_is_child and not new_is_child:
            by_id[vid] = ev
        # else keep existing (already prematch, or both children)
    return list(by_id.values())
