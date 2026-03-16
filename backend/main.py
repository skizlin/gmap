from __future__ import annotations

import asyncio
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json
import os
from pathlib import Path
from datetime import date, datetime, timedelta, timezone

# Initialize App
app = FastAPI(title="PTC Global Mapper")

# Setup Paths (from config; config ensures data dirs exist)
from backend import config
BASE_DIR = config.BASE_DIR
TEMPLATES_DIR = config.TEMPLATES_DIR
STATIC_DIR = config.STATIC_DIR
DATA_DIR = config.DATA_DIR
PROJECT_ROOT = config.PROJECT_ROOT
FEED_JSON_DIR = config.FEED_JSON_DIR
FEED_DATA_DIR = config.FEED_DATA_DIR
DATA_COUNTRIES_DIR = config.DATA_COUNTRIES_DIR

# Feed pull module uses this for stored feed data (e.g. bet365 from API)
from backend import feed_pull
feed_pull.FEED_DATA_DIR = FEED_DATA_DIR
DATA_MARKETS_DIR = config.DATA_MARKETS_DIR
COUNTRY_CODE_NONE = config.COUNTRY_CODE_NONE

# Schema constants (alias with leading _ for internal use in this module)
_ENTITY_FIELDS = config.ENTITY_FIELDS
_ENTITY_FEED_MAPPING_FIELDS = config.ENTITY_FEED_MAPPING_FIELDS
_DOMAIN_EVENT_FIELDS = config.DOMAIN_EVENT_FIELDS
_MAPPING_FIELDS = config.MAPPING_FIELDS
_MARKET_TYPE_MAPPING_FIELDS = config.MARKET_TYPE_MAPPING_FIELDS
_MARKET_TEMPLATE_FIELDS = config.MARKET_TEMPLATE_FIELDS
_BRANDS_FIELDS = config.BRANDS_FIELDS

# Path constants
DOMAIN_EVENTS_PATH = config.DOMAIN_EVENTS_PATH
EVENT_MAPPINGS_PATH = config.EVENT_MAPPINGS_PATH
ENTITY_FEED_MAPPINGS_PATH = config.ENTITY_FEED_MAPPINGS_PATH
SPORT_FEED_MAPPINGS_PATH = config.SPORT_FEED_MAPPINGS_PATH
MARKET_TEMPLATES_PATH = config.MARKET_TEMPLATES_PATH
MARKET_PERIOD_TYPE_PATH = config.MARKET_PERIOD_TYPE_PATH
MARKET_SCORE_TYPE_PATH = config.MARKET_SCORE_TYPE_PATH
MARKET_GROUPS_PATH = config.MARKET_GROUPS_PATH
MARKET_TYPE_MAPPINGS_PATH = config.MARKET_TYPE_MAPPINGS_PATH
MARKET_OUTCOMES_PATH = config.MARKET_OUTCOMES_PATH
COUNTRIES_PATH = config.COUNTRIES_PATH
PARTICIPANT_TYPE_PATH = config.PARTICIPANT_TYPE_PATH
UNDERAGE_CATEGORIES_PATH = config.UNDERAGE_CATEGORIES_PATH
LANGUAGES_PATH = config.LANGUAGES_PATH
TRANSLATIONS_PATH = config.TRANSLATIONS_PATH
BRANDS_PATH = config.BRANDS_PATH
PARTNERS_PATH = config.PARTNERS_PATH
_PARTNERS_FIELDS = config.PARTNERS_FIELDS
FEED_SPORTS_PATH = config.FEED_SPORTS_PATH
FEED_TIME_STATUSES_PATH = getattr(config, "FEED_TIME_STATUSES_PATH", None) or (config.DATA_DIR / "feed_time_statuses.csv")
FEED_LAST_PULL_PATH = getattr(config, "FEED_LAST_PULL_PATH", None) or (config.DATA_DIR / "feed_last_pull.csv")
FEEDER_CONFIG_PATH = config.FEEDER_CONFIG_PATH
FEEDER_INCIDENTS_PATH = config.FEEDER_INCIDENTS_PATH
FEEDER_EVENT_NOTES_PATH = config.FEEDER_EVENT_NOTES_PATH
FEEDER_IGNORED_EVENTS_PATH = getattr(config, "FEEDER_IGNORED_EVENTS_PATH", None)
FEEDER_EVENT_LOG_PATH = getattr(config, "FEEDER_EVENT_LOG_PATH", None)
NOTES_PATH = config.NOTES_PATH
NOTES_PATH_LEGACY = getattr(config, "NOTES_PATH_LEGACY", None)  # optional one-time move from data/ to data/notes/
EVENT_NAVIGATOR_NOTES_PATH = getattr(config, "EVENT_NAVIGATOR_NOTES_PATH", None)
NOTIFICATIONS_PATH = getattr(config, "NOTIFICATIONS_PATH", None)
MARGIN_TEMPLATES_PATH = config.MARGIN_TEMPLATES_PATH
MARGIN_TEMPLATE_COMPETITIONS_PATH = config.MARGIN_TEMPLATE_COMPETITIONS_PATH
# RBAC
RBAC_USERS_PATH = config.RBAC_USERS_PATH
RBAC_ROLES_PATH = config.RBAC_ROLES_PATH
RBAC_USER_ROLES_PATH = config.RBAC_USER_ROLES_PATH
RBAC_ROLE_PERMISSIONS_PATH = config.RBAC_ROLE_PERMISSIONS_PATH
RBAC_USER_BRANDS_PATH = config.RBAC_USER_BRANDS_PATH
RBAC_AUDIT_LOG_PATH = config.RBAC_AUDIT_LOG_PATH
_RBAC_USERS_FIELDS = config.RBAC_USERS_FIELDS
_RBAC_ROLES_FIELDS = config.RBAC_ROLES_FIELDS
_RBAC_USER_ROLES_FIELDS = config.RBAC_USER_ROLES_FIELDS
_RBAC_ROLE_PERMISSIONS_FIELDS = config.RBAC_ROLE_PERMISSIONS_FIELDS
_RBAC_USER_BRANDS_FIELDS = config.RBAC_USER_BRANDS_FIELDS
_RBAC_AUDIT_LOG_FIELDS = config.RBAC_AUDIT_LOG_FIELDS

# Mount Static & Templates
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


def _ensure_rbac_csv_if_missing(path: Path, fieldnames: list[str]) -> None:
    """If path does not exist, create it with CSV header only (structure from config). Used so RBAC data is not in repo and is created empty on first deploy."""
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()


@app.on_event("startup")
def _ensure_rbac_data_structure() -> None:
    """Create RBAC CSV files with headers only if they don't exist. Admins and roles are not in repo; each env (local/server) has its own data. Structure comes from config."""
    _ensure_rbac_csv_if_missing(RBAC_USERS_PATH, list(config.RBAC_USERS_FIELDS))
    _ensure_rbac_csv_if_missing(RBAC_ROLES_PATH, list(config.RBAC_ROLES_FIELDS))
    _ensure_rbac_csv_if_missing(RBAC_USER_ROLES_PATH, list(config.RBAC_USER_ROLES_FIELDS))
    _ensure_rbac_csv_if_missing(RBAC_ROLE_PERMISSIONS_PATH, list(config.RBAC_ROLE_PERMISSIONS_FIELDS))
    _ensure_rbac_csv_if_missing(RBAC_USER_BRANDS_PATH, list(config.RBAC_USER_BRANDS_FIELDS))
    _ensure_rbac_csv_if_missing(RBAC_AUDIT_LOG_PATH, list(config.RBAC_AUDIT_LOG_FIELDS))


def _parse_start_time(s: str | None) -> datetime | None:
    """Parse start_time string to datetime (naive UTC). Returns None if invalid."""
    if not s or not s.strip():
        return None
    s = s.strip()
    # Try ISO-style first (fromisoformat handles many variants)
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt.replace(tzinfo=None) if dt.tzinfo else dt
    except (ValueError, TypeError):
        pass
    # Try strptime with common formats (use slice so string length matches format)
    for fmt, max_len in (
        ("%Y-%m-%dT%H:%M:%S", 19),
        ("%Y-%m-%dT%H:%M", 16),
        ("%Y-%m-%d %H:%M:%S", 19),
        ("%Y-%m-%d %H:%M", 16),
        ("%d/%m/%Y %H:%M", 16),
        ("%d/%m/%Y", 10),
    ):
        try:
            dt = datetime.strptime(s[:max_len], fmt)
            return dt
        except (ValueError, TypeError):
            pass
    return None


def _feeder_event_start_time_sort_key(e: dict, ascending: bool) -> tuple:
    """Sort key for feeder events by start_time. Valid times sorted by dt; invalid/empty always at end."""
    dt = _parse_start_time(e.get("start_time"))
    if dt is not None:
        return (0, dt) if ascending else (0, -dt.timestamp())
    return (1, 0)  # invalid/missing at end in both directions


def _domain_event_start_time_sort_key(ev: dict, ascending: bool) -> tuple:
    """Sort key for domain events by start_time. Same semantics as feeder (valid first, invalid at end)."""
    dt = _parse_start_time(ev.get("start_time"))
    if dt is not None:
        return (0, dt) if ascending else (0, -dt.timestamp())
    return (1, 0)


def _format_start_time(s: str | None) -> str:
    """Format start_time for display (DD/MM/YYYY HH:mm). Returns '' if invalid."""
    dt = _parse_start_time(s)
    return dt.strftime("%d/%m/%Y %H:%M") if dt else (s or "")


def _date_range_from_param(
    date_str: str | None,
    date_from_str: str | None = None,
    date_to_str: str | None = None,
) -> tuple[date, date] | None:
    """
    Parse date filter param into (start_date, end_date) in UTC for filtering events by start_time.
    date_str can be: today, tomorrow, yesterday, next_7_days, last_7_days, this_month, next_month,
    or a single date YYYY-MM-DD. For 'custom', pass date_from_str and date_to_str (YYYY-MM-DD).
    Returns None for empty or invalid (no date filter).
    """
    if not date_str or not (s := date_str.strip()):
        return None
    s = s.strip().lower()
    if s == "custom":
        from_s = (date_from_str or "").strip()[:10]
        to_s = (date_to_str or "").strip()[:10]
        if from_s and to_s:
            try:
                d_from = datetime.strptime(from_s, "%Y-%m-%d").date()
                d_to = datetime.strptime(to_s, "%Y-%m-%d").date()
                if d_from <= d_to:
                    return (d_from, d_to)
                return (d_to, d_from)
            except (ValueError, TypeError):
                pass
        return None
    now = datetime.now(timezone.utc)
    today = now.date()
    if s == "today":
        return (today, today)
    if s == "tomorrow":
        t = today + timedelta(days=1)
        return (t, t)
    if s == "yesterday":
        y = today - timedelta(days=1)
        return (y, y)
    if s == "next_7_days":
        end = today + timedelta(days=6)
        return (today, end)
    if s == "last_7_days":
        start = today - timedelta(days=6)
        return (start, today)
    if s == "this_month":
        start = today.replace(day=1)
        # last day of current month
        if today.month == 12:
            end = today.replace(month=12, day=31)
        else:
            end = (today.replace(month=today.month + 1, day=1) - timedelta(days=1))
        return (start, end)
    if s == "next_month":
        if today.month == 12:
            start = today.replace(year=today.year + 1, month=1, day=1)
        else:
            start = today.replace(month=today.month + 1, day=1)
        if start.month == 12:
            end = start.replace(day=31)
        else:
            end = (start.replace(month=start.month + 1, day=1) - timedelta(days=1))
        return (start, end)
    # Single date YYYY-MM-DD
    try:
        d = datetime.strptime(s[:10], "%Y-%m-%d").date()
        return (d, d)
    except (ValueError, TypeError):
        return None


def _start_time_past(s: str | None) -> bool:
    """True if start_time is in the past (for red styling)."""
    dt = _parse_start_time(s)
    return dt < datetime.utcnow() if dt else False


templates.env.filters["format_start_time"] = lambda s: _format_start_time(s)
templates.env.filters["start_time_past"] = lambda s: _start_time_past(s)




def _format_entity_date(s: str | None) -> str:
    """Format created_at/updated_at ISO string for display (DD/MM/YYYY HH:mm). Returns '—' if empty."""
    if not s or not str(s).strip():
        return "—"
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00").strip())
        return dt.strftime("%d/%m/%Y %H:%M")
    except (ValueError, TypeError):
        return "—"


templates.env.filters["format_entity_date"] = lambda s: _format_entity_date(s)

from fastapi import Query
from typing import List

# Known feed providers (drives the filter dropdown)
KNOWN_FEEDS = ["bet365", "betfair", "1xbet", "bwin"]

# DUMMY DATA FOR PROTOTYPE
from backend.mock_data import load_all_mock_data
DUMMY_EVENTS = load_all_mock_data()

# Feed sports: loaded from feed_sports.csv; (feed_code, feed_sport_id) -> name; feed_code -> list of {id, name}
_FEED_SPORTS_LOOKUP: dict[tuple[str, str], str] = {}
_FEED_SPORTS_BY_FEED: dict[str, list[dict]] = {}
def _load_feed_sports() -> None:
    """Load feed_sports.csv into _FEED_SPORTS_LOOKUP and _FEED_SPORTS_BY_FEED."""
    global _FEED_SPORTS_LOOKUP, _FEED_SPORTS_BY_FEED
    _FEED_SPORTS_LOOKUP = {}
    _FEED_SPORTS_BY_FEED = {f: [] for f in KNOWN_FEEDS}
    if not FEED_SPORTS_PATH.exists():
        return
    with open(FEED_SPORTS_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            feed = (row.get("feed_provider") or "").strip().lower()
            raw_sid = row.get("feed_sport_id")
            sid = str(int(raw_sid)).strip() if isinstance(raw_sid, (int, float)) else (raw_sid or "").strip()
            name = (row.get("feed_sport_name") or "").strip()
            if not feed:
                continue
            key = (feed, sid)
            _FEED_SPORTS_LOOKUP[key] = name or sid or "—"
            if feed not in _FEED_SPORTS_BY_FEED:
                _FEED_SPORTS_BY_FEED[feed] = []
            if not any(x.get("id") == sid for x in _FEED_SPORTS_BY_FEED[feed]):
                _FEED_SPORTS_BY_FEED[feed].append({"id": sid, "name": name or sid or "—"})
    for feed in _FEED_SPORTS_BY_FEED:
        _FEED_SPORTS_BY_FEED[feed].sort(key=lambda x: (x["name"].lower(), x["id"]))

def _get_feed_sport_name(feed_provider: str, sport_id: str | int | None, fallback_name: str | None = None) -> str:
    """Resolve display name for (feed, feed_sport_id) from feed_sports.csv. Fallback: fallback_name, else 'Sport {id}'."""
    if not _FEED_SPORTS_LOOKUP:
        _load_feed_sports()
    if sport_id is None or (isinstance(sport_id, str) and not sport_id.strip()):
        sid_str = ""
    else:
        sid_str = str(int(sport_id)) if isinstance(sport_id, (int, float)) else str(sport_id).strip()
    feed = (feed_provider or "").strip().lower()
    if feed and sid_str:
        key = (feed, sid_str)
        if key in _FEED_SPORTS_LOOKUP:
            return _FEED_SPORTS_LOOKUP[key]
    if fallback_name and (fallback_name or "").strip():
        return (fallback_name or "").strip()
    return f"Sport {sid_str}" if sid_str else "—"

def _get_sports_for_feed(feed_provider: str, events_for_feed: list[dict] | None = None) -> list[str]:
    """Return sorted list of sport names for this feed: from feed_sports.csv, or distinct from events if CSV empty."""
    if not _FEED_SPORTS_BY_FEED:
        _load_feed_sports()
    feed = (feed_provider or "").strip().lower()
    if feed and _FEED_SPORTS_BY_FEED.get(feed):
        return [x["name"] for x in _FEED_SPORTS_BY_FEED[feed]]
    if events_for_feed:
        return sorted({e.get("sport") or "" for e in events_for_feed if e.get("sport")})
    return []


def _enrich_feed_events_sport_names() -> None:
    """Fill event['sport'] from feed_sports.csv (or keep existing / 'Sport {id}'). Call before using DUMMY_EVENTS in feeder views."""
    _load_feed_sports()
    for e in DUMMY_EVENTS:
        e["sport"] = _get_feed_sport_name(e.get("feed_provider") or "", e.get("sport_id"), e.get("sport"))


def _load_feed_sports_rows() -> list[dict]:
    """Load feed_sports.csv as list of dicts (feed_provider, feed_sport_id, feed_sport_name) for Entities UI."""
    if not FEED_SPORTS_PATH.exists():
        return []
    with open(FEED_SPORTS_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _save_feed_sports(rows: list[dict]) -> None:
    """Overwrite feed_sports.csv with rows. Each row: feed_provider, feed_sport_id, feed_sport_name."""
    fieldnames = ["feed_provider", "feed_sport_id", "feed_sport_name"]
    with open(FEED_SPORTS_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    global _FEED_SPORTS_LOOKUP, _FEED_SPORTS_BY_FEED
    _FEED_SPORTS_LOOKUP = {}
    _FEED_SPORTS_BY_FEED = {}
    _load_feed_sports()

# Derive per-feed sport lists (fallback when feed_sports empty); will be overridden by feed_sports when loaded
KNOWN_SPORTS = sorted({e["sport"] for e in DUMMY_EVENTS if e.get("sport")})
SPORTS_BY_FEED = {
    feed: sorted({e["sport"] for e in DUMMY_EVENTS if e["feed_provider"] == feed and e.get("sport")})
    for feed in KNOWN_FEEDS
}


# --- API Endpoints ---

from typing import Optional
import uuid, csv, json
import difflib

from backend.schemas import (
    CreateDomainEventRequest,
    CreateEntityRequest,
    UpdateEntityNameRequest,
    UpdateEntityJurisdictionRequest,
    UpdateMarketRequest,
    CreatePartnerRequest,
    UpdatePartnerRequest,
    CreateBrandRequest,
    UpdateBrandRequest,
    CreateRbacUserRequest,
    UpdateRbacUserRequest,
    AssignUserRolesRequest,
    CreateRbacRoleRequest,
    UpdateRbacRoleRequest,
    UpdateRolePermissionsRequest,
    CreateMarketGroupRequest,
    MarketTypeMappingItem,
    SaveMarketTypeMappingsRequest,
    CountryUpsertRequest,
    LanguageUpsertRequest,
    TranslationUpsertRequest,
    CreateMarginTemplateRequest,
    UpdateMarginTemplateRequest,
    AssignCompetitionToTemplateRequest,
    CopyFromBrandRequest,
)




def _load_feeds() -> list[dict]:
    """Load feeds.csv into memory."""
    path = config.FEEDS_PATH
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["domain_id"] = int(r["domain_id"])
    return rows


_FEEDER_CONFIG_FIELDS = ["level", "sport_id", "category_id", "league_id", "feed_provider_id", "setting_key", "value"]
_FEEDER_INCIDENT_FIELDS = ["sport_id", "feed_provider_id", "incident_type", "enabled", "sort_order"]


def _load_feeder_config() -> list[dict]:
    """Load feeder_config.csv (level, sport_id, category_id, league_id, feed_provider_id, setting_key, value)."""
    if not FEEDER_CONFIG_PATH.exists():
        return []
    rows = []
    with open(FEEDER_CONFIG_PATH, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            for key in ("sport_id", "category_id", "league_id", "feed_provider_id"):
                if r.get(key) and r[key].strip():
                    try:
                        r[key] = int(r[key])
                    except (ValueError, TypeError):
                        r[key] = None
                else:
                    r[key] = None
            rows.append(r)
    return rows


def _load_feeder_incidents() -> list[dict]:
    """Load feeder_incidents.csv (sport_id, feed_provider_id, incident_type, enabled, sort_order)."""
    if not FEEDER_INCIDENTS_PATH.exists():
        return []
    rows = []
    with open(FEEDER_INCIDENTS_PATH, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            for key in ("sport_id", "feed_provider_id", "sort_order"):
                if r.get(key) and r[key].strip():
                    try:
                        r[key] = int(r[key])
                    except (ValueError, TypeError):
                        r[key] = None
                else:
                    r[key] = None if key != "sort_order" else 0
            r["enabled"] = (r.get("enabled") or "").strip() in ("1", "true", "yes")
            rows.append(r)
    return rows


def _save_feeder_config(rows: list[dict]) -> None:
    """Overwrite feeder_config.csv with the given rows."""
    with open(FEEDER_CONFIG_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=_FEEDER_CONFIG_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({
                "level": (r.get("level") or "").strip(),
                "sport_id": r.get("sport_id") if r.get("sport_id") is not None else "",
                "category_id": r.get("category_id") if r.get("category_id") is not None else "",
                "league_id": r.get("league_id") if r.get("league_id") is not None else "",
                "feed_provider_id": r.get("feed_provider_id") if r.get("feed_provider_id") is not None else "",
                "setting_key": (r.get("setting_key") or "").strip(),
                "value": (r.get("value") or "").strip(),
            })


def _save_feeder_incidents(rows: list[dict]) -> None:
    """Overwrite feeder_incidents.csv with the given rows."""
    with open(FEEDER_INCIDENTS_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=_FEEDER_INCIDENT_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({
                "sport_id": r.get("sport_id") if r.get("sport_id") is not None else "",
                "feed_provider_id": r.get("feed_provider_id") if r.get("feed_provider_id") is not None else "",
                "incident_type": (r.get("incident_type") or "").strip(),
                "enabled": "1" if r.get("enabled") else "0",
                "sort_order": r.get("sort_order") if r.get("sort_order") is not None else "0",
            })


# Margin config: templates are per (brand_id, sport_id). Global = brand_id empty.
# Uncategorized template is always present per scope. See docs/MARGIN_CONFIG_SPEC.md.
_MARGIN_TEMPLATE_FIELDS = [
    "id", "name", "short_name", "pm_margin", "ip_margin",
    "cashout", "betbuilder", "bet_delay", "risk_class_id", "leagues_count", "markets_count", "is_default",
    "brand_id", "sport_id",
]


def _load_margin_templates(brand_id=None, sport_id=None) -> list[dict]:
    """
    Load margin_templates.csv, optionally filtered by (brand_id, sport_id).
    When scope is given, only templates for that scope are returned, and an Uncategorized
    template is ensured to exist for that scope (created and persisted if missing).
    Enriches with risk_class from RISK_CLASSES.
    """
    default_one = {
        "id": 1, "name": "Uncategorized", "short_name": "", "pm_margin": "", "ip_margin": "",
        "cashout": "", "betbuilder": "", "bet_delay": "", "risk_class_id": None,
        "leagues_count": 0, "markets_count": 0, "is_default": True,
        "brand_id": "", "sport_id": "",
    }
    if not MARGIN_TEMPLATES_PATH.exists():
        default_one["is_default"] = 1
        return [_enrich_margin_template_risk_class(default_one)]
    rows = []
    with open(MARGIN_TEMPLATES_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rid = r.get("id")
            try:
                r["id"] = int(rid) if rid and str(rid).strip() else None
            except (TypeError, ValueError):
                r["id"] = None
            rc = (r.get("risk_class_id") or "").strip()
            try:
                r["risk_class_id"] = int(rc) if rc else None
            except (TypeError, ValueError):
                r["risk_class_id"] = None
            for k in ("leagues_count", "markets_count"):
                try:
                    r[k] = int(r.get(k) or 0)
                except (TypeError, ValueError):
                    r[k] = 0
            r["is_default"] = (r.get("is_default") or "").strip() in ("1", "true", "yes")
            # Backward compat: missing columns => Global / any sport
            r["brand_id"] = (r.get("brand_id") or "").strip()
            r["sport_id"] = (r.get("sport_id") or "").strip()
            rows.append(_enrich_margin_template_risk_class(r))
    if not rows:
        return [_enrich_margin_template_risk_class(default_one)]

    # Filter by scope when (brand_id, sport_id) provided
    b_key = str(brand_id).strip() if brand_id is not None else ""
    s_key = str(sport_id).strip() if sport_id is not None else ""
    if b_key != "" or s_key != "":
        def _matches_scope(t: dict) -> bool:
            rb, rs = (t.get("brand_id") or "").strip(), (t.get("sport_id") or "").strip()
            brand_ok = rb == b_key
            # Legacy: empty sport_id at Global matches any sport
            sport_ok = rs == s_key or (rs == "" and b_key == "")
            return brand_ok and sport_ok

        filtered = [t for t in rows if _matches_scope(t)]
        # Ensure Uncategorized exists for this scope (spec: always present per brand × sport)
        uncat = next((t for t in filtered if (t.get("name") or "").strip().lower() == "uncategorized"), None)
        if not uncat:
            next_id = max((r.get("id") or 0 for r in rows), default=0) + 1
            new_uncat = {
                "id": next_id, "name": "Uncategorized", "short_name": "", "pm_margin": "", "ip_margin": "",
                "cashout": "", "betbuilder": "", "bet_delay": "", "risk_class_id": None,
                "leagues_count": 0, "markets_count": 0, "is_default": True,
                "brand_id": b_key, "sport_id": s_key,
            }
            rows.append(_enrich_margin_template_risk_class(new_uncat))
            _save_margin_templates(rows)
            filtered.append(new_uncat)
        return filtered
    return rows


def _enrich_margin_template_risk_class(t: dict) -> dict:
    """Set t['risk_class'] from RISK_CLASSES by t.get('risk_class_id'). Call after loading templates."""
    rc_id = t.get("risk_class_id")
    if rc_id is None:
        t["risk_class"] = None
        return t
    rc = next((c for c in RISK_CLASSES if c.get("id") == rc_id), None)
    t["risk_class"] = {"id": rc["id"], "letter": rc["letter"], "name": rc["name"], "circle_color": rc["circle_color"]} if rc else None
    return t


def _save_margin_templates(rows: list[dict]) -> None:
    """Overwrite margin_templates.csv (includes brand_id, sport_id for per brand×sport scoping)."""
    with open(MARGIN_TEMPLATES_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=_MARGIN_TEMPLATE_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({
                "id": r.get("id") or "",
                "name": (r.get("name") or "").strip(),
                "short_name": (r.get("short_name") or "").strip(),
                "pm_margin": (r.get("pm_margin") or "").strip(),
                "ip_margin": (r.get("ip_margin") or "").strip(),
                "cashout": (r.get("cashout") or "").strip(),
                "betbuilder": (r.get("betbuilder") or "").strip(),
                "bet_delay": (r.get("bet_delay") or "").strip(),
                "risk_class_id": r.get("risk_class_id") if r.get("risk_class_id") is not None else "",
                "leagues_count": r.get("leagues_count") if r.get("leagues_count") is not None else 0,
                "markets_count": r.get("markets_count") if r.get("markets_count") is not None else 0,
                "is_default": "1" if r.get("is_default") else "0",
                "brand_id": (r.get("brand_id") or "").strip(),
                "sport_id": (r.get("sport_id") or "").strip(),
            })


def _load_margin_template_competitions() -> list[dict]:
    """Load margin_template_competitions.csv (template_id, competition_id)."""
    if not MARGIN_TEMPLATE_COMPETITIONS_PATH.exists():
        return []
    rows = []
    with open(MARGIN_TEMPLATE_COMPETITIONS_PATH, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                tid = int(r.get("template_id") or 0)
                cid = int(r.get("competition_id") or 0)
                if tid and cid:
                    rows.append({"template_id": tid, "competition_id": cid})
            except (TypeError, ValueError):
                pass
    return rows


def _save_margin_template_competitions(rows: list[dict]) -> None:
    """Overwrite margin_template_competitions.csv."""
    with open(MARGIN_TEMPLATE_COMPETITIONS_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["template_id", "competition_id"])
        w.writeheader()
        for r in rows:
            w.writerow({"template_id": r.get("template_id"), "competition_id": r.get("competition_id")})


def _assign_competition_to_margin_template(competition_id: int, template_id: int = 1) -> None:
    """Assign a domain competition to a margin template (default Uncategorized). Idempotent. Use the scope's Uncategorized template_id when assigning new competitions per (brand, sport)."""
    rows = _load_margin_template_competitions()
    if any(r.get("template_id") == template_id and r.get("competition_id") == competition_id for r in rows):
        return
    rows.append({"template_id": template_id, "competition_id": competition_id})
    _save_margin_template_competitions(rows)


def _competition_sport_to_risk_class_map() -> dict[tuple[int, str], dict]:
    """
    Build (competition_id, template_sport_id) -> risk_class from margin_template_competitions and margin_templates.
    template_sport_id is the template's sport_id (scope); use '' for global. Used by Event Navigator to show bet class per event.
    """
    templates = _load_margin_templates()  # no filter: all templates
    by_id = {t["id"]: t for t in templates if t.get("id")}
    tcs = _load_margin_template_competitions()
    out: dict[tuple[int, str], dict] = {}
    for r in tcs:
        tid = r.get("template_id")
        cid = r.get("competition_id")
        if not tid or not cid:
            continue
        t = by_id.get(tid)
        if not t:
            continue
        sport_key = (t.get("sport_id") or "").strip()
        rc = t.get("risk_class")
        if rc:
            out[(cid, sport_key)] = rc
    return out


def _event_risk_class(ev: dict, comp_sport_to_rc: dict[tuple[int, str], dict]) -> dict | None:
    """
    Resolve event's competition + sport to a margin template risk_class (bet class) for Event Navigator.
    ev must have 'sport' and 'competition' (names). Uses DOMAIN_ENTITIES to resolve to ids, then comp_sport_to_rc.
    """
    sport_name = (ev.get("sport") or "").strip()
    comp_name = (ev.get("competition") or "").strip()
    if not comp_name:
        return None
    sport_id = None
    for s in DOMAIN_ENTITIES.get("sports", []):
        if (s.get("name") or "").strip() == sport_name:
            sport_id = s.get("domain_id")
            break
    comp_id = None
    for c in DOMAIN_ENTITIES.get("competitions", []):
        if (c.get("name") or "").strip() == comp_name and c.get("sport_id") == sport_id:
            comp_id = c.get("domain_id")
            break
    if comp_id is None:
        return None
    sport_key = str(sport_id) if sport_id is not None else ""
    rc = comp_sport_to_rc.get((comp_id, sport_key)) or comp_sport_to_rc.get((comp_id, ""))
    return rc


def _load_market_templates() -> list[dict]:
    """
    Load market_templates.csv from data/markets/.
    Templates are developer-managed blueprints (not creatable from Create Market Type view).
    Each template can have a set of params (future: parsed from params column).
    """
    if not MARKET_TEMPLATES_PATH.exists():
        return []
    with open(MARKET_TEMPLATES_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        if "domain_id" in r and r["domain_id"]:
            try:
                r["domain_id"] = int(r["domain_id"])
            except (ValueError, TypeError):
                pass
    return rows

def _load_market_csv(path: Path) -> list[dict]:
    """Load a 3-column market CSV (domain_id, code, name)."""
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        if "domain_id" in r and r["domain_id"]:
            try:
                r["domain_id"] = int(r["domain_id"])
            except (ValueError, TypeError):
                pass
    return rows

def _load_market_period_types() -> list[dict]:
    """Load market_period_type.csv (domain_id, code, name). Developer-managed."""
    return _load_market_csv(MARKET_PERIOD_TYPE_PATH)

def _load_market_score_types() -> list[dict]:
    """Load market_score_type.csv (domain_id, code, name). Developer-managed."""
    return _load_market_csv(MARKET_SCORE_TYPE_PATH)

def _load_market_groups() -> list[dict]:
    """Load market_groups.csv (domain_id, code, name). Populated from Create Market Group modal."""
    return _load_market_csv(MARKET_GROUPS_PATH)


def _load_market_outcomes() -> list[dict]:
    """Load market_outcomes.csv (template outcomes: o1..o50, outcome_type fixed|dynamic)."""
    if not MARKET_OUTCOMES_PATH.exists():
        return []
    with open(MARKET_OUTCOMES_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _get_outcome_labels_for_market(market: dict, sport_id: int | None = None) -> tuple[list[str], str]:
    """
    Resolve outcome labels and type for a market from market_outcomes.csv.
    Returns (outcome_labels, outcome_type). For fixed templates, labels come from o1, o2, ...; for dynamic, labels are empty (UI can show S1/S2/... or handle later).
    """
    template = (market.get("template") or "").strip().upper()
    if not template:
        return [], "dynamic"
    rows = _load_market_outcomes()
    candidates = [r for r in rows if (r.get("market_template_code") or "").strip().upper() == template]
    if not candidates:
        return [], "dynamic"
    # If multiple rows (e.g. CORRECT_SCORE best_of 5 vs 3), prefer by sport: volleyball (8) -> best_of 5
    row = candidates[0]
    if len(candidates) > 1 and sport_id == 8 and template == "CORRECT_SCORE":
        by_best = next((r for r in candidates if str(r.get("best_of") or "").strip() == "5"), None)
        if by_best:
            row = by_best
    outcome_type = (row.get("outcome_type") or "").strip().lower() or "dynamic"
    labels: list[str] = []
    for i in range(1, 51):
        val = (row.get("o" + str(i)) or "").strip()
        if val:
            labels.append(val)
    return labels, outcome_type


def _save_market_group(code: str, name: str) -> int:
    """Append one market group to market_groups.csv; return new domain_id."""
    groups = _load_market_groups()
    next_id = max((g.get("domain_id") or 0 for g in groups), default=0) + 1
    row = {"domain_id": next_id, "code": (code or "").strip(), "name": (name or "").strip()}
    write_header = not MARKET_GROUPS_PATH.exists() or MARKET_GROUPS_PATH.stat().st_size == 0
    with open(MARKET_GROUPS_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["domain_id", "code", "name"])
        if write_header:
            w.writeheader()
        w.writerow(row)
    return next_id


def _markets_by_group(sport_id: int | None = None) -> list[dict]:
    """Build list of { group, markets } for event details left column. If sport_id is set, only include markets created for that sport.
    Only includes groups that have at least one market (so e.g. HALF, CORNERS, CARDS are hidden when they have no markets for that sport)."""
    market_groups = _load_market_groups()
    markets = DOMAIN_ENTITIES.get("markets") or []
    if sport_id is not None:
        markets = [m for m in markets if (m.get("sport_id") or 0) == sport_id]
    group_codes = {(g.get("code") or "").strip() for g in market_groups}
    result: list[dict] = []
    for g in market_groups:
        code = (g.get("code") or "").strip()
        group_markets = [m for m in markets if (m.get("market_group") or "").strip() == code]
        if group_markets:
            result.append({"group": g, "markets": group_markets})
    orphan = [m for m in markets if (m.get("market_group") or "").strip() not in group_codes]
    if orphan:
        result.append({"group": {"domain_id": 0, "code": "", "name": "Other"}, "markets": orphan})
    return result


# Special country code for "no jurisdiction" (e.g. International category, Champions League). Not persisted.
COUNTRY_CODE_NONE = "-"

def _load_countries() -> list[dict]:
    """Load countries from data/countries/countries.json (shape: { success, results: [ { cc, name } ] ).
    Always prepends a synthetic 'None' option (code '-') for entities without a country/jurisdiction."""
    if not COUNTRIES_PATH.exists():
        out: list[dict] = []
    else:
        try:
            with open(COUNTRIES_PATH, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            out = []
        else:
            results = data.get("results") or []
            out = []
            for c in results:
                cc = (c.get("cc") or c.get("code") or "").strip()
                name = (c.get("name") or "").strip()
                if cc == COUNTRY_CODE_NONE:
                    continue  # never load from file; we add it below
                if not cc and not name:
                    continue
                out.append({"cc": cc, "name": name})
            out.sort(key=lambda x: x["name"].lower())
    # Prepend None option for "no jurisdiction" (International, Champions League, etc.)
    out.insert(0, {"cc": COUNTRY_CODE_NONE, "name": "None"})
    return out


def _load_participant_types() -> list[dict]:
    """Load participant types from data/countries/participant_type.csv (id, name)."""
    if not PARTICIPANT_TYPE_PATH.exists():
        return []
    out: list[dict] = []
    with open(PARTICIPANT_TYPE_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                out.append({"id": int(row["id"]), "name": (row.get("name") or "").strip()})
            except (ValueError, KeyError):
                continue
    return out


def _load_underage_categories() -> list[dict]:
    """Load underage categories from data/countries/underage_categories.csv (id, name)."""
    if not UNDERAGE_CATEGORIES_PATH.exists():
        return []
    out: list[dict] = []
    with open(UNDERAGE_CATEGORIES_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                out.append({"id": int(row["id"]), "name": (row.get("name") or "").strip()})
            except (ValueError, KeyError):
                continue
    return out


def _save_countries(countries: list[dict]) -> None:
    """Persist countries back to countries.json. Excludes the synthetic 'None' (code '-') entry."""
    filtered = [c for c in countries if (c.get("cc") or "").strip() != COUNTRY_CODE_NONE]
    payload = {
        "success": 1,
        "results": [{"cc": (c.get("cc") or "").strip(), "name": (c.get("name") or "").strip()} for c in filtered],
    }
    with open(COUNTRIES_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=4, sort_keys=False)


def _load_languages() -> list[dict]:
    """Load languages from data/languages.csv (id, name, native_name, direction, active, created_at, updated_at)."""
    if not LANGUAGES_PATH.exists():
        return []
    with open(LANGUAGES_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out: list[dict] = []
    for r in rows:
        try:
            lang_id = int(r.get("id", "0") or "0")
        except (TypeError, ValueError):
            lang_id = 0
        out.append({
            "id": lang_id,
            "name": (r.get("name") or "").strip(),
            "native_name": (r.get("native_name") or "").strip(),
            "direction": (r.get("direction") or "ltr").strip() or "ltr",
            "active": (r.get("active") or "").strip() == "1",
            "created_at": (r.get("created_at") or "").strip(),
            "updated_at": (r.get("updated_at") or "").strip(),
        })
    # Sort by name for display
    out.sort(key=lambda x: x["name"].lower())
    return out


def _save_languages(languages: list[dict]) -> None:
    """Persist languages to data/languages.csv."""
    fieldnames = ["id", "name", "native_name", "direction", "active", "created_at", "updated_at"]
    with open(LANGUAGES_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for lang in languages:
            row = {
                "id": lang.get("id"),
                "name": lang.get("name", ""),
                "native_name": lang.get("native_name", ""),
                "direction": (lang.get("direction") or "ltr"),
                "active": "1" if lang.get("active") else "0",
                "created_at": lang.get("created_at", ""),
                "updated_at": lang.get("updated_at", ""),
            }
            w.writerow(row)


def _load_translations() -> list[dict]:
    """Load translations from data/translations.csv."""
    if not TRANSLATIONS_PATH.exists():
        return []
    with open(TRANSLATIONS_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out: list[dict] = []
    for r in rows:
        try:
            lang_id = int(r.get("language_id", "0") or "0")
        except (TypeError, ValueError):
            lang_id = 0
        out.append({
            "entity_type": (r.get("entity_type") or "").strip(),
            "entity_id": (r.get("entity_id") or "").strip(),
            "field": (r.get("field") or "name").strip() or "name",
            "language_id": lang_id,
            "brand_id": (r.get("brand_id") or "").strip() or None,
            "text": (r.get("text") or "").strip(),
            "created_at": (r.get("created_at") or "").strip(),
            "updated_at": (r.get("updated_at") or "").strip(),
        })
    return out


def _save_translations(translations: list[dict]) -> None:
    """Persist translations to data/translations.csv."""
    fieldnames = ["entity_type", "entity_id", "field", "language_id", "brand_id", "text", "created_at", "updated_at"]
    with open(TRANSLATIONS_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for t in translations:
            row = {
                "entity_type": t.get("entity_type", ""),
                "entity_id": t.get("entity_id", ""),
                "field": t.get("field", "name") or "name",
                "language_id": str(t.get("language_id") or 0),
                "brand_id": t.get("brand_id") or "",
                "text": t.get("text", ""),
                "created_at": t.get("created_at", ""),
                "updated_at": t.get("updated_at", ""),
            }
            w.writerow(row)


def _load_partners() -> list[dict]:
    """Load partners from data/partners.csv (B2B clients)."""
    if not PARTNERS_PATH.exists():
        return []
    with open(PARTNERS_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out: list[dict] = []
    for r in rows:
        try:
            pid = int(r.get("id", "0") or "0")
        except (TypeError, ValueError):
            pid = 0
        out.append({
            "id": pid,
            "name": (r.get("name") or "").strip(),
            "code": (r.get("code") or "").strip(),
            "active": (r.get("active") or "1").strip().lower() in ("1", "true", "yes"),
            "created_at": (r.get("created_at") or "").strip(),
            "updated_at": (r.get("updated_at") or "").strip(),
        })
    return out


def _save_partners(partners: list[dict]) -> None:
    """Persist partners to data/partners.csv."""
    with open(PARTNERS_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=_PARTNERS_FIELDS)
        w.writeheader()
        for p in partners:
            w.writerow({
                "id": p.get("id", ""),
                "name": p.get("name", ""),
                "code": p.get("code", ""),
                "active": "1" if p.get("active", True) else "0",
                "created_at": p.get("created_at", ""),
                "updated_at": p.get("updated_at", ""),
            })


def _load_brands() -> list[dict]:
    """Load brands from data/brands.csv. Global is not stored; it is a virtual row in the UI."""
    if not BRANDS_PATH.exists():
        return []
    with open(BRANDS_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out: list[dict] = []
    for r in rows:
        try:
            bid = int(r.get("id", "0") or "0")
        except (TypeError, ValueError):
            bid = 0
        partner_id_raw = (r.get("partner_id") or "").strip()
        try:
            partner_id = int(partner_id_raw) if partner_id_raw else None
        except (TypeError, ValueError):
            partner_id = None
        out.append({
            "id": bid,
            "name": (r.get("name") or "").strip(),
            "code": (r.get("code") or "").strip(),
            "partner_id": partner_id,
            "jurisdiction": (r.get("jurisdiction") or "").strip(),  # comma-separated country codes
            "language_ids": (r.get("language_ids") or "").strip(),  # comma-separated
            "currencies": (r.get("currencies") or "").strip(),  # comma-separated
            "odds_formats": (r.get("odds_formats") or "").strip(),  # comma-separated
            "created_at": (r.get("created_at") or "").strip(),
            "updated_at": (r.get("updated_at") or "").strip(),
        })
    return out


def _save_brands(brands: list[dict]) -> None:
    """Persist brands to data/brands.csv."""
    with open(BRANDS_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=_BRANDS_FIELDS)
        w.writeheader()
        for b in brands:
            pid = b.get("partner_id")
            w.writerow({
                "id": b.get("id", ""),
                "name": b.get("name", ""),
                "code": b.get("code", ""),
                "partner_id": str(pid) if pid is not None else "",
                "jurisdiction": b.get("jurisdiction", ""),
                "language_ids": b.get("language_ids", ""),
                "currencies": b.get("currencies", ""),
                "odds_formats": b.get("odds_formats", ""),
                "created_at": b.get("created_at", ""),
                "updated_at": b.get("updated_at", ""),
            })


# ── RBAC load/save/audit ───────────────────────────────────────────────────

def _load_rbac_users() -> list[dict]:
    """Load users from data/rbac/users.csv."""
    if not RBAC_USERS_PATH.exists():
        return []
    out = []
    with open(RBAC_USERS_PATH, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            uid = _int_or_none(r.get("user_id"))
            pid = _int_or_none(r.get("partner_id"))
            created_by = (r.get("created_by") or "").strip() or "SuperAdmin"
            out.append({
                "user_id": uid or 0,
                "login": (r.get("login") or "").strip(),
                "email": (r.get("email") or "").strip(),
                "display_name": (r.get("display_name") or "").strip(),
                "active": (r.get("active") or "1").strip().lower() in ("1", "true", "yes"),
                "partner_id": pid,
                "created_by": created_by,
                "created_at": (r.get("created_at") or "").strip(),
                "updated_at": (r.get("updated_at") or "").strip(),
                "last_login": (r.get("last_login") or "").strip(),
                "online": (r.get("online") or "0").strip().lower() in ("1", "true", "yes"),
            })
    return out


def _int_or_none(v):
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _save_rbac_users(users: list[dict]) -> None:
    with open(RBAC_USERS_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=_RBAC_USERS_FIELDS)
        w.writeheader()
        for u in users:
            w.writerow({
                "user_id": u.get("user_id", ""),
                "login": u.get("login", ""),
                "email": u.get("email", ""),
                "display_name": u.get("display_name", ""),
                "active": "1" if u.get("active", True) else "0",
                "partner_id": u.get("partner_id") if u.get("partner_id") is not None else "",
                "created_by": (u.get("created_by") or "SuperAdmin").strip(),
                "created_at": u.get("created_at", ""),
                "updated_at": u.get("updated_at", ""),
                "last_login": u.get("last_login", ""),
                "online": "1" if u.get("online", False) else "0",
            })


def _load_rbac_roles() -> list[dict]:
    if not RBAC_ROLES_PATH.exists():
        return []
    out = []
    with open(RBAC_ROLES_PATH, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rid = _int_or_none(r.get("role_id")) or 0
            pid = _int_or_none(r.get("partner_id"))
            out.append({
                "role_id": rid,
                "name": (r.get("name") or "").strip(),
                "active": (r.get("active") or "1").strip().lower() in ("1", "true", "yes"),
                "is_system": (r.get("is_system") or "0").strip().lower() in ("1", "true", "yes"),
                "partner_id": pid,
                "created_at": (r.get("created_at") or "").strip(),
                "updated_at": (r.get("updated_at") or "").strip(),
            })
    return out


def _save_rbac_roles(roles: list[dict]) -> None:
    with open(RBAC_ROLES_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=_RBAC_ROLES_FIELDS)
        w.writeheader()
        for row in roles:
            w.writerow({
                "role_id": row.get("role_id", ""),
                "name": row.get("name", ""),
                "active": "1" if row.get("active", True) else "0",
                "is_system": "1" if row.get("is_system", False) else "0",
                "partner_id": row.get("partner_id") if row.get("partner_id") is not None else "",
                "created_at": row.get("created_at", ""),
                "updated_at": row.get("updated_at", ""),
            })


def _save_rbac_role_permissions(rows: list[dict]) -> None:
    with open(RBAC_ROLE_PERMISSIONS_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=_RBAC_ROLE_PERMISSIONS_FIELDS)
        w.writeheader()
        for row in rows:
            w.writerow({"role_id": row.get("role_id", ""), "permission_code": row.get("permission_code", "")})


def _load_rbac_user_roles() -> list[dict]:
    if not RBAC_USER_ROLES_PATH.exists():
        return []
    out = []
    with open(RBAC_USER_ROLES_PATH, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out.append({
                "user_id": int(r.get("user_id") or 0),
                "role_id": int(r.get("role_id") or 0),
                "assigned_at": (r.get("assigned_at") or "").strip(),
                "assigned_by_user_id": _int_or_none(r.get("assigned_by_user_id")),
            })
    return out


def _save_rbac_user_roles(rows: list[dict]) -> None:
    with open(RBAC_USER_ROLES_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=_RBAC_USER_ROLES_FIELDS)
        w.writeheader()
        for row in rows:
            w.writerow({
                "user_id": row.get("user_id", ""),
                "role_id": row.get("role_id", ""),
                "assigned_at": row.get("assigned_at", ""),
                "assigned_by_user_id": row.get("assigned_by_user_id") if row.get("assigned_by_user_id") is not None else "",
            })


def _load_rbac_role_permissions() -> list[dict]:
    if not RBAC_ROLE_PERMISSIONS_PATH.exists():
        return []
    out = []
    with open(RBAC_ROLE_PERMISSIONS_PATH, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out.append({"role_id": int(r.get("role_id") or 0), "permission_code": (r.get("permission_code") or "").strip()})
    return out


def _load_rbac_user_brands() -> list[dict]:
    if not RBAC_USER_BRANDS_PATH.exists():
        return []
    out = []
    with open(RBAC_USER_BRANDS_PATH, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out.append({"user_id": int(r.get("user_id") or 0), "brand_id": int(r.get("brand_id") or 0)})
    return out


def _save_rbac_user_brands(rows: list[dict]) -> None:
    with open(RBAC_USER_BRANDS_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=_RBAC_USER_BRANDS_FIELDS)
        w.writeheader()
        for row in rows:
            w.writerow({"user_id": row.get("user_id", ""), "brand_id": row.get("brand_id", "")})


def _rbac_audit_next_id() -> int:
    if not RBAC_AUDIT_LOG_PATH.exists() or RBAC_AUDIT_LOG_PATH.stat().st_size == 0:
        return 1
    with open(RBAC_AUDIT_LOG_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    if not rows:
        return 1
    ids = [_int_or_none(r.get("id")) or 0 for r in rows]
    return max(ids, default=0) + 1


def _rbac_audit_append(actor_user_id: int | None, action: str, target_type: str, target_id: str, details: str = "") -> None:
    """Append one row to rbac_audit_log.csv. Append-only."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    next_id = _rbac_audit_next_id()
    write_header = not RBAC_AUDIT_LOG_PATH.exists() or RBAC_AUDIT_LOG_PATH.stat().st_size == 0
    if RBAC_AUDIT_LOG_PATH.exists() and RBAC_AUDIT_LOG_PATH.stat().st_size > 0:
        with open(RBAC_AUDIT_LOG_PATH, "rb+") as f:
            f.seek(-1, 2)
            if f.read(1) != b"\n":
                f.write(b"\n")
    with open(RBAC_AUDIT_LOG_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=_RBAC_AUDIT_LOG_FIELDS)
        if write_header:
            w.writeheader()
        w.writerow({
            "id": next_id,
            "created_at": now,
            "actor_user_id": actor_user_id if actor_user_id is not None else "",
            "action": action,
            "target_type": target_type,
            "target_id": str(target_id),
            "details": details,
        })


def _load_market_type_mappings() -> list[dict]:
    """Load market_type_mappings.csv (domain_market_id, feed_provider_id, feed_market_id, feed_market_name, phase)."""
    if not MARKET_TYPE_MAPPINGS_PATH.exists():
        return []
    rows = []
    with open(MARKET_TYPE_MAPPINGS_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            row["domain_market_id"] = int(row["domain_market_id"])
            row["feed_provider_id"] = int(row["feed_provider_id"])
            rows.append(row)
    return rows


def _save_market_type_mappings_for_domain(domain_market_id: int, prematch: list[dict], live: list[dict]) -> None:
    """Replace all mappings for domain_market_id with the given prematch and live lists. phase = prematch | live."""
    all_mappings = _load_market_type_mappings()
    rest = [m for m in all_mappings if m["domain_market_id"] != domain_market_id]
    new_rows = []
    for item in prematch:
        new_rows.append({
            "domain_market_id": domain_market_id,
            "feed_provider_id": int(item["feed_provider_id"]),
            "feed_market_id": str(item.get("id", item.get("feed_market_id", ""))),
            "feed_market_name": (item.get("name") or item.get("feed_market_name") or "").strip(),
            "phase": "prematch",
        })
    for item in live:
        new_rows.append({
            "domain_market_id": domain_market_id,
            "feed_provider_id": int(item["feed_provider_id"]),
            "feed_market_id": str(item.get("id", item.get("feed_market_id", ""))),
            "feed_market_name": (item.get("name") or item.get("feed_market_name") or "").strip(),
            "phase": "live",
        })
    with open(MARKET_TYPE_MAPPINGS_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=_MARKET_TYPE_MAPPING_FIELDS)
        w.writeheader()
        for r in rest:
            w.writerow({k: r.get(k, "") for k in _MARKET_TYPE_MAPPING_FIELDS})
        w.writerows(new_rows)


def _migrate_entity_created_updated_if_needed() -> None:
    """One-time: add created_at and updated_at columns to entity CSVs if missing."""
    for etype in ("sports", "categories", "competitions", "teams", "markets"):
        if etype not in _ENTITY_FIELDS:
            continue
        path = DATA_DIR / f"{etype}.csv"
        if not path.exists():
            continue
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            fieldnames = list(reader.fieldnames or [])
        if "created_at" in fieldnames:
            continue  # already migrated for this file
        fields = _ENTITY_FIELDS[etype]
        for row in rows:
            row.setdefault("created_at", "")
            row.setdefault("updated_at", "")
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)


def _migrate_entity_baseid_if_needed() -> None:
    """One-time: add baseid column to sports, categories, competitions, teams CSVs if missing."""
    for etype in ("sports", "categories", "competitions", "teams"):
        path = DATA_DIR / f"{etype}.csv"
        if not path.exists():
            continue
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            fieldnames = list(reader.fieldnames or [])
        if "baseid" in fieldnames:
            continue
        fields = _ENTITY_FIELDS[etype]
        for row in rows:
            row["baseid"] = (row.get("baseid") or "").strip()
            if etype in ("categories", "competitions", "teams"):
                row.setdefault("jurisdiction", COUNTRY_CODE_NONE)
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)


def _migrate_entity_jurisdiction_if_needed() -> None:
    """One-time: add jurisdiction column to categories, competitions, teams CSVs if missing."""
    for etype in ("categories", "competitions", "teams"):
        path = DATA_DIR / f"{etype}.csv"
        if not path.exists():
            continue
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            fieldnames = list(reader.fieldnames or [])
        if "jurisdiction" in fieldnames:
            continue
        fields = _ENTITY_FIELDS[etype]
        for row in rows:
            row["jurisdiction"] = (row.get("jurisdiction") or "").strip() or COUNTRY_CODE_NONE
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)


def _migrate_entity_underage_participant_amateur_if_needed() -> None:
    """One-time: add underage_category_id, participant_type_id, is_amateur to competitions/teams CSVs if missing."""
    for etype in ("competitions", "teams"):
        path = DATA_DIR / f"{etype}.csv"
        if not path.exists():
            continue
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            fieldnames = list(reader.fieldnames or [])
        fields = _ENTITY_FIELDS[etype]
        missing = [f for f in fields if f not in fieldnames]
        if not missing:
            continue
        for row in rows:
            row.setdefault("underage_category_id", "")
            row.setdefault("participant_type_id", "")
            if etype == "competitions":
                row.setdefault("is_amateur", "0")
            elif etype == "teams":
                row.setdefault("is_amateur", "0")
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)


def _load_entities() -> dict:
    """Load all entity CSVs into memory with int FKs. Skips rows with invalid domain_id (e.g. merge conflict markers)."""
    store: dict[str, list[dict]] = {k: [] for k in _ENTITY_FIELDS if k != "feeds"}
    for etype in store:
        path = DATA_DIR / f"{etype}.csv"
        if path.exists():
            with open(path, newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    try:
                        row["domain_id"] = int(row["domain_id"])
                    except (TypeError, ValueError):
                        continue  # skip rows with non-numeric domain_id (e.g. merge conflict markers)
                    for fk in ("sport_id", "category_id"):
                        if fk in row and row[fk]:
                            try:
                                row[fk] = int(row[fk])
                            except (TypeError, ValueError):
                                row[fk] = None
                    if etype == "markets":
                        if row.get("sport_id"):
                            try:
                                row["sport_id"] = int(row["sport_id"])
                            except (TypeError, ValueError):
                                row["sport_id"] = None
                        else:
                            row["sport_id"] = None
                    if etype == "competitions":
                        for fk in ("underage_category_id", "participant_type_id"):
                            if fk in row and row.get(fk):
                                try:
                                    row[fk] = int(row[fk])
                                except (TypeError, ValueError):
                                    row[fk] = None
                            else:
                                row[fk] = None
                        row["is_amateur"] = (row.get("is_amateur") or "").strip() in ("1", "true", "yes")
                    elif etype == "teams":
                        for fk in ("underage_category_id", "participant_type_id"):
                            if fk in row and row.get(fk):
                                try:
                                    row[fk] = int(row[fk])
                                except (TypeError, ValueError):
                                    row[fk] = None
                            else:
                                row[fk] = None
                        row["is_amateur"] = (row.get("is_amateur") or "").strip() in ("1", "true", "yes")
                    row.setdefault("created_at", "")
                    row.setdefault("updated_at", "")
                    if etype in ("sports", "categories", "competitions", "teams"):
                        row["baseid"] = (row.get("baseid") or "").strip()
                    if etype in ("categories", "competitions", "teams"):
                        row["jurisdiction"] = (row.get("jurisdiction") or "").strip() or COUNTRY_CODE_NONE
                    store[etype].append(row)
    return store

def _save_entity(etype: str, entity: dict) -> None:
    """Append one entity row to its CSV file."""
    path = DATA_DIR / f"{etype}.csv"
    fields = _ENTITY_FIELDS[etype]
    write_header = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        writer.writerow(entity)


def _update_entity_name(
    etype: str,
    domain_id: int,
    new_name: str,
    updated_at: str,
    jurisdiction: str | None = None,
    baseid: str | None = None,
    participant_type_id: int | None = None,
    underage_category_id: int | None = None,
    is_amateur: bool | None = None,
) -> None:
    """
    Update name and optionally jurisdiction, baseid, participant_type_id (teams), underage_category_id (teams), is_amateur (teams), and updated_at for a single entity row.
    """
    path = DATA_DIR / f"{etype}.csv"
    if not path.exists():
        return
    fields = _ENTITY_FIELDS[etype]
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    for row in rows:
        try:
            row_id = int(row.get("domain_id", 0))
        except (TypeError, ValueError):
            continue
        if etype in ("sports", "categories", "competitions", "teams"):
            row.setdefault("baseid", "")
        if etype in ("categories", "competitions", "teams"):
            row.setdefault("jurisdiction", COUNTRY_CODE_NONE)
        if etype == "teams":
            row.setdefault("underage_category_id", "")
            row.setdefault("is_amateur", "0")
        if etype == "competitions":
            row.setdefault("underage_category_id", "")
            row.setdefault("is_amateur", "0")
        if row_id == domain_id:
            row["name"] = new_name
            row["updated_at"] = updated_at
            if etype in ("categories", "competitions", "teams") and jurisdiction is not None:
                row["jurisdiction"] = (jurisdiction or "").strip() or COUNTRY_CODE_NONE
            if etype in ("sports", "categories", "competitions", "teams") and baseid is not None:
                row["baseid"] = (baseid or "").strip()
            if etype == "teams":
                if participant_type_id is not None:
                    row["participant_type_id"] = str(participant_type_id) if participant_type_id else ""
                row["underage_category_id"] = str(underage_category_id) if underage_category_id else ""
                if is_amateur is not None:
                    row["is_amateur"] = "1" if is_amateur else "0"
            elif etype == "competitions":
                row["underage_category_id"] = str(underage_category_id) if underage_category_id else ""
                if is_amateur is not None:
                    row["is_amateur"] = "1" if is_amateur else "0"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _update_entity_jurisdiction(etype: str, domain_id: int, jurisdiction: str, updated_at: str) -> None:
    """Update the jurisdiction (and updated_at) for a single entity row. etype must be categories, competitions, or teams."""
    path = DATA_DIR / f"{etype}.csv"
    if not path.exists():
        return
    fields = _ENTITY_FIELDS[etype]
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    for row in rows:
        try:
            row_id = int(row.get("domain_id", 0))
        except (TypeError, ValueError):
            continue
        if etype in ("categories", "competitions", "teams"):
            row.setdefault("jurisdiction", COUNTRY_CODE_NONE)
        if row_id == domain_id:
            row["jurisdiction"] = (jurisdiction or "").strip() or COUNTRY_CODE_NONE
            row["updated_at"] = updated_at
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _update_entity_market(domain_id: int, updated_at: str, **kwargs: str | bool | None) -> None:
    """Update a single market row in markets.csv and in DOMAIN_ENTITIES. kwargs: name, code, abb, market_type, market_group, template, period_type, score_type, side_type, score_dependant."""
    path = DATA_DIR / "markets.csv"
    if not path.exists():
        return
    fields = _ENTITY_FIELDS["markets"]
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    for row in rows:
        try:
            row_id = int(row.get("domain_id", 0))
        except (TypeError, ValueError):
            continue
        if row_id == domain_id:
            if "name" in kwargs and kwargs["name"] is not None:
                row["name"] = (kwargs["name"] or "").strip()
            if "code" in kwargs and kwargs["code"] is not None:
                row["code"] = (kwargs["code"] or "").strip()
            if "abb" in kwargs and kwargs["abb"] is not None:
                row["abb"] = (kwargs["abb"] or "").strip()
            if "market_type" in kwargs and kwargs["market_type"] is not None:
                row["market_type"] = (kwargs["market_type"] or "").strip()
            if "market_group" in kwargs and kwargs["market_group"] is not None:
                row["market_group"] = (kwargs["market_group"] or "").strip()
            if "template" in kwargs and kwargs["template"] is not None:
                row["template"] = (kwargs["template"] or "").strip()
            if "period_type" in kwargs and kwargs["period_type"] is not None:
                row["period_type"] = (kwargs["period_type"] or "").strip()
            if "score_type" in kwargs and kwargs["score_type"] is not None:
                row["score_type"] = (kwargs["score_type"] or "").strip()
            if "side_type" in kwargs and kwargs["side_type"] is not None:
                row["side_type"] = (kwargs["side_type"] or "").strip()
            if "score_dependant" in kwargs and kwargs["score_dependant"] is not None:
                row["score_dependant"] = "1" if kwargs["score_dependant"] else "0"
            row["updated_at"] = updated_at
            break
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    # Update in-memory
    bucket = DOMAIN_ENTITIES.get("markets") or []
    for m in bucket:
        if m.get("domain_id") == domain_id:
            m["updated_at"] = updated_at
            if "name" in kwargs and kwargs["name"] is not None:
                m["name"] = (kwargs["name"] or "").strip()
            if "code" in kwargs and kwargs["code"] is not None:
                m["code"] = (kwargs["code"] or "").strip()
            if "abb" in kwargs and kwargs["abb"] is not None:
                m["abb"] = (kwargs["abb"] or "").strip()
            if "market_type" in kwargs and kwargs["market_type"] is not None:
                m["market_type"] = (kwargs["market_type"] or "").strip()
            if "market_group" in kwargs and kwargs["market_group"] is not None:
                m["market_group"] = (kwargs["market_group"] or "").strip()
            if "template" in kwargs and kwargs["template"] is not None:
                m["template"] = (kwargs["template"] or "").strip()
            if "period_type" in kwargs and kwargs["period_type"] is not None:
                m["period_type"] = (kwargs["period_type"] or "").strip()
            if "score_type" in kwargs and kwargs["score_type"] is not None:
                m["score_type"] = (kwargs["score_type"] or "").strip()
            if "side_type" in kwargs and kwargs["side_type"] is not None:
                m["side_type"] = (kwargs["side_type"] or "").strip()
            if "score_dependant" in kwargs and kwargs["score_dependant"] is not None:
                m["score_dependant"] = "1" if kwargs["score_dependant"] else "0"
            break


# In-memory stores — initialised from CSV on startup
def _load_domain_events() -> list[dict]:
    """Load domain_events.csv into memory on startup. Skips rows missing domain_id."""
    if not DOMAIN_EVENTS_PATH.exists():
        return []
    with open(DOMAIN_EVENTS_PATH, newline="", encoding="utf-8") as f:
        rows = []
        for row in csv.DictReader(f):
            if "domain_id" not in row or not str(row.get("domain_id", "")).strip():
                continue
            rows.append({
                "id":          row["domain_id"],
                "sport":       row.get("sport", ""),
                "category":    row.get("category", ""),
                "competition": row.get("competition", ""),
                "home":        row.get("home", ""),
                "home_id":     row.get("home_id", ""),
                "away":        row.get("away", ""),
                "away_id":     row.get("away_id", ""),
                "start_time":  row.get("start_time", ""),
            })
        return rows

def _save_domain_event(event: dict) -> None:
    """Append one domain event row to domain_events.csv (no feeder info)."""
    row = {
        "domain_id":   event["id"],
        "sport":       event.get("sport", ""),
        "category":    event.get("category", ""),
        "competition": event.get("competition", ""),
        "home":        event.get("home", ""),
        "home_id":     event.get("home_id", ""),
        "away":        event.get("away", ""),
        "away_id":     event.get("away_id", ""),
        "start_time":  event.get("start_time", ""),
    }
    write_header = not DOMAIN_EVENTS_PATH.exists() or DOMAIN_EVENTS_PATH.stat().st_size == 0
    # Ensure file ends with newline before appending (prevents merged rows)
    if not write_header and DOMAIN_EVENTS_PATH.stat().st_size > 0:
        with open(DOMAIN_EVENTS_PATH, "rb+") as f:
            f.seek(-1, 2)
            if f.read(1) != b"\n":
                f.write(b"\n")
    with open(DOMAIN_EVENTS_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_DOMAIN_EVENT_FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerow(row)

def _load_event_mappings() -> list[dict]:
    """Load event_mappings.csv — additional multi-feed mappings."""
    if not EVENT_MAPPINGS_PATH.exists():
        return []
    with open(EVENT_MAPPINGS_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def _load_entity_feed_mappings() -> list[dict]:
    """Load entity_feed_mappings.csv (non-sport only) + sport_feed_mappings.csv (sports). Sport mappings are developer-controlled and never dumped."""
    def _parse_row(row: dict) -> dict:
        row["domain_id"] = int(row["domain_id"])
        row["feed_provider_id"] = int(row["feed_provider_id"])
        if not (row.get("domain_name") or str(row.get("domain_name", "")).strip()):
            try:
                bucket = DOMAIN_ENTITIES.get(row["entity_type"], [])
                ent = next((e for e in bucket if e["domain_id"] == row["domain_id"]), None)
                row["domain_name"] = (ent.get("name") or "").strip() if ent else ""
            except NameError:
                row["domain_name"] = ""
        return row

    rows = []
    if ENTITY_FEED_MAPPINGS_PATH.exists():
        with open(ENTITY_FEED_MAPPINGS_PATH, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if (row.get("entity_type") or "").strip().lower() == "sports":
                    continue
                rows.append(_parse_row(row))

    if SPORT_FEED_MAPPINGS_PATH.exists():
        with open(SPORT_FEED_MAPPINGS_PATH, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if (row.get("entity_type") or "").strip().lower() != "sports":
                    continue
                rows.append(_parse_row(row))
    return rows


def _load_sport_feed_mappings() -> list[dict]:
    """Load sport_feed_mappings.csv only. Used for resolving feed sport id by domain sport (e.g. feed-markets API)."""
    out: list[dict] = []
    if not SPORT_FEED_MAPPINGS_PATH.exists():
        return out
    with open(SPORT_FEED_MAPPINGS_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if (row.get("entity_type") or "").strip().lower() != "sports":
                continue
            try:
                out.append({
                    "entity_type": "sports",
                    "domain_id": int(row["domain_id"]),
                    "feed_provider_id": int(row["feed_provider_id"]),
                    "feed_id": row.get("feed_id", ""),
                    "domain_name": (row.get("domain_name") or "").strip(),
                })
            except (KeyError, TypeError, ValueError):
                continue
    return out


def _domain_entity_name(entity_type: str, domain_id: int) -> str:
    """Return display name for a domain entity (from DOMAIN_ENTITIES). Empty if not found or not yet loaded."""
    try:
        bucket = DOMAIN_ENTITIES.get(entity_type, [])
        ent = next((e for e in bucket if e["domain_id"] == domain_id), None)
        return (ent.get("name") or "").strip() if ent else ""
    except NameError:
        return ""

def _save_entity_feed_mapping(entity_type: str, domain_id: int, feed_provider_id: int, feed_id: str, domain_name: str | None = None) -> None:
    """Append one row to entity_feed_mappings.csv (one feed reference per domain entity). Sport mappings are not written (they live in sport_feed_mappings.csv, developer-controlled)."""
    if (entity_type or "").strip().lower() == "sports":
        return
    if domain_name is None:
        try:
            domain_name = _domain_entity_name(entity_type, domain_id)
        except NameError:
            domain_name = ""
    row = {
        "entity_type": entity_type,
        "domain_id": domain_id,
        "feed_provider_id": feed_provider_id,
        "feed_id": str(feed_id),
        "domain_name": domain_name or "",
    }
    write_header = not ENTITY_FEED_MAPPINGS_PATH.exists() or ENTITY_FEED_MAPPINGS_PATH.stat().st_size == 0
    with open(ENTITY_FEED_MAPPINGS_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_ENTITY_FEED_MAPPING_FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerow(row)

def _feed_id_looks_numeric(feed_id: str) -> bool:
    """True if feed_id is non-empty and numeric (preferred for sports)."""
    s = (feed_id or "").strip()
    if not s:
        return False
    try:
        int(s)
        return True
    except (TypeError, ValueError):
        return False


def _persist_entity_feed_mappings() -> None:
    """Rewrite entity_feed_mappings.csv from current ENTITY_FEED_MAPPINGS (non-sport rows only). Sport mappings stay in sport_feed_mappings.csv and are not written here."""
    with open(ENTITY_FEED_MAPPINGS_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_ENTITY_FEED_MAPPING_FIELDS)
        writer.writeheader()
        for m in ENTITY_FEED_MAPPINGS:
            if (m.get("entity_type") or "").strip().lower() == "sports":
                continue
            writer.writerow({
                "entity_type": m["entity_type"],
                "domain_id": m["domain_id"],
                "feed_provider_id": m["feed_provider_id"],
                "feed_id": str(m.get("feed_id", "")),
                "domain_name": (m.get("domain_name") or "").strip(),
            })


def _ensure_entity_feed_mapping(entity_type: str, domain_id: int, feed_provider_id: int, feed_id: str) -> None:
    """Idempotent: add (entity_type, domain_id, feed_provider_id, feed_id) to entity_feed_mappings if not present.
    For sports: only one mapping per (domain_id, feed_provider_id); prefer storing feed's numeric sport ID over name."""
    feed_id_str = str(feed_id).strip()
    if not feed_id_str:
        return
    if entity_type == "sports":
        existing = next(
            (m for m in ENTITY_FEED_MAPPINGS
             if m["entity_type"] == "sports" and m["domain_id"] == domain_id and m["feed_provider_id"] == feed_provider_id),
            None,
        )
        if existing:
            # Prefer numeric feed_id (feed sport ID) over name for stability
            if _feed_id_looks_numeric(feed_id_str) and not _feed_id_looks_numeric(str(existing.get("feed_id", ""))):
                existing["feed_id"] = feed_id_str
                _persist_entity_feed_mappings()
            return
    exists = any(
        m["entity_type"] == entity_type
        and m["domain_id"] == domain_id
        and m["feed_provider_id"] == feed_provider_id
        and str(m["feed_id"]).lower() == feed_id_str.lower()
        for m in ENTITY_FEED_MAPPINGS
    )
    if not exists:
        domain_name = _domain_entity_name(entity_type, domain_id)
        ENTITY_FEED_MAPPINGS.append({
            "entity_type": entity_type,
            "domain_id": domain_id,
            "feed_provider_id": feed_provider_id,
            "feed_id": feed_id_str,
            "domain_name": domain_name,
        })
        _save_entity_feed_mapping(entity_type, domain_id, feed_provider_id, feed_id_str, domain_name)

def _migrate_sport_aliases_to_entity_feed_mappings() -> None:
    """
    One-time migration: move sport_aliases.csv rows into entity_feed_mappings.csv
    as entity_type='sports', then remove sport_aliases.csv.
    """
    sport_aliases_path = DATA_DIR / "sport_aliases.csv"
    if not sport_aliases_path.exists():
        return
    with open(sport_aliases_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        try:
            feed_provider_id = int(r.get("feed_provider_id", 0))
            sport_id = int(r.get("sport_id", 0))
            feed_sport_name = (r.get("feed_sport_name") or "").strip()
        except (ValueError, TypeError):
            continue
        if not feed_sport_name:
            continue
        _save_entity_feed_mapping("sports", sport_id, feed_provider_id, feed_sport_name)
    try:
        sport_aliases_path.unlink()
    except OSError:
        pass

def _migrate_entity_feed_mappings_if_needed() -> None:
    """
    One-time migration: if entity CSVs still have feed_id/feed_provider_id columns,
    move those into entity_feed_mappings.csv and rewrite entity CSVs without feed columns.
    """
    if ENTITY_FEED_MAPPINGS_PATH.exists():
        return  # already migrated
    for etype in ("teams", "categories", "competitions"):
        path = DATA_DIR / f"{etype}.csv"
        if not path.exists():
            continue
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        if not rows or "feed_id" not in rows[0]:
            continue
        # Migrate: write each (domain_id, feed_provider_id, feed_id) to entity_feed_mappings
        for r in rows:
            fid, fpid = r.get("feed_id"), r.get("feed_provider_id")
            if fid is None or fid == "" or fpid is None or fpid == "":
                continue
            try:
                fpid_int = int(fpid)
                domain_id_int = int(r["domain_id"])
            except (TypeError, ValueError):
                continue
            _save_entity_feed_mapping(etype, domain_id_int, fpid_int, str(fid))
        # Rewrite CSV without feed columns
        new_fields = _ENTITY_FIELDS[etype]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=new_fields, extrasaction="ignore")
            writer.writeheader()
            for r in rows:
                writer.writerow({k: r.get(k) for k in new_fields})

def _save_event_mapping(domain_event_id: str, feed_provider: str, feed_valid_id: str) -> None:
    """Append one row to event_mappings.csv."""
    row = {"domain_event_id": domain_event_id, "feed_provider": feed_provider, "feed_valid_id": feed_valid_id}
    write_header = not EVENT_MAPPINGS_PATH.exists() or EVENT_MAPPINGS_PATH.stat().st_size == 0
    with open(EVENT_MAPPINGS_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_MAPPING_FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerow(row)

DOMAIN_EVENTS: list[dict] = _load_domain_events()
FEEDS: list[dict] = _load_feeds()
_migrate_entity_feed_mappings_if_needed()
_migrate_sport_aliases_to_entity_feed_mappings()
_migrate_entity_created_updated_if_needed()
_migrate_entity_jurisdiction_if_needed()
_migrate_entity_baseid_if_needed()
_migrate_entity_underage_participant_amateur_if_needed()
DOMAIN_ENTITIES: dict[str, list[dict]] = _load_entities()
ENTITY_FEED_MAPPINGS: list[dict] = _load_entity_feed_mappings()
SPORT_FEED_MAPPINGS: list[dict] = _load_sport_feed_mappings()


def _deduplicate_sport_feed_mappings() -> None:
    """One-time: keep at most one sport mapping per (domain_id, feed_provider_id), preferring numeric feed_id."""
    seen: dict[tuple[int, int], dict] = {}
    others: list[dict] = []
    for m in ENTITY_FEED_MAPPINGS:
        if m["entity_type"] != "sports":
            others.append(m)
            continue
        key = (m["domain_id"], m["feed_provider_id"])
        cur_id = str(m.get("feed_id", "")).strip()
        if key not in seen:
            seen[key] = m
            continue
        existing = seen[key]
        exist_id = str(existing.get("feed_id", "")).strip()
        # Prefer numeric feed_id
        if _feed_id_looks_numeric(cur_id) and not _feed_id_looks_numeric(exist_id):
            seen[key] = m
    new_list = list(seen.values()) + others
    if len(new_list) == len(ENTITY_FEED_MAPPINGS):
        return
    ENTITY_FEED_MAPPINGS.clear()
    ENTITY_FEED_MAPPINGS.extend(new_list)
    _persist_entity_feed_mappings()


_deduplicate_sport_feed_mappings()


def _dump_entity_and_relation_csvs() -> None:
    """
    Clear entity and relation CSV files (header-only). Does not touch feeds.csv, sports.csv, or sport_feed_mappings.csv
    (sports and sport–feed mappings are developer-controlled, same on local and server via git).
    Caller must reload DOMAIN_EVENTS, DOMAIN_ENTITIES, ENTITY_FEED_MAPPINGS after.
    """
    with open(DOMAIN_EVENTS_PATH, "w", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=_DOMAIN_EVENT_FIELDS).writeheader()
    with open(EVENT_MAPPINGS_PATH, "w", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=_MAPPING_FIELDS).writeheader()
    with open(ENTITY_FEED_MAPPINGS_PATH, "w", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=_ENTITY_FEED_MAPPING_FIELDS).writeheader()
    for etype in _ENTITY_FIELDS:
        if etype in ("feeds", "sports"):
            continue
        path = DATA_DIR / f"{etype}.csv"
        with open(path, "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=_ENTITY_FIELDS[etype]).writeheader()


def _rewrite_entity_feed_mappings_with_domain_name() -> None:
    """If CSV has no domain_name column, rewrite it with new schema and backfilled domain_name. Only non-sport rows go to entity_feed_mappings.csv."""
    if not ENTITY_FEED_MAPPINGS_PATH.exists():
        return
    with open(ENTITY_FEED_MAPPINGS_PATH, newline="", encoding="utf-8") as f:
        first_line = f.readline() or ""
    if "domain_name" in first_line:
        return
    rows = []
    for m in ENTITY_FEED_MAPPINGS:
        if (m.get("entity_type") or "").strip().lower() == "sports":
            continue
        name = m.get("domain_name") or _domain_entity_name(m["entity_type"], m["domain_id"])
        rows.append({
            "entity_type": m["entity_type"],
            "domain_id": m["domain_id"],
            "feed_provider_id": m["feed_provider_id"],
            "feed_id": str(m["feed_id"]),
            "domain_name": name or "",
        })
    with open(ENTITY_FEED_MAPPINGS_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_ENTITY_FEED_MAPPING_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


_rewrite_entity_feed_mappings_with_domain_name()

_FEEDER_IGNORED_FIELDS = ["feed_provider", "feed_valid_id"]


def _load_feeder_ignored_set() -> set[tuple[str, str]]:
    """Set of (feed_provider, feed_valid_id) that are ignored (bad/wrong events; not deleted, just hidden from mapping)."""
    if not FEEDER_IGNORED_EVENTS_PATH or not FEEDER_IGNORED_EVENTS_PATH.exists():
        return set()
    out = set()
    with open(FEEDER_IGNORED_EVENTS_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            p = (row.get("feed_provider") or "").strip()
            v = (row.get("feed_valid_id") or "").strip()
            if p or v:
                out.add((p, v))
    return out


def _set_feeder_event_ignored(feed_provider: str, feed_valid_id: str, ignored: bool) -> None:
    """Add or remove (feed_provider, feed_valid_id) from feeder_ignored_events.csv."""
    if not FEEDER_IGNORED_EVENTS_PATH:
        return
    feed_provider = (feed_provider or "").strip()
    feed_valid_id = (feed_valid_id or "").strip()
    current = _load_feeder_ignored_set()
    key = (feed_provider, feed_valid_id)
    if ignored:
        current.add(key)
    else:
        current.discard(key)
    FEEDER_IGNORED_EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(FEEDER_IGNORED_EVENTS_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=_FEEDER_IGNORED_FIELDS)
        w.writeheader()
        for (p, v) in sorted(current):
            w.writerow({"feed_provider": p, "feed_valid_id": v})
    _sync_feeder_events_mapping_status()


def _sync_feeder_events_mapping_status() -> None:
    """Re-sync DUMMY_EVENTS mapping_status and domain_id from event_mappings.csv; override to IGNORED if in feeder_ignored_events."""
    ignored_set = _load_feeder_ignored_set() if FEEDER_IGNORED_EVENTS_PATH else set()
    mapped_index = {
        (_m["feed_provider"], _m["feed_valid_id"]): _m["domain_event_id"]
        for _m in _load_event_mappings()
    }
    for _e in DUMMY_EVENTS:
        _key = (_e.get("feed_provider", ""), str(_e.get("valid_id", "")))
        if _key in ignored_set:
            _e["mapping_status"] = "IGNORED"
            _e.pop("domain_id", None)
        elif _key in mapped_index:
            _e["mapping_status"] = "MAPPED"
            _e["domain_id"] = mapped_index[_key]
        else:
            _e["mapping_status"] = "UNMAPPED"
            _e.pop("domain_id", None)


_sync_feeder_events_mapping_status()

def _next_entity_id(entity_type: str) -> int:
    bucket = DOMAIN_ENTITIES[entity_type]
    if not bucket:
        return 1
    return max(e["domain_id"] for e in bucket) + 1

def _sport_name(sport_id: int) -> str:
    s = next((s for s in DOMAIN_ENTITIES["sports"] if s["domain_id"] == sport_id), None)
    return s["name"] if s else ""

def _category_name(cat_id: int) -> str:
    c = next((c for c in DOMAIN_ENTITIES["categories"] if c["domain_id"] == cat_id), None)
    return c["name"] if c else ""

def _normalize_sport_feed_id(value: str | int | float | None) -> str:
    """Canonical form for sport feed_id: numeric -> int string ('5'); else stripped lower."""
    if value is None:
        return ""
    s = (str(value) or "").strip()
    if not s:
        return ""
    try:
        return str(int(float(s)))
    except (ValueError, TypeError):
        return s.lower()


def _resolve_sport_alias(feed_provider_id: int, feed_sport_id_or_name: str) -> dict | None:
    """Return the domain sport dict if a sport mapping exists. Prefer match by feed sport ID, then by sport name (case-insensitive)."""
    incoming = (feed_sport_id_or_name or "").strip()
    if not incoming or feed_provider_id is None:
        return None
    incoming_norm = _normalize_sport_feed_id(incoming)
    incoming_lower = incoming.lower()
    fid = int(feed_provider_id)
    for m in ENTITY_FEED_MAPPINGS:
        if m.get("entity_type") != "sports" or m["feed_provider_id"] != fid:
            continue
        mid = (m.get("feed_id") or "").strip()
        mid_norm = _normalize_sport_feed_id(mid)
        if mid_norm and mid_norm == incoming_norm:
            return next((s for s in DOMAIN_ENTITIES["sports"] if s["domain_id"] == m["domain_id"]), None)
        if mid.lower() == incoming_lower:
            return next((s for s in DOMAIN_ENTITIES["sports"] if s["domain_id"] == m["domain_id"]), None)
    return None


# Register for use in feeder_events template (sport green check)
def _register_sport_feed_id_filter():
    templates.env.filters["normalize_sport_feed_id"] = lambda v: _normalize_sport_feed_id(v)
_register_sport_feed_id_filter()


def _mapped_category_feed_ids_by_sport() -> set[tuple[int, str, int]]:
    """Set of (feed_provider_id, feed_category_id, domain_sport_id) so category green is only for same sport."""
    out: set[tuple[int, str, int]] = set()
    for m in ENTITY_FEED_MAPPINGS:
        if m.get("entity_type") != "categories":
            continue
        cat = next((c for c in DOMAIN_ENTITIES["categories"] if c.get("domain_id") == m.get("domain_id")), None)
        if cat is not None:
            sid = cat.get("sport_id")
            if sid is not None:
                try:
                    out.add((int(m["feed_provider_id"]), str(m.get("feed_id") or "").strip(), int(sid)))
                except (TypeError, ValueError):
                    pass
    return out


def _mapped_comp_feed_ids_by_sport() -> set[tuple[int, str, int]]:
    """Set of (feed_provider_id, feed_comp_id, domain_sport_id) so competition green is only for same sport."""
    out: set[tuple[int, str, int]] = set()
    for m in ENTITY_FEED_MAPPINGS:
        if m.get("entity_type") != "competitions":
            continue
        comp = next((c for c in DOMAIN_ENTITIES["competitions"] if c.get("domain_id") == m.get("domain_id")), None)
        if comp is not None:
            sid = comp.get("sport_id")
            if sid is not None:
                try:
                    out.add((int(m["feed_provider_id"]), str(m.get("feed_id") or "").strip(), int(sid)))
                except (TypeError, ValueError):
                    pass
    return out


def _get_sport_slug(domain_sport_id: int) -> str:
    """Return lowercase sport name with no spaces for sport-specific feed filenames (e.g. volleyball)."""
    sports = DOMAIN_ENTITIES.get("sports") or []
    sport = next((s for s in sports if s.get("domain_id") == domain_sport_id), None)
    if not sport:
        return ""
    name = (sport.get("name") or "").strip()
    return name.lower().replace(" ", "") if name else ""


def _load_feed_markets_from_event_details(
    feed_code: str, feed_sport_id: int, domain_sport_id: int | None
) -> list[dict]:
    """
    Load unique markets from stored event-details JSONs (feed_event_details/{feed_code}/*.json).
    Each file is one event-details API response. Filter by feed_sport_id when event has SportId.
    If sport filter yields no events, include all stored events so at least one cached event shows markets.
    """
    feed_lower = (feed_code or "").strip().lower()
    if feed_lower not in ("bwin", "bet365", "1xbet"):
        return []
    details_dir = config.FEED_EVENT_DETAILS_DIR / feed_lower
    if not details_dir.exists():
        return []

    def _sport_match(ev: dict, fsid: int | None) -> bool:
        if fsid is None:
            return True
        if ev.get("SportId") == fsid or ev.get("sport_id") == fsid:
            return True
        if ev.get("SportId") is None and ev.get("sport_id") is None:
            return True
        return False

    def _collect_events() -> list[dict]:
        out: list[dict] = []
        for path in details_dir.glob("*.json"):
            try:
                with open(path, encoding="utf-8") as f:
                    raw = json.load(f)
            except (json.JSONDecodeError, OSError):
                continue
            event = None
            if isinstance(raw, dict):
                if "results" in raw and isinstance(raw["results"], list):
                    for ev in raw["results"]:
                        if isinstance(ev, dict) and _sport_match(ev, feed_sport_id):
                            out.append(ev)
                    continue
                if "result" in raw and isinstance(raw["result"], dict):
                    event = raw["result"]
                else:
                    event = raw
            if isinstance(event, dict) and _sport_match(event, feed_sport_id):
                out.append(event)
        return out

    results = _collect_events()
    # If sport filter excluded everything (e.g. "All sports" -> Football, but only Volleyball events cached), use all events
    if not results:
        for path in details_dir.glob("*.json"):
            try:
                with open(path, encoding="utf-8") as f:
                    raw = json.load(f)
            except (json.JSONDecodeError, OSError):
                continue
            if isinstance(raw, dict):
                if "results" in raw and isinstance(raw["results"], list):
                    for ev in raw["results"]:
                        if isinstance(ev, dict):
                            results.append(ev)
                elif "result" in raw and isinstance(raw["result"], dict):
                    results.append(raw["result"])
                elif raw.get("Markets") is not None or raw.get("main") is not None or raw.get("Value") is not None:
                    results.append(raw)
    if not results:
        return []
    # Attach sport_name from each event and dedupe by (id, name, sport_name)
    def _with_sport_dedupe(parse_fn, *args):
        all_markets: list[dict] = []
        for event in results:
            sport_name = (event.get("SportName") or event.get("sport_name") or "").strip() or ""
            markets = parse_fn([event], *args) if args else parse_fn([event])
            for m in markets:
                m["sport_name"] = sport_name
                all_markets.append(m)
        seen: set[tuple] = set()
        out: list[dict] = []
        for m in all_markets:
            key = (m.get("id"), m.get("name"), m.get("sport_name", ""), m.get("line") or "")
            if key not in seen:
                seen.add(key)
                out.append(m)
        return out

    if feed_lower == "bet365":
        return _with_sport_dedupe(_parse_bet365_feed_markets)
    if feed_lower == "1xbet":
        return _with_sport_dedupe(_parse_1xbet_feed_markets)
    return _with_sport_dedupe(_parse_bwin_feed_markets, feed_sport_id, True)


def _load_feed_markets_for_sport(
    feed_code: str, feed_sport_id: int, domain_sport_id: int | None = None
) -> list[dict]:
    """
    Load unique markets for a sport from feed JSON. Prefers stored event-details (from create/map),
    then sport-specific example file, then generic feed file.
    Returns list of { "id", "name", "is_prematch" } for the mapping modal.
    """
    feed_lower = (feed_code or "").strip().lower()
    # 1) Stored event details (from event-details API when domain event created/mapped)
    from_stored = _load_feed_markets_from_event_details(feed_code, feed_sport_id, domain_sport_id)
    if from_stored:
        return from_stored

    sport_slug = _get_sport_slug(domain_sport_id) if domain_sport_id is not None else ""
    paths_to_try: list[Path] = []
    if sport_slug:
        paths_to_try.append(FEED_JSON_DIR / f"{feed_code}{sport_slug}.json")
    paths_to_try.append(FEED_DATA_DIR / f"{feed_code}.json")
    paths_to_try.append(FEED_JSON_DIR / f"{feed_code}.json")

    data = None
    used_sport_specific = False
    for path in paths_to_try:
        if path.exists():
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                used_sport_specific = sport_slug and sport_slug in path.name
                break
            except (json.JSONDecodeError, OSError):
                continue
    if not data:
        return []

    if feed_lower == "bet365":
        markets = _parse_bet365_feed_markets(data)
    elif feed_lower == "1xbet":
        markets = _parse_1xbet_feed_markets(data)
    else:
        markets = _parse_bwin_feed_markets(data, feed_sport_id, used_sport_specific)
    sport_name = _get_feed_sport_name(feed_lower, feed_sport_id)
    for m in markets:
        m.setdefault("sport_name", sport_name)
    return markets


def _parse_bwin_feed_markets(
    data: dict | list, feed_sport_id: int, skip_sport_filter: bool = False
) -> list[dict]:
    """Extract unique markets from Bwin-style results. Uses templateId as market ID. One entry per market ID;
    line (attr) is not part of identity - lines vary per match, so we do not create separate list entries per line."""
    if isinstance(data, list):
        results = data
    else:
        results = data.get("results") or []
    by_key: dict[int, dict] = {}
    for event in results:
        if not skip_sport_filter and event.get("SportId") != feed_sport_id:
            continue
        is_prematch = event.get("IsPreMatch", True)
        for item in (event.get("Markets") or []) + (event.get("optionMarkets") or []):
            tc = item.get("templateCategory") or {}
            template_id = item.get("templateId")
            if template_id is None:
                template_id = tc.get("id")
            if template_id is None:
                continue
            try:
                mid = int(template_id)
            except (TypeError, ValueError):
                continue
            if mid in by_key:
                continue
            name = (item.get("name") or {}).get("value") or ""
            if not name:
                name = (tc.get("name") or {}).get("value") or ""
            name = (name or "").strip() or ("(id " + str(mid) + ")")
            by_key[mid] = {"id": mid, "name": name, "is_prematch": is_prematch, "line": None}
    return list(by_key.values())


# Bet365: Game Lines (910000) and Set 1 Lines (910204) each contain 3 market types in one block; split into 3 virtual markets.
_BET365_GAME_LINES_ID = "910000"
_BET365_SET1_LINES_ID = "910204"
_BET365_GAME_LINES_SUBMARKETS = (
    ("Winner", "1", "Game Lines - Winner"),
    ("Handicap", "2", "Game Lines - Handicap"),
    ("Total", "3", "Game Lines - Total"),
)
_BET365_SET1_LINES_SUBMARKETS = (
    ("Winner", "1", "Set 1 Lines - Winner"),
    ("Handicap", "2", "Set 1 Lines - Handicap"),
    ("Total", "3", "Set 1 Lines - Total"),
)


def _bet365_lines_split(block: dict, base_id: str, base_name: str, submarkets: tuple) -> list[dict]:
    """If block has Winner/Handicap/Total submarkets, return 3 markets (base_id_1, _2, _3). Else return single market."""
    odds = block.get("odds") or []
    if not isinstance(odds, list):
        return [{"id": base_id, "name": base_name, "is_prematch": True}]
    seen_names: set[str] = set()
    for o in odds:
        if isinstance(o, dict):
            n = (o.get("name") or "").strip()
            if n in ("Winner", "Handicap", "Total"):
                seen_names.add(n)
    if not seen_names:
        return [{"id": base_id, "name": base_name, "is_prematch": True}]
    out: list[dict] = []
    for sub_name, suffix, display_name in submarkets:
        if sub_name in seen_names:
            out.append({"id": f"{base_id}_{suffix}", "name": display_name, "is_prematch": True})
    return out if out else [{"id": base_id, "name": base_name, "is_prematch": True}]


def _parse_bet365_feed_markets(data: dict | list) -> list[dict]:
    """Extract unique market types from Bet365 results (main.sp + others[].sp). Game Lines (910000) and Set 1 Lines (910204) split into Winner/Handicap/Total."""
    if isinstance(data, list):
        results = data
    else:
        results = data.get("results") or []
    by_key: dict[tuple, dict] = {}

    def _process_sp(sp: dict) -> None:
        for market_key, block in (sp or {}).items():
            if not isinstance(block, dict):
                continue
            mid = str(block.get("id") or market_key)
            base_name = (block.get("name") or market_key.replace("_", " ").title()).strip()
            if mid == _BET365_GAME_LINES_ID:
                for m in _bet365_lines_split(block, mid, base_name, _BET365_GAME_LINES_SUBMARKETS):
                    key = (m["id"], m["name"])
                    if key not in by_key:
                        by_key[key] = m
            elif mid == _BET365_SET1_LINES_ID:
                for m in _bet365_lines_split(block, mid, base_name, _BET365_SET1_LINES_SUBMARKETS):
                    key = (m["id"], m["name"])
                    if key not in by_key:
                        by_key[key] = m
            else:
                key = (mid, base_name)
                if key not in by_key:
                    by_key[key] = {"id": mid, "name": base_name, "is_prematch": True}

    for event in results:
        main_sp = (event.get("main") or {}).get("sp") or {}
        _process_sp(main_sp)
        for other in event.get("others") or []:
            sp = (other or {}).get("sp") or {}
            _process_sp(sp)
    return list(by_key.values())


def _parse_1xbet_feed_markets(data: dict | list) -> list[dict]:
    """Extract unique market types from 1xbet results (Value.SG segments + MEC)."""
    if isinstance(data, list):
        results = data
    else:
        results = data.get("results") or []
    by_key: dict[tuple, dict] = {}
    for event in results:
        value = event.get("Value") or event.get("value") or {}
        for seg in value.get("SG") or []:
            if not isinstance(seg, dict):
                continue
            seg_id = seg.get("I") or seg.get("N")
            pn = (seg.get("PN") or "").strip() or "Match"
            for mec in seg.get("MEC") or []:
                if not isinstance(mec, dict):
                    continue
                mt = mec.get("MT")
                n = (mec.get("N") or "").strip()
                if not n or n == "All markets":
                    continue
                mid = f"{seg_id}_{mt}"
                name = f"{pn} – {n}" if pn else n
                key = (mid, name)
                if key not in by_key:
                    by_key[key] = {"id": mid, "name": name, "is_prematch": True}
    return list(by_key.values())


def _extract_bwin_market_odds(events_data: list[dict] | dict, feed_market_id: str) -> dict:
    """From Bwin event details, extract outcomes and line (attr) for market by templateId (or categoryId for legacy). Returns {outcomes: [...], line: str}.
    For OVERUNDER/total markets (e.g. 6356, 9210), line comes from attr; if attr is missing, derive from outcome names (e.g. 'Over 45,5' -> '45,5')."""
    import re
    results = events_data if isinstance(events_data, list) else (events_data.get("results") or [])
    fid = str(feed_market_id).strip()
    for event in results:
        for m in (event.get("Markets") or []) + (event.get("optionMarkets") or []):
            template_id = m.get("templateId")
            if template_id is not None and str(template_id).strip() == fid:
                pass
            else:
                tc = m.get("templateCategory")
                cid = m.get("categoryId")
                tid = (tc.get("id") if isinstance(tc, dict) else None) or cid
                if tid is None or str(tid).strip() != fid:
                    continue
            outcomes = []
            for r in m.get("results") or []:
                name = (r.get("name") or {}).get("value") or (r.get("sourceName") or {}).get("value") or ""
                odds = r.get("odds")
                if odds is not None:
                    outcomes.append({"name": str(name).strip() or "—", "price": str(odds)})
            line = (m.get("attr") or "").strip() or ""
            # Fallback for OVERUNDER/total (6356, 9210): parse line from outcome names if attr missing
            if not line and len(outcomes) >= 2:
                first_name = (outcomes[0].get("name") or "").strip()
                # e.g. "Over 45,5" or "Over 148,5" -> "45,5" / "148,5"
                match = re.search(r"(?:Over|Under)\s+([\d,\.]+)", first_name, re.IGNORECASE)
                if match:
                    line = match.group(1).strip()
            return {"outcomes": outcomes, "line": line}
    return {"outcomes": [], "line": ""}


def _extract_bet365_market_odds(events_data: list[dict] | dict, feed_market_id: str) -> list[dict]:
    """From Bet365 event details, extract outcomes for market. Handles 910000_1/2/3 (Game Lines) and 910204_1/2/3 (Set 1 Lines) submarkets."""
    results = events_data if isinstance(events_data, list) else (events_data.get("results") or [])
    fid = str(feed_market_id).strip()
    base_id, suffix = (fid.split("_", 1) + [""])[:2]  # e.g. "910000_1" -> base "910000", suffix "1"

    def from_sp(sp: dict) -> list[dict]:
        if not sp:
            return []
        for block in (sp or {}).values():
            if not isinstance(block, dict):
                continue
            bid = str(block.get("id") or "").strip()
            if bid != base_id:
                continue
            odds_list = block.get("odds") or []
            if suffix == "1":  # Winner
                sub = [o for o in odds_list if isinstance(o, dict) and (o.get("name") or "").strip() == "Winner"]
            elif suffix == "2":  # Handicap
                sub = [o for o in odds_list if isinstance(o, dict) and (o.get("name") or "").strip() == "Handicap"]
            elif suffix == "3":  # Total
                sub = [o for o in odds_list if isinstance(o, dict) and (o.get("name") or "").strip() == "Total"]
            else:
                sub = odds_list
            outcomes = []
            for o in sub:
                if not isinstance(o, dict):
                    continue
                header = str(o.get("header") or "").strip()
                price = o.get("odds")
                if price is not None:
                    outcomes.append({"name": header or "—", "price": str(price)})
            return outcomes
        return []

    for event in results:
        main_sp = (event.get("main") or {}).get("sp") or {}
        out = from_sp(main_sp)
        if out:
            return out
        for other in event.get("others") or []:
            out = from_sp((other or {}).get("sp") or {})
            if out:
                return out
    return []


def _extract_1xbet_market_odds(_events_data: list[dict] | dict, _feed_market_id: str) -> list[dict]:
    """From 1xbet event details, extract outcomes for market. Structure differs; return empty for now."""
    return []


def _get_feed_odds_for_event_market(domain_event_id: str, domain_market_id: int) -> list[dict]:
    """Return list of { feed_name, feed_market_id, outcomes: [{ name, price }] } from cached event details and market type mappings."""
    event_mappings = [m for m in _load_event_mappings() if (m.get("domain_event_id") or "").strip() == str(domain_event_id).strip()]
    mt_mappings = [m for m in _load_market_type_mappings() if m.get("domain_market_id") == domain_market_id]
    feed_by_id = {f["domain_id"]: f for f in FEEDS}
    code_by_id = {f["domain_id"]: (f.get("code") or "").strip().lower() for f in FEEDS}
    result: list[dict] = []
    for em in event_mappings:
        feed_provider_str = (em.get("feed_provider") or "").strip().lower()
        feed_valid_id = (em.get("feed_valid_id") or "").strip()
        if not feed_valid_id:
            continue
        feed_obj = next((f for f in FEEDS if (f.get("code") or "").strip().lower() == feed_provider_str), None)
        if not feed_obj:
            continue
        feed_provider_id = feed_obj["domain_id"]
        feed_name = feed_obj.get("name") or feed_obj.get("code") or feed_provider_str
        mt = next((m for m in mt_mappings if m.get("feed_provider_id") == feed_provider_id), None)
        if not mt:
            result.append({"feed_name": feed_name, "feed_market_id": "", "outcomes": []})
            continue
        feed_market_id = str(mt.get("feed_market_id") or "").strip()
        if feed_provider_str == "bet365" and feed_market_id == "910000":
            feed_market_id = "910000_1"
        if feed_provider_str == "bet365" and feed_market_id == "910204":
            feed_market_id = "910204_1"
        path = config.FEED_EVENT_DETAILS_DIR / feed_provider_str / f"{feed_valid_id}.json"
        if not path.exists():
            result.append({"feed_name": feed_name, "feed_market_id": feed_market_id, "outcomes": []})
            continue
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            result.append({"feed_name": feed_name, "feed_market_id": feed_market_id, "outcomes": []})
            continue
        events_list = data.get("results") if isinstance(data, dict) else (data if isinstance(data, list) else [])
        if feed_provider_str == "bwin":
            bwin_data = _extract_bwin_market_odds(events_list or data, feed_market_id)
            outcomes = bwin_data.get("outcomes") or []
            line = bwin_data.get("line") or ""
            result.append({"feed_name": feed_name, "feed_market_id": feed_market_id, "outcomes": outcomes, "line": line})
        elif feed_provider_str == "bet365":
            outcomes = _extract_bet365_market_odds(events_list or data, feed_market_id)
            result.append({"feed_name": feed_name, "feed_market_id": feed_market_id, "outcomes": outcomes})
        elif feed_provider_str == "1xbet":
            outcomes = _extract_1xbet_market_odds(events_list or data, feed_market_id)
            result.append({"feed_name": feed_name, "feed_market_id": feed_market_id, "outcomes": outcomes})
        else:
            result.append({"feed_name": feed_name, "feed_market_id": feed_market_id, "outcomes": []})
    return result


def _resolve_entity(etype: str, feed_id: str, feed_provider_id: int, domain_sport_id: int | None = None) -> dict | None:
    """
    Look up a domain entity by its raw feed_id and provider (from entity_feed_mappings).
    For categories and competitions: when domain_sport_id is given, only return an entity that belongs to that sport.
    (Feeds like Bwin reuse the same category_id across sports; we must match within the event's sport.)
    """
    if feed_id is None or feed_provider_id is None:
        return None
    feed_id_str = str(feed_id).strip()
    if not feed_id_str:
        return None
    # Sports: case-insensitive feed_id match (feed sport name may vary in casing)
    if etype == "sports":
        feed_id_lower = feed_id_str.lower()
        mapping = next((m for m in ENTITY_FEED_MAPPINGS
                       if m["entity_type"] == "sports"
                       and m["feed_provider_id"] == int(feed_provider_id)
                       and (m.get("feed_id") or "").strip().lower() == feed_id_lower), None)
    else:
        mapping = next((m for m in ENTITY_FEED_MAPPINGS
                       if m["entity_type"] == etype
                       and m["feed_provider_id"] == int(feed_provider_id)
                       and str(m["feed_id"]) == feed_id_str), None)
    if not mapping:
        return None
    entity = next((e for e in DOMAIN_ENTITIES[etype] if e["domain_id"] == mapping["domain_id"]), None)
    if not entity:
        return None
    # Categories and competitions are sport-scoped: only match if the entity's sport is the event's sport
    if domain_sport_id is not None and etype in ("categories", "competitions"):
        if (entity.get("sport_id") or 0) != domain_sport_id:
            return None
    return entity


def _fuzzy_score(a: str, b: str) -> int:
    """Return similarity 0-100 between two strings (case-insensitive)."""
    if not a or not b:
        return 0
    a, b = a.strip().lower(), b.strip().lower()
    if a == b:
        return 100
    return int(round(100 * difflib.SequenceMatcher(None, a, b).ratio()))


def _suggest_domain_events(feed_event: dict) -> list[dict]:
    """
    Find all matching domain events for this feed event (same match from another feed).
    Supports reverse home/away (feed home vs domain away, feed away vs domain home).
    Returns list of { "event": dict, "score": int, "reversed_home_away": bool } sorted by score desc.
    """
    if not DOMAIN_EVENTS:
        return []
    feed_home = (feed_event.get("raw_home_name") or "").strip()
    feed_away = (feed_event.get("raw_away_name") or "").strip()
    feed_comp = (feed_event.get("raw_league_name") or "").strip()
    feed_start = (feed_event.get("start_time") or "").strip()
    if not feed_home and not feed_away:
        return []
    candidates: list[dict] = []
    for ev in DOMAIN_EVENTS:
        d_home = (ev.get("home") or "").strip()
        d_away = (ev.get("away") or "").strip()
        d_comp = (ev.get("competition") or "").strip()
        d_start = (ev.get("start_time") or "").strip()
        s_comp = _fuzzy_score(feed_comp, d_comp) if feed_comp or d_comp else 100
        s_start = 100 if feed_start and d_start and feed_start == d_start else (50 if feed_start and d_start else 100)
        # Normal: feed_home↔domain_home, feed_away↔domain_away
        s_home_n = _fuzzy_score(feed_home, d_home) if feed_home and d_home else (100 if not feed_home and not d_home else 0)
        s_away_n = _fuzzy_score(feed_away, d_away) if feed_away and d_away else (100 if not feed_away and not d_away else 0)
        score_n = int(round(0.4 * s_home_n + 0.4 * s_away_n + 0.15 * s_comp + 0.05 * s_start))
        # Reversed: feed_home↔domain_away, feed_away↔domain_home
        s_home_r = _fuzzy_score(feed_home, d_away) if feed_home and d_away else (100 if not feed_home and not d_away else 0)
        s_away_r = _fuzzy_score(feed_away, d_home) if feed_away and d_home else (100 if not feed_away and not d_home else 0)
        score_r = int(round(0.4 * s_home_r + 0.4 * s_away_r + 0.15 * s_comp + 0.05 * s_start))
        best_score = max(score_n, score_r)
        if best_score >= 50:
            candidates.append({
                "event": ev,
                "score": best_score,
                "reversed_home_away": score_r > score_n,
            })
    candidates.sort(key=lambda x: -x["score"])
    return candidates


def _suggest_entity_by_name(
    etype: str, feed_name: str, sport_id: int | None, category_id: int | None = None
) -> list[dict]:
    """
    Suggest domain entities matching feed_name within sport (and category for competitions).
    Returns list of { "name", "domain_id", "match_pct" } sorted by match_pct desc.
    """
    if not feed_name or not feed_name.strip():
        return []
    feed_name = feed_name.strip()
    bucket = DOMAIN_ENTITIES.get(etype, [])
    candidates = []
    for e in bucket:
        if sport_id is not None and e.get("sport_id") != sport_id:
            continue
        if etype == "competitions" and category_id is not None and e.get("category_id") != category_id:
            continue
        name = (e.get("name") or "").strip()
        if not name:
            continue
        pct = _fuzzy_score(feed_name, name)
        if pct >= 30:
            candidates.append({"name": name, "domain_id": e["domain_id"], "match_pct": pct})
    candidates.sort(key=lambda x: -x["match_pct"])
    return candidates[:10]


def _suggest_sport_by_feed_name(feed_sport_name: str) -> list[dict]:
    """Suggest domain sports matching feed sport name (e.g. Soccer -> Football). Returns [{ name, domain_id, match_pct }]."""
    if not feed_sport_name or not feed_sport_name.strip():
        return []
    feed_sport_name = feed_sport_name.strip()
    out = []
    for s in DOMAIN_ENTITIES["sports"]:
        name = (s.get("name") or "").strip()
        if not name:
            continue
        pct = _fuzzy_score(feed_sport_name, name)
        if pct >= 30:
            out.append({"name": name, "domain_id": s["domain_id"], "match_pct": pct})
    out.sort(key=lambda x: -x["match_pct"])
    return out[:10]


# (Request/response models imported from backend.schemas)

@app.post("/api/market-groups")
async def create_market_group(body: CreateMarketGroupRequest):
    """Create a new market group (domain_id, code, name). Persisted to data/markets/market_groups.csv."""
    code = (body.code or "").strip()
    name = (body.name or "").strip()
    if not name:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Name is required")
    if not code:
        code = name.lower().replace(" ", "_")[:32]
    groups = _load_market_groups()
    existing = next((g for g in groups if (g.get("code") or "").lower() == code.lower()), None)
    if existing:
        return {"domain_id": existing["domain_id"], "code": existing["code"], "name": existing["name"], "created": False}
    domain_id = _save_market_group(code, name)
    return {"domain_id": domain_id, "code": code, "name": name, "created": True}

@app.post("/api/entities")
async def create_entity(body: CreateEntityRequest):
    """
    Create a domain entity (sport/category/competition/team).
    Idempotent per type. Uses integer FKs for relational integrity.
    """
    from fastapi import HTTPException
    bucket = DOMAIN_ENTITIES.get(body.entity_type)
    if bucket is None:
        raise HTTPException(status_code=400, detail=f"Unknown entity type: {body.entity_type}")
    if body.entity_type == "sports":
        raise HTTPException(status_code=400, detail="Sports cannot be created from backoffice. Add them in code/data and map in entity feed mappings.")

    # Resolve parent FKs from names ─────────────────────────────────────────
    sport_id: Optional[int] = None
    category_id: Optional[int] = None

    if body.entity_type in ("categories", "competitions", "teams", "markets") and body.sport:
        sport_key = (body.sport or "").strip().lower()
        sp = next((s for s in DOMAIN_ENTITIES["sports"] if (s.get("name") or "").strip().lower() == sport_key), None)
        if sp:
            sport_id = sp["domain_id"]
        else:
            raise HTTPException(status_code=400, detail=f"Sport '{body.sport}' not found. Create it in Entities first.")
    if body.entity_type == "categories" and (not body.sport or not str(body.sport).strip()):
        raise HTTPException(status_code=400, detail="Sport is required to create a category. Ensure the feed's sport is mapped by the developer.")
    if body.entity_type == "markets" and (not body.sport or not str(body.sport).strip()):
        raise HTTPException(status_code=400, detail="Sport is required to create a market. Select the sport in which this market applies.")

    if body.entity_type == "competitions" and body.category:
        cp = next((c for c in DOMAIN_ENTITIES["categories"]
                   if c["name"].lower() == body.category.lower()
                   and c.get("sport_id") == sport_id), None)
        if cp:
            category_id = cp["domain_id"]
        else:
            raise HTTPException(status_code=400, detail=f"Category '{body.category}' not found under sport '{body.sport}'.")

    # For teams/categories/competitions/markets: check if this feed already maps to a domain entity (idempotent)
    # For categories/competitions, same feed_id can map to different domain entities per sport (e.g. Bwin 38 = Argentina Football vs Argentina Basketball)
    if body.entity_type in ("categories", "competitions", "teams", "markets") and body.feed_id and body.feed_provider_id:
        already_mapped = next((m for m in ENTITY_FEED_MAPPINGS
                              if m["entity_type"] == body.entity_type
                              and m["feed_provider_id"] == body.feed_provider_id
                              and str(m["feed_id"]) == str(body.feed_id)), None)
        if already_mapped:
            e = next((x for x in bucket if x["domain_id"] == already_mapped["domain_id"]), None)
            if e:
                # Only treat as "already mapped" if the entity is for the same sport (and category for competitions)
                if body.entity_type == "categories" and (e.get("sport_id") or 0) != (sport_id or 0):
                    pass  # different sport → create new category with new id
                elif body.entity_type == "competitions" and ((e.get("sport_id") or 0) != (sport_id or 0) or (e.get("category_id") or 0) != (category_id or 0)):
                    pass  # different sport/category → create new competition
                elif body.entity_type == "teams" and (e.get("sport_id") or 0) != (sport_id or 0):
                    pass  # different sport → create new team
                else:
                    return {"domain_id": e["domain_id"], "name": e["name"], "created": False}

    # Deduplication: same name+sport (and category for comp) → link this feed to existing entity
    if body.entity_type == "sports":
        existing = next((e for e in bucket if e["name"].lower() == body.name.lower()), None)
    elif body.entity_type == "markets":
        existing = next((e for e in bucket if (e.get("sport_id")) == sport_id and (e.get("name") or "").strip().lower() == (body.name or "").strip().lower()), None)
    elif body.entity_type == "categories":
        existing = next((e for e in bucket if e.get("sport_id") == sport_id
                         and e["name"].lower() == body.name.lower()), None)
    elif body.entity_type == "competitions":
        existing = next((e for e in bucket if e.get("sport_id") == sport_id
                         and e.get("category_id") == category_id
                         and e["name"].lower() == body.name.lower()), None)
    else:  # teams
        existing = next((e for e in bucket if e.get("sport_id") == sport_id
                         and e["name"].lower() == body.name.lower()), None)

    if existing and body.entity_type in ("categories", "competitions", "teams", "markets") and body.feed_id and body.feed_provider_id:
        # Link this feed to the existing domain entity (multi-feed reference)
        already_in_mappings = any(
            m["entity_type"] == body.entity_type and m["domain_id"] == existing["domain_id"]
            and m["feed_provider_id"] == body.feed_provider_id and str(m["feed_id"]) == str(body.feed_id)
            for m in ENTITY_FEED_MAPPINGS
        )
        if not already_in_mappings:
            ENTITY_FEED_MAPPINGS.append({
                "entity_type": body.entity_type,
                "domain_id": existing["domain_id"],
                "feed_provider_id": body.feed_provider_id,
                "feed_id": str(body.feed_id),
            })
            _save_entity_feed_mapping(body.entity_type, existing["domain_id"], body.feed_provider_id, body.feed_id)
        return {"domain_id": existing["domain_id"], "name": existing["name"], "created": False}

    if existing:
        return {"domain_id": existing["domain_id"], "name": existing["name"], "created": False}

    # Create new entity (no feed columns on entity table)
    _now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
    domain_id = _next_entity_id(body.entity_type)
    entity: dict = {"domain_id": domain_id, "name": body.name, "created_at": _now, "updated_at": _now}
    if body.entity_type in ("sports", "categories", "competitions", "teams"):
        baseid_val = (body.baseid or "").strip()
        if baseid_val:
            if any((e.get("baseid") or "").strip() == baseid_val for e in bucket):
                raise HTTPException(status_code=400, detail=f"Another {body.entity_type[:-1]} already has baseid '{baseid_val}'.")
        entity["baseid"] = baseid_val
    if body.entity_type == "markets":
        entity["sport_id"] = sport_id
        entity["code"] = (body.code or "").strip()
        entity["abb"] = (body.abb or "").strip()
        entity["market_type"] = (body.market_type or "").strip()
        entity["market_group"] = (body.market_group or "").strip()
        entity["template"] = (body.template or "").strip()
        entity["period_type"] = (body.period_type or "").strip()
        entity["score_type"] = (body.score_type or "").strip()
        entity["side_type"] = (body.side_type or "").strip()
        entity["score_dependant"] = "1" if body.score_dependant else "0"

    if body.entity_type in ("sports", "markets"):
        pass  # name only for sports; markets have code and sport_id set above
    elif body.entity_type in ("categories", "teams"):
        entity["sport_id"] = sport_id
        entity["jurisdiction"] = (body.jurisdiction or "").strip() or COUNTRY_CODE_NONE
        if body.entity_type == "teams":
            entity["underage_category_id"] = body.underage_category_id
            entity["participant_type_id"] = body.participant_type_id
            entity["is_amateur"] = bool(body.is_amateur) if body.is_amateur is not None else False
    elif body.entity_type == "competitions":
        entity["sport_id"]         = sport_id
        entity["category_id"]      = category_id
        entity["jurisdiction"]    = (body.jurisdiction or "").strip() or COUNTRY_CODE_NONE
        entity["underage_category_id"] = body.underage_category_id
        entity["participant_type_id"] = body.participant_type_id
        entity["is_amateur"] = bool(body.is_amateur)

    bucket.append(entity)
    # Build CSV row with string values for optional int/bool columns
    save_row = dict(entity)
    if body.entity_type == "teams":
        save_row["underage_category_id"] = str(entity["underage_category_id"]) if entity.get("underage_category_id") else ""
        save_row["participant_type_id"] = str(entity["participant_type_id"]) if entity.get("participant_type_id") else ""
        save_row["is_amateur"] = "1" if entity.get("is_amateur") else "0"
    elif body.entity_type == "competitions":
        save_row["underage_category_id"] = str(entity["underage_category_id"]) if entity.get("underage_category_id") else ""
        save_row["participant_type_id"] = str(entity["participant_type_id"]) if entity.get("participant_type_id") else ""
        save_row["is_amateur"] = "1" if entity.get("is_amateur") else "0"
    _save_entity(body.entity_type, save_row)

    # New competitions are automatically assigned to Uncategorized margin template
    if body.entity_type == "competitions":
        _assign_competition_to_margin_template(domain_id, 1)

    # Record feed → domain entity mapping (one row per feed reference)
    if body.entity_type in ("categories", "competitions", "teams", "markets") and body.feed_id and body.feed_provider_id:
        ENTITY_FEED_MAPPINGS.append({
            "entity_type": body.entity_type,
            "domain_id": domain_id,
            "feed_provider_id": body.feed_provider_id,
            "feed_id": str(body.feed_id),
        })
        _save_entity_feed_mapping(body.entity_type, domain_id, body.feed_provider_id, body.feed_id)

    # Record feed-sport → domain-sport mapping (prefer feed sport ID when available, else name)
    if sport_id and body.feed_provider_id and (body.feed_sport_id is not None or body.feed_sport):
        _feed_sport_val = (str(body.feed_sport_id).strip() if body.feed_sport_id is not None and str(body.feed_sport_id).strip() else (body.feed_sport or "").strip())
        if _feed_sport_val:
            _ensure_entity_feed_mapping("sports", sport_id, body.feed_provider_id, _feed_sport_val)

    return {"domain_id": domain_id, "name": body.name, "created": True}


@app.post("/api/entities/name")
async def update_entity_name(body: UpdateEntityNameRequest):
    """
    Rename an existing domain entity (sports/categories/competitions/teams) from the Entities UI.
    Only the display name (and updated_at) is changed; relationships stay the same.
    """
    from fastapi import HTTPException

    allowed_types = ("sports", "categories", "competitions", "teams")
    if body.entity_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Renaming is only supported for sports, categories, competitions, and teams.")

    new_name = (body.name or "").strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="Name is required")

    bucket = DOMAIN_ENTITIES.get(body.entity_type) or []
    entity = next((e for e in bucket if e["domain_id"] == body.domain_id), None)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    _now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
    jurisdiction_val: str | None = None
    baseid_val: str | None = None

    if body.entity_type in ("categories", "competitions", "teams") and body.jurisdiction is not None:
        jurisdiction_val = (body.jurisdiction or "").strip() or COUNTRY_CODE_NONE
        entity["jurisdiction"] = jurisdiction_val

    if body.entity_type in ("sports", "categories", "competitions", "teams") and body.baseid is not None:
        baseid_val = (body.baseid or "").strip()
        if baseid_val:
            other = next((e for e in bucket if e["domain_id"] != body.domain_id and (e.get("baseid") or "").strip() == baseid_val), None)
            if other:
                singular = body.entity_type[:-1]  # sport, category, competition, team
                raise HTTPException(status_code=400, detail=f"Another {singular} already has baseid '{baseid_val}'.")
        entity["baseid"] = baseid_val

    if body.entity_type == "teams":
        if body.participant_type_id is not None:
            entity["participant_type_id"] = body.participant_type_id
        if body.underage_category_id is not None:
            entity["underage_category_id"] = body.underage_category_id
        if body.is_amateur is not None:
            entity["is_amateur"] = body.is_amateur
    if body.entity_type == "competitions":
        if body.underage_category_id is not None:
            entity["underage_category_id"] = body.underage_category_id
        if body.is_amateur is not None:
            entity["is_amateur"] = body.is_amateur

    entity["name"] = new_name
    entity["updated_at"] = _now

    _update_entity_name(
        body.entity_type,
        body.domain_id,
        new_name,
        _now,
        jurisdiction=jurisdiction_val,
        baseid=baseid_val,
        participant_type_id=body.participant_type_id if body.entity_type == "teams" else None,
        underage_category_id=body.underage_category_id if body.entity_type in ("teams", "competitions") else None,
        is_amateur=body.is_amateur if body.entity_type in ("teams", "competitions") else None,
    )

    for m in ENTITY_FEED_MAPPINGS:
        if m["entity_type"] == body.entity_type and m["domain_id"] == body.domain_id:
            m["domain_name"] = new_name

    return {"domain_id": body.domain_id, "name": new_name, "jurisdiction": jurisdiction_val, "baseid": baseid_val}


@app.post("/api/entities/jurisdiction")
async def update_entity_jurisdiction(body: UpdateEntityJurisdictionRequest):
    """Update jurisdiction (country code or '-') for a category, competition, or team."""
    from fastapi import HTTPException

    if body.entity_type not in ("categories", "competitions", "teams"):
        raise HTTPException(status_code=400, detail="Jurisdiction is only supported for categories, competitions, and teams.")

    jurisdiction = (body.jurisdiction or "").strip() or COUNTRY_CODE_NONE
    bucket = DOMAIN_ENTITIES.get(body.entity_type) or []
    entity = next((e for e in bucket if e["domain_id"] == body.domain_id), None)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found.")

    _now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
    entity["jurisdiction"] = jurisdiction
    entity["updated_at"] = _now
    _update_entity_jurisdiction(body.entity_type, body.domain_id, jurisdiction, _now)
    return {"domain_id": body.domain_id, "jurisdiction": jurisdiction}


@app.get("/api/entities/markets/{domain_id:int}")
async def get_market(domain_id: int):
    """Return a single market by domain_id for edit form."""
    from fastapi import HTTPException

    bucket = DOMAIN_ENTITIES.get("markets") or []
    entity = next((e for e in bucket if e["domain_id"] == domain_id), None)
    if not entity:
        raise HTTPException(status_code=404, detail="Market not found.")
    return entity


@app.patch("/api/entities/markets/{domain_id:int}")
async def update_market(domain_id: int, body: UpdateMarketRequest):
    """Update a market type by domain_id. All fields optional."""
    from fastapi import HTTPException

    bucket = DOMAIN_ENTITIES.get("markets") or []
    entity = next((e for e in bucket if e["domain_id"] == domain_id), None)
    if not entity:
        raise HTTPException(status_code=404, detail="Market not found.")

    _now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
    kwargs = {}
    if body.name is not None:
        kwargs["name"] = body.name
    if body.code is not None:
        kwargs["code"] = body.code
    if body.abb is not None:
        kwargs["abb"] = body.abb
    if body.market_type is not None:
        kwargs["market_type"] = body.market_type
    if body.market_group is not None:
        kwargs["market_group"] = body.market_group
    if body.template is not None:
        kwargs["template"] = body.template
    if body.period_type is not None:
        kwargs["period_type"] = body.period_type
    if body.score_type is not None:
        kwargs["score_type"] = body.score_type
    if body.side_type is not None:
        kwargs["side_type"] = body.side_type
    if body.score_dependant is not None:
        kwargs["score_dependant"] = body.score_dependant

    _update_entity_market(domain_id, _now, **kwargs)
    return {"domain_id": domain_id, "updated_at": _now}


async def _fetch_and_save_event_details(feed_provider: str, feed_valid_id: str) -> None:
    """Background: fetch event details from BetsAPI and save under feed_event_details/{feed}/{id}.json. Token from .env (BETSAPI_TOKEN)."""
    token = (config.BETSAPI_TOKEN or "").strip()
    if not token:
        return
    feed_code = (feed_provider or "").strip().lower()
    if feed_code not in ("bwin", "bet365", "1xbet"):
        return
    try:
        data = await feed_pull.fetch_event_details_async(feed_code, feed_valid_id, token)
        if data:
            feed_pull.save_event_details(feed_code, feed_valid_id, data)
    except Exception:
        pass  # Don't fail create/map if details fetch fails


@app.post("/api/domain-events")
async def create_domain_event(body: CreateDomainEventRequest):
    """
    API Endpoint: Create a new domain event from feed data and auto-map the feeder event.
    """
    # Generate a new unique domain event ID
    new_id = f"G-{uuid.uuid4().hex[:8].upper()}"

    # Build the in-memory event dict (empty string for missing IDs so CSV and lookups work)
    new_event = {
        "id":          new_id,
        "sport":       body.sport,
        "category":    body.category,
        "competition": body.competition,
        "home":        body.home,
        "home_id":     (body.home_id or "").strip() if body.home_id else "",
        "away":        body.away,
        "away_id":     (body.away_id or "").strip() if body.away_id else "",
        "start_time":  body.start_time,
    }
    DOMAIN_EVENTS.append(new_event)
    # Persist clean domain event to domain_events.csv
    _save_domain_event(new_event)
    # Record the originating feed mapping in event_mappings.csv (join table)
    _save_event_mapping(new_id, body.feeder_provider, body.feeder_valid_id)

    # Fetch event details in background (BetsAPI token from .env) so we have markets for mapping modal
    if config.BETSAPI_TOKEN and body.feeder_provider and body.feeder_valid_id:
        asyncio.create_task(_fetch_and_save_event_details(body.feeder_provider, body.feeder_valid_id))

    # Also mark the feeder event as MAPPED in memory
    for e in DUMMY_EVENTS:
        if e["feed_provider"] == body.feeder_provider and e["valid_id"] == body.feeder_valid_id:
            e["mapping_status"] = "MAPPED"
            e["domain_id"] = new_id
            break

    event_label = f"{body.home} vs {body.away}" if (body.home and body.away) else (body.home or "Outright Event")

    return HTMLResponse(f"""
        <div class="p-6 bg-slate-800 text-center flex flex-col items-center justify-center h-full">
            <div class="text-emerald-400 text-4xl mb-4"><i class="fa-solid fa-circle-check"></i></div>
            <h3 class="text-white text-lg font-medium">Domain Event Created &amp; Mapped!</h3>
            <p class="text-slate-400 text-sm mt-2">
                <span class="font-mono text-secondary bg-secondary/10 px-2 py-0.5 rounded">{new_id}</span>
            </p>
            <p class="text-slate-500 text-xs mt-1">{event_label}</p>
            <button onclick="closeModal(true)" class="mt-6 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white text-sm rounded transition-all">
                Close
            </button>
        </div>
    """)

# --- Map existing feeder event to existing domain event ---

@app.post("/api/map-event")
async def map_event_to_domain(
    domain_id_selected: str = Form(default=""),
    feeder_provider: str = Form(default=""),
    feeder_valid_id: str = Form(default=""),
):
    """Confirm Mapping: link a feeder event to an existing domain event."""
    from fastapi import HTTPException
    # Validate inputs
    if not domain_id_selected:
        return HTMLResponse("""
            <div class="p-6 text-center text-red-400 text-sm">
                <i class="fa-solid fa-triangle-exclamation mr-2"></i>
                No domain event selected. Search and click a result first.
            </div>
        """)
    # Check domain event exists
    domain_ev = next((e for e in DOMAIN_EVENTS if e["id"] == domain_id_selected), None)
    if not domain_ev:
        return HTMLResponse("""
            <div class="p-6 text-center text-red-400 text-sm">
                <i class="fa-solid fa-triangle-exclamation mr-2"></i>
                Domain event not found.
            </div>
        """)

    # Check not already mapped
    existing = _load_event_mappings()
    already = any(
        m["feed_provider"] == feeder_provider and m["feed_valid_id"] == feeder_valid_id
        for m in existing
    )
    if not already:
        _save_event_mapping(domain_id_selected, feeder_provider, feeder_valid_id)
    # Fetch event details in background (BetsAPI token from .env) so we have markets for mapping modal
    if config.BETSAPI_TOKEN and feeder_provider and feeder_valid_id:
        asyncio.create_task(_fetch_and_save_event_details(feeder_provider, feeder_valid_id))
    _append_feeder_event_log(feeder_provider, feeder_valid_id, "mapped", details=domain_id_selected)

    # Mark feeder event as MAPPED in memory
    feeder_ev = None
    for e in DUMMY_EVENTS:
        if e["feed_provider"] == feeder_provider and e["valid_id"] == feeder_valid_id:
            e["mapping_status"] = "MAPPED"
            e["domain_id"] = domain_id_selected
            feeder_ev = e
            break

    # Ensure entity_feed_mappings for this feed so the second (and later) feed’s entities point to the same domain entities
    if feeder_ev:
        feed_obj = next((f for f in FEEDS if (f.get("code") or "").lower() == (feeder_provider or "").lower()), None)
        feed_pid = int(feed_obj["domain_id"]) if feed_obj else None
        if feed_pid is not None:
            sport_name = (domain_ev.get("sport") or "").strip()
            cat_name = (domain_ev.get("category") or "").strip()
            comp_name = (domain_ev.get("competition") or "").strip()
            sport_ent = next((s for s in DOMAIN_ENTITIES["sports"] if (s.get("name") or "").strip() == sport_name), None)
            sport_domain_id = sport_ent["domain_id"] if sport_ent else None
            # Store feed's sport_id from JSON when present (e.g. bet365 sends only sport_id, no sport name); else fall back to sport name
            _raw_sport_id = feeder_ev.get("sport_id")
            if sport_domain_id and (_raw_sport_id is not None and _raw_sport_id != "" or feeder_ev.get("sport")):
                _feed_sport_val = str(_raw_sport_id).strip() if _raw_sport_id not in (None, "") else (feeder_ev.get("sport") or "").strip()
                if _feed_sport_val:
                    _ensure_entity_feed_mapping("sports", sport_domain_id, feed_pid, _feed_sport_val)
            category_domain_id = None
            if sport_domain_id and cat_name:
                cat_ent = next((c for c in DOMAIN_ENTITIES["categories"] if c.get("sport_id") == sport_domain_id and (c.get("name") or "").strip() == cat_name), None)
                category_domain_id = cat_ent["domain_id"] if cat_ent else None
            if category_domain_id:
                feed_cat_id = (feeder_ev.get("category_id") or feeder_ev.get("category") or "").strip() or None
                if feed_cat_id:
                    _ensure_entity_feed_mapping("categories", category_domain_id, feed_pid, feed_cat_id)
            comp_ent = next((c for c in DOMAIN_ENTITIES["competitions"] if (c.get("name") or "").strip() == comp_name and c.get("sport_id") == sport_domain_id and c.get("category_id") == category_domain_id), None) if sport_domain_id else None
            competition_domain_id = comp_ent["domain_id"] if comp_ent else None
            if competition_domain_id:
                feed_comp_id = (feeder_ev.get("raw_league_id") or feeder_ev.get("raw_league_name") or "").strip() or None
                if feed_comp_id:
                    _ensure_entity_feed_mapping("competitions", competition_domain_id, feed_pid, feed_comp_id)
            def _normalize(s: str) -> str:
                return (s or "").strip().lower()

            for team_key, name_key, feed_id_key, feed_name_key in (
                ("home_id", "home", "raw_home_id", "raw_home_name"),
                ("away_id", "away", "raw_away_id", "raw_away_name"),
            ):
                team_domain_id = None
                try:
                    raw_id = domain_ev.get(team_key)
                    if raw_id is not None and (not isinstance(raw_id, str) or raw_id.strip()):
                        team_domain_id = int(raw_id)
                except (TypeError, ValueError):
                    pass
                if team_domain_id is None and sport_domain_id is not None:
                    team_name = (domain_ev.get(name_key) or "").strip()
                    if team_name:
                        team_name_norm = _normalize(team_name)
                        team_ent = next(
                            (t for t in DOMAIN_ENTITIES["teams"]
                             if t.get("sport_id") == sport_domain_id
                             and _normalize(t.get("name") or "") == team_name_norm),
                            None,
                        )
                        if team_ent:
                            team_domain_id = team_ent["domain_id"]
                feed_team_id_raw = feeder_ev.get(feed_id_key) or feeder_ev.get(feed_name_key)
                feed_team_id = (str(feed_team_id_raw).strip() if feed_team_id_raw is not None else "") or None
                if team_domain_id is not None and feed_team_id:
                    _ensure_entity_feed_mapping("teams", team_domain_id, feed_pid, feed_team_id)

    label = domain_ev.get("home", "") or "Event"
    if domain_ev.get("away"):
        label += f" vs {domain_ev['away']}"

    return HTMLResponse(f"""
        <div class="p-6 bg-slate-800 text-center flex flex-col items-center justify-center h-full">
            <div class="text-emerald-400 text-4xl mb-4"><i class="fa-solid fa-circle-check"></i></div>
            <h3 class="text-white text-lg font-medium">Feed Mapped!</h3>
            <p class="text-slate-400 text-sm mt-2">
                Linked to domain event
                <span class="font-mono text-secondary bg-secondary/10 px-2 py-0.5 rounded">{domain_id_selected}</span>
            </p>
            <p class="text-slate-500 text-xs mt-1">{label}</p>
            <button onclick="closeModal(true)" class="mt-6 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white text-sm rounded transition-all">
                Close
            </button>
        </div>
    """)

@app.get("/api/search-domain-events", response_class=HTMLResponse)
async def search_domain_events(q: str = ""):
    """Search DOMAIN_EVENTS by home/away/competition name for the mapping modal."""
    q_lower = q.strip().lower()
    if q_lower:
        results = [
            e for e in DOMAIN_EVENTS
            if q_lower in (e.get("home") or "").lower()
            or q_lower in (e.get("away") or "").lower()
            or q_lower in (e.get("competition") or "").lower()
            or q_lower in (e.get("id") or "").lower()
        ]
    else:
        results = DOMAIN_EVENTS[:]   # return all when query is empty

    if not results:
        return HTMLResponse(
            '<p class="text-[10px] text-slate-600 italic self-center py-1">'
            "No domain events found. Use 'Create &amp; Map' to create a new one."
            "</p>"
        )

    cards = ""
    for ev in results:
        ev_id = ev["id"]
        home = ev.get("home") or ""
        away = ev.get("away") or ""
        comp = ev.get("competition") or ""
        cat = ev.get("category") or "—"
        start_fmt = _format_start_time(ev.get("start_time")) or "—"
        label = f"{home} vs {away}" if (home and away) else (home or ev_id)
        # Escape for HTML attributes
        label_attr = label.replace("'", "&#39;").replace('"', "&quot;")
        comp_attr = comp.replace("'", "&#39;").replace('"', "&quot;")
        cat_attr = cat.replace("'", "&#39;").replace('"', "&quot;")
        start_attr = start_fmt.replace("'", "&#39;").replace('"', "&quot;")
        cards += f"""
        <div class="domain-event-card p-2 border border-slate-600 bg-slate-800/50 rounded flex justify-between items-center cursor-pointer hover:bg-slate-700/50 hover:border-slate-500 transition-colors w-full"
             data-domain-id="{ev_id}"
             data-label="{label_attr}"
             data-start-time="{start_attr}"
             data-category="{cat_attr}"
             data-competition="{comp_attr}"
             onclick="selectDomainEvent(this)">
            <div class="min-w-0 flex-1">
                <div class="text-white text-xs font-medium">{label}</div>
                <div class="text-[10px] text-slate-400">
                    <span>{start_fmt}</span>
                    <span class="mx-1.5">·</span>
                    <span>{cat}</span>
                    <span class="mx-1.5">·</span>
                    <span>{comp}</span>
                    <span class="mx-1.5">·</span>
                    <span class="font-mono text-slate-500">ID {ev_id}</span>
                </div>
            </div>
        </div>"""

    return HTMLResponse(cards)

# --- Views ---

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """
    Main Dashboard View.
    """
    return templates.TemplateResponse("index.html", {
        "request": request,
        "section": "dashboard"
    })


def _load_feed_last_pulls() -> dict[tuple[str, str], str]:
    """Load feed_last_pull.csv into a dict (feed_provider, feed_sport_id) -> last_pull_at (ISO string)."""
    path = FEED_LAST_PULL_PATH
    out: dict[tuple[str, str], str] = {}
    if not path.exists():
        return out
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            feed = (row.get("feed_provider") or "").strip().lower()
            sport_id = (row.get("feed_sport_id") or "").strip()
            at = (row.get("last_pull_at") or "").strip()
            if feed and at:
                out[(feed, sport_id)] = at
    return out


def _format_last_pull(iso_str: str | None) -> str:
    """Format ISO last_pull_at for display (e.g. 25 Feb 2025, 14:30). Returns '—' if missing."""
    if not iso_str or not iso_str.strip():
        return "—"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%d %b %Y, %H:%M")
    except (ValueError, TypeError):
        return "—"


def _save_feed_last_pull(feed_provider: str, feed_sport_id: str) -> None:
    """Record last pull time for (feed_provider, feed_sport_id) in feed_last_pull.csv."""
    path = FEED_LAST_PULL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    feed_key = (feed_provider or "").strip().lower()
    sport_key = (feed_sport_id or "").strip()
    fieldnames = ["feed_provider", "feed_sport_id", "last_pull_at"]
    key_to_row: dict[tuple[str, str], dict[str, str]] = {}
    if path.exists():
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                k = ((row.get("feed_provider") or "").strip().lower(), (row.get("feed_sport_id") or "").strip())
                key_to_row[k] = {fn: row.get(fn, "") for fn in fieldnames}
    key_to_row[(feed_key, sport_key)] = {
        "feed_provider": feed_key,
        "feed_sport_id": sport_key,
        "last_pull_at": now,
    }
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(key_to_row.values())


@app.get("/pull-feeds", response_class=HTMLResponse)
async def pull_feeds_view(request: Request):
    """Pull Feeds Data screen: manually pull fresh data from each feed (Bet365/Betfair per-sport, Bwin all sports)."""
    rows = _load_feed_sports_rows()
    last_pulls = _load_feed_last_pulls()
    bet365_sports = [r for r in rows if (r.get("feed_provider") or "").strip().lower() == "bet365"]
    betfair_sports = [r for r in rows if (r.get("feed_provider") or "").strip().lower() == "betfair"]
    onexbet_sports = [r for r in rows if (r.get("feed_provider") or "").strip().lower() == "1xbet"]
    bwin_sports = [r for r in rows if (r.get("feed_provider") or "").strip().lower() == "bwin"]
    for s in bet365_sports:
        s["last_pull"] = _format_last_pull(last_pulls.get(("bet365", (s.get("feed_sport_id") or "").strip())))
    for s in betfair_sports:
        s["last_pull"] = _format_last_pull(last_pulls.get(("betfair", (s.get("feed_sport_id") or "").strip())))
    for s in onexbet_sports:
        s["last_pull"] = _format_last_pull(last_pulls.get(("1xbet", (s.get("feed_sport_id") or "").strip())))
    for s in bwin_sports:
        s["last_pull"] = _format_last_pull(last_pulls.get(("bwin", (s.get("feed_sport_id") or "").strip())))
    return templates.TemplateResponse("pull_feeds.html", {
        "request": request,
        "section": "pull_feeds",
        "bet365_sports": bet365_sports,
        "betfair_sports": betfair_sports,
        "onexbet_sports": onexbet_sports,
        "bwin_sports": bwin_sports,
    })


@app.post("/api/pull-feed")
async def api_pull_feed(
    feed_provider: str = Form(...),
    feed_sport_id: str = Form(""),
    feed_sport_name: str = Form(""),
    api_token: str = Form(""),
):
    """
    Pull upcoming/prematch events from a feed. Bet365: per-sport (feed_sport_id required). Bwin: all sports, no sport param.
    API key from request only (not stored). Reloads DUMMY_EVENTS after successful pull.
    """
    from fastapi import HTTPException
    feed_provider = (feed_provider or "").strip().lower()
    feed_sport_id = (feed_sport_id or "").strip()
    feed_sport_name = (feed_sport_name or "").strip()
    token = (api_token or "").strip()

    if feed_provider == "bet365":
        if not feed_sport_id:
            raise HTTPException(status_code=400, detail="feed_sport_id is required for Bet365.")
        if not token:
            return {"ok": False, "added": 0, "skipped": 0, "total": 0, "error": "Please enter API key"}
        if not feed_sport_name:
            for r in _load_feed_sports_rows():
                if (r.get("feed_provider") or "").strip().lower() == "bet365" and (r.get("feed_sport_id") or "").strip() == feed_sport_id:
                    feed_sport_name = (r.get("feed_sport_name") or feed_sport_id).strip()
                    break
            feed_sport_name = feed_sport_name or f"Sport {feed_sport_id}"
        result = await feed_pull.pull_bet365_sport(feed_sport_id, feed_sport_name, token)
    elif feed_provider == "betfair":
        if not feed_sport_id:
            raise HTTPException(status_code=400, detail="feed_sport_id is required for Betfair.")
        if not token:
            return {"ok": False, "added": 0, "skipped": 0, "total": 0, "error": "Please enter API key"}
        if not feed_sport_name:
            for r in _load_feed_sports_rows():
                if (r.get("feed_provider") or "").strip().lower() == "betfair" and (r.get("feed_sport_id") or "").strip() == feed_sport_id:
                    feed_sport_name = (r.get("feed_sport_name") or feed_sport_id).strip()
                    break
            feed_sport_name = feed_sport_name or f"Sport {feed_sport_id}"
        result = await feed_pull.pull_betfair_sport(feed_sport_id, feed_sport_name, token)
    elif feed_provider == "1xbet":
        if not feed_sport_id:
            raise HTTPException(status_code=400, detail="feed_sport_id is required for 1xbet.")
        if not token:
            return {"ok": False, "added": 0, "skipped": 0, "total": 0, "error": "Please enter API key"}
        if not feed_sport_name:
            for r in _load_feed_sports_rows():
                if (r.get("feed_provider") or "").strip().lower() == "1xbet" and (r.get("feed_sport_id") or "").strip() == feed_sport_id:
                    feed_sport_name = (r.get("feed_sport_name") or feed_sport_id).strip()
                    break
            feed_sport_name = feed_sport_name or f"Sport {feed_sport_id}"
        result = await feed_pull.pull_1xbet_sport(feed_sport_id, feed_sport_name, token)
    elif feed_provider == "bwin":
        if not feed_sport_id:
            raise HTTPException(status_code=400, detail="feed_sport_id is required for Bwin.")
        if not token:
            return {"ok": False, "added": 0, "updated": 0, "total": 0, "error": "Please enter API key"}
        if not feed_sport_name:
            for r in _load_feed_sports_rows():
                if (r.get("feed_provider") or "").strip().lower() == "bwin" and (r.get("feed_sport_id") or "").strip() == feed_sport_id:
                    feed_sport_name = (r.get("feed_sport_name") or feed_sport_id).strip()
                    break
            feed_sport_name = feed_sport_name or f"Sport {feed_sport_id}"
        result = await feed_pull.pull_bwin_sport(feed_sport_id, feed_sport_name, token)
    else:
        raise HTTPException(status_code=400, detail="Only bet365, betfair, 1xbet and bwin are supported.")

    if result.get("ok"):
        _save_feed_last_pull(feed_provider, feed_sport_id)
        result["last_pull_display"] = _format_last_pull(datetime.now(timezone.utc).isoformat())
        global DUMMY_EVENTS
        DUMMY_EVENTS = load_all_mock_data()
        _enrich_feed_events_sport_names()
    return result


@app.post("/api/pull-feed-all")
async def api_pull_feed_all(
    feed_provider: str = Form(...),
    api_token: str = Form(""),
    concurrency: int = Form(5),
):
    """
    Pull all sports for one feed in parallel (async, with concurrency cap).
    Reloads DUMMY_EVENTS and updates last_pull for each sport on success.
    """
    from fastapi import HTTPException
    feed_provider = (feed_provider or "").strip().lower()
    token = (api_token or "").strip()
    if not token:
        return {"ok": False, "results": [], "error": "Please enter API key"}
    if feed_provider not in ("bet365", "betfair", "1xbet", "bwin"):
        raise HTTPException(status_code=400, detail="Unsupported feed.")
    rows = _load_feed_sports_rows()
    sports = [
        ((r.get("feed_sport_id") or "").strip(), (r.get("feed_sport_name") or r.get("feed_sport_id") or "").strip())
        for r in rows
        if (r.get("feed_provider") or "").strip().lower() == feed_provider
    ]
    if not sports:
        return {"ok": False, "results": [], "error": "No sports configured for this feed."}
    concurrency = max(1, min(concurrency, 10))
    result = await feed_pull.pull_feed_all_sports_async(feed_provider, sports, token, concurrency=concurrency)
    if result.get("ok"):
        now_iso = datetime.now(timezone.utc).isoformat()
        last_pull_display = _format_last_pull(now_iso)
        for sid, _ in sports:
            _save_feed_last_pull(feed_provider, sid)
        result["last_pull_display"] = last_pull_display
        global DUMMY_EVENTS
        DUMMY_EVENTS = load_all_mock_data()
        _enrich_feed_events_sport_names()
    return result


@app.post("/api/dump-csv-data", response_class=HTMLResponse)
async def dump_csv_data(request: Request):
    """
    Clear all entity and relation CSVs (header-only). feeds.csv is not touched.
    Reloads in-memory state and redirects to dashboard.
    """
    _dump_entity_and_relation_csvs()
    global DOMAIN_EVENTS, DOMAIN_ENTITIES, ENTITY_FEED_MAPPINGS, SPORT_FEED_MAPPINGS
    DOMAIN_EVENTS = _load_domain_events()
    DOMAIN_ENTITIES = _load_entities()
    ENTITY_FEED_MAPPINGS = _load_entity_feed_mappings()
    SPORT_FEED_MAPPINGS = _load_sport_feed_mappings()
    return RedirectResponse(url="/", status_code=303)


def _feeder_category_key(e: dict) -> str:
    """Canonical category value for a feeder event (for filter dropdown and matching)."""
    return (e.get("category") or str(e.get("category_id") or "")).strip()


def _feeder_competition_key(e: dict) -> str:
    """Canonical competition value for a feeder event."""
    return (e.get("raw_league_name") or str(e.get("raw_league_id") or "")).strip()


def _feeder_categories(feed: str, sports: list[str] | None) -> list[str]:
    """Unique category values from feeder events for the given feed and sports. Empty if no sports."""
    if not sports:
        return []
    sport_set = set(sports)
    return sorted({
        _feeder_category_key(e)
        for e in DUMMY_EVENTS
        if e.get("feed_provider") == feed and e.get("sport") in sport_set and _feeder_category_key(e)
    })


def _feeder_competitions(feed: str, sports: list[str] | None, categories: list[str] | None) -> list[str]:
    """Unique competition values from feeder events for given feed, sports, and categories."""
    if not sports or not categories:
        return []
    sport_set = set(sports)
    cat_set = set(categories)
    return sorted({
        _feeder_competition_key(e)
        for e in DUMMY_EVENTS
        if e.get("feed_provider") == feed
        and e.get("sport") in sport_set
        and _feeder_category_key(e) in cat_set
        and _feeder_competition_key(e)
    })


# time_status: codes from feed_time_statuses.csv; display description. If feed does not return status, show "—".
FEEDER_TIME_STATUS_MAP: dict[str, str] = {}
FEEDER_TIME_STATUS_OPTIONS: list[tuple[str, str]] = []


def _load_feed_time_statuses() -> None:
    """Load feed_time_statuses.csv into FEEDER_TIME_STATUS_MAP and FEEDER_TIME_STATUS_OPTIONS. Create file with defaults if missing."""
    global FEEDER_TIME_STATUS_MAP, FEEDER_TIME_STATUS_OPTIONS
    default_rows = [
        ("0", "Not Started"),
        ("1", "InPlay"),
        ("2", "TO BE FIXED"),
        ("3", "Ended"),
        ("4", "Postponed"),
        ("5", "Cancelled"),
        ("6", "Walkover"),
        ("7", "Interrupted"),
        ("8", "Abandoned"),
        ("9", "Retired"),
        ("10", "Suspended"),
        ("11", "Decided by FA"),
        ("12", "Disqualified"),
        ("99", "Removed"),
    ]
    path = FEED_TIME_STATUSES_PATH
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8") as f:
            f.write("code,description\n")
            for code, desc in default_rows:
                f.write(f"{code},{desc}\n")
    FEEDER_TIME_STATUS_MAP = {}
    FEEDER_TIME_STATUS_OPTIONS = [("", "—")]
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            code = (row.get("code") or "").strip()
            desc = (row.get("description") or "").strip()
            if code != "" or desc != "":
                FEEDER_TIME_STATUS_MAP[code] = desc or "—"
                FEEDER_TIME_STATUS_OPTIONS.append((code, desc or "—"))
    # Ensure standard codes exist if CSV was edited and missing some
    for code, desc in default_rows:
        if code not in FEEDER_TIME_STATUS_MAP:
            FEEDER_TIME_STATUS_MAP[code] = desc
            FEEDER_TIME_STATUS_OPTIONS.append((code, desc))


def _time_status_description(code) -> str:
    """Map time_status code from feed to display label. Missing/unknown -> '—'."""
    if code is None or (isinstance(code, str) and code.strip() == ""):
        return "—"
    return FEEDER_TIME_STATUS_MAP.get(str(code).strip(), "—")


# Load time statuses at import so filter and views have data
_load_feed_time_statuses()
# Legacy alias for any code that referenced the old list of status labels
FEEDER_EVENT_STATUSES = [desc for _code, desc in FEEDER_TIME_STATUS_OPTIONS if _code]
templates.env.filters["time_status_description"] = _time_status_description

# Platform notes: categorized by entity_type; multiple notes per entity. entity_ref identifies the entity within that type.
# Example types: feeder_event (ref=feed_provider|feed_valid_id), domain_event (ref=domain_id), competition (ref=competition_id).
NOTES_ENTITY_FEEDER_EVENT = "feeder_event"
_NOTES_FIELDS = ["entity_type", "entity_ref", "note_id", "note_text", "created_at", "updated_at", "created_by", "updated_by", "requires_confirmation"]
NOTES_DEFAULT_USER = "Admin"
_NOTIFICATION_FIELDS = ["notification_id", "note_id", "message_snippet", "created_at", "confirmed"]


def _feeder_entity_ref(feed_provider: str, feed_valid_id: str) -> str:
    """Entity ref for a feeder event (used in platform_notes)."""
    return f"{(feed_provider or '').strip()}|{(feed_valid_id or '').strip()}"


def _normalize_note_row(row: dict) -> dict:
    """Ensure note has created_by, updated_by, requires_confirmation (for backward compatibility)."""
    out = dict(row)
    if not out.get("created_by"):
        out["created_by"] = NOTES_DEFAULT_USER
    if not out.get("updated_by"):
        out["updated_by"] = NOTES_DEFAULT_USER
    if out.get("requires_confirmation") not in ("1", 1, True):
        out["requires_confirmation"] = "0"
    return out


def _load_platform_notes() -> list[dict]:
    """Load platform_notes.csv. Columns include created_by, updated_by, requires_confirmation."""
    if not NOTES_PATH.exists():
        if NOTES_PATH_LEGACY and NOTES_PATH_LEGACY.exists():
            import shutil
            NOTES_PATH.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(NOTES_PATH_LEGACY), str(NOTES_PATH))
        else:
            _migrate_legacy_feeder_notes_to_platform()
    if not NOTES_PATH.exists():
        return []
    rows = []
    with open(NOTES_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(_normalize_note_row(row))
    return rows


def _migrate_legacy_feeder_notes_to_platform() -> None:
    """One-time: copy rows from feeder_event_notes.csv into platform_notes.csv."""
    if not FEEDER_EVENT_NOTES_PATH.exists():
        return
    legacy_rows = []
    with open(FEEDER_EVENT_NOTES_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            legacy_rows.append(row)
    if not legacy_rows:
        return
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
    new_notes = []
    for r in legacy_rows:
        provider = (r.get("feed_provider") or "").strip()
        valid_id = (r.get("feed_valid_id") or "").strip()
        if not provider and not valid_id:
            continue
        new_notes.append({
            "entity_type": NOTES_ENTITY_FEEDER_EVENT,
            "entity_ref": _feeder_entity_ref(provider, valid_id),
            "note_id": str(uuid.uuid4()),
            "note_text": (r.get("note_text") or "").strip(),
            "created_at": r.get("updated_at") or now,
            "updated_at": r.get("updated_at") or now,
            "created_by": NOTES_DEFAULT_USER,
            "updated_by": NOTES_DEFAULT_USER,
            "requires_confirmation": "0",
        })
    if not new_notes:
        return
    NOTES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(NOTES_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=_NOTES_FIELDS)
        w.writeheader()
        w.writerows(new_notes)


def _get_notes_for_entity(entity_type: str, entity_ref: str) -> list[dict]:
    """Return all notes for this entity (newest updated_at first)."""
    entity_ref = (entity_ref or "").strip()
    notes = [n for n in _load_platform_notes() if (n.get("entity_type") or "").strip() == entity_type and (n.get("entity_ref") or "").strip() == entity_ref]
    notes.sort(key=lambda n: (n.get("updated_at") or ""), reverse=True)
    return notes


def _entity_refs_with_notes(entity_type: str) -> set[str]:
    """Set of entity_ref values that have at least one note (for badges/indicators)."""
    notes = _load_platform_notes()
    return {(n.get("entity_ref") or "").strip() for n in notes if (n.get("entity_type") or "").strip() == entity_type and (n.get("entity_ref") or "").strip()}


def _feeder_notes_has_set() -> set[tuple[str, str]]:
    """Set of (feed_provider, feed_valid_id) that have at least one note (for feeder events table)."""
    refs = _entity_refs_with_notes(NOTES_ENTITY_FEEDER_EVENT)
    out = set()
    for ref in refs:
        if "|" in ref:
            a, b = ref.split("|", 1)
            out.add((a, b))
    return out


def _add_note(entity_type: str, entity_ref: str, note_text: str, requires_confirmation: bool = False, created_by: str = None) -> dict:
    """Append a note. If requires_confirmation, create a platform notification. Returns the new note dict."""
    entity_type = (entity_type or "").strip()
    entity_ref = (entity_ref or "").strip()
    note_text = (note_text or "").strip()
    created_by = (created_by or NOTES_DEFAULT_USER).strip()
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
    note_id = str(uuid.uuid4())
    note = {
        "entity_type": entity_type, "entity_ref": entity_ref, "note_id": note_id, "note_text": note_text,
        "created_at": now, "updated_at": now,
        "created_by": created_by, "updated_by": created_by,
        "requires_confirmation": "1" if requires_confirmation else "0",
    }
    notes = _load_platform_notes()
    notes.append(note)
    NOTES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(NOTES_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=_NOTES_FIELDS)
        w.writeheader()
        w.writerows(notes)
    if requires_confirmation and NOTIFICATIONS_PATH:
        _create_notification(note_id, (note_text[:200] + "…") if len(note_text) > 200 else note_text)
    return note


def _update_note(note_id: str, note_text: str, updated_by: str = None) -> bool:
    """Update note_text, updated_at and updated_by for the given note_id. Returns True if found."""
    note_id = (note_id or "").strip()
    note_text = (note_text or "").strip()
    updated_by = (updated_by or NOTES_DEFAULT_USER).strip()
    notes = _load_platform_notes()
    for n in notes:
        if (n.get("note_id") or "").strip() == note_id:
            n["note_text"] = note_text
            n["updated_at"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
            n["updated_by"] = updated_by
            with open(NOTES_PATH, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=_NOTES_FIELDS)
                w.writeheader()
                w.writerows(notes)
            return True
    return False


def _delete_note(note_id: str) -> bool:
    """Remove the note by note_id. Returns True if found and removed."""
    note_id = (note_id or "").strip()
    notes = [n for n in _load_platform_notes() if (n.get("note_id") or "").strip() != note_id]
    if len(notes) == len(_load_platform_notes()):
        return False
    with open(NOTES_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=_NOTES_FIELDS)
        w.writeheader()
        if notes:
            w.writerows(notes)
    return True


# ── Event Navigator notes (screen-only; separate from feeder/platform notes) ──
_EVENT_NAVIGATOR_NOTE_FIELDS = ["domain_event_id", "note_text", "updated_at"]


def _load_event_navigator_notes() -> dict[str, dict]:
    """Load event_navigator_notes.csv. Returns dict domain_event_id -> {note_text, updated_at}. Event Navigator screen only."""
    if not EVENT_NAVIGATOR_NOTES_PATH or not EVENT_NAVIGATOR_NOTES_PATH.exists():
        return {}
    out: dict[str, dict] = {}
    with open(EVENT_NAVIGATOR_NOTES_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            eid = (row.get("domain_event_id") or "").strip()
            if not eid:
                continue
            out[eid] = {
                "note_text": (row.get("note_text") or "").strip(),
                "updated_at": (row.get("updated_at") or "").strip(),
            }
    return out


def _save_event_navigator_note(domain_event_id: str, note_text: str) -> None:
    """Create or update the single note for this domain event. Overwrites any existing note. Event Navigator screen only."""
    domain_event_id = (domain_event_id or "").strip()
    note_text = (note_text or "").strip()
    if not EVENT_NAVIGATOR_NOTES_PATH:
        return
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
    notes_map = _load_event_navigator_notes()
    notes_map[domain_event_id] = {"note_text": note_text, "updated_at": now}
    EVENT_NAVIGATOR_NOTES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(EVENT_NAVIGATOR_NOTES_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=_EVENT_NAVIGATOR_NOTE_FIELDS)
        w.writeheader()
        for eid, data in notes_map.items():
            w.writerow({"domain_event_id": eid, "note_text": data["note_text"], "updated_at": data["updated_at"]})


def _load_notifications() -> list[dict]:
    """Load platform_notifications.csv. Returns list of dicts with notification_id, note_id, message_snippet, created_at, confirmed."""
    if not NOTIFICATIONS_PATH or not NOTIFICATIONS_PATH.exists():
        return []
    rows = []
    with open(NOTIFICATIONS_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows


def _get_unconfirmed_notifications() -> list[dict]:
    """Return notifications where confirmed is not 1."""
    return [n for n in _load_notifications() if (n.get("confirmed") or "").strip() != "1"]


def _create_notification(note_id: str, message_snippet: str) -> None:
    """Append a notification row (requires user to confirm read)."""
    if not NOTIFICATIONS_PATH:
        return
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
    notification_id = str(uuid.uuid4())
    row = {"notification_id": notification_id, "note_id": note_id, "message_snippet": (message_snippet or "").strip(), "created_at": now, "confirmed": "0"}
    notifications = _load_notifications()
    notifications.append(row)
    NOTIFICATIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(NOTIFICATIONS_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=_NOTIFICATION_FIELDS)
        w.writeheader()
        w.writerows(notifications)


def _confirm_notification(notification_id: str) -> bool:
    """Set confirmed=1 for this notification. Returns True if found."""
    notification_id = (notification_id or "").strip()
    notifications = _load_notifications()
    for n in notifications:
        if (n.get("notification_id") or "").strip() == notification_id:
            n["confirmed"] = "1"
            with open(NOTIFICATIONS_PATH, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=_NOTIFICATION_FIELDS)
                w.writeheader()
                w.writerows(notifications)
            return True
    return False


# --- Feeder event log (appeared, mapped, note_added, ignored, unignored) ---
_FEEDER_EVENT_LOG_FIELDS = ["feed_provider", "feed_valid_id", "action_type", "details", "created_at"]


def _load_feeder_event_log() -> list[dict]:
    """All rows from feeder_event_log.csv."""
    if not FEEDER_EVENT_LOG_PATH or not FEEDER_EVENT_LOG_PATH.exists():
        return []
    out = []
    with open(FEEDER_EVENT_LOG_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out.append({k: row.get(k, "") for k in _FEEDER_EVENT_LOG_FIELDS})
    return out


def _append_feeder_event_log(feed_provider: str, feed_valid_id: str, action_type: str, details: str | None = None) -> None:
    """Append one log entry. action_type: appeared, mapped, note_added, ignored, unignored."""
    if not FEEDER_EVENT_LOG_PATH:
        return
    feed_provider = (feed_provider or "").strip()
    feed_valid_id = (feed_valid_id or "").strip()
    created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    row = {
        "feed_provider": feed_provider,
        "feed_valid_id": feed_valid_id,
        "action_type": (action_type or "").strip(),
        "details": (details or "").strip(),
        "created_at": created,
    }
    FEEDER_EVENT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    file_exists = FEEDER_EVENT_LOG_PATH.exists()
    with open(FEEDER_EVENT_LOG_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=_FEEDER_EVENT_LOG_FIELDS)
        if not file_exists:
            w.writeheader()
        w.writerow(row)


def _get_event_log_entries(feed_provider: str, feed_valid_id: str) -> list[dict]:
    """Log entries for this feeder event, newest first."""
    provider = (feed_provider or "").strip()
    valid_id = (feed_valid_id or "").strip()
    rows = [r for r in _load_feeder_event_log() if (r.get("feed_provider") or "").strip() == provider and (r.get("feed_valid_id") or "").strip() == valid_id]
    rows.sort(key=lambda r: (r.get("created_at") or ""), reverse=True)
    return rows


def _ensure_appeared_batch(events: list[dict]) -> None:
    """For each event that has no log entry yet, add one 'appeared' entry (idempotent per event)."""
    if not FEEDER_EVENT_LOG_PATH or not events:
        return
    existing_keys = set()
    for r in _load_feeder_event_log():
        k = ((r.get("feed_provider") or "").strip(), (r.get("feed_valid_id") or "").strip())
        if k[0] or k[1]:
            existing_keys.add(k)
    to_add = []
    for e in events:
        p = (e.get("feed_provider") or "").strip()
        v = (e.get("valid_id") or str(e.get("valid_id") or "")).strip()
        if (p, v) not in existing_keys:
            to_add.append((p, v))
            existing_keys.add((p, v))
    for p, v in to_add:
        _append_feeder_event_log(p, v, "appeared")


@app.get("/feeder-events", response_class=HTMLResponse)
async def feeder_events_view(
    request: Request,
    feed_provider: str = None,
    date: str = None,
    date_from: str = None,
    date_to: str = None,
    sports: List[str] = Query(default=None),
    categories: List[str] = Query(default=None),
    competitions: List[str] = Query(default=None),
    statuses: List[str] = Query(default=None),
    live_only: str = "0",
    notes_only: str = "0",
):
    _sync_feeder_events_mapping_status()
    _enrich_feed_events_sport_names()
    selected_feed = (feed_provider or KNOWN_FEEDS[0]).strip().lower()
    selected_feed_pid = next((f["domain_id"] for f in FEEDS if (f.get("code") or "").strip().lower() == selected_feed), None)
    events_for_feed = [e for e in DUMMY_EVENTS if (e.get("feed_provider") or "").strip().lower() == selected_feed]
    csv_sports = _get_sports_for_feed(selected_feed, events_for_feed) or []
    event_sports = sorted({e.get("sport") for e in events_for_feed if e.get("sport")})
    feed_sports_live = sorted(set(csv_sports + event_sports)) if (csv_sports or event_sports) else SPORTS_BY_FEED.get(selected_feed, KNOWN_SPORTS)
    selected_sports = sports if sports else feed_sports_live
    selected_categories = categories or []
    selected_competitions = competitions or []
    selected_statuses = statuses or []
    live_only_active = (live_only or "").strip() in ("1", "true", "yes")
    notes_only_active = (notes_only or "").strip() in ("1", "true", "yes")
    filtered = [
        e for e in DUMMY_EVENTS
        if (e.get("feed_provider") or "").strip().lower() == selected_feed
        and e.get("sport") in selected_sports
    ]
    if selected_categories:
        filtered = [e for e in filtered if _feeder_category_key(e) in selected_categories]
    if selected_competitions:
        filtered = [e for e in filtered if _feeder_competition_key(e) in selected_competitions]
    if selected_statuses:
        status_set = set(selected_statuses)
        filtered = [e for e in filtered if str(e.get("time_status") or "") in status_set]
    if live_only_active:
        filtered = [e for e in filtered if (e.get("time_status") or "0") == "1"]
    has_notes = _feeder_notes_has_set()
    if notes_only_active:
        filtered = [e for e in filtered if ((e.get("feed_provider") or "").strip(), (e.get("valid_id") or "").strip()) in has_notes]
    date_filter = (date or "").strip() or "today"
    date_range = _date_range_from_param(date_filter, date_from, date_to)
    if date_range is not None:
        start_d, end_d = date_range
        filtered = [
            e for e in filtered
            if _parse_start_time(e.get("start_time")) and start_d <= _parse_start_time(e["start_time"]).date() <= end_d
        ]
    # Sort by start time and paginate (same logic as feeder_events_table)
    sort_start_time = (request.query_params.get("sort_start_time") or "asc").strip().lower()
    if sort_start_time not in ("asc", "desc"):
        sort_start_time = "asc"
    sort_asc = sort_start_time != "desc"
    filtered.sort(key=lambda e: _feeder_event_start_time_sort_key(e, sort_asc))
    page = max(1, int(request.query_params.get("page") or 1))
    per_page = max(1, min(int(request.query_params.get("per_page") or FEEDER_EVENTS_PER_PAGE), 500))
    total_events = len(filtered)
    total_pages = (total_events + per_page - 1) // per_page if total_events else 1
    page = max(1, min(page, total_pages))
    start_idx = (page - 1) * per_page
    page_events = filtered[start_idx : start_idx + per_page]
    for e in page_events:
        r = _resolve_sport_alias(selected_feed_pid, e.get("sport_id")) if selected_feed_pid else None
        e["domain_sport_id"] = r["domain_id"] if r else None
    available_categories = _feeder_categories(selected_feed, selected_sports)
    available_competitions = _feeder_competitions(selected_feed, selected_sports, selected_categories if selected_categories else None)
    _mk = lambda etype: {(m["feed_provider_id"], str(m["feed_id"])) for m in ENTITY_FEED_MAPPINGS if m["entity_type"] == etype}
    _mk_sport = lambda: {(m["feed_provider_id"], _normalize_sport_feed_id(m.get("feed_id"))) for m in ENTITY_FEED_MAPPINGS if m.get("entity_type") == "sports"}
    mapped_sport_feed_ids = _mk_sport()
    mapped_category_feed_ids = _mapped_category_feed_ids_by_sport()
    mapped_comp_feed_ids    = _mapped_comp_feed_ids_by_sport()
    mapped_team_feed_ids    = _mk("teams")
    return templates.TemplateResponse("feeder_events/feeder_events.html", {
        "request": request,
        "section": "feeder",
        "feeds": KNOWN_FEEDS,
        "selected_feed": selected_feed,
        "selected_feed_pid": selected_feed_pid,
        "sports": feed_sports_live,
        "selected_sports": selected_sports,
        "available_categories": available_categories,
        "selected_categories": selected_categories,
        "available_competitions": available_competitions,
        "selected_competitions": selected_competitions,
        "available_statuses": FEEDER_TIME_STATUS_OPTIONS,
        "selected_statuses": selected_statuses,
        "live_only": "1" if live_only_active else "0",
        "notes_only": "1" if notes_only_active else "0",
        "events": page_events,
        "has_notes": has_notes,
        "mapped_sport_feed_ids": mapped_sport_feed_ids,
        "mapped_category_feed_ids": mapped_category_feed_ids,
        "mapped_comp_feed_ids": mapped_comp_feed_ids,
        "mapped_team_feed_ids": mapped_team_feed_ids,
        "feeder_total_events": total_events,
        "feeder_page": page,
        "feeder_per_page": per_page,
        "feeder_total_pages": total_pages,
        "feeder_sort_start_time": sort_start_time,
        "selected_date": date_filter,
        "date_from": (date_from or "").strip() or "",
        "date_to": (date_to or "").strip() or "",
    })

@app.get("/feeder-events/sport-options", response_class=HTMLResponse)
async def feeder_events_sport_options(request: Request, feed_provider: str = None):
    """
    HTMX Endpoint: Returns sport checkboxes (all checked) for the given feed.
    Called when the feed filter changes so the sport list updates.
    """
    _enrich_feed_events_sport_names()
    selected_feed = feed_provider or KNOWN_FEEDS[0]
    events_for_feed = [e for e in DUMMY_EVENTS if e.get("feed_provider") == selected_feed]
    feed_sports = _get_sports_for_feed(selected_feed, events_for_feed) or SPORTS_BY_FEED.get(selected_feed, KNOWN_SPORTS)
    return templates.TemplateResponse("feeder_events/_sport_checkboxes.html", {
        "request": request,
        "sports": feed_sports
    })

FEEDER_EVENTS_PER_PAGE = 50
EVENT_NAVIGATOR_PER_PAGE = 50


@app.get("/feeder-events/table", response_class=HTMLResponse)
async def feeder_events_table(
    request: Request,
    feed_provider: str = None,
    date: str = None,
    date_from: str = None,
    date_to: str = None,
    mapping_status_filter: str = "",
    outright_filter: str = "",
    q: str = "",
    sports: List[str] = Query(default=None),
    categories: List[str] = Query(default=None),
    competitions: List[str] = Query(default=None),
    statuses: List[str] = Query(default=None),
    live_only: str = "0",
    notes_only: str = "0",
    sort_start_time: str = "asc",
    page: int = 1,
    per_page: int = FEEDER_EVENTS_PER_PAGE,
):
    """
    HTMX Endpoint: Returns filtered, sorted, and paginated tbody rows.
    Sort and filters apply to full dataset; then one page is returned. Sends HX-Trigger with pager state.
    """
    _sync_feeder_events_mapping_status()
    _enrich_feed_events_sport_names()
    selected_feed = (feed_provider or KNOWN_FEEDS[0]).strip().lower()
    events_for_feed = [e for e in DUMMY_EVENTS if (e.get("feed_provider") or "").strip().lower() == selected_feed]
    csv_sports = _get_sports_for_feed(selected_feed, events_for_feed) or []
    event_sports = sorted({e.get("sport") for e in events_for_feed if e.get("sport")})
    feed_sports = sorted(set(csv_sports + event_sports)) if (csv_sports or event_sports) else SPORTS_BY_FEED.get(selected_feed, KNOWN_SPORTS)
    if not feed_sports:
        feed_sports = SPORTS_BY_FEED.get(selected_feed, KNOWN_SPORTS)
    requested_set = set(sports or [])
    feed_set = set(feed_sports)
    overlap = requested_set & feed_set
    if not requested_set or (requested_set - feed_set):
        active_sports = feed_sports
    else:
        active_sports = sorted(overlap) if overlap else feed_sports
    q_lower = q.strip().lower()
    notes_only_on = (notes_only or "").strip() in ("1", "true", "yes")
    has_notes_set = _feeder_notes_has_set() if notes_only_on else None

    filtered = []
    for e in DUMMY_EVENTS:
        if (e.get("feed_provider") or "").strip().lower() != selected_feed:
            continue
        if e.get("sport") not in active_sports:
            continue
        if categories and _feeder_category_key(e) not in categories:
            continue
        if competitions and _feeder_competition_key(e) not in competitions:
            continue
        if statuses and str(e.get("time_status") or "") not in statuses:
            continue
        if mapping_status_filter and e["mapping_status"] != mapping_status_filter:
            continue
        if outright_filter == "outright" and not e.get("is_outright"):
            continue
        if outright_filter == "regular" and e.get("is_outright"):
            continue
        if (live_only or "").strip() in ("1", "true", "yes") and (e.get("time_status") or "0") != "1":
            continue
        if notes_only_on and has_notes_set is not None:
            if ((e.get("feed_provider") or "").strip(), (e.get("valid_id") or "").strip()) not in has_notes_set:
                continue
        if q_lower:
            event_label = e.get("market_name") if e.get("is_outright") else f"{e.get('raw_home_name', '')} {e.get('raw_away_name', '')}"
            haystack = " ".join(filter(None, [
                e.get("sport", ""),
                e.get("category", ""),
                e.get("raw_league_name", ""),
                event_label,
            ])).lower()
            if q_lower not in haystack:
                continue
        filtered.append(e)

    date_filter = (date or "").strip() or "today"
    date_range = _date_range_from_param(date_filter, date_from, date_to)
    if date_range is not None:
        start_d, end_d = date_range
        filtered = [
            e for e in filtered
            if _parse_start_time(e.get("start_time")) and start_d <= _parse_start_time(e["start_time"]).date() <= end_d
        ]

    # Sort by start time (all data, then paginate)
    sort_asc = (sort_start_time or "asc").strip().lower() != "desc"
    filtered.sort(key=lambda e: _feeder_event_start_time_sort_key(e, sort_asc))

    total_events = len(filtered)
    per_page = max(1, min(per_page, 500))
    total_pages = (total_events + per_page - 1) // per_page if total_events else 1
    page = max(1, min(page, total_pages))
    start_idx = (page - 1) * per_page
    page_events = filtered[start_idx : start_idx + per_page]

    _ensure_appeared_batch(page_events)
    selected_feed_pid = next((f["domain_id"] for f in FEEDS if (f.get("code") or "").strip().lower() == selected_feed), None)
    for e in page_events:
        r = _resolve_sport_alias(selected_feed_pid, e.get("sport_id")) if selected_feed_pid else None
        e["domain_sport_id"] = r["domain_id"] if r else None
    has_notes = _feeder_notes_has_set()
    _mk = lambda etype: {(m["feed_provider_id"], str(m["feed_id"])) for m in ENTITY_FEED_MAPPINGS if m["entity_type"] == etype}
    _mk_sport = lambda: {(m["feed_provider_id"], _normalize_sport_feed_id(m.get("feed_id"))) for m in ENTITY_FEED_MAPPINGS if m.get("entity_type") == "sports"}
    mapped_sport_feed_ids = _mk_sport()
    mapped_category_feed_ids = _mapped_category_feed_ids_by_sport()
    mapped_comp_feed_ids    = _mapped_comp_feed_ids_by_sport()
    mapped_team_feed_ids    = _mk("teams")

    response = templates.TemplateResponse("feeder_events/_rows.html", {
        "request": request,
        "events": page_events,
        "selected_feed_pid": selected_feed_pid,
        "has_notes": has_notes,
        "mapped_sport_feed_ids": mapped_sport_feed_ids,
        "mapped_category_feed_ids": mapped_category_feed_ids,
        "mapped_comp_feed_ids": mapped_comp_feed_ids,
        "mapped_team_feed_ids": mapped_team_feed_ids,
    })
    response.headers["HX-Trigger"] = json.dumps({
        "feederPager": {
            "total_events": total_events,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "sort_start_time": "desc" if not sort_asc else "asc",
        }
    })
    return response


@app.get("/feeder-events/category-options", response_class=HTMLResponse)
async def feeder_events_category_options(
    request: Request,
    feed_provider: str = None,
    sports: List[str] = Query(default=None),
    categories: List[str] = Query(default=None),
):
    """HTMX: Category checkboxes for feeder events filter. Only categories for the given feed and sports."""
    feed = feed_provider or KNOWN_FEEDS[0]
    cat_list = _feeder_categories(feed, sports) if sports else []
    selected = categories or []
    return templates.TemplateResponse("feeder_events/_category_checkboxes.html", {
        "request": request,
        "categories": cat_list,
        "selected_categories": selected,
    })


@app.get("/feeder-events/competition-options", response_class=HTMLResponse)
async def feeder_events_competition_options(
    request: Request,
    feed_provider: str = None,
    sports: List[str] = Query(default=None),
    categories: List[str] = Query(default=None),
    competitions: List[str] = Query(default=None),
):
    """HTMX: Competition checkboxes for feeder events filter. Only competitions for given feed, sports, and categories."""
    feed = feed_provider or KNOWN_FEEDS[0]
    comp_list = _feeder_competitions(feed, sports, categories) if (sports and categories) else []
    selected = competitions or []
    return templates.TemplateResponse("feeder_events/_competition_checkboxes.html", {
        "request": request,
        "competitions": comp_list,
        "selected_competitions": selected,
    })


def _domain_events_sports() -> list[str]:
    """Unique sport names from domain events (for filter dropdown)."""
    return sorted({ev.get("sport") or "" for ev in DOMAIN_EVENTS if ev.get("sport")})


def _domain_events_categories(sports: list[str] | None) -> list[str]:
    """Unique category names from domain events that have one of the given sports. Empty if no sports."""
    if not sports:
        return []
    sport_set = set(sports)
    return sorted({
        ev.get("category") or ""
        for ev in DOMAIN_EVENTS
        if (ev.get("sport") or "") in sport_set and ev.get("category")
    })


def _domain_events_competitions(sports: list[str] | None, categories: list[str] | None) -> list[str]:
    """Unique competition names from domain events for given sports and categories. Empty if no sports or categories."""
    if not sports or not categories:
        return []
    sport_set = set(sports)
    cat_set = set(categories)
    return sorted({
        ev.get("competition") or ""
        for ev in DOMAIN_EVENTS
        if (ev.get("sport") or "") in sport_set
        and (ev.get("category") or "") in cat_set
        and ev.get("competition")
    })


def _domain_event_start_time_mismatch(domain_event_id: str, mappings: list[dict], feed_events: list[dict] | None = None) -> bool:
    """True if mapped feed events have more than one distinct start time (easy to notice discrepancy).
    Uses feed_events if provided (e.g. fresh load from JSON so edits are picked up without restart)."""
    if len(mappings) < 2:
        return False
    source = feed_events if feed_events is not None else DUMMY_EVENTS
    seen: set[str] = set()
    for m in mappings:
        feed_provider = (m.get("feed_provider") or "").strip()
        feed_valid_id = (m.get("feed_valid_id") or "").strip()
        feed_ev = next(
            (e for e in source if (e.get("feed_provider") or "").strip() == feed_provider and str(e.get("valid_id") or "").strip() == feed_valid_id),
            None,
        )
        if not feed_ev:
            continue
        st = (feed_ev.get("start_time") or "").strip()
        dt = _parse_start_time(st) if st else None
        key = dt.isoformat() if dt else "__none__"
        seen.add(key)
    return len(seen) > 1


def _domain_event_feed_start_times(mappings: list[dict], feed_events: list[dict] | None = None) -> list[dict]:
    """Return list of {feed, start_time} for each mapped feed event (start_time formatted for display)."""
    source = feed_events if feed_events is not None else DUMMY_EVENTS
    out: list[dict] = []
    for m in mappings:
        feed_provider = (m.get("feed_provider") or "").strip()
        feed_valid_id = (m.get("feed_valid_id") or "").strip()
        feed_ev = next(
            (e for e in source if (e.get("feed_provider") or "").strip() == feed_provider and str(e.get("valid_id") or "").strip() == feed_valid_id),
            None,
        )
        feed_label = feed_provider or "—"
        if not feed_ev:
            out.append({"feed": feed_label, "start_time": "—"})
            continue
        st = (feed_ev.get("start_time") or "").strip()
        out.append({"feed": feed_label, "start_time": _format_start_time(st) or "—"})
    return out


def _filter_domain_events(
    enriched: list[dict],
    date_str: str | None,
    sports: list[str] | None,
    q: str | None = None,
    categories: list[str] | None = None,
    competitions: list[str] | None = None,
    date_from_str: str | None = None,
    date_to_str: str | None = None,
) -> list[dict]:
    """Filter enriched domain events by optional date, sports, categories, competitions, and text search."""
    out = enriched
    date_range = _date_range_from_param(date_str, date_from_str, date_to_str)
    if date_range is not None:
        start_d, end_d = date_range
        out = [
            ev for ev in out
            if _parse_start_time(ev.get("start_time")) and start_d <= _parse_start_time(ev["start_time"]).date() <= end_d
        ]
    if sports:
        out = [ev for ev in out if (ev.get("sport") or "") in sports]
    if categories:
        out = [ev for ev in out if (ev.get("category") or "") in categories]
    if competitions:
        out = [ev for ev in out if (ev.get("competition") or "") in competitions]
    if q and q.strip():
        q_lower = q.strip().lower()
        out = [
            ev for ev in out
            if q_lower in " ".join([
                ev.get("id") or "",
                ev.get("sport") or "",
                ev.get("category") or "",
                ev.get("competition") or "",
                ev.get("home") or "",
                ev.get("away") or "",
            ]).lower()
        ]
    return out


@app.get("/event-navigator", response_class=HTMLResponse)
async def event_navigator_view(
    request: Request,
    date: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    sports: List[str] = Query(default=None),
    categories: List[str] = Query(default=None),
    competitions: List[str] = Query(default=None),
    statuses: List[str] = Query(default=None),
    live_only: str | None = None,
    notes_only: str | None = None,
    outright_filter: str | None = None,
    has_bets_only: str | None = None,
    brands: List[str] = Query(default=None),
    q: str | None = None,
    sort_start_time: str = "asc",
    page: int = 1,
    per_page: int = EVENT_NAVIGATOR_PER_PAGE,
):
    """
    Domain Events Table (Golden Copy). Supports filter by date, sport, category, competition, status, live/notes/outright, has_bets, brands, text search; sort by start time; paging.
    """
    global DOMAIN_EVENTS
    DOMAIN_EVENTS = _load_domain_events()
    mappings_by_event: dict[str, list[dict]] = {}
    for m in _load_event_mappings():
        mappings_by_event.setdefault(m["domain_event_id"], []).append(m)
    feed_events = load_all_mock_data()
    enriched = []
    for ev in DOMAIN_EVENTS:
        mappings = mappings_by_event.get(ev["id"], [])
        providers = ", ".join(sorted({m["feed_provider"] for m in mappings}))
        start_time_mismatch = _domain_event_start_time_mismatch(ev["id"], mappings, feed_events)
        feed_start_times = _domain_event_feed_start_times(mappings, feed_events)
        enriched.append({**ev, "mapped_providers": providers, "mapped_feed_count": len(mappings), "start_time_mismatch": start_time_mismatch, "feed_start_times": feed_start_times})
    domain_sports = _domain_events_sports()
    selected_sports = sports if sports else domain_sports
    active_sports = selected_sports if sports else None
    available_categories = _domain_events_categories(active_sports)
    selected_categories = categories or []
    available_competitions = _domain_events_competitions(active_sports, selected_categories if selected_categories else None)
    selected_competitions = competitions or []
    brands_list = _load_brands()
    selected_brands = brands if brands else ["Global"]
    date_filter = (date or "").strip() or "today"
    filtered = _filter_domain_events(
        enriched, date_filter, active_sports, q,
        selected_categories if selected_categories else None,
        selected_competitions if selected_competitions else None,
        date_from_str=date_from,
        date_to_str=date_to,
    )
    en_notes = _load_event_navigator_notes()
    for ev in filtered:
        data = en_notes.get(str(ev.get("id")), {})
        ev["en_note"] = (data.get("note_text") or "").strip()
        ev["has_en_note"] = bool(ev["en_note"])
    if notes_only == "1":
        filtered = [ev for ev in filtered if ev.get("has_en_note")]
    if outright_filter == "outright":
        filtered = [ev for ev in filtered if not (ev.get("home") or ev.get("away"))]
    elif outright_filter == "regular":
        filtered = [ev for ev in filtered if bool(ev.get("home") or ev.get("away"))]
    sort_st = (sort_start_time or "asc").strip().lower()
    if sort_st not in ("asc", "desc"):
        sort_st = "asc"
    sort_asc = sort_st != "desc"
    filtered.sort(key=lambda ev: _domain_event_start_time_sort_key(ev, sort_asc))
    total_events = len(filtered)
    per_page = max(1, min(per_page, 500))
    total_pages = (total_events + per_page - 1) // per_page if total_events else 1
    page = max(1, min(page, total_pages))
    start_idx = (page - 1) * per_page
    page_events = filtered[start_idx : start_idx + per_page]
    comp_sport_to_rc = _competition_sport_to_risk_class_map()
    for e in page_events:
        e["risk_class"] = _event_risk_class(e, comp_sport_to_rc)
    return templates.TemplateResponse("event_navigator/event_navigator.html", {
        "request": request,
        "section": "domain",
        "domain_events": page_events,
        "mappings_by_event": mappings_by_event,
        "sports": domain_sports,
        "selected_sports": selected_sports,
        "available_categories": available_categories,
        "selected_categories": selected_categories,
        "available_competitions": available_competitions,
        "selected_competitions": selected_competitions,
        "available_statuses": FEEDER_EVENT_STATUSES,
        "selected_statuses": statuses or [],
        "live_only": "1" if live_only == "1" else "0",
        "notes_only": "1" if notes_only == "1" else "0",
        "outright_filter": outright_filter or "",
        "has_bets_only": "1" if has_bets_only == "1" else "0",
        "brands": brands_list,
        "selected_brands": selected_brands,
        "selected_date": date_filter,
        "date_from": (date_from or "").strip() or "",
        "date_to": (date_to or "").strip() or "",
        "search_q": q or "",
        "en_total_events": total_events,
        "en_page": page,
        "en_per_page": per_page,
        "en_total_pages": total_pages,
        "en_sort_start_time": sort_st,
    })


@app.get("/event-navigator/table", response_class=HTMLResponse)
async def event_navigator_table(
    request: Request,
    date: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    sports: List[str] = Query(default=None),
    categories: List[str] = Query(default=None),
    competitions: List[str] = Query(default=None),
    statuses: List[str] = Query(default=None),
    live_only: str | None = None,
    notes_only: str | None = None,
    outright_filter: str | None = None,
    has_bets_only: str | None = None,
    brands: List[str] = Query(default=None),
    q: str | None = None,
    sort_start_time: str = "asc",
    page: int = 1,
    per_page: int = EVENT_NAVIGATOR_PER_PAGE,
):
    """
    HTMX Endpoint: Returns filtered, sorted, and paginated domain events table rows.
    Sends HX-Trigger with navigatorPager state.
    """
    global DOMAIN_EVENTS
    DOMAIN_EVENTS = _load_domain_events()
    mappings_by_event: dict[str, list[dict]] = {}
    for m in _load_event_mappings():
        mappings_by_event.setdefault(m["domain_event_id"], []).append(m)
    feed_events = load_all_mock_data()
    enriched = []
    for ev in DOMAIN_EVENTS:
        mappings = mappings_by_event.get(ev["id"], [])
        providers = ", ".join(sorted({m["feed_provider"] for m in mappings}))
        start_time_mismatch = _domain_event_start_time_mismatch(ev["id"], mappings, feed_events)
        feed_start_times = _domain_event_feed_start_times(mappings, feed_events)
        enriched.append({**ev, "mapped_providers": providers, "mapped_feed_count": len(mappings), "start_time_mismatch": start_time_mismatch, "feed_start_times": feed_start_times})
    domain_sports = _domain_events_sports()
    selected_sports = sports if sports else domain_sports
    active_sports = selected_sports if sports else None
    date_filter = (date or "").strip() or "today"
    filtered = _filter_domain_events(
        enriched, date_filter, active_sports, q,
        categories if categories else None,
        competitions if competitions else None,
        date_from_str=date_from,
        date_to_str=date_to,
    )
    en_notes = _load_event_navigator_notes()
    for ev in filtered:
        data = en_notes.get(str(ev.get("id")), {})
        ev["en_note"] = (data.get("note_text") or "").strip()
        ev["has_en_note"] = bool(ev["en_note"])
    if notes_only == "1":
        filtered = [ev for ev in filtered if ev.get("has_en_note")]
    if outright_filter == "outright":
        filtered = [ev for ev in filtered if not (ev.get("home") or ev.get("away"))]
    elif outright_filter == "regular":
        filtered = [ev for ev in filtered if bool(ev.get("home") or ev.get("away"))]
    sort_st = (sort_start_time or "asc").strip().lower()
    if sort_st not in ("asc", "desc"):
        sort_st = "asc"
    sort_asc = sort_st != "desc"
    filtered.sort(key=lambda ev: _domain_event_start_time_sort_key(ev, sort_asc))
    total_events = len(filtered)
    per_page = max(1, min(per_page, 500))
    total_pages = (total_events + per_page - 1) // per_page if total_events else 1
    page = max(1, min(page, total_pages))
    start_idx = (page - 1) * per_page
    page_events = filtered[start_idx : start_idx + per_page]
    comp_sport_to_rc = _competition_sport_to_risk_class_map()
    for e in page_events:
        e["risk_class"] = _event_risk_class(e, comp_sport_to_rc)
    response = templates.TemplateResponse("event_navigator/_rows.html", {
        "request": request,
        "domain_events": page_events,
    })
    response.headers["HX-Trigger"] = json.dumps({
        "navigatorPager": {
            "total_events": total_events,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "sort_start_time": sort_st,
        }
    })
    return response


def _template_outcome_count(market: dict) -> int:
    """Return number of outcomes for a market from its template/code or from market_outcomes (outcome_labels). Match Winner (WINNER2/2way)=2, 3way=3, HCP2/OU/HANDICAP2/SetHcp=2; default 3."""
    labels = market.get("outcome_labels")
    if labels and isinstance(labels, list) and len(labels) > 0:
        return len(labels)
    template = (market.get("template") or "").strip().upper()
    code = (market.get("code") or "").strip().lower()
    if template in ("WINNER2",) or code in ("2way",):
        return 2
    if template in ("WINNER2D",) or code in ("3way",):
        return 3
    if template in ("HCP2", "OU", "HANDICAP2") or code in ("hcp2", "ou", "sethcp"):
        return 2
    return 3


def _market_has_line(market: dict) -> bool:
    """True if this market has a line (e.g. handicap or over/under) with multiple lines to pick."""
    template = (market.get("template") or "").strip().upper()
    code = (market.get("code") or "").strip().lower()
    return template in ("HCP2", "OU", "HANDICAP2") or code in ("hcp2", "ou", "sethcp")


def _event_sport_id(ev: dict) -> int | None:
    """Resolve event sport name to domain sport_id. Returns None if not found."""
    sport_name = (ev.get("sport") or "").strip()
    if not sport_name:
        return None
    sports = DOMAIN_ENTITIES.get("sports") or []
    for s in sports:
        if (s.get("name") or "").strip() == sport_name:
            return s.get("domain_id")
    return None


@app.get("/event-navigator/event_details/{domain_id}", response_class=HTMLResponse)
async def event_navigator_event_details(request: Request, domain_id: str):
    """Event details page for a single domain event. Opens in new tab from Event column."""
    from fastapi import HTTPException
    ev = next((e for e in DOMAIN_EVENTS if e.get("id") == domain_id), None)
    if not ev:
        raise HTTPException(status_code=404, detail="Domain event not found")
    mappings = [m for m in _load_event_mappings() if m.get("domain_event_id") == domain_id]
    sport_id = _event_sport_id(ev)
    markets_by_group = _markets_by_group(sport_id)
    for item in markets_by_group:
        for m in item.get("markets") or []:
            labels, otype = _get_outcome_labels_for_market(m, sport_id)
            m["outcome_labels"] = labels
            m["outcome_type"] = otype
    brands = _load_brands()
    template_outcome_count = _template_outcome_count
    market_has_line = _market_has_line
    return templates.TemplateResponse("event_details.html", {
        "request": request,
        "section": "domain",
        "event": ev,
        "mappings": mappings,
        "markets_by_group": markets_by_group,
        "brands": brands,
        "template_outcome_count": template_outcome_count,
        "market_has_line": market_has_line,
    })


@app.get("/event-navigator/notes-modal/{domain_event_id}", response_class=HTMLResponse)
async def event_navigator_notes_modal(request: Request, domain_event_id: str):
    """Modal content for Event Navigator notes (screen-only; not related to feeder notes)."""
    en_notes = _load_event_navigator_notes()
    data = en_notes.get(domain_event_id.strip(), {})
    note_text = (data.get("note_text") or "").strip()
    ev = next((e for e in DOMAIN_EVENTS if str(e.get("id")) == domain_event_id.strip()), None)
    event_label = ""
    if ev:
        event_label = (ev.get("home") or "") + " v " + (ev.get("away") or "") if (ev.get("home") or ev.get("away")) else (ev.get("name") or str(ev.get("id")))
    return templates.TemplateResponse("event_navigator/modal_notes.html", {
        "request": request,
        "domain_event_id": domain_event_id,
        "event_label": event_label,
        "note_text": note_text,
    })


@app.post("/api/event-navigator/notes")
async def api_event_navigator_notes(
    domain_event_id: str = Form(...),
    note_text: str = Form(default=""),
    requires_confirmation: str = Form("0"),
):
    """Save Event Navigator note for a domain event. Screen-only; not related to feeder notes. If requires_confirmation=1, create a platform notification."""
    domain_event_id = (domain_event_id or "").strip()
    if not domain_event_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="domain_event_id required")
    _save_event_navigator_note(domain_event_id, note_text or "")
    if (requires_confirmation or "").strip() in ("1", "true", "yes"):
        snippet = (note_text or "").strip()
        if len(snippet) > 200:
            snippet = snippet[:200] + "…"
        _create_notification("en-" + domain_event_id, snippet or "Event Navigator note")
    return {"ok": True}


@app.get("/event-navigator/category-options", response_class=HTMLResponse)
async def event_navigator_category_options(
    request: Request,
    sports: List[str] = Query(default=None),
    categories: List[str] = Query(default=None),
):
    """HTMX: Category checkboxes for domain events filter. Only categories for the given sports."""
    cat_list = _domain_events_categories(sports) if sports else []
    selected = categories or []
    return templates.TemplateResponse("event_navigator/_category_checkboxes.html", {
        "request": request,
        "categories": cat_list,
        "selected_categories": selected,
    })


@app.get("/event-navigator/competition-options", response_class=HTMLResponse)
async def event_navigator_competition_options(
    request: Request,
    sports: List[str] = Query(default=None),
    categories: List[str] = Query(default=None),
    competitions: List[str] = Query(default=None),
):
    """HTMX: Competition checkboxes for domain events filter. Only competitions for given sports and categories."""
    comp_list = _domain_events_competitions(sports, categories) if (sports and categories) else []
    selected = competitions or []
    return templates.TemplateResponse("event_navigator/_competition_checkboxes.html", {
        "request": request,
        "competitions": comp_list,
        "selected_competitions": selected,
    })


@app.get("/archived-events", response_class=HTMLResponse)
async def archived_events_view(request: Request):
    """Betting Program > Archived Events. Placeholder page; full functionality to be added later."""
    return templates.TemplateResponse("archived_events/archived_events.html", {
        "request": request,
        "section": "archived_events",
    })


def _render_mapping_modal(request: Request, event_id: str):
    """
    Build and return the Mapping Modal HTML. Used by GET modal.
    Pre-resolves any already-mapped entities (sport alias, category/competition/team by feed_id).
    """
    event = next((e for e in DUMMY_EVENTS if e["valid_id"] == event_id), None)
    if not event:
        return HTMLResponse('<div class="p-6 text-red-500">Error: Event Not Found</div>')

    # Look up the feed's domain_id
    feed_obj = next((f for f in FEEDS if f["code"].lower() == (event.get("feed_provider") or "").lower()), None)
    feed_pid = feed_obj["domain_id"] if feed_obj else None

    # Pre-resolve entities from entity_feed_mappings (prefer feed IDs then names so we find existing mappings)
    # Sport: resolve by feed sport_id only (not by sport name)
    r_sport = None
    if feed_pid:
        _sid = event.get("sport_id")
        if _sid not in (None, "") and str(_sid).strip():
            r_sport = _resolve_sport_alias(feed_pid, str(_sid).strip())
    domain_sport_id = r_sport["domain_id"] if r_sport else None
    # Category and competition: resolve by feed ID and require same sport (e.g. Bwin category 38 = Argentina in Football only, not Basketball)
    r_category = None
    if feed_pid and (event.get("category_id") not in (None, "")):
        r_category = _resolve_entity("categories", str(event.get("category_id") or ""), feed_pid, domain_sport_id=domain_sport_id)
    r_competition = None
    if feed_pid and (event.get("raw_league_id") not in (None, "")):
        r_competition = _resolve_entity("competitions", str(event.get("raw_league_id") or ""), feed_pid, domain_sport_id=domain_sport_id)
    r_home = _resolve_entity("teams", str(event.get("raw_home_id") or event.get("raw_home_name") or ""), feed_pid) if feed_pid else None
    r_away = _resolve_entity("teams", str(event.get("raw_away_id") or event.get("raw_away_name") or ""), feed_pid) if feed_pid else None

    # Enrich resolved entities with display names
    def _enrich(e):
        if not e:
            return None
        return {**e,
                "sport_name": _sport_name(e.get("sport_id") or 0),
                "category_name": _category_name(e.get("category_id") or 0)}

    resolved = {
        "sport":       r_sport,
        "category":    _enrich(r_category),
        "competition": _enrich(r_competition),
        "home":        _enrich(r_home),
        "away":        _enrich(r_away),
    }
    sports_by_id = {s["domain_id"]: s["name"] for s in DOMAIN_ENTITIES["sports"]}

    # Fuzzy: suggest all matching domain events (same match from another feed; supports reversed home/away)
    suggested_domain_events = _suggest_domain_events(event)
    best_suggestion = suggested_domain_events[0] if suggested_domain_events else None
    suggested_domain_event = best_suggestion["event"] if best_suggestion else None
    suggested_match_score = best_suggestion["score"] if best_suggestion else 0

    # Sport: no suggestions or fuzzy when unmapped — UI shows dropdown of domain sports + Map button only
    suggested_sports = []

    # Entity suggestions: best match per field (for prefill / match %)
    sport_id_for_suggest = r_sport["domain_id"] if r_sport else (suggested_sports[0]["domain_id"] if suggested_sports else None)
    category_id_for_suggest = None

    # Category: always derive from feed first. Feed "Barbados" → suggest Barbados.
    # Only use a domain category when match is strong (≥55%); otherwise use feed value with Create.
    cat_candidates = _suggest_entity_by_name("categories", event.get("category") or event.get("raw_league_name") or "", sport_id_for_suggest)
    raw_cat = (event.get("category") or "").strip()
    best_cat = cat_candidates[0] if cat_candidates else None
    suggested_category = best_cat if (best_cat and (best_cat.get("match_pct") or 0) >= 55) else ({"name": raw_cat, "match_pct": 0} if raw_cat else None)
    if isinstance(suggested_category, dict) and suggested_category.get("name"):
        cat_ent = next((c for c in DOMAIN_ENTITIES["categories"] if c["name"] == suggested_category["name"] and c.get("sport_id") == sport_id_for_suggest), None)
        if cat_ent:
            category_id_for_suggest = cat_ent["domain_id"]
            suggested_category = dict(suggested_category)
            suggested_category["domain_id"] = cat_ent["domain_id"]
            j = (cat_ent.get("jurisdiction") or "").strip()
            if j and j != COUNTRY_CODE_NONE:
                suggested_category["jurisdiction"] = j

    # Competition: always derive from feed first; only use domain when match ≥55%
    comp_candidates = _suggest_entity_by_name("competitions", event.get("raw_league_name") or "", sport_id_for_suggest, category_id_for_suggest)
    raw_comp = (event.get("raw_league_name") or "").strip()
    best_comp = comp_candidates[0] if comp_candidates else None
    suggested_competition = best_comp if (best_comp and (best_comp.get("match_pct") or 0) >= 55) else ({"name": raw_comp, "match_pct": 0} if raw_comp else None)

    # Teams: suggest raw feed names; when mapping same match (score >= 70) and per-team match ≥55%, pre-fill from suggested domain event
    # match_pct = similarity between feed name and domain name (like category/competition), not 100%
    suggested_home = {"name": (event.get("raw_home_name") or "").strip(), "match_pct": 0, "is_suggested": True}
    suggested_away = {"name": (event.get("raw_away_name") or "").strip(), "match_pct": 0, "is_suggested": True}
    if suggested_domain_event and suggested_match_score >= 70:
        feed_home = (event.get("raw_home_name") or "").strip()
        feed_away = (event.get("raw_away_name") or "").strip()
        d_home = (suggested_domain_event.get("home") or "").strip()
        d_away = (suggested_domain_event.get("away") or "").strip()
        pct_home = _fuzzy_score(feed_home, d_home)
        pct_away = _fuzzy_score(feed_away, d_away)
        if pct_home >= 55 and pct_away >= 55:
            suggested_home = {"name": suggested_domain_event.get("home") or "", "match_pct": pct_home, "is_suggested": pct_home == 0, "domain_id": suggested_domain_event.get("home_id")}
            suggested_away = {"name": suggested_domain_event.get("away") or "", "match_pct": pct_away, "is_suggested": pct_away == 0, "domain_id": suggested_domain_event.get("away_id")}
    # Normalize to dict with name + match_pct + is_suggested for template (raw_name used when no match)
    def _norm(v, raw_name: str = ""):
        if v is None and not raw_name:
            return None
        if v is None:
            return {"name": raw_name, "match_pct": 0, "is_suggested": True}
        if isinstance(v, dict) and "match_pct" in v:
            out = dict(v)
            out.setdefault("is_suggested", (out.get("match_pct") or 0) == 0)
            return out
        return {"name": (v.get("name") if isinstance(v, dict) else str(v)) or raw_name or "", "match_pct": 100, "is_suggested": False}
    suggested_entities = {
        "category":    _norm(suggested_category, raw_cat) if (suggested_category or raw_cat) else None,
        "competition": _norm(suggested_competition, raw_comp) if (suggested_competition or raw_comp) else None,
        "home":        suggested_home,
        "away":        suggested_away,
    }
    # Only use suggested_domain_event for category/competition when feed and domain match (≥55%).
    # E.g. feed "Barbados" vs domain "Argentina" → keep Barbados (Create), don't show Argentina (Map).
    if suggested_domain_event and suggested_match_score >= 70:
        feed_cat = (event.get("category") or "").strip()
        feed_comp = (event.get("raw_league_name") or "").strip()
        d_cat = (suggested_domain_event.get("category") or "").strip()
        d_comp = (suggested_domain_event.get("competition") or "").strip()
        pct_cat = _fuzzy_score(feed_cat, d_cat)
        pct_comp = _fuzzy_score(feed_comp, d_comp)
        # Only override category when feed category matches domain event category (≥55%)
        if feed_cat and d_cat and pct_cat >= 55:
            suggested_entities["category"] = {"name": suggested_domain_event.get("category") or "", "match_pct": pct_cat, "is_suggested": pct_cat == 0}
            if sport_id_for_suggest is not None:
                cat_ent = next((c for c in DOMAIN_ENTITIES["categories"] if (c.get("name") or "").strip() == d_cat and c.get("sport_id") == sport_id_for_suggest), None)
                if cat_ent:
                    suggested_entities["category"] = dict(suggested_entities["category"])
                    suggested_entities["category"]["domain_id"] = cat_ent["domain_id"]
                    j = (cat_ent.get("jurisdiction") or "").strip()
                    if j and j != COUNTRY_CODE_NONE:
                        suggested_entities["category"]["jurisdiction"] = j
        # Only override competition when feed competition matches domain event competition (≥55%)
        if feed_comp and d_comp and pct_comp >= 55:
            suggested_entities["competition"] = {"name": suggested_domain_event.get("competition") or "", "match_pct": pct_comp, "is_suggested": pct_comp == 0}
    # Ensure is_suggested when match_pct is 0 (raw feed name suggested)
    for key in ("category", "competition", "home", "away"):
        if suggested_entities.get(key):
            suggested_entities[key]["is_suggested"] = (suggested_entities[key].get("match_pct") or 0) == 0

    countries = _load_countries()
    # When feed category matches a country (e.g. Barbados) but not in domain, pre-select that country in dropdown
    if suggested_entities.get("category") and not suggested_entities["category"].get("jurisdiction"):
        cat_name = (suggested_entities["category"].get("name") or "").strip()
        if cat_name:
            country_match = next((c for c in countries if (c.get("name") or "").strip().lower() == cat_name.lower()), None)
            if country_match and (country_match.get("cc") or "").strip() != COUNTRY_CODE_NONE:
                suggested_entities["category"] = dict(suggested_entities["category"])
                suggested_entities["category"]["jurisdiction"] = (country_match.get("cc") or "").strip()

    participant_types = _load_participant_types()
    underage_categories = _load_underage_categories()
    underage_ids = {int(u["id"]) for u in underage_categories}
    def _suggest_underage_id(raw_name: str):
        if not raw_name:
            return None
        import re
        m = re.search(r"U(\d+)", raw_name, re.IGNORECASE)
        if not m:
            return None
        try:
            n = int(m.group(1))
            return n if n in underage_ids else None
        except (ValueError, TypeError):
            return None
    suggested_underage_competition_id = _suggest_underage_id(event.get("raw_league_name") or "")
    suggested_underage_home_id = _suggest_underage_id(event.get("raw_home_name") or "")
    suggested_underage_away_id = _suggest_underage_id(event.get("raw_away_name") or "")

    exception_categories = [c for c in DOMAIN_ENTITIES["categories"] if (c.get("jurisdiction") or "").strip() == COUNTRY_CODE_NONE]

    return templates.TemplateResponse("modal_mapping.html", {
        "request": request,
        "event": event,
        "domain_entities": DOMAIN_ENTITIES,
        "feeds": FEEDS,
        "resolved": resolved,
        "feed_pid": feed_pid,
        "sports_by_id": sports_by_id,
        "suggested_domain_event": suggested_domain_event,
        "suggested_match_score": suggested_match_score,
        "suggested_domain_events": suggested_domain_events,
        "suggested_sports": suggested_sports,
        "suggested_entities": suggested_entities,
        "countries": countries,
        "participant_types": participant_types,
        "underage_categories": underage_categories,
        "exception_categories": exception_categories,
        "suggested_underage_competition_id": suggested_underage_competition_id,
        "suggested_underage_home_id": suggested_underage_home_id,
        "suggested_underage_away_id": suggested_underage_away_id,
    })


@app.get("/modal/map-event/{event_id}", response_class=HTMLResponse)
async def modal_map_event(request: Request, event_id: str):
    """Returns the HTML partial for the Mapping Modal."""
    return _render_mapping_modal(request, event_id)


@app.get("/modal/feeder-event-notes/{valid_id}", response_class=HTMLResponse)
async def modal_feeder_event_notes(
    request: Request,
    valid_id: str,
    feed_provider: str = "",
    event_label: str = "",
):
    """Returns the HTML partial for the Feeder Event Notes modal (multiple notes per event)."""
    feed_provider = (feed_provider or "").strip()
    entity_ref = _feeder_entity_ref(feed_provider, valid_id) if (feed_provider or valid_id) else ""
    notes = _get_notes_for_entity(NOTES_ENTITY_FEEDER_EVENT, entity_ref) if entity_ref else []
    # Build a short label for display if not provided
    if not event_label:
        for e in DUMMY_EVENTS:
            if (e.get("feed_provider") or "").strip() == feed_provider and str(e.get("valid_id")) == str(valid_id):
                if e.get("is_outright"):
                    event_label = e.get("market_name") or f"Event {valid_id}"
                else:
                    event_label = f"{e.get('raw_home_name', '')} vs {e.get('raw_away_name', '')}".strip() or f"Event {valid_id}"
                break
        else:
            event_label = f"Event {valid_id}"
    return templates.TemplateResponse("feeder_events/modal_feeder_notes.html", {
        "request": request,
        "notes": notes,
        "entity_type": NOTES_ENTITY_FEEDER_EVENT,
        "entity_ref": entity_ref,
        "feed_provider": feed_provider,
        "feed_valid_id": valid_id,
        "event_label": event_label or f"Event {valid_id}",
    })


def _feeder_event_label(feed_provider: str, valid_id: str) -> str:
    """Short label for a feeder event (for modal titles)."""
    feed_provider = (feed_provider or "").strip()
    valid_id = str(valid_id or "").strip()
    for e in DUMMY_EVENTS:
        if (e.get("feed_provider") or "").strip() == feed_provider and str(e.get("valid_id")) == valid_id:
            if e.get("is_outright"):
                return e.get("market_name") or f"Event {valid_id}"
            return f"{e.get('raw_home_name', '')} vs {e.get('raw_away_name', '')}".strip() or f"Event {valid_id}"
    return f"Event {valid_id}"


@app.get("/modal/feeder-event-log/{valid_id}", response_class=HTMLResponse)
async def modal_feeder_event_log(
    request: Request,
    valid_id: str,
    feed_provider: str = "",
):
    """Returns the HTML partial for the Feeder Event Log modal (all actions: appeared, mapped, note_added, ignored, unignored)."""
    feed_provider = (feed_provider or "").strip()
    entries = _get_event_log_entries(feed_provider, valid_id)
    event_label = _feeder_event_label(feed_provider, valid_id)
    return templates.TemplateResponse("feeder_events/modal_feeder_event_log.html", {
        "request": request,
        "entries": entries,
        "feed_provider": feed_provider,
        "feed_valid_id": valid_id,
        "event_label": event_label,
    })


@app.get("/notifications/unconfirmed", response_class=HTMLResponse)
async def notifications_unconfirmed(request: Request):
    """HTMX: returns HTML fragment of unconfirmed notifications for top-right panel."""
    items = _get_unconfirmed_notifications()
    return templates.TemplateResponse("partials/notifications_unconfirmed.html", {
        "request": request,
        "notifications": items,
    })


@app.post("/api/notifications/{notification_id}/confirm")
async def api_confirm_notification(notification_id: str):
    """Mark notification as confirmed (user read and acknowledged)."""
    ok = _confirm_notification(notification_id)
    return {"ok": ok}


@app.post("/api/feeder-events/set-ignored")
async def api_feeder_events_set_ignored(
    feed_provider: str = Form(...),
    feed_valid_id: str = Form(...),
    ignored: str = Form("1"),
):
    """Set or clear ignored state for a feeder event. ignored=1 to ignore, 0 to un-ignore. No data is deleted."""
    is_ignored = (ignored or "").strip() in ("1", "true", "yes")
    _set_feeder_event_ignored(feed_provider, feed_valid_id, is_ignored)
    _append_feeder_event_log(feed_provider, feed_valid_id, "ignored" if is_ignored else "unignored")
    return {"ok": True}


@app.post("/api/notes")
async def api_add_note(
    entity_type: str = Form(...),
    entity_ref: str = Form(...),
    note_text: str = Form(""),
    requires_confirmation: str = Form("0"),
    created_by: str = Form(""),
):
    """Add a note for any entity. If requires_confirmation=1, all users get a notification to confirm read."""
    rc = (requires_confirmation or "").strip() in ("1", "true", "yes")
    note = _add_note(entity_type, entity_ref, note_text, requires_confirmation=rc, created_by=created_by or None)
    if entity_type == NOTES_ENTITY_FEEDER_EVENT and entity_ref and "|" in entity_ref:
        parts = entity_ref.strip().split("|", 1)
        if len(parts) == 2:
            _append_feeder_event_log(parts[0].strip(), parts[1].strip(), "note_added")
    return {"ok": True, "note_id": note["note_id"], "created_at": note["created_at"], "updated_at": note["updated_at"]}


@app.patch("/api/notes/{note_id}")
async def api_update_note(note_id: str, note_text: str = Form("")):
    """Update an existing note by note_id."""
    ok = _update_note(note_id, note_text)
    return {"ok": ok}


@app.post("/api/notes/{note_id}/delete")
async def api_delete_note(note_id: str):
    """Delete a note by note_id."""
    ok = _delete_note(note_id)
    return {"ok": ok}


@app.get("/api/feed-markets")
async def api_feed_markets(
    feed_provider_id: int = Query(..., description="Feed domain_id from feeds.csv"),
    domain_sport_id: int = Query(..., description="Domain sport id (e.g. 1 = Football) to resolve feed's sport id"),
):
    """
    Return unique markets from a feed JSON for the given feed and sport.
    Resolves feed sport id from sport_feed_mappings.csv. If no mapping, returns [].
    Each item: { id, name, is_prematch, feed_name }.
    """
    mapping = next(
        (m for m in SPORT_FEED_MAPPINGS
         if m.get("domain_id") == domain_sport_id
         and m.get("feed_provider_id") == feed_provider_id),
        None,
    )
    if not mapping:
        return {"feed_name": "", "markets": []}
    feed_sport_id_raw = mapping.get("feed_id")
    try:
        feed_sport_id = int(feed_sport_id_raw) if feed_sport_id_raw is not None else None
    except (TypeError, ValueError):
        feed_sport_id = None
    if feed_sport_id is None:
        return {"feed_name": "", "markets": []}
    feed = next((f for f in FEEDS if f.get("domain_id") == feed_provider_id), None)
    feed_code = (feed.get("code") or "").strip() or ""
    feed_name = (feed.get("name") or feed_code) or ""
    markets = _load_feed_markets_for_sport(feed_code, feed_sport_id, domain_sport_id)
    sport_display = _get_feed_sport_name(feed_code, feed_sport_id)
    for m in markets:
        m["feed_name"] = feed_name
        # Always fill sport_name when empty (Bet365/1xbet stored events often lack SportName)
        m["sport_name"] = (m.get("sport_name") or "").strip() or sport_display
    return {"feed_name": feed_name, "markets": markets}


@app.get("/api/event-details/feed-odds")
async def api_event_details_feed_odds(
    domain_event_id: str = Query(..., description="Domain event id (e.g. G-xxx)"),
    domain_market_id: int = Query(..., description="Domain market type id"),
):
    """Return feed odds for the selected market from each mapped feed (from cached event details)."""
    rows = _get_feed_odds_for_event_market(domain_event_id, domain_market_id)
    return {"feed_odds": rows}


@app.get("/api/market-type-mappings/all-mapped")
async def api_get_all_mapped_feed_market_keys():
    """Return all (feed_provider_id, feed_market_id) keys that are mapped to any domain market. Used to hide those from Available markets in the mapper.
    Bet365 Game Lines (910000) and Set 1 Lines (910204): only the specific sub-market (_1/2/3) that is mapped is added."""
    mappings = _load_market_type_mappings()
    bet365_codes = {f["domain_id"] for f in FEEDS if (f.get("code") or "").strip().lower() == "bet365"}
    game_lines_names = {"Game Lines - Winner": "1", "Game Lines - Handicap": "2", "Game Lines - Total": "3"}
    set1_lines_names = {"Set 1 Lines - Winner": "1", "Set 1 Lines - Handicap": "2", "Set 1 Lines - Total": "3"}
    keys: set[str] = set()
    for m in mappings:
        fid = str(m.get("feed_market_id") or "").strip()
        pid = m.get("feed_provider_id")
        if fid and pid is not None:
            if pid in bet365_codes and fid == "910000":
                name = (m.get("feed_market_name") or "").strip()
                suffix = game_lines_names.get(name)
                if suffix:
                    keys.add(f"{pid}|910000_{suffix}")
                else:
                    keys.add(f"{pid}|910000_1")
                    keys.add(f"{pid}|910000_2")
                    keys.add(f"{pid}|910000_3")
            elif pid in bet365_codes and fid == "910204":
                name = (m.get("feed_market_name") or "").strip()
                suffix = set1_lines_names.get(name)
                if suffix:
                    keys.add(f"{pid}|910204_{suffix}")
                else:
                    keys.add(f"{pid}|910204_1")
                    keys.add(f"{pid}|910204_2")
                    keys.add(f"{pid}|910204_3")
            else:
                keys.add(f"{pid}|{fid}")
    return {"mapped_keys": list(keys)}


@app.get("/api/market-type-mappings")
async def api_get_market_type_mappings(
    domain_market_id: int = Query(..., description="Domain market type id"),
):
    """Return prematch and live feed mappings for a domain market type."""
    mappings = _load_market_type_mappings()
    prematch = []
    live = []
    feeds_by_id = {f["domain_id"]: f.get("name") or f.get("code") or "" for f in FEEDS}
    # Bet365 Game Lines (910000) and Set 1 Lines (910204) legacy: normalize to composite id so left shows _1/2/3
    bet365_codes = {f["domain_id"] for f in FEEDS if (f.get("code") or "").strip().lower() == "bet365"}
    game_lines_names = {"Game Lines - Winner": "1", "Game Lines - Handicap": "2", "Game Lines - Total": "3"}
    set1_lines_names = {"Set 1 Lines - Winner": "1", "Set 1 Lines - Handicap": "2", "Set 1 Lines - Total": "3"}
    for m in mappings:
        if m["domain_market_id"] != domain_market_id:
            continue
        fid_raw = (m.get("feed_market_id") or "").strip()
        try:
            item_id = int(fid_raw) if fid_raw.isdigit() else fid_raw or None
        except (TypeError, ValueError):
            item_id = fid_raw or None
        name = (m.get("feed_market_name") or "").strip()
        if (item_id == 910000 or (isinstance(item_id, str) and item_id == "910000")) and m["feed_provider_id"] in bet365_codes and name in game_lines_names:
            item_id = "910000_" + game_lines_names[name]
            fid_raw = item_id
        elif (item_id == 910204 or (isinstance(item_id, str) and item_id == "910204")) and m["feed_provider_id"] in bet365_codes and name in set1_lines_names:
            item_id = "910204_" + set1_lines_names[name]
            fid_raw = item_id
        item = {
            "feed_provider_id": m["feed_provider_id"],
            "id": item_id,
            "name": name or fid_raw,
            "feed_market_name": name or fid_raw,
            "feed_name": feeds_by_id.get(m["feed_provider_id"], ""),
        }
        if (m.get("phase") or "").strip().lower() == "live":
            live.append(item)
        else:
            prematch.append(item)
    return {"prematch": prematch, "live": live}


@app.post("/api/market-type-mappings")
async def api_save_market_type_mappings(body: SaveMarketTypeMappingsRequest):
    """Save prematch and live feed mappings for a domain market type. Replaces existing mappings for that market."""
    def to_item(i: MarketTypeMappingItem) -> dict:
        fid = i.feed_market_id or (str(i.id) if i.id is not None else "")
        name = (i.feed_market_name or i.name or "").strip()
        return {"feed_provider_id": i.feed_provider_id, "id": i.id, "feed_market_id": fid, "feed_market_name": name}
    prematch = [to_item(x) for x in body.prematch]
    live = [to_item(x) for x in body.live]
    _save_market_type_mappings_for_domain(body.domain_market_id, prematch, live)
    return {"ok": True}


@app.post("/api/localization/countries")
async def api_localization_upsert_country(body: CountryUpsertRequest):
    """Add or update a country in data/countries/countries.json. The 'None' (code '-') option is reserved and cannot be edited."""
    from fastapi import HTTPException
    name = (body.name or "").strip()
    cc = (body.cc or "").strip()
    if not name or not cc:
        raise HTTPException(status_code=400, detail="Name and code are required.")
    cc_lower = cc.lower()
    if cc_lower == COUNTRY_CODE_NONE or (body.original_cc or "").strip().lower() == COUNTRY_CODE_NONE:
        raise HTTPException(status_code=400, detail="The 'None' option is reserved for no jurisdiction and cannot be modified.")
    countries = _load_countries()
    updated = False
    # Update existing by original_cc if provided, otherwise by cc
    orig = (body.original_cc or "").strip().lower()
    for c in countries:
        key = (c.get("cc") or "").strip().lower()
        if (orig and key == orig) or (not orig and key == cc_lower):
            c["cc"] = cc_lower
            c["name"] = name
            updated = True
            break
    if not updated:
        countries.append({"cc": cc_lower, "name": name})
    _save_countries(countries)
    return {"ok": True, "updated": updated}


@app.post("/api/localization/languages")
async def api_localization_upsert_language(body: LanguageUpsertRequest):
    """Add or update a language in data/languages.csv."""
    name = (body.name or "").strip()
    if not name:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Name is required.")
    native_name = (body.native_name or "").strip()
    direction = (body.direction or "ltr").strip().lower()
    if direction not in ("ltr", "rtl"):
        direction = "ltr"
    active = bool(body.active)
    languages = _load_languages()
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    updated = False
    if body.id is not None:
        for lang in languages:
            if lang.get("id") == body.id:
                lang["name"] = name
                lang["native_name"] = native_name
                lang["direction"] = direction
                lang["active"] = active
                if not lang.get("created_at"):
                    lang["created_at"] = now
                lang["updated_at"] = now
                updated = True
                break
    if not updated:
        next_id = max((l.get("id") or 0 for l in languages), default=0) + 1
        languages.append({
            "id": next_id,
            "name": name,
            "native_name": native_name,
            "direction": direction,
            "active": active,
            "created_at": now,
            "updated_at": now,
        })
    _save_languages(languages)
    return {"ok": True, "updated": updated}


@app.post("/api/localization/translations")
async def api_localization_upsert_translation(body: TranslationUpsertRequest):
    """Add or update a translation for an entity field, language and optional brand (empty brand_id = global)."""
    entity_type = (body.entity_type or "").strip()
    entity_id = (body.entity_id or "").strip()
    field = (body.field or "name").strip() or "name"
    text = (body.text or "").strip()
    if not entity_type or not entity_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="entity_type and entity_id are required.")
    brand_val = "" if body.brand_id is None else str(body.brand_id)
    translations = _load_translations()
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    updated = False
    for t in translations:
        t_brand = (t.get("brand_id") or "").strip()
        if (
            t["entity_type"] == entity_type
            and t["entity_id"] == entity_id
            and (t.get("field") or "name") == field
            and t["language_id"] == body.language_id
            and t_brand == brand_val
        ):
            t["text"] = text
            if not t.get("created_at"):
                t["created_at"] = now
            t["updated_at"] = now
            updated = True
            break
    if not updated:
        translations.append({
            "entity_type": entity_type,
            "entity_id": entity_id,
            "field": field,
            "language_id": body.language_id,
            "brand_id": brand_val,
            "text": text,
            "created_at": now,
            "updated_at": now,
        })
    _save_translations(translations)
    return {"ok": True, "updated": updated}


# ── Brands (Configuration) ─────────────────────────────────────────────────
def _next_brand_id(brands: list[dict]) -> int:
    if not brands:
        return 1
    return max((b.get("id") or 0 for b in brands), default=0) + 1


def _next_partner_id(partners: list[dict]) -> int:
    if not partners:
        return 1
    return max((p.get("id") or 0 for p in partners), default=0) + 1


@app.post("/api/partners")
async def create_partner(body: CreatePartnerRequest):
    """Create a new partner (B2B client). Stored in data/partners.csv."""
    from fastapi import HTTPException
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    code = (body.code or "").strip() or name.lower().replace(" ", "_")[:32]
    partners = _load_partners()
    if any((p.get("code") or "").lower() == code.lower() for p in partners):
        raise HTTPException(status_code=400, detail=f"Partner with code '{code}' already exists")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    pid = _next_partner_id(partners)
    new_partner = {
        "id": pid,
        "name": name,
        "code": code,
        "active": body.active if body.active is not None else True,
        "created_at": now,
        "updated_at": now,
    }
    partners.append(new_partner)
    _save_partners(partners)
    return {"ok": True, "partner": new_partner}


@app.put("/api/partners/{partner_id:int}")
async def update_partner(partner_id: int, body: UpdatePartnerRequest):
    """Update an existing partner."""
    from fastapi import HTTPException
    partners = _load_partners()
    partner = next((p for p in partners if p.get("id") == partner_id), None)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    if body.name is not None:
        partner["name"] = (body.name or "").strip()
    if body.code is not None:
        partner["code"] = (body.code or "").strip()
    if body.active is not None:
        partner["active"] = body.active
    partner["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    _save_partners(partners)
    return {"ok": True, "partner": partner}


@app.post("/api/brands")
async def create_brand(body: CreateBrandRequest):
    """Create a new brand. Stored in data/brands.csv."""
    from fastapi import HTTPException
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    code = (body.code or "").strip() or name.lower().replace(" ", "_")[:32]
    brands = _load_brands()
    if any((b.get("code") or "").lower() == code.lower() for b in brands):
        raise HTTPException(status_code=400, detail=f"Brand with code '{code}' already exists")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    jurisdiction = ",".join(body.jurisdiction) if body.jurisdiction else ""
    language_ids = ",".join(str(x) for x in (body.language_ids or []))
    currencies = ",".join(body.currencies or [])
    odds_formats = ",".join(body.odds_formats or [])
    partner_id = getattr(body, "partner_id", None)  # None = Global (platform)
    bid = _next_brand_id(brands)
    new_brand = {
        "id": bid,
        "name": name,
        "code": code,
        "partner_id": partner_id,
        "jurisdiction": jurisdiction,
        "language_ids": language_ids,
        "currencies": currencies,
        "odds_formats": odds_formats,
        "created_at": now,
        "updated_at": now,
    }
    brands.append(new_brand)
    _save_brands(brands)
    return {"ok": True, "brand": new_brand}


@app.put("/api/brands/{brand_id:int}")
async def update_brand(brand_id: int, body: UpdateBrandRequest):
    """Update an existing brand."""
    from fastapi import HTTPException
    brands = _load_brands()
    brand = next((b for b in brands if b.get("id") == brand_id), None)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    if body.name is not None:
        brand["name"] = (body.name or "").strip()
    if body.code is not None:
        brand["code"] = (body.code or "").strip()
    if body.partner_id is not None:
        brand["partner_id"] = body.partner_id
    if body.jurisdiction is not None:
        brand["jurisdiction"] = ",".join(body.jurisdiction) if body.jurisdiction else ""
    if body.language_ids is not None:
        brand["language_ids"] = ",".join(str(x) for x in body.language_ids)
    if body.currencies is not None:
        brand["currencies"] = ",".join(body.currencies)
    if body.odds_formats is not None:
        brand["odds_formats"] = ",".join(body.odds_formats)
    brand["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    _save_brands(brands)
    return {"ok": True, "brand": brand}


# ── RBAC API ───────────────────────────────────────────────────────────────

def _next_rbac_user_id(users: list[dict]) -> int:
    if not users:
        return 1
    return max((u.get("user_id") or 0 for u in users), default=0) + 1


def _get_user_permissions(user_id: int) -> set[str]:
    """Resolve all permission codes for a user from their roles. Returns empty set if user inactive or not found."""
    users = _load_rbac_users()
    user = next((u for u in users if u.get("user_id") == user_id), None)
    if not user or not user.get("active"):
        return set()
    user_roles = _load_rbac_user_roles()
    role_ids = [ur["role_id"] for ur in user_roles if ur.get("user_id") == user_id]
    perms = _load_rbac_role_permissions()
    return {p["permission_code"] for p in perms if p["role_id"] in role_ids and p.get("permission_code")}


@app.get("/api/rbac/users")
async def list_rbac_users(partner_id: Optional[int] = None):
    """List users. If partner_id given, filter to that partner (for partner-scoped admin)."""
    users = _load_rbac_users()
    if partner_id is not None:
        users = [u for u in users if u.get("partner_id") == partner_id]
    roles = _load_rbac_roles()
    user_roles = _load_rbac_user_roles()
    role_by_id = {r["role_id"]: r for r in roles}
    partners = _load_partners()
    partner_by_id = {p["id"]: p for p in partners}
    for u in users:
        u["roles"] = [
            role_by_id[ur["role_id"]]
            for ur in user_roles
            if ur["user_id"] == u["user_id"] and ur["role_id"] in role_by_id
        ]
        u["partner_name"] = partner_by_id.get(u["partner_id"], {}).get("name", "") if u.get("partner_id") else "Platform"
    return {"users": users}


@app.get("/api/rbac/users/{user_id:int}")
async def get_rbac_user(user_id: int):
    from fastapi import HTTPException
    users = _load_rbac_users()
    user = next((u for u in users if u.get("user_id") == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user_roles = _load_rbac_user_roles()
    roles = _load_rbac_roles()
    role_by_id = {r["role_id"]: r for r in roles}
    user["roles"] = [
        role_by_id[ur["role_id"]]
        for ur in user_roles
        if ur["user_id"] == user_id and ur["role_id"] in role_by_id
    ]
    user["role_ids"] = [r["role_id"] for r in user["roles"]]
    user_brands = _load_rbac_user_brands()
    user["brand_ids"] = [ub["brand_id"] for ub in user_brands if ub["user_id"] == user_id]
    partners = _load_partners()
    user["partner_name"] = next((p["name"] for p in partners if p["id"] == user.get("partner_id")), None) or "Platform"
    return {"user": user}


@app.post("/api/rbac/users")
async def create_rbac_user(body: CreateRbacUserRequest):
    from fastapi import HTTPException
    email = (body.email or "").strip()
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    users = _load_rbac_users()
    if any((u.get("email") or "").lower() == email.lower() for u in users):
        raise HTTPException(status_code=400, detail="User with this email already exists")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    uid = _next_rbac_user_id(users)
    login = (body.login or "").strip() or email.split("@")[0]
    role_ids = list(body.role_ids) if body.role_ids else []
    if len(role_ids) > 1:
        raise HTTPException(status_code=400, detail="Each user may have only one role.")
    role_ids = role_ids[:1]
    new_user = {
        "user_id": uid,
        "login": login,
        "email": email,
        "display_name": (body.display_name or "").strip() or login,
        "active": body.active if body.active is not None else True,
        "partner_id": body.partner_id,
        "created_by": "SuperAdmin",
        "created_at": now,
        "updated_at": now,
        "last_login": "",
        "online": False,
    }
    users.append(new_user)
    _save_rbac_users(users)
    user_roles = _load_rbac_user_roles()
    for rid in role_ids:
        user_roles.append({
            "user_id": uid,
            "role_id": rid,
            "assigned_at": now,
            "assigned_by_user_id": None,
        })
    _save_rbac_user_roles(user_roles)
    if body.brand_ids:
        user_brands = _load_rbac_user_brands()
        for bid in body.brand_ids:
            user_brands.append({"user_id": uid, "brand_id": bid})
        _save_rbac_user_brands(user_brands)
    _rbac_audit_append(None, "user.create", "user", str(uid), f"email={email}")
    return {"ok": True, "user": new_user}


@app.put("/api/rbac/users/{user_id:int}")
async def update_rbac_user(user_id: int, body: UpdateRbacUserRequest):
    from fastapi import HTTPException
    users = _load_rbac_users()
    user = next((u for u in users if u.get("user_id") == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if body.email is not None:
        email = (body.email or "").strip()
        if not email:
            raise HTTPException(status_code=400, detail="Email cannot be empty")
        if any((u.get("email") or "").lower() == email.lower() for u in users if u.get("user_id") != user_id):
            raise HTTPException(status_code=400, detail="Another user with this email exists")
        user["email"] = email
    if body.login is not None:
        user["login"] = (body.login or "").strip() or user.get("email", "").split("@")[0]
    if body.display_name is not None:
        user["display_name"] = (body.display_name or "").strip()
    if body.partner_id is not None:
        user["partner_id"] = body.partner_id
    if body.active is not None:
        user["active"] = body.active
    if body.role_ids is not None:
        role_ids = list(body.role_ids)
        if len(role_ids) > 1:
            raise HTTPException(status_code=400, detail="Each user may have only one role.")
        role_ids = role_ids[:1]
        user_roles = _load_rbac_user_roles()
        user_roles = [ur for ur in user_roles if ur["user_id"] != user_id]
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        for rid in role_ids:
            user_roles.append({"user_id": user_id, "role_id": rid, "assigned_at": now, "assigned_by_user_id": None})
        _save_rbac_user_roles(user_roles)
    if body.brand_ids is not None:
        user_brands = _load_rbac_user_brands()
        user_brands = [ub for ub in user_brands if ub["user_id"] != user_id]
        for bid in body.brand_ids:
            user_brands.append({"user_id": user_id, "brand_id": bid})
        _save_rbac_user_brands(user_brands)
    user["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    _save_rbac_users(users)
    _rbac_audit_append(None, "user.update", "user", str(user_id), "")
    return {"ok": True, "user": user}


@app.delete("/api/rbac/users/{user_id:int}")
async def delete_rbac_user(user_id: int):
    from fastapi import HTTPException
    users = _load_rbac_users()
    user = next((u for u in users if u.get("user_id") == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.get("active"):
        raise HTTPException(status_code=400, detail="Cannot delete active user; deactivate first")
    users = [u for u in users if u.get("user_id") != user_id]
    _save_rbac_users(users)
    user_roles = _load_rbac_user_roles()
    user_roles = [ur for ur in user_roles if ur["user_id"] != user_id]
    _save_rbac_user_roles(user_roles)
    user_brands = _load_rbac_user_brands()
    user_brands = [ub for ub in user_brands if ub["user_id"] != user_id]
    _save_rbac_user_brands(user_brands)
    _rbac_audit_append(None, "user.delete", "user", str(user_id), "")
    return {"ok": True}


@app.get("/api/rbac/roles")
async def list_rbac_roles():
    roles = _load_rbac_roles()
    perms = _load_rbac_role_permissions()
    perms_by_role = {}
    for p in perms:
        perms_by_role.setdefault(p["role_id"], []).append(p["permission_code"])
    for r in roles:
        r["permission_codes"] = perms_by_role.get(r["role_id"], [])
    return {"roles": roles}


@app.post("/api/rbac/roles")
async def create_rbac_role(body: CreateRbacRoleRequest):
    """Create a new role. partner_id optional (null = Platform). New roles are non-system."""
    from fastapi import HTTPException
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    roles = _load_rbac_roles()
    next_id = max((r.get("role_id") or 0 for r in roles), default=0) + 1
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    new_role = {
        "role_id": next_id,
        "name": name,
        "active": body.active if body.active is not None else True,
        "is_system": False,
        "partner_id": body.partner_id,
        "created_at": now,
        "updated_at": now,
    }
    roles.append(new_role)
    _save_rbac_roles(roles)
    if body.permission_codes:
        perms = _load_rbac_role_permissions()
        for code in body.permission_codes:
            code = (code or "").strip()
            if code:
                perms.append({"role_id": next_id, "permission_code": code})
        _save_rbac_role_permissions(perms)
    _rbac_audit_append(None, "role.create", "role", str(next_id), name)
    return {"ok": True, "role_id": next_id}


@app.put("/api/rbac/roles/{role_id:int}/permissions")
async def update_rbac_role_permissions(role_id: int, body: UpdateRolePermissionsRequest):
    """Replace all permissions for a role. Sends full list (including always-granted)."""
    from fastapi import HTTPException
    roles = _load_rbac_roles()
    if not any(r.get("role_id") == role_id for r in roles):
        raise HTTPException(status_code=404, detail="Role not found")
    perms = _load_rbac_role_permissions()
    perms = [p for p in perms if p["role_id"] != role_id]
    codes = [c for c in (body.permission_codes or []) if (c or "").strip()]
    for code in codes:
        perms.append({"role_id": role_id, "permission_code": code.strip()})
    _save_rbac_role_permissions(perms)
    _rbac_audit_append(None, "role.permissions.update", "role", str(role_id), str(len(codes)) + " permissions")
    return {"ok": True}


@app.get("/api/rbac/audit-log")
async def list_rbac_audit_log(limit: int = 100):
    if not RBAC_AUDIT_LOG_PATH.exists():
        return {"entries": []}
    with open(RBAC_AUDIT_LOG_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    rows = sorted(rows, key=lambda r: (r.get("created_at") or ""), reverse=True)[:limit]
    return {"entries": rows}


@app.post("/api/margin-templates")
async def create_margin_template(body: CreateMarginTemplateRequest):
    """Create a new margin template for the given (brand_id, sport_id) scope. Name required; 'Uncategorized' is reserved."""
    from fastapi import HTTPException
    rows = _load_margin_templates()  # all rows for next_id
    next_id = max((r.get("id") or 0 for r in rows), default=0) + 1
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    if name.lower() == "uncategorized":
        raise HTTPException(status_code=400, detail="Name 'Uncategorized' is reserved")
    b_key = str(body.brand_id).strip() if body.brand_id is not None else ""
    s_key = str(body.sport_id).strip() if body.sport_id is not None else ""
    new_template = {
        "id": next_id,
        "name": name,
        "short_name": (body.short_name or "").strip(),
        "pm_margin": (body.pm_margin or "").strip(),
        "ip_margin": (body.ip_margin or "").strip(),
        "cashout": (body.cashout or "").strip(),
        "betbuilder": (body.betbuilder or "").strip(),
        "bet_delay": (body.bet_delay or "").strip(),
        "leagues_count": 0,
        "markets_count": 0,
        "is_default": False,
        "brand_id": b_key,
        "sport_id": s_key,
    }
    rows.append(_enrich_margin_template_risk_class(new_template))
    _save_margin_templates(rows)
    return {"ok": True, "template": new_template}


@app.patch("/api/margin-templates/{template_id:int}")
async def update_margin_template(template_id: int, body: UpdateMarginTemplateRequest):
    """Update a margin template (name, short_name, pm_margin, ip_margin, cashout, betbuilder, bet_delay)."""
    from fastapi import HTTPException
    rows = _load_margin_templates()
    template = next((r for r in rows if r.get("id") == template_id), None)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    if body.name is not None:
        template["name"] = (body.name or "").strip()
    if body.short_name is not None:
        template["short_name"] = (body.short_name or "").strip()
    if body.pm_margin is not None:
        template["pm_margin"] = (body.pm_margin or "").strip()
    if body.ip_margin is not None:
        template["ip_margin"] = (body.ip_margin or "").strip()
    if body.cashout is not None:
        template["cashout"] = (body.cashout or "").strip()
    if body.betbuilder is not None:
        template["betbuilder"] = (body.betbuilder or "").strip()
    if body.bet_delay is not None:
        template["bet_delay"] = (body.bet_delay or "").strip()
    if body.risk_class_id is not None:
        template["risk_class_id"] = body.risk_class_id if body.risk_class_id else None
        rc = next((c for c in RISK_CLASSES if c.get("id") == template["risk_class_id"]), None)
        template["risk_class"] = (
            {"id": rc["id"], "letter": rc["letter"], "name": rc["name"], "circle_color": rc["circle_color"]}
            if rc else None
        )
    _save_margin_templates(rows)
    return {"ok": True, "template": template}


@app.get("/api/margin-templates/copy-sources")
async def margin_templates_copy_sources(
    sport_id: str | None = None,
    current_brand_id: str | None = None,
):
    """
    List brands that can be copied from (for Copy from modal).
    Returns brands with templates for this sport; excludes current brand to avoid copy-from-self.
    """
    brands = _load_brands()
    current_bid = (current_brand_id or "").strip()
    out = [{"id": None, "label": "Global"}]
    for b in brands:
        bid = str(b.get("id") or "").strip()
        if not bid:
            continue
        if bid == current_bid:
            continue
        label = (b.get("name") or b.get("code") or bid)
        out.append({"id": b.get("id"), "label": label})
    return {"brands": out}


@app.post("/api/margin-templates/copy-from")
async def margin_templates_copy_from(body: CopyFromBrandRequest):
    """
    Copy all templates and their settings from source brand to target brand (same sport).
    For each source template: find or create by name in target scope, copy config and competition assignments.
    One-time copy; no link between source and target.
    """
    from fastapi import HTTPException
    source_brand_key = "" if body.source_brand_id is None else str(body.source_brand_id).strip()
    target_brand_key = "" if body.target_brand_id is None else str(body.target_brand_id).strip()
    sport_key = str(body.sport_id).strip()
    if not sport_key:
        raise HTTPException(status_code=400, detail="sport_id is required")

    # Ensure target scope has Uncategorized (so we have a scope to copy into)
    _load_margin_templates(
        int(target_brand_key) if target_brand_key else None,
        int(sport_key) if sport_key else None,
    )
    all_rows = _load_margin_templates()

    def in_scope(t: dict, b_key: str, s_key: str) -> bool:
        rb = (t.get("brand_id") or "").strip()
        rs = (t.get("sport_id") or "").strip()
        brand_ok = rb == b_key
        sport_ok = rs == s_key or (b_key == "" and rs == "")
        return brand_ok and sport_ok

    source_templates = [t for t in all_rows if in_scope(t, source_brand_key, sport_key)]
    target_templates = [t for t in all_rows if in_scope(t, target_brand_key, sport_key)]
    name_to_target = {(t.get("name") or "").strip(): t for t in target_templates}
    source_id_to_name = {t["id"]: (t.get("name") or "").strip() for t in source_templates}
    source_template_ids = {t["id"] for t in source_templates}

    tcs = _load_margin_template_competitions()
    source_assignments = [(r["template_id"], r["competition_id"]) for r in tcs if r["template_id"] in source_template_ids]

    for s in source_templates:
        name = (s.get("name") or "").strip()
        target_t = name_to_target.get(name)
        if target_t:
            for key in ("short_name", "pm_margin", "ip_margin", "cashout", "betbuilder", "bet_delay", "risk_class_id"):
                target_t[key] = s.get(key)
            target_t["risk_class"] = s.get("risk_class")
        else:
            next_id = max((r.get("id") or 0 for r in all_rows), default=0) + 1
            new_t = {
                "id": next_id,
                "name": name,
                "short_name": s.get("short_name") or "",
                "pm_margin": s.get("pm_margin") or "",
                "ip_margin": s.get("ip_margin") or "",
                "cashout": s.get("cashout") or "",
                "betbuilder": s.get("betbuilder") or "",
                "bet_delay": s.get("bet_delay") or "",
                "risk_class_id": s.get("risk_class_id"),
                "leagues_count": 0,
                "markets_count": 0,
                "is_default": s.get("is_default") if name.lower() == "uncategorized" else False,
                "brand_id": target_brand_key,
                "sport_id": sport_key,
            }
            all_rows.append(_enrich_margin_template_risk_class(new_t))
            name_to_target[name] = new_t

    _save_margin_templates(all_rows)

    target_scope_ids = {t["id"] for t in all_rows if in_scope(t, target_brand_key, sport_key)}
    name_to_target_id = {name: t["id"] for name, t in name_to_target.items()}
    new_assignments = []
    for stid, cid in source_assignments:
        sname = source_id_to_name.get(stid)
        if not sname:
            continue
        ttid = name_to_target_id.get(sname)
        if ttid is not None:
            new_assignments.append((ttid, cid))

    tcs = _load_margin_template_competitions()
    tcs = [r for r in tcs if r["template_id"] not in target_scope_ids]
    for ttid, cid in new_assignments:
        tcs.append({"template_id": ttid, "competition_id": cid})
    _save_margin_template_competitions(tcs)

    return {"ok": True, "templates_copied": len(source_templates), "competitions_copied": len(new_assignments)}


def _template_ids_for_scope(brand_id: int | None, sport_id: int | None) -> list[int]:
    """Return template IDs for the given (brand_id, sport_id) scope."""
    templates = _load_margin_templates(brand_id, sport_id)
    return [t["id"] for t in templates if t.get("id") is not None]


@app.get("/api/margin-templates/{template_id:int}/competitions")
async def margin_template_competitions(
    template_id: int,
    brand_id: str | None = None,
    sport_id: str | None = None,
):
    """
    List competitions in this template and not in this template (for current scope).
    Used by Add/Remove Competitions modal. brand_id/sport_id define scope (query params).
    """
    from fastapi import HTTPException
    b = (brand_id or "").strip()
    s = (sport_id or "").strip()
    try:
        sport_id_int = int(s) if s else None
    except (TypeError, ValueError):
        sport_id_int = None
    brand_id_int = None
    if b:
        try:
            brand_id_int = int(b)
        except (TypeError, ValueError):
            pass
    scope_templates = _load_margin_templates(brand_id_int, sport_id_int)
    scope_template_ids = [t["id"] for t in scope_templates if t.get("id") is not None]
    if template_id not in scope_template_ids:
        raise HTTPException(status_code=404, detail="Template not in current scope")
    template_name_by_id = {t["id"]: (t.get("name") or "").strip() or "—" for t in scope_templates}
    categories = DOMAIN_ENTITIES.get("categories", [])
    category_name_by_id = {cat["domain_id"]: (cat.get("name") or "").strip() or "—" for cat in categories}
    competitions = DOMAIN_ENTITIES.get("competitions", [])
    sport_competitions = [
        {
            "competition_id": c["domain_id"],
            "name": (c.get("name") or "").strip() or "—",
            "category_name": category_name_by_id.get(c.get("category_id"), "—"),
        }
        for c in competitions
        if c.get("domain_id") is not None and c.get("sport_id") == sport_id_int
    ] if sport_id_int else []
    tcs = _load_margin_template_competitions()
    comp_to_template: dict[int, int] = {}
    for r in tcs:
        tid, cid = r.get("template_id"), r.get("competition_id")
        if tid in scope_template_ids and cid is not None:
            comp_to_template[cid] = tid
    is_uncategorized = (template_name_by_id.get(template_id) or "").strip().lower() == "uncategorized"
    if is_uncategorized:
        # Default bucket: in_template = explicitly in Uncategorized or not in any scope template
        in_template = [
            {"competition_id": c["competition_id"], "name": c["name"], "category_name": c.get("category_name", "—")}
            for c in sport_competitions
            if comp_to_template.get(c["competition_id"]) == template_id or comp_to_template.get(c["competition_id"]) is None
        ]
        not_in_template = [
            {
                "competition_id": c["competition_id"],
                "name": c["name"],
                "category_name": c.get("category_name", "—"),
                "current_template_name": template_name_by_id.get(comp_to_template.get(c["competition_id"]), "—"),
            }
            for c in sport_competitions
            if comp_to_template.get(c["competition_id"]) is not None and comp_to_template.get(c["competition_id"]) != template_id
        ]
    else:
        in_template = [
            {"competition_id": c["competition_id"], "name": c["name"], "category_name": c.get("category_name", "—")}
            for c in sport_competitions
            if comp_to_template.get(c["competition_id"]) == template_id
        ]
        not_in_template = [
            {
                "competition_id": c["competition_id"],
                "name": c["name"],
                "category_name": c.get("category_name", "—"),
                "current_template_name": template_name_by_id.get(comp_to_template.get(c["competition_id"]), "—"),
            }
            for c in sport_competitions
            if comp_to_template.get(c["competition_id"]) != template_id
        ]
    other_templates = [{"id": t["id"], "name": (t.get("name") or "").strip() or "—"} for t in scope_templates if t.get("id") != template_id]
    return {
        "template_id": template_id,
        "template_name": template_name_by_id.get(template_id, "—"),
        "in_template": in_template,
        "not_in_template": not_in_template,
        "other_templates": other_templates,
    }


@app.post("/api/margin-templates/competitions/assign")
async def assign_competition_to_template(body: AssignCompetitionToTemplateRequest):
    """
    Move a competition into a margin template (within current scope).
    Removes the competition from any other template in the same scope, then adds to the given template.
    """
    from fastapi import HTTPException
    scope_templates = _load_margin_templates(body.brand_id, body.sport_id)
    scope_template_ids = [t["id"] for t in scope_templates if t.get("id") is not None]
    if body.template_id not in scope_template_ids:
        raise HTTPException(status_code=400, detail="Template not in current scope")
    competitions = DOMAIN_ENTITIES.get("competitions", [])
    comp = next((c for c in competitions if c.get("domain_id") == body.competition_id), None)
    if not comp or (body.sport_id is not None and comp.get("sport_id") != body.sport_id):
        raise HTTPException(status_code=400, detail="Competition not found or not in selected sport")
    rows = _load_margin_template_competitions()
    rows = [r for r in rows if not (r.get("competition_id") == body.competition_id and r.get("template_id") in scope_template_ids)]
    rows.append({"template_id": body.template_id, "competition_id": body.competition_id})
    _save_margin_template_competitions(rows)
    return {"ok": True, "template_id": body.template_id, "competition_id": body.competition_id}


@app.get("/entities", response_class=HTMLResponse)
async def entities_view(
    request: Request,
    sort_sports: str = "asc",
    market_sport_id: str | None = None,
):
    """
    Configuration > Entities page.
    Shows Sports, Categories, Competitions, Teams, Markets tabs.
    Sports: sort by name (default asc); sort_sports=asc|desc toggles via Name column header.
    Markets: filter by sport when market_sport_id is set.
    """
    sports_list = list(DOMAIN_ENTITIES["sports"])
    sort_asc = (sort_sports or "asc").strip().lower() != "desc"
    sports_list.sort(key=lambda e: (e.get("name") or "").strip().lower(), reverse=not sort_asc)
    markets_list = list(DOMAIN_ENTITIES["markets"])
    market_sport_id_int: int | None = None
    if market_sport_id and str(market_sport_id).strip():
        try:
            market_sport_id_int = int(market_sport_id)
            markets_list = [m for m in markets_list if (m.get("sport_id")) == market_sport_id_int]
        except (TypeError, ValueError):
            pass
    entities = {
        "sports":       sports_list,
        "categories":   DOMAIN_ENTITIES["categories"],
        "competitions": DOMAIN_ENTITIES["competitions"],
        "teams":        DOMAIN_ENTITIES["teams"],
        "markets":      markets_list,
    }
    stats = {k: len(v) for k, v in entities.items()}

    # FK lookup dicts for template display
    sports_by_id     = {s["domain_id"]: s["name"] for s in DOMAIN_ENTITIES["sports"]}
    categories_by_id = {c["domain_id"]: c["name"] for c in DOMAIN_ENTITIES["categories"]}
    feeds_by_id      = {f["domain_id"]: f["name"] for f in FEEDS}
    # Per-entity list of feed refs from entity_feed_mappings.csv (reload from disk so manual edits are visible)
    mappings = _load_entity_feed_mappings()
    entity_feed_refs_by_key = {}
    for m in mappings:
        k = f"{m['entity_type']}:{m['domain_id']}"
        entity_feed_refs_by_key.setdefault(k, []).append({
            "feed_provider_id": m["feed_provider_id"],
            "feed_id": m["feed_id"],
        })

    market_templates = _load_market_templates()
    market_period_types = _load_market_period_types()
    market_score_types = _load_market_score_types()
    market_groups = _load_market_groups()
    countries = _load_countries()
    countries_by_cc = {c.get("cc", ""): c.get("name", "") for c in countries}
    participant_types = _load_participant_types()
    participant_types_by_id = {pt["id"]: pt["name"] for pt in participant_types}
    underage_categories = _load_underage_categories()
    underage_categories_by_id = {u["id"]: u["name"] for u in underage_categories}

    # Feeds that have at least one sport mapping (for market mapper dropdown; hides removed feeds like SBObet)
    feed_ids_with_sport_mappings = {m["feed_provider_id"] for m in SPORT_FEED_MAPPINGS}
    mapper_feeds = [f for f in FEEDS if f.get("domain_id") in feed_ids_with_sport_mappings]

    return templates.TemplateResponse("configuration/entities.html", {
        "participant_types": participant_types,
        "underage_categories": underage_categories,
        "underage_categories_by_id": underage_categories_by_id,
        "request": request,
        "countries": countries,
        "countries_by_cc": countries_by_cc,
        "section": "entities",
        "entities": entities,
        "stats": stats,
        "sports_sort": "desc" if not sort_asc else "asc",
        "sports_by_id": sports_by_id,
        "categories_by_id": categories_by_id,
        "feeds_by_id": feeds_by_id,
        "feeds": FEEDS,
        "mapper_feeds": mapper_feeds,
        "entity_feed_refs_by_key": entity_feed_refs_by_key,
        "market_templates": market_templates,
        "market_period_types": market_period_types,
        "market_score_types": market_score_types,
        "market_groups": market_groups,
        "participant_types_by_id": participant_types_by_id,
        "market_sport_id": market_sport_id_int,
    })


@app.post("/api/feed-sports")
async def api_add_feed_sport(
    feed_provider: str = Form(...),
    feed_sport_id: str = Form(...),
    feed_sport_name: str = Form(""),
):
    """Add a row to feed_sports.csv. feed_provider = feed code (e.g. betfair), feed_sport_id = feed's sport id, feed_sport_name = display name."""
    feed_provider = (feed_provider or "").strip()
    feed_sport_id = (feed_sport_id or "").strip()
    feed_sport_name = (feed_sport_name or "").strip()
    if not feed_provider or not feed_sport_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="feed_provider and feed_sport_id are required.")
    rows = _load_feed_sports_rows()
    if any((r.get("feed_provider") or "").strip() == feed_provider and (r.get("feed_sport_id") or "").strip() == feed_sport_id for r in rows):
        return {"ok": True, "message": "Already exists"}
    rows.append({"feed_provider": feed_provider, "feed_sport_id": feed_sport_id, "feed_sport_name": feed_sport_name or feed_sport_id})
    _save_feed_sports(rows)
    return {"ok": True, "created": True}


# Feeder Configuration: system action keys (for grid columns)
FEEDER_SYSTEM_ACTIONS = [
    ("automapping_enabled", "Automapping enabled"),
    ("automapping_teams_enabled", "Automapping teams enabled"),
    ("automapping_start_time_threshold_hours", "Start time threshold (h)"),
    ("auto_live_offer", "Auto live offer"),
    ("automap_neutral_grounds", "Automap neutral grounds"),
    ("auto_update_start_time_rank", "Start time rank"),
    ("market_mapping_behavior", "Market mapping behavior"),
    ("auto_create_domain_event", "Auto create domain event"),
    ("auto_create_domain_player", "Auto create domain player"),
    ("automap_market_type_enabled", "Automap market type enabled"),
    ("auto_create_market_type_enabled", "Auto create market type enabled"),
    ("settlement_enabled", "Settlement enabled"),
    ("resettlement_enabled", "Resettlement enabled"),
    ("bet_void_enabled", "Bet void enabled"),
    ("bet_void_rollback_enabled", "Bet void rollback enabled"),
    ("auto_map_one_to_many_enabled", "Auto map one to many enabled"),
    ("external_trading_service_enabled", "External trading service enabled"),
]
FEEDER_INCIDENT_TYPES = [
    ("score", "Score"),
    ("time", "Time"),
    ("live_state", "Live State"),
    ("incidents", "Incidents"),
    ("stats", "Stats"),
    ("podcast", "Podcast"),
    ("weather", "Weather"),
    ("pitch", "Pitch"),
    ("surface", "Surface"),
    ("video", "Video"),
]

# Risk Rules Configuration: rule name -> list of {name, type} (type: text, checkbox, number)
RISK_RULES_CONFIG = [
    {"rule": "Betting Function", "params": [
        {"name": "Active", "type": "checkbox"},
        {"name": "Lower limit", "type": "number"},
        {"name": "Upper limit", "type": "number"},
    ]},
    {"rule": "Night Switch Factor", "params": [
        {"name": "Factor", "type": "number"},
        {"name": "Sign Period", "type": "text"},
    ]},
    {"rule": "Always Lay", "params": [
        {"name": "Active", "type": "checkbox"},
        {"name": "Limit", "type": "number"},
    ]},
    {"rule": "Simple Max Bet Stake", "params": [
        {"name": "Limit", "type": "number"},
    ]},
    {"rule": "Simple Max Bet Win", "params": [
        {"name": "Limit", "type": "number"},
    ]},
    {"rule": "Max Accumulated Open Stake", "params": [
        {"name": "Limit", "type": "number"},
    ]},
    {"rule": "Max Accumulated Open Win", "params": [
        {"name": "Limit", "type": "number"},
    ]},
    {"rule": "Max Same Single Bet Win", "params": [
        {"name": "Limit", "type": "number"},
    ]},
    {"rule": "Max Book Loss", "params": [
        {"name": "Limit", "type": "number"},
    ]},
    {"rule": "Max Same Multiple Bet Win", "params": [
        {"name": "Limit", "type": "number"},
    ]},
    {"rule": "Max Repeated Bet Frequency", "params": [
        {"name": "By Bet", "type": "checkbox"},
        {"name": "By Bet limit", "type": "number"},
        {"name": "By POS", "type": "checkbox"},
        {"name": "By POS limit", "type": "number"},
        {"name": "By Agent", "type": "checkbox"},
        {"name": "By Agent limit", "type": "number"},
        {"name": "By Player", "type": "checkbox"},
        {"name": "By Player limit", "type": "number"},
        {"name": "Time frame (sec)", "type": "number"},
    ]},
]


def _risk_rules_config_rows() -> list[dict]:
    """Flatten RISK_RULES_CONFIG into one row per parameter for the config table."""
    rows: list[dict] = []
    for block in RISK_RULES_CONFIG:
        rule = block["rule"]
        for p in block["params"]:
            rows.append({"risk_rule": rule, "param_name": p["name"], "param_type": p["type"]})
    return rows


# Risk Classes: id, letter, name, description, active, mbl_pct, msw_pct, mmw_pct, circle_color (Tailwind-style)
RISK_CLASSES = [
    {"id": 1, "letter": "A", "name": "A", "description": "", "active": True, "mbl_pct": 100, "msw_pct": 100, "mmw_pct": 100, "circle_color": "bg-emerald-500"},
    {"id": 2, "letter": "B", "name": "B", "description": "", "active": True, "mbl_pct": 100, "msw_pct": 100, "mmw_pct": 100, "circle_color": "bg-lime-500"},
    {"id": 3, "letter": "C", "name": "C", "description": "", "active": True, "mbl_pct": 60, "msw_pct": 60, "mmw_pct": 60, "circle_color": "bg-sky-400"},
    {"id": 4, "letter": "D", "name": "D", "description": "", "active": True, "mbl_pct": 40, "msw_pct": 40, "mmw_pct": 40, "circle_color": "bg-blue-600"},
    {"id": 5, "letter": "E", "name": "E", "description": "", "active": True, "mbl_pct": 25, "msw_pct": 25, "mmw_pct": 30, "circle_color": "bg-violet-500"},
    {"id": 6, "letter": "F", "name": "F", "description": "", "active": True, "mbl_pct": 15, "msw_pct": 15, "mmw_pct": 30, "circle_color": "bg-pink-500"},
    {"id": 7, "letter": "G", "name": "G", "description": "", "active": True, "mbl_pct": 10, "msw_pct": 10, "mmw_pct": 30, "circle_color": "bg-red-500"},
    {"id": 8, "letter": "H", "name": "H", "description": "", "active": True, "mbl_pct": 5, "msw_pct": 5, "mmw_pct": 30, "circle_color": "bg-slate-500"},
    {"id": 9, "letter": "I", "name": "I", "description": "", "active": True, "mbl_pct": 3, "msw_pct": 3, "mmw_pct": 3, "circle_color": "bg-slate-700"},
    {"id": 10, "letter": "N", "name": "Default", "description": "", "active": True, "mbl_pct": 100, "msw_pct": 100, "mmw_pct": 100, "circle_color": "bg-red-500"},
]

# Risk Categories: id, name, colour (hex), factor, description, updated
RISK_CATEGORIES = [
    {"id": "rc001", "name": "VIP", "colour": "#22c55e", "factor": "2", "description": "VIP", "updated": "31/07/25 11:04"},
    {"id": "rc002", "name": "Core", "colour": "#ef4444", "factor": "1.01", "description": "Core Business", "updated": "06/01/25 09:31"},
    {"id": "rc003", "name": "Square", "colour": "#94a3b8", "factor": "1", "description": "Normal unclassified account that requires larger sample of bets before being moved", "updated": "01/10/25 15:20"},
    {"id": "rc004", "name": "OpPolicy", "colour": "#06b6d4", "factor": "0.99", "description": "Operator Policy", "updated": "27/02/24 10:07"},
    {"id": "rc005", "name": "Unclass", "colour": "#a855f7", "factor": "0.5", "description": "Unclassified Players", "updated": "18/12/23 14:11"},
    {"id": "rc006", "name": "SpainClos", "colour": "#f97316", "factor": "0.49", "description": "Spanish Legal Closure", "updated": "21/08/23 18:13"},
    {"id": "rc007", "name": "Review", "colour": "#eab308", "factor": "0.1", "description": "Review Business", "updated": "26/01/26 09:14"},
    {"id": "rc008", "name": "PPTR", "colour": "#84cc16", "factor": "0.01", "description": "PP Management Review", "updated": "15/03/25 12:00"},
    {"id": "rc009", "name": "Wise", "colour": "#78716c", "factor": "0", "description": "Wise/Syndicates", "updated": "10/02/25 08:45"},
    {"id": "rc010", "name": "BonusAbuse", "colour": "#000000", "factor": "10", "description": "Bonus abusers", "updated": "05/11/24 16:30"},
    {"id": "rc011", "name": "Arbs", "colour": "#22c55e", "factor": "1", "description": "Arber", "updated": "20/09/24 11:20"},
    {"id": "rc012", "name": "Palps", "colour": "#ef4444", "factor": "1", "description": "Palps/Errors", "updated": "12/07/24 14:15"},
    {"id": "rc024", "name": "Exchange", "colour": "#06b6d4", "factor": "0.5", "description": "Exchange Driven Business", "updated": "01/05/25 09:00"},
    {"id": "123654", "name": "teor ★", "colour": "#a855f7", "factor": "1", "description": "jygckhgv", "updated": "03/04/25 17:22"},
]


@app.get("/risk-rules", response_class=HTMLResponse)
async def risk_rules_view(request: Request):
    """Configuration > Risk Rules page. Tabs: Configurations, Classes, Categories."""
    brands = _load_brands()
    risk_config_rows = _risk_rules_config_rows()
    risk_classes = RISK_CLASSES
    risk_categories = RISK_CATEGORIES
    return templates.TemplateResponse("configuration/risk_rules.html", {
        "request": request,
        "section": "risk_rules",
        "brands": brands,
        "risk_config_rows": risk_config_rows,
        "risk_classes": risk_classes,
        "risk_categories": risk_categories,
    })


@app.get("/feeders", response_class=HTMLResponse)
async def feeders_view(
    request: Request,
    sport_id: str | None = None,
    category_id: str | None = None,
    league_id: str | None = None,
):
    """
    Configuration > Feeder page.
    Filters: Sport, Category, League (cascading). Main grid: feeder config system actions per feed.
    When sport selected: Feeder Incidents Configuration section at bottom.
    """
    sports = DOMAIN_ENTITIES["sports"]
    categories = DOMAIN_ENTITIES["categories"]
    competitions = DOMAIN_ENTITIES["competitions"]
    sports_by_id = {s["domain_id"]: s["name"] for s in sports}
    categories_by_id = {c["domain_id"]: c["name"] for c in categories}
    competitions_by_id = {c["domain_id"]: c["name"] for c in competitions}
    feeder_config_rows = _load_feeder_config()
    feeder_incident_rows = _load_feeder_incidents()

    sid_int = int(sport_id) if sport_id and sport_id.strip() else None
    cid_int = int(category_id) if category_id and category_id.strip() else None
    lid_int = int(league_id) if league_id and league_id.strip() else None
    level = "league" if lid_int is not None else "category" if cid_int is not None else "sport" if sid_int is not None else None

    config_lookup = {}
    for r in feeder_config_rows:
        rsid, rcid, rlid = r.get("sport_id"), r.get("category_id"), r.get("league_id")
        if level == "sport" and rsid == sid_int and rcid is None and rlid is None:
            fid, key = r.get("feed_provider_id"), r.get("setting_key")
            if fid is not None and key:
                config_lookup[(fid, key)] = (r.get("value") or "").strip() or "Not set"
        elif level == "category" and rsid == sid_int and rcid == cid_int and rlid is None:
            fid, key = r.get("feed_provider_id"), r.get("setting_key")
            if fid is not None and key:
                config_lookup[(fid, key)] = (r.get("value") or "").strip() or "Not set"
        elif level == "league" and rsid == sid_int and rcid == cid_int and rlid == lid_int:
            fid, key = r.get("feed_provider_id"), r.get("setting_key")
            if fid is not None and key:
                config_lookup[(fid, key)] = (r.get("value") or "").strip() or "Not set"

    incident_lookup = {}
    if sid_int is not None:
        for r in feeder_incident_rows:
            if r.get("sport_id") == sid_int:
                fid, itype = r.get("feed_provider_id"), r.get("incident_type")
                if fid is not None and itype:
                    incident_lookup[(fid, itype)] = r.get("enabled", False)

    feed_sports = _load_feed_sports_rows()
    feed_sports_count = len(feed_sports)

    return templates.TemplateResponse("configuration/feeders.html", {
        "request": request,
        "section": "feeders",
        "feeds": FEEDS,
        "sports": sports,
        "categories": categories,
        "competitions": competitions,
        "sports_by_id": sports_by_id,
        "categories_by_id": categories_by_id,
        "competitions_by_id": competitions_by_id,
        "feeder_config_lookup": config_lookup,
        "feeder_incident_lookup": incident_lookup,
        "system_actions": FEEDER_SYSTEM_ACTIONS,
        "incident_types": FEEDER_INCIDENT_TYPES,
        "selected_sport_id": sid_int,
        "selected_category_id": cid_int,
        "selected_league_id": lid_int,
        "config_level": level,
        "feed_sports": feed_sports,
        "feed_sports_count": feed_sports_count,
    })


@app.post("/api/feeder-config")
async def api_save_feeder_config(request: Request):
    """Save feeder configuration for the given level (sport/category/league). Replaces existing rows for that level."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"detail": "Invalid JSON"}, status_code=400)
    level = (body.get("level") or "").strip()
    sport_id = body.get("sport_id")
    category_id = body.get("category_id")
    league_id = body.get("league_id")
    settings = body.get("settings") or []
    if level not in ("sport", "category", "league") or sport_id is None:
        return JSONResponse({"detail": "level and sport_id required"}, status_code=400)
    cid = int(category_id) if category_id is not None else None
    lid = int(league_id) if league_id is not None else None
    sid = int(sport_id)
    if level == "category" and cid is None:
        return JSONResponse({"detail": "category_id required for category level"}, status_code=400)
    if level == "league" and (cid is None or lid is None):
        return JSONResponse({"detail": "category_id and league_id required for league level"}, status_code=400)
    existing = _load_feeder_config()
    def match_row(r):
        rsid, rcid, rlid = r.get("sport_id"), r.get("category_id"), r.get("league_id")
        if level == "sport":
            return rsid == sid and rcid is None and rlid is None
        if level == "category":
            return rsid == sid and rcid == cid and rlid is None
        return rsid == sid and rcid == cid and rlid == lid
    kept = [r for r in existing if not match_row(r)]
    new_rows = []
    for s in settings:
        fid = s.get("feed_provider_id")
        key = (s.get("setting_key") or "").strip()
        val = (s.get("value") or "").strip()
        if fid is None or not key:
            continue
        new_rows.append({
            "level": level,
            "sport_id": sid,
            "category_id": cid,
            "league_id": lid,
            "feed_provider_id": int(fid),
            "setting_key": key,
            "value": val or "Not set",
        })
    all_rows = kept + new_rows
    _save_feeder_config(all_rows)
    return {"ok": True}


@app.post("/api/feeder-incidents")
async def api_save_feeder_incidents(request: Request):
    """Save feeder incidents configuration for the given sport_id. Replaces existing rows for that sport."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"detail": "Invalid JSON"}, status_code=400)
    sport_id = body.get("sport_id")
    incidents = body.get("incidents") or []
    if sport_id is None:
        return JSONResponse({"detail": "sport_id required"}, status_code=400)
    sid = int(sport_id)
    existing = _load_feeder_incidents()
    kept = [r for r in existing if r.get("sport_id") != sid]
    new_rows = []
    for i, inc in enumerate(incidents):
        fid = inc.get("feed_provider_id")
        itype = (inc.get("incident_type") or "").strip()
        enabled = bool(inc.get("enabled"))
        if fid is None or not itype:
            continue
        new_rows.append({
            "sport_id": sid,
            "feed_provider_id": int(fid),
            "incident_type": itype,
            "enabled": enabled,
            "sort_order": i,
        })
    all_rows = kept + new_rows
    _save_feeder_incidents(all_rows)
    return {"ok": True}


@app.get("/margin", response_class=HTMLResponse)
async def margin_view(
    request: Request,
    brand_id: str | None = None,
    sport_id: str | None = None,
    template_id: str | None = None,
):
    """
    Betting Program > Margin Configuration.
    Templates are per (brand × sport). Global = no brand. Uncategorized is always present per scope.
    Top: Brand (Global level + brands), Sport, Apply. Tables shown only after Apply.
    See docs/MARGIN_CONFIG_SPEC.md.
    """
    brands = _load_brands()
    sports = DOMAIN_ENTITIES.get("sports", [])

    # User must click Apply (sport_id in query) before we show tables or load table data
    applied = sport_id is not None and str(sport_id).strip() != ""

    selected_brand_id = None
    if brand_id and str(brand_id).strip():
        try:
            selected_brand_id = int(brand_id)
        except (TypeError, ValueError):
            pass

    # Default Sport to Football when not applied (for dropdown preload)
    football = next((s for s in sports if (s.get("name") or "").strip().lower() == "football"), sports[0] if sports else None)
    default_sport_id = int(football["domain_id"]) if football and football.get("domain_id") is not None else None

    selected_sport_id = default_sport_id
    if applied and sport_id and str(sport_id).strip():
        try:
            selected_sport_id = int(sport_id)
        except (TypeError, ValueError):
            selected_sport_id = default_sport_id

    if not applied:
        return templates.TemplateResponse("margin/margin.html", {
            "request": request,
            "section": "margin_config",
            "brands": brands,
            "sports": sports,
            "selected_brand_id": selected_brand_id,
            "selected_sport_id": selected_sport_id,
            "show_tables": False,
            "margin_templates": [],
            "risk_classes": RISK_CLASSES,
            "market_groups_with_markets": [],
            "selected_template_id": None,
            "market_templates": [],
            "period_types": [],
            "score_types": [],
        })

    # Load templates for this (brand, sport) scope; ensures Uncategorized exists per scope (see MARGIN_CONFIG_SPEC).
    # Uncategorized is kept empty by default; traders move competitions into their respective templates.
    margin_templates = _load_margin_templates(selected_brand_id, selected_sport_id)
    template_competitions = _load_margin_template_competitions()
    # Competition count per template: only competitions for the selected sport.
    # Uncategorized is the default bucket: count also competitions not assigned to any template in this scope.
    competition_ids_for_sport = {
        int(c["domain_id"]) for c in DOMAIN_ENTITIES.get("competitions", [])
        if c.get("domain_id") is not None and c.get("sport_id") == selected_sport_id
    } if selected_sport_id else set()
    scope_template_ids = [t["id"] for t in margin_templates if t.get("id") is not None]
    comp_to_scope_template: dict[int, int] = {}
    for r in template_competitions:
        tid, cid = r.get("template_id"), r.get("competition_id")
        if tid in scope_template_ids and cid is not None:
            comp_to_scope_template[cid] = tid
    uncategorized_ids = {t["id"] for t in margin_templates if (t.get("name") or "").strip().lower() == "uncategorized"}
    for t in margin_templates:
        tid = t.get("id")
        explicit = sum(
            1 for r in template_competitions
            if r.get("template_id") == tid and r.get("competition_id") in competition_ids_for_sport
        )
        if tid in uncategorized_ids:
            # Default bucket: add competitions of this sport not in any template of this scope
            unassigned = sum(
                1 for cid in competition_ids_for_sport
                if comp_to_scope_template.get(cid) is None
            )
            t["leagues_count"] = explicit + unassigned
        else:
            t["leagues_count"] = explicit
    market_templates = _load_market_templates()
    market_period_types = _load_market_period_types()
    market_score_types = _load_market_score_types()

    selected_template_id = None
    if template_id and str(template_id).strip():
        try:
            selected_template_id = int(template_id)
        except (TypeError, ValueError):
            pass
    if selected_template_id is None and margin_templates:
        default_t = next((t for t in margin_templates if t.get("is_default")), margin_templates[0])
        selected_template_id = default_t.get("id")

    all_markets = DOMAIN_ENTITIES.get("markets", [])
    # Only show markets for the selected sport (e.g. no Tennis markets under Football)
    if selected_sport_id is not None:
        markets = [m for m in all_markets if (m.get("sport_id")) == selected_sport_id]
    else:
        markets = []
    market_groups_list = _load_market_groups()
    if markets:
        group_codes = {(g.get("code") or "").strip() for g in market_groups_list}
        market_groups_with_markets: list[dict] = []
        for g in market_groups_list:
            code = (g.get("code") or "").strip()
            group_markets = [{"domain_id": m.get("domain_id"), "code": m.get("code"), "name": m.get("name") or m.get("code"), "market_group": m.get("market_group")} for m in markets if (m.get("market_group") or "").strip() == code]
            # Only show market groups that have at least one market (hide empty Half, Corners, Cards, etc.)
            if group_markets:
                market_groups_with_markets.append({"group": g, "markets": group_markets})
        orphan = [{"domain_id": m.get("domain_id"), "code": m.get("code"), "name": m.get("name") or m.get("code"), "market_group": m.get("market_group")} for m in markets if (m.get("market_group") or "").strip() not in group_codes]
        if orphan:
            market_groups_with_markets.append({"group": {"domain_id": 0, "code": "", "name": "Other"}, "markets": orphan})
    else:
        market_groups_with_markets = [{"group": {"domain_id": 0, "code": "", "name": "Main"}, "markets": [{"domain_id": t.get("domain_id"), "code": t.get("code"), "name": (t.get("name") or "").strip() or t.get("code")} for t in market_templates]}] if selected_sport_id is None else []

    selected_template_name = ""
    template_prematch_dyn = ""
    template_inplay_dyn = ""
    template_risk_class = None
    if selected_template_id and margin_templates:
        sel = next((t for t in margin_templates if t.get("id") == selected_template_id), None)
        if sel:
            selected_template_name = (sel.get("name") or "").strip()
            pm = (sel.get("pm_margin") or "").strip()
            if pm:
                try:
                    template_prematch_dyn = f"{float(pm):.1f} DYN"
                except (TypeError, ValueError):
                    template_prematch_dyn = f"{pm} DYN"
            ip = (sel.get("ip_margin") or "").strip()
            if ip:
                try:
                    template_inplay_dyn = f"{float(ip):.1f} DYN"
                except (TypeError, ValueError):
                    template_inplay_dyn = f"{ip} DYN"
            template_risk_class = sel.get("risk_class")

    return templates.TemplateResponse("margin/margin.html", {
        "request": request,
        "section": "margin_config",
        "brands": brands,
        "sports": sports,
        "selected_brand_id": selected_brand_id,
        "selected_sport_id": selected_sport_id,
        "show_tables": True,
        "margin_templates": margin_templates,
        "risk_classes": RISK_CLASSES,
        "market_groups_with_markets": market_groups_with_markets,
        "selected_template_id": selected_template_id,
        "selected_template_name": selected_template_name,
        "template_prematch_dyn": template_prematch_dyn,
        "template_inplay_dyn": template_inplay_dyn,
        "template_risk_class": template_risk_class,
        "market_templates": market_templates,
        "period_types": market_period_types,
        "score_types": market_score_types,
    })


@app.get("/localization", response_class=HTMLResponse)
async def localization_view(request: Request):
    """
    Configuration > Localization page.
    Shows Languages and Countries tabs. Countries are loaded from data/countries/countries.json.
    """
    countries = _load_countries()
    languages = _load_languages()
    brands = _load_brands()
    translations = _load_translations()

    # Filters for translations tab
    params = request.query_params
    selected_et = (params.get("tr_type") or "all").strip()
    try:
        selected_lang_id = int(params.get("tr_language_id")) if params.get("tr_language_id") else None
    except (TypeError, ValueError):
        selected_lang_id = None
    if selected_lang_id is None and languages:
        selected_lang_id = languages[0].get("id")
    # Brand filter: "" = Global, or brand id (int)
    try:
        tr_brand = params.get("tr_brand_id", "").strip()
        selected_brand_id: int | None = int(tr_brand) if tr_brand else None
    except (TypeError, ValueError):
        selected_brand_id = None
    show_untranslated = (params.get("tr_untranslated") == "1")

    # Build translation rows. When a brand is selected: show Global + Brand columns; when Global: one Translation column.
    rows: list[dict] = []

    def _get_tr(e_type: str, e_id: str, field: str, lang_id: int | None, brand_val: str) -> dict | None:
        if lang_id is None:
            return None
        for t in translations:
            t_brand = (t.get("brand_id") or "").strip()
            if (
                t["entity_type"] == e_type
                and t["entity_id"] == e_id
                and (t.get("field") or "name") == field
                and t["language_id"] == lang_id
                and t_brand == brand_val
            ):
                return t
        return None

    def _add_entity_rows(e_type: str, bucket: list[dict], label_prefix: str):
        for e in bucket:
            eid = str(e["domain_id"])
            base_name = (e.get("name") or "").strip()
            if selected_brand_id is None:
                tr = _get_tr(e_type, eid, "name", selected_lang_id, "")
                if show_untranslated and tr and tr.get("text"):
                    continue
                if show_untranslated and not base_name:
                    continue
                rows.append({
                    "entity_type": e_type,
                    "entity_id": eid,
                    "type_label": label_prefix,
                    "field": "name",
                    "baseid": (e.get("baseid") or "").strip() if e_type in ("sports", "categories", "competitions", "teams") else "",
                    "source": base_name,
                    "translation": tr.get("text") if tr else "",
                })
            else:
                tr_global = _get_tr(e_type, eid, "name", selected_lang_id, "")
                tr_brand = _get_tr(e_type, eid, "name", selected_lang_id, str(selected_brand_id))
                if show_untranslated and tr_brand and tr_brand.get("text"):
                    continue
                if show_untranslated and not base_name:
                    continue
                rows.append({
                    "entity_type": e_type,
                    "entity_id": eid,
                    "type_label": label_prefix,
                    "field": "name",
                    "baseid": (e.get("baseid") or "").strip() if e_type in ("sports", "categories", "competitions", "teams") else "",
                    "source": base_name,
                    "translation_global": tr_global.get("text") if tr_global else "",
                    "translation_brand": tr_brand.get("text") if tr_brand else "",
                })

    if selected_lang_id is not None:
        # Sports, Categories, Competitions, Teams, Markets
        if selected_et in ("all", "sports"):
            _add_entity_rows("sports", DOMAIN_ENTITIES["sports"], "Sport")
        if selected_et in ("all", "categories"):
            _add_entity_rows("categories", DOMAIN_ENTITIES["categories"], "Category")
        if selected_et in ("all", "competitions"):
            _add_entity_rows("competitions", DOMAIN_ENTITIES["competitions"], "Competition")
        if selected_et in ("all", "teams"):
            _add_entity_rows("teams", DOMAIN_ENTITIES["teams"], "Team")
        if selected_et in ("all", "markets"):
            _add_entity_rows("markets", DOMAIN_ENTITIES["markets"], "Market")
        # Countries (from countries.json; synthetic entity_type "countries")
        if selected_et in ("all", "countries"):
            for c in countries:
                eid = c.get("cc") or ""
                if not eid:
                    continue
                base_name = (c.get("name") or "").strip()
                if selected_brand_id is None:
                    tr = _get_tr("countries", eid, "name", selected_lang_id, "")
                    if show_untranslated and tr and tr.get("text"):
                        continue
                    if show_untranslated and not base_name:
                        continue
                    rows.append({
                        "entity_type": "countries",
                        "entity_id": eid,
                        "type_label": "Country",
                        "field": "name",
                        "baseid": "",
                        "source": base_name,
                        "translation": tr.get("text") if tr else "",
                    })
                else:
                    tr_global = _get_tr("countries", eid, "name", selected_lang_id, "")
                    tr_brand = _get_tr("countries", eid, "name", selected_lang_id, str(selected_brand_id))
                    if show_untranslated and tr_brand and tr_brand.get("text"):
                        continue
                    if show_untranslated and not base_name:
                        continue
                    rows.append({
                        "entity_type": "countries",
                        "entity_id": eid,
                        "type_label": "Country",
                        "field": "name",
                        "baseid": "",
                        "source": base_name,
                        "translation_global": tr_global.get("text") if tr_global else "",
                        "translation_brand": tr_brand.get("text") if tr_brand else "",
                    })

    return templates.TemplateResponse("configuration/localization.html", {
        "request": request,
        "section": "localization",
        "countries": countries,
        "languages": languages,
        "brands": brands,
        "translation_rows": rows,
        "translation_selected_type": selected_et,
        "translation_selected_language_id": selected_lang_id,
        "translation_selected_brand_id": selected_brand_id,
        "translation_show_untranslated": show_untranslated,
    })


# Static options for brands (currencies and odds formats)
BRAND_CURRENCIES = ["USD", "EUR", "GBP", "CHF", "SEK", "NOK", "DKK", "CAD", "AUD", "JPY", "CNY", "INR", "BRL", "MXN", "ZAR"]
BRAND_ODDS_FORMATS = ["Decimal", "Fractional", "American"]


@app.get("/brands", response_class=HTMLResponse)
async def brands_view(request: Request):
    """
    Configuration > Brands page.
    First row is Global (read-only; represents platform default / B2B provider admins).
    Other rows are brands from data/brands.csv; each brand can be assigned to a Partner (B2B client).
    """
    brands = _load_brands()
    partners = _load_partners()
    countries = _load_countries()
    languages = _load_languages()
    countries_by_cc = {c.get("cc", ""): c.get("name", "") for c in countries}
    languages_by_id = {str(l.get("id")): l.get("name", "") for l in languages}
    partners_by_id = {p["id"]: p for p in partners}
    # Attach brands to each partner for Partners tab
    brands_by_partner: dict[int, list[dict]] = {}
    for b in brands:
        pid = b.get("partner_id")
        if pid is not None:
            brands_by_partner.setdefault(pid, []).append(b)
    for p in partners:
        p["brands"] = brands_by_partner.get(p["id"], [])
    # Resolve jurisdiction, language, and partner display names for table
    for b in brands:
        j_codes = [x.strip() for x in (b.get("jurisdiction") or "").split(",") if x.strip()]
        b["jurisdiction_display"] = ", ".join(countries_by_cc.get(cc, cc) for cc in j_codes) or "—"
        l_ids = [x.strip() for x in (b.get("language_ids") or "").split(",") if x.strip()]
        b["language_display"] = ", ".join(languages_by_id.get(lid, lid) for lid in l_ids) or "—"
        pid = b.get("partner_id")
        b["partner_name"] = partners_by_id.get(pid, {}).get("name", "—") if pid else "Global"
    return templates.TemplateResponse("configuration/brands.html", {
        "request": request,
        "section": "brands",
        "brands": brands,
        "partners": partners,
        "countries": countries,
        "languages": languages,
        "currencies": BRAND_CURRENCIES,
        "odds_formats": BRAND_ODDS_FORMATS,
    })


@app.get("/users", response_class=HTMLResponse)
async def users_view(
    request: Request,
    status: str = "active",
    role_id: str | None = None,
    partner_id: str | None = None,
    brand_ids: list[int] | None = None,
    search: str = "",
    rp_partner_id: str | None = None,
):
    """Admin Management. Users list with filters: status, role, partner, brands (when partner set), search. rp_partner_id filters Roles & Permissions panel by partner."""
    users = _load_rbac_users()
    roles = _load_rbac_roles()
    user_roles = _load_rbac_user_roles()
    user_brands = _load_rbac_user_brands()
    partners = _load_partners()
    brands = _load_brands()
    brand_by_id = {b["id"]: b for b in brands}
    partner_by_id = {p["id"]: p for p in partners}
    for r in roles:
        r["partner_name"] = partner_by_id.get(r.get("partner_id"), {}).get("name", "Platform") if r.get("partner_id") else "Platform"
    role_by_id = {r["role_id"]: r for r in roles}
    from collections import Counter
    role_user_count = Counter(ur["role_id"] for ur in user_roles)
    for r in roles:
        r["active_admins"] = role_user_count.get(r["role_id"], 0)
    # Roles & Permissions panel: filter roles by partner (All / Platform / Partner X)
    _rp_raw = (rp_partner_id or "").strip().lower()
    if _rp_raw == "platform":
        roles_filtered = [r for r in roles if r.get("partner_id") is None]
    elif _rp_raw and _rp_raw != "all":
        _rp_id = _int_or_none(rp_partner_id)
        roles_filtered = [r for r in roles if r.get("partner_id") == _rp_id] if _rp_id is not None else roles
    else:
        roles_filtered = roles
    rp_partner_id_for_template = _rp_raw if _rp_raw in ("platform", "all") or _int_or_none(rp_partner_id) is not None else ""
    for u in users:
        u["roles"] = [
            role_by_id[ur["role_id"]]
            for ur in user_roles
            if ur["user_id"] == u["user_id"] and ur["role_id"] in role_by_id
        ]
        u["role_ids"] = [r["role_id"] for r in u["roles"]]
        u["brand_ids"] = [ub["brand_id"] for ub in user_brands if ub["user_id"] == u["user_id"]]
        u["brand_names"] = [brand_by_id.get(bid, {}).get("name", "") for bid in u["brand_ids"] if bid in brand_by_id]
        u["partner_name"] = partner_by_id.get(u["partner_id"], {}).get("name", "Platform") if u.get("partner_id") else "Platform"

    # Apply filters (default status=active)
    status = (status or "active").strip().lower()
    if status not in ("active", "inactive", "all"):
        status = "active"
    search = (search or "").strip().lower()
    filtered = users
    if status == "active":
        filtered = [u for u in filtered if u.get("active", True)]
    elif status == "inactive":
        filtered = [u for u in filtered if not u.get("active", True)]
    _role_id = _int_or_none(role_id) if role_id else None
    _partner_id_raw = (partner_id or "").strip().lower()
    _partner_id = None if _partner_id_raw in ("", "all") else ("platform" if _partner_id_raw == "platform" else _int_or_none(partner_id))
    if _partner_id == "platform":
        filtered = [u for u in filtered if u.get("partner_id") is None]
    elif isinstance(_partner_id, int):
        filtered = [u for u in filtered if u.get("partner_id") == _partner_id]
    if _role_id is not None:
        filtered = [u for u in filtered if (u.get("role_ids") or []) and u["role_ids"][0] == _role_id]
    if brand_ids:
        _brand_ids_set = set(brand_ids)
        filtered = [u for u in filtered if _brand_ids_set & set(u.get("brand_ids") or [])]
    if search:
        filtered = [
            u for u in filtered
            if search in (u.get("email") or "").lower()
            or search in (u.get("display_name") or "").lower()
            or search in (u.get("login") or "").lower()
        ]

    brands_for_partner = []
    if isinstance(_partner_id, int):
        brands_for_partner = [b for b in brands if b.get("partner_id") == _partner_id]
    filter_partner_id_for_template = None if _partner_id_raw in ("", "all") else (_partner_id_raw if _partner_id_raw == "platform" else _partner_id)

    perms = _load_rbac_role_permissions()
    perms_by_role = {}
    for p in perms:
        perms_by_role.setdefault(p["role_id"], []).append(p["permission_code"])
    for r in roles:
        r["permission_codes"] = perms_by_role.get(r["role_id"], [])
    permission_tree = config.RBAC_PERMISSION_TREE
    return templates.TemplateResponse("configuration/users.html", {
        "request": request,
        "section": "users",
        "users": filtered,
        "roles": roles,
        "roles_filtered": roles_filtered,
        "partners": partners,
        "brands": brands,
        "brands_for_partner": brands_for_partner,
        "permission_tree": permission_tree,
        "filter_status": status,
        "filter_role_id": _role_id,
        "filter_partner_id": filter_partner_id_for_template,
        "filter_brand_ids": brand_ids or [],
        "filter_search": search or "",
        "filter_rp_partner_id": rp_partner_id or "",
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
