from __future__ import annotations

import asyncio
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import copy
import json
import logging
import time
import math
import re
import os
from pathlib import Path
from threading import Lock
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
from backend import alerts_csv

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
ONEXBET_MARKET_NAMES_PATH = config.ONEXBET_MARKET_NAMES_PATH
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
FEED_DASHBOARD_STATE_PATH = getattr(config, "FEED_DASHBOARD_STATE_PATH", None) or (config.DATA_DIR / "feed_dashboard_state.json")
DASHBOARD_FEED_STATS_TTL_SEC = 600.0
_dashboard_feed_stats_cache_mono: float = 0.0
_dashboard_feed_stats_cache_rows: list[dict] | None = None
_dashboard_feed_stats_cache_lock = Lock()
_feed_dashboard_state_lock = Lock()
FEEDER_CONFIG_PATH = config.FEEDER_CONFIG_PATH
FEEDER_INCIDENTS_PATH = config.FEEDER_INCIDENTS_PATH
FEEDER_EVENT_NOTES_PATH = config.FEEDER_EVENT_NOTES_PATH
FEEDER_IGNORED_EVENTS_PATH = getattr(config, "FEEDER_IGNORED_EVENTS_PATH", None)
FEEDER_EVENT_LOG_PATH = getattr(config, "FEEDER_EVENT_LOG_PATH", None)
DOMAIN_EVENT_LOG_PATH = getattr(config, "DOMAIN_EVENT_LOG_PATH", None)
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
    _migrate_rbac_roles_is_master_if_needed()
    _migrate_rbac_users_is_superadmin_if_needed()
    _migrate_rbac_users_login_pin_if_needed()
    _migrate_rbac_users_updated_by_if_needed()
    _migrate_rbac_audit_was_now_if_needed()
    _migrate_rbac_users_manage_to_granular_permissions()
    _migrate_rbac_entities_page_action_permissions()
    if config.GMP_DEV_LOGIN and not (config.GMP_DEV_SESSION_SECRET or "").strip():
        logging.getLogger("uvicorn.error").warning(
            "GMP_DEV_LOGIN=1 but GMP_DEV_SESSION_SECRET is empty — using an insecure embedded default. "
            "Set a long random GMP_DEV_SESSION_SECRET in .env for any non-local use."
        )
    if config.GMP_DEV_LOGIN and not (config.GMP_SUPERADMIN_PIN or "").strip():
        logging.getLogger("uvicorn.error").warning(
            "GMP_SUPERADMIN_PIN is empty — users with is_superadmin cannot sign in until you set it in .env."
        )
    alerts_csv.ensure_initialized()


def _migrate_rbac_users_is_superadmin_if_needed() -> None:
    """Add is_superadmin column to users.csv if missing; default 0."""
    if not RBAC_USERS_PATH.exists():
        return
    with open(RBAC_USERS_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    if "is_superadmin" in fieldnames:
        return
    want = list(config.RBAC_USERS_FIELDS)
    for row in rows:
        row["is_superadmin"] = "0"
    with open(RBAC_USERS_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=want, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in want})


def _migrate_rbac_users_login_pin_if_needed() -> None:
    """Add login_pin column to users.csv if missing; default empty (use GMP_DEFAULT_USER_PIN at sign-in)."""
    if not RBAC_USERS_PATH.exists():
        return
    with open(RBAC_USERS_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    if "login_pin" in fieldnames:
        return
    want = list(config.RBAC_USERS_FIELDS)
    for row in rows:
        row["login_pin"] = ""
    with open(RBAC_USERS_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=want, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in want})


def _migrate_rbac_users_updated_by_if_needed() -> None:
    """Add updated_by column (last modifier display label); default empty."""
    if not RBAC_USERS_PATH.exists():
        return
    with open(RBAC_USERS_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    if "updated_by" in fieldnames:
        return
    want = list(config.RBAC_USERS_FIELDS)
    for row in rows:
        row["updated_by"] = ""
    with open(RBAC_USERS_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=want, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in want})


def _seed_rbac_if_empty() -> None:
    """First-time RBAC: SuperAdmin user + SuperAdmin Console role (Admin menu + always-granted). Both CSVs must be empty."""
    if _load_rbac_users() or _load_rbac_roles():
        return
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    codes = sorted(config.rbac_superadmin_console_permission_codes())
    role_row = {
        "role_id": 1,
        "name": "SuperAdmin Console",
        "active": True,
        "is_system": True,
        "partner_id": None,
        "is_master": False,
        "created_at": now,
        "updated_at": now,
    }
    _save_rbac_roles([role_row])
    perms = [{"role_id": 1, "permission_code": c} for c in codes]
    _save_rbac_role_permissions(perms)
    user_row = {
        "user_id": 1,
        "login": "superadmin",
        "email": "superadmin@platform.local",
        "display_name": "Super Admin",
        "active": True,
        "partner_id": None,
        "created_by": "System",
        "updated_by": "System",
        "created_at": now,
        "updated_at": now,
        "last_login": "",
        "online": False,
        "is_superadmin": True,
        "login_pin": "",
    }
    _save_rbac_users([user_row])
    _save_rbac_user_roles([{"user_id": 1, "role_id": 1, "assigned_at": now, "assigned_by_user_id": None}])
    _rbac_audit_append(
        None,
        "rbac.bootstrap",
        "system",
        "1",
        was="—",
        now="SuperAdmin user + SuperAdmin Console role (initial RBAC)",
    )


def _rbac_partner_scope_match(a: int | None, b: int | None) -> bool:
    """True if both are Platform (None) or same numeric partner id."""
    return (a is None and b is None) or (a is not None and b is not None and int(a) == int(b))


def _migrate_rbac_roles_is_master_if_needed() -> None:
    """Add is_master column to roles.csv if missing; default 0. Dedupe: at most one master per partner scope."""
    if not RBAC_ROLES_PATH.exists():
        return
    with open(RBAC_ROLES_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    if "is_master" in fieldnames:
        return
    want = list(config.RBAC_ROLES_FIELDS)
    for row in rows:
        row["is_master"] = "0"
    with open(RBAC_ROLES_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=want, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in want})
    # Dedupe masters (keep first per partner_id key)
    roles = _load_rbac_roles()
    seen_master: set[int | None] = set()
    changed = False
    for r in roles:
        if not r.get("is_master"):
            continue
        key = r.get("partner_id")
        if key is not None:
            key = int(key)
        if key in seen_master:
            r["is_master"] = False
            changed = True
        else:
            seen_master.add(key)
    if changed:
        _save_rbac_roles(roles)


def _any_rbac_superadmin_exists(users: list[dict]) -> bool:
    return any(u.get("is_superadmin") and u.get("active", True) for u in users)


def _rbac_actor_user_id_from_request(request: Request) -> int | None:
    if config.RBAC_TRUST_ACTOR_HEADER:
        raw = request.headers.get("x-rbac-actor-user-id") or request.headers.get("X-RBAC-Actor-User-Id")
        if raw and str(raw).strip():
            try:
                return int(str(raw).strip())
            except ValueError:
                pass
    if config.GMP_DEV_LOGIN:
        try:
            uid = request.session.get("dev_actor_user_id")
            if uid is not None:
                return int(uid)
        except (AssertionError, AttributeError, TypeError, ValueError):
            pass
    return None


def _rbac_actor_is_superadmin(request: Request) -> bool:
    uid = _rbac_actor_user_id_from_request(request)
    if uid is None:
        return False
    u = next((x for x in _load_rbac_users() if x.get("user_id") == uid), None)
    return bool(u and u.get("is_superadmin") and u.get("active", True))


def _rbac_actor_audit_label(request: Request) -> str:
    """Human-readable label for audit rows and updated_by (email, else login, else id)."""
    uid = _rbac_actor_user_id_from_request(request)
    if uid is None:
        return "System"
    u = next((x for x in _load_rbac_users() if x.get("user_id") == uid), None)
    if not u:
        return f"user#{uid}"
    return ((u.get("email") or u.get("login") or str(uid)) or "").strip() or f"user#{uid}"


def _rbac_user_modified_by_display(u: dict) -> str:
    """Table column: last modifier, else creator; legacy placeholders shown as System."""
    v = ((u.get("updated_by") or "").strip() or (u.get("created_by") or "").strip())
    if not v:
        return "—"
    if v in ("SuperAdmin", "bootstrap"):
        return "System"
    return v


def _rbac_request_bypasses_master_caps(request: Request) -> bool:
    """True when the resolved actor (trusted header or dev session) is an active SuperAdmin."""
    return _rbac_actor_is_superadmin(request)


def _rbac_can_assign_superadmin(request: Request) -> bool:
    """Bootstrap: allowed if no SuperAdmin exists yet; otherwise actor must be SuperAdmin (trusted header)."""
    if _rbac_actor_is_superadmin(request):
        return True
    return not _any_rbac_superadmin_exists(_load_rbac_users())


def _rbac_actor_enforced_partner_id(request: Request) -> int | None:
    """Partner-scoped sign-in: return that partner_id. Platform users (partner_id None) return None — see all tenants."""
    uid = _rbac_actor_user_id_from_request(request)
    if uid is None:
        return None
    users = _load_rbac_users()
    u = next((x for x in users if x.get("user_id") == uid), None)
    if not u or not u.get("active", True):
        return None
    pid = u.get("partner_id")
    if pid is None:
        return None
    return int(pid)


def _rbac_assert_actor_may_access_user_row(request: Request, target_user: dict) -> None:
    enf = _rbac_actor_enforced_partner_id(request)
    if enf is None:
        return
    tpid = target_user.get("partner_id")
    if tpid is None or int(tpid) != enf:
        raise HTTPException(status_code=403, detail="Cannot access users outside your partner scope")


def _rbac_assert_actor_may_access_role_row(request: Request, role: dict) -> None:
    enf = _rbac_actor_enforced_partner_id(request)
    if enf is None:
        return
    rpid = role.get("partner_id")
    if rpid is None or int(rpid) != enf:
        raise HTTPException(status_code=403, detail="Cannot access roles outside your partner scope")


def _rbac_assert_partner_actor_role_and_brand_ids(
    request: Request,
    role_ids: list[int] | None,
    brand_ids: list[int] | None,
) -> None:
    enf = _rbac_actor_enforced_partner_id(request)
    if enf is None:
        return
    if role_ids:
        roles = _load_rbac_roles()
        role_by_id = {r["role_id"]: r for r in roles}
        for rid in role_ids:
            r = role_by_id.get(rid)
            if not r or r.get("partner_id") != enf:
                raise HTTPException(status_code=403, detail="Cannot assign roles outside your partner scope")
    if brand_ids:
        brands = _load_brands()
        bmap = {b["id"]: b for b in brands}
        for bid in brand_ids:
            b = bmap.get(bid)
            if not b or b.get("partner_id") != enf:
                raise HTTPException(status_code=403, detail="Cannot assign brands outside your partner scope")


_rbac_presence_lock = Lock()
_rbac_presence_last_seen: dict[int, datetime] = {}


def _rbac_presence_touch(user_id: int | None) -> None:
    """Mark user as recently active (UTC). Used for Admin “Online” column."""
    if user_id is None:
        return
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return
    now = datetime.now(timezone.utc)
    with _rbac_presence_lock:
        _rbac_presence_last_seen[uid] = now


def _rbac_presence_clear(user_id: int | None) -> None:
    if user_id is None:
        return
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return
    with _rbac_presence_lock:
        _rbac_presence_last_seen.pop(uid, None)


def _rbac_user_presence_online(user_id: int | None) -> bool:
    if user_id is None:
        return False
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return False
    idle = max(30, int(getattr(config, "RBAC_ONLINE_IDLE_SECONDS", 180) or 180))
    with _rbac_presence_lock:
        seen = _rbac_presence_last_seen.get(uid)
    if seen is None:
        return False
    return (datetime.now(timezone.utc) - seen).total_seconds() < idle


def _rbac_persist_last_login(user_id: int) -> None:
    """Write last_login and updated_at to users.csv (successful sign-in)."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    users = _load_rbac_users()
    for u in users:
        if u.get("user_id") == user_id:
            u["last_login"] = now
            u["updated_at"] = now
            break
    _save_rbac_users(users)


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


def _canonical_start_minute(s: str | None) -> str | None:
    """Normalize start_time to 'YYYY-MM-DD HH:MM' for cross-feed comparison, or None if unparseable."""
    dt = _parse_start_time(s)
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%d %H:%M")


def _rbac_last_login_display_and_stale(last_login_raw: str | None) -> tuple[str, bool]:
    """Admin Last login: show stored date/time until 8+ full days ago, then 'N days'; stale (15+ days) for red styling."""
    s = (last_login_raw or "").strip()
    if not s:
        return "—", False
    dt = _parse_start_time(s)
    if dt is None:
        return s, False
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if dt > now:
        return s, False
    days = (now - dt).days
    if days < 8:
        return s, False
    return (f"{days} days", days >= 15)


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

from typing import Any, Optional
import uuid, csv, json
import difflib

from backend.domain_ids import (
    ENTITY_PREFIX,
    format_prefixed,
    is_prefixed_entity,
    next_entity_domain_id,
    next_event_domain_id,
    entity_ids_equal,
    nullable_fk_equal,
    fid_str,
    mapping_feed_id_key,
    mapping_related_feed_id_keys,
)

templates.env.globals["entity_ids_equal"] = entity_ids_equal
from backend.migrate_prefixed_ids import migrate_prefixed_domain_ids_if_needed
from backend.schemas import (
    CreateDomainEventRequest,
    CreateEntityRequest,
    UpdateEntityNameRequest,
    UpdateEntityCountryRequest,
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


_FEEDER_CONFIG_FIELDS = ["level", "sport_id", "category_id", "competition_id", "feed_provider_id", "setting_key", "value"]
_FEEDER_INCIDENT_FIELDS = ["sport_id", "feed_provider_id", "incident_type", "enabled", "sort_order"]


def _load_feeder_config() -> list[dict]:
    """Load feeder_config.csv (competition_id; legacy column league_id still read)."""
    if not FEEDER_CONFIG_PATH.exists():
        return []
    rows = []
    with open(FEEDER_CONFIG_PATH, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            row = dict(r)
            comp_cell = (row.get("competition_id") or row.get("league_id") or "").strip()
            for key in ("sport_id", "category_id", "feed_provider_id"):
                cell = (row.get(key) or "").strip() if row.get(key) is not None else ""
                if not cell:
                    row[key] = None
                    continue
                if key == "feed_provider_id":
                    try:
                        row[key] = int(cell)
                    except (ValueError, TypeError):
                        row[key] = None
                else:
                    row[key] = int(cell) if cell.isdigit() else cell
            if not comp_cell:
                row["competition_id"] = None
            else:
                row["competition_id"] = int(comp_cell) if comp_cell.isdigit() else comp_cell
            row.pop("league_id", None)
            lvl = (row.get("level") or "").strip()
            if lvl == "league":
                lvl = "competition"
            row["level"] = lvl
            rows.append(row)
    return rows


def _load_feeder_incidents() -> list[dict]:
    """Load feeder_incidents.csv (sport_id, feed_provider_id, incident_type, enabled, sort_order)."""
    if not FEEDER_INCIDENTS_PATH.exists():
        return []
    rows = []
    with open(FEEDER_INCIDENTS_PATH, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            for key in ("sport_id", "feed_provider_id", "sort_order"):
                cell = (r.get(key) or "").strip() if r.get(key) is not None else ""
                if not cell:
                    r[key] = None if key != "sort_order" else 0
                    continue
                if key == "sport_id":
                    r[key] = int(cell) if cell.isdigit() else cell
                elif key == "feed_provider_id":
                    try:
                        r[key] = int(cell)
                    except (ValueError, TypeError):
                        r[key] = None
                else:
                    try:
                        r[key] = int(cell)
                    except (ValueError, TypeError):
                        r[key] = 0
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
                "competition_id": r.get("competition_id") if r.get("competition_id") is not None else "",
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


_ADMIN_AUDIT_LOG_FIELDS = [
    "id", "created_at", "actor_user_id", "actor_label", "resource", "action", "subject", "was", "now", "details",
]


def _admin_audit_clip(s: str, max_len: int = 6000) -> str:
    s = s if s is not None else ""
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."


def _admin_audit_next_id() -> int:
    p = config.ADMIN_AUDIT_LOG_PATH
    if not p.exists() or p.stat().st_size == 0:
        return 1
    max_id = 0
    with open(p, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                max_id = max(max_id, int((row.get("id") or "0").strip() or "0"))
            except ValueError:
                pass
    return max_id + 1


def _admin_audit_append(
    request: Request,
    *,
    resource: str,
    action: str,
    subject: str,
    was: str,
    now: str,
    details: str = "",
) -> None:
    """Append one row to admin_audit_log.csv (append-only, per-environment under data/audit/)."""
    actor_id = _rbac_actor_user_id_from_request(request)
    label = _rbac_actor_audit_label(request)
    created = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    next_id = _admin_audit_next_id()
    p = config.ADMIN_AUDIT_LOG_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    write_header = not p.exists() or p.stat().st_size == 0
    if p.exists() and p.stat().st_size > 0:
        with open(p, "rb+") as f:
            f.seek(-1, 2)
            if f.read(1) != b"\n":
                f.write(b"\n")
    with open(p, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=_ADMIN_AUDIT_LOG_FIELDS)
        if write_header:
            w.writeheader()
        w.writerow({
            "id": next_id,
            "created_at": created,
            "actor_user_id": actor_id if actor_id is not None else "",
            "actor_label": _admin_audit_clip(label, 400),
            "resource": (resource or "").strip()[:120],
            "action": (action or "").strip()[:120],
            "subject": _admin_audit_clip(subject, 4000),
            "was": _admin_audit_clip(was),
            "now": _admin_audit_clip(now),
            "details": _admin_audit_clip(details, 2000),
        })


def _admin_audit_entries(
    *,
    resource: str | None = None,
    setting_key: str | None = None,
    sport_id_filter: Any = None,
    limit: int = 150,
) -> list[dict]:
    """Newest first. Optional filters: resource, feeder_config setting_key, feeder_incidents sport_id."""
    p = config.ADMIN_AUDIT_LOG_PATH
    if not p.exists():
        return []
    lim = max(1, min(int(limit) or 150, 500))
    with open(p, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    rows.reverse()
    out: list[dict] = []
    for r in rows:
        res = (r.get("resource") or "").strip()
        if resource and res != resource.strip():
            continue
        sub_raw = r.get("subject") or ""
        try:
            sub_obj = json.loads(sub_raw) if sub_raw.strip().startswith("{") else {}
        except json.JSONDecodeError:
            sub_obj = {}
        if setting_key and sub_obj.get("setting_key") != setting_key:
            continue
        if sport_id_filter is not None and sport_id_filter != "":
            sid_f = sub_obj.get("sport_id")
            if sid_f is None or not entity_ids_equal(sid_f, sport_id_filter):
                continue
        out.append(dict(r))
        if len(out) >= lim:
            break
    return out


def _feeder_config_row_matches_scope(r: dict, level: str, sid: Any, cid: Any, comp_id: Any) -> bool:
    rsid, rcid, rcomp = r.get("sport_id"), r.get("category_id"), r.get("competition_id")
    if level == "all_sports":
        return rsid is None and rcid is None and rcomp is None
    if level == "sport":
        return entity_ids_equal(rsid, sid) and rcid is None and rcomp is None
    if level == "category":
        return entity_ids_equal(rsid, sid) and entity_ids_equal(rcid, cid) and rcomp is None
    return entity_ids_equal(rsid, sid) and entity_ids_equal(rcid, cid) and entity_ids_equal(rcomp, comp_id)


def _feeder_config_snapshot_setting(
    existing: list[dict], level: str, sid: Any, cid: Any, comp_id: Any, setting_key: str,
) -> dict[str, str]:
    """feed_provider_id str -> Yes/No for one setting at scope."""
    out: dict[str, str] = {}
    for r in existing:
        if not _feeder_config_row_matches_scope(r, level, sid, cid, comp_id):
            continue
        if (r.get("setting_key") or "").strip() != setting_key:
            continue
        fid = r.get("feed_provider_id")
        if fid is not None:
            try:
                out[str(int(fid))] = _feeder_config_yes_no_value(r.get("value"))
            except (TypeError, ValueError):
                pass
    return out


# Margin config: templates are per (brand_id, sport_id). Global = brand_id empty.
# Uncategorized template is always present per scope. See docs/MARGIN_CONFIG_SPEC.md.
# Competitions per template are derived from margin_template_competitions.csv, not stored here.
_MARGIN_TEMPLATE_FIELDS = [
    "id", "name", "short_name", "pm_margin", "ip_margin",
    "cashout", "betbuilder", "bet_delay", "risk_class_id", "is_default",
    "brand_id", "sport_id",
]


def _margin_scope_sport_key(sport_domain_id: Any) -> str:
    """Normalize sport id to ``S-{{n}}`` so margin CSV scope matches ``_event_sport_id`` (int or prefixed)."""
    if sport_domain_id is None:
        return ""
    s = str(sport_domain_id).strip()
    if not s:
        return ""
    m = re.match(r"^[sS]-(\d+)$", s)
    if m:
        return format_prefixed(ENTITY_PREFIX["sports"], int(m.group(1)))
    if is_prefixed_entity(s, "sports"):
        return s
    try:
        n = int(float(s))
    except (TypeError, ValueError):
        return s
    return format_prefixed(ENTITY_PREFIX["sports"], n)


def _margin_scope_competition_key(comp_domain_id: Any) -> str:
    """Normalize competition id to ``C-{{n}}`` for margin_template_competitions lookups."""
    if comp_domain_id is None:
        return ""
    s = str(comp_domain_id).strip()
    if not s:
        return ""
    m = re.match(r"^[cC]-(\d+)$", s)
    if m:
        return format_prefixed(ENTITY_PREFIX["competitions"], int(m.group(1)))
    if is_prefixed_entity(s, "competitions"):
        return s
    try:
        n = int(float(s))
    except (TypeError, ValueError):
        return s
    return format_prefixed(ENTITY_PREFIX["competitions"], n)


def _read_margin_templates_csv_rows() -> list[dict]:
    """Read every row from margin_templates.csv (no scope filter, no auto-create). Ignores legacy count columns."""
    rows: list[dict] = []
    if not MARGIN_TEMPLATES_PATH.exists():
        return rows
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
            r["is_default"] = (r.get("is_default") or "").strip() in ("1", "true", "yes")
            r["brand_id"] = (r.get("brand_id") or "").strip()
            r["sport_id"] = (r.get("sport_id") or "").strip()
            r.pop("leagues_count", None)
            r.pop("markets_count", None)
            rows.append(_enrich_margin_template_risk_class(r))
    return rows


def _load_margin_templates(
    brand_id=None,
    sport_id=None,
    *,
    for_event_global_pricing: bool = False,
) -> list[dict]:
    """
    Load margin_templates.csv, optionally filtered by (brand_id, sport_id).

    **Configuration** (default ``for_event_global_pricing=False``): strict ``brand_id`` × sport,
    used by Margin UI and assignment APIs. "Global level" means ``brand_id`` empty only.

    **Event Details — Global pricing** (``for_event_global_pricing=True``): same sport filter, but
    **any** ``brand_id`` row for that sport is included so ``margin_template_competitions`` template
    ids (often saved under numeric partner brands) resolve. Not used for the Margin configuration table.
    """
    default_one = {
        "id": 1, "name": "Uncategorized", "short_name": "", "pm_margin": "", "ip_margin": "",
        "cashout": "", "betbuilder": "", "bet_delay": "", "risk_class_id": None,
        "is_default": True,
        "brand_id": "", "sport_id": "",
    }
    if not MARGIN_TEMPLATES_PATH.exists():
        default_one["is_default"] = 1
        return [_enrich_margin_template_risk_class(default_one)]
    rows = _read_margin_templates_csv_rows()
    if not rows:
        return [_enrich_margin_template_risk_class(default_one)]

    # Filter by scope when (brand_id, sport_id) provided
    b_key = str(brand_id).strip() if brand_id is not None else ""
    s_key = _margin_scope_sport_key(sport_id)
    if b_key != "" or s_key != "":
        def _matches_scope(t: dict, *, strict_sport: bool) -> bool:
            rb, rs = (t.get("brand_id") or "").strip(), (t.get("sport_id") or "").strip()
            if for_event_global_pricing and s_key:
                brand_ok = True
            else:
                brand_ok = rb == b_key
            rs_norm = _margin_scope_sport_key(rs) if rs else ""
            if strict_sport and s_key:
                # Sport-specific margin scope: ignore legacy rows with empty sport_id so we do not
                # merge Global "Uncategorized" (109) into every sport's template set.
                sport_ok = rs_norm == s_key
            else:
                # Legacy: empty sport_id at Global matches any sport (when no per-sport rows exist).
                sport_ok = rs_norm == s_key or (rs == "" and b_key == "")
            return brand_ok and sport_ok

        filtered = [t for t in rows if _matches_scope(t, strict_sport=bool(s_key))]
        # Do not widen to legacy empty-sport rows when Global+sport already meant "this sport only";
        # that re-introduces id 1 Uncategorized (109). Legacy widen only for an explicit brand scope.
        if not filtered and s_key and b_key != "":
            filtered = [t for t in rows if _matches_scope(t, strict_sport=False)]
        # Ensure Uncategorized exists for this scope (spec: always present per brand × sport)
        uncat = next((t for t in filtered if (t.get("name") or "").strip().lower() == "uncategorized"), None)
        if not uncat:
            # Re-read disk so a concurrent PATCH cannot be overwritten by this full-file save.
            rows = _read_margin_templates_csv_rows()
            filtered = [t for t in rows if _matches_scope(t, strict_sport=bool(s_key))]
            if not filtered and s_key and b_key != "":
                filtered = [t for t in rows if _matches_scope(t, strict_sport=False)]
            uncat = next((t for t in filtered if (t.get("name") or "").strip().lower() == "uncategorized"), None)
            if uncat:
                return filtered
            next_id = max((r.get("id") or 0 for r in rows), default=0) + 1
            new_uncat = {
                "id": next_id, "name": "Uncategorized", "short_name": "", "pm_margin": "", "ip_margin": "",
                "cashout": "", "betbuilder": "", "bet_delay": "", "risk_class_id": None,
                "is_default": True,
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
    """Overwrite margin_templates.csv. Competition counts live in margin_template_competitions, not in this file."""
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
                cid = str(r.get("competition_id") or "").strip()
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


def _assign_competition_to_margin_template(competition_id: str, template_id: int = 1) -> None:
    """Assign a domain competition to a margin template (default Uncategorized). Replaces any prior rows for that competition."""
    rows = _load_margin_template_competitions()
    ck = _margin_scope_competition_key(competition_id) or str(competition_id).strip()
    rows = [r for r in rows if _margin_scope_competition_key(r.get("competition_id")) != ck]
    rows.append({"template_id": template_id, "competition_id": ck})
    _save_margin_template_competitions(rows)


def _margin_templates_for_brand_sport(brand_id_str: str, sport_domain_id: Any) -> list[dict]:
    """Strict (brand × sport) template list for Margin configuration and APIs. Not for Event Global pricing."""
    s_key = fid_str(sport_domain_id) if sport_domain_id is not None else ""
    return _load_margin_templates(
        brand_id=str(brand_id_str).strip(),
        sport_id=s_key,
        for_event_global_pricing=False,
    )


def _margin_assignment_pick_template_id(
    competition_domain_id: Any,
    scope_template_ids: set[int],
    *,
    catalog_by_id: dict[int, dict] | None = None,
) -> int | None:
    """
    Choose ``template_id`` for this competition when ``margin_template_competitions`` has multiple rows
    for the same league (CSV order is not authoritative).

    Prefer assignments whose template is in ``scope_template_ids`` (current brand×sport or Global
    pricing list). If several match, prefer **Global** margin row (empty ``brand_id``) then **higher**
    template id so e.g. Global Volleyball Tier 1 wins over an older partner-scoped row for the same name.
    """
    cid = _margin_scope_competition_key(competition_domain_id)
    if not cid or not scope_template_ids:
        return None
    tids_in_scope: list[int] = []
    for r in _load_margin_template_competitions():
        if _margin_scope_competition_key(r.get("competition_id")) != cid:
            continue
        try:
            tid = int(r.get("template_id") or 0)
        except (TypeError, ValueError):
            continue
        if tid in scope_template_ids:
            tids_in_scope.append(tid)
    if not tids_in_scope:
        return None
    uniq = list(dict.fromkeys(tids_in_scope))
    cat = catalog_by_id
    if cat is None:
        cat = {t["id"]: t for t in _load_margin_templates() if t.get("id") is not None}

    def _rank(tid: int) -> tuple:
        t = cat.get(tid)
        if not t:
            return (2, 0)
        non_global = 1 if (t.get("brand_id") or "").strip() else 0
        return (non_global, -tid)

    return sorted(uniq, key=_rank)[0]


def _pick_margin_template_for_event_scope(
    templates: list[dict],
    competition_domain_id: Any | None,
    scope_sport_key: str = "",
) -> dict | None:
    """
    Pick the margin template for this competition within ``templates`` (already scoped to brand × sport).

    ``margin_template_competitions`` stores ``template_id`` from whichever scope the trader used in
    Configuration → Margin (e.g. Global). Template **numeric ids are not shared** across scopes, so
    the same row often does not match ``templates`` for another brand. When the assigned id is
    missing from this list, resolve the assigned template by **name** from the full catalog and pick
    the same-named template in this scope (e.g. Global assignment "Tier 1" → each brand's "Tier 1").
    """
    if not templates:
        return None

    sk = (scope_sport_key or "").strip()

    def _fallback_uncat() -> dict | None:
        cands = [t for t in templates if (t.get("name") or "").strip().lower() == "uncategorized"]
        if sk:
            sk_c = [t for t in cands if _margin_scope_sport_key(t.get("sport_id")) == sk]
            if sk_c:
                cands = sk_c
        if not cands:
            return templates[0] if templates else None
        cands.sort(key=lambda t: ((t.get("brand_id") or "").strip() != "", t.get("id") or 0))
        return cands[0]

    assigned_tid: int | None = None
    if competition_domain_id is not None:
        cid = _margin_scope_competition_key(competition_domain_id)
        if cid:
            scope_ids = {t.get("id") for t in templates if t.get("id") is not None}
            picked = _margin_assignment_pick_template_id(cid, scope_ids)
            if picked is not None:
                assigned_tid = picked
            else:
                row = next(
                    (
                        r
                        for r in _load_margin_template_competitions()
                        if _margin_scope_competition_key(r.get("competition_id")) == cid
                    ),
                    None,
                )
                if row is not None:
                    try:
                        assigned_tid = int(row.get("template_id"))
                    except (TypeError, ValueError):
                        assigned_tid = None

    if assigned_tid is not None:
        by_id = next((t for t in templates if t.get("id") == assigned_tid), None)
        if by_id:
            return by_id
        ref = next((t for t in _load_margin_templates() if t.get("id") == assigned_tid), None)
        if ref:
            ref_name = (ref.get("name") or "").strip()
            if ref_name:
                lo = ref_name.lower()
                name_cands = [
                    t
                    for t in templates
                    if (t.get("name") or "").strip().lower() == lo and (not sk or _margin_scope_sport_key(t.get("sport_id")) == sk)
                ]
                if name_cands:
                    ref_brand = (ref.get("brand_id") or "").strip()
                    if ref_brand:
                        same_brand = [t for t in name_cands if (t.get("brand_id") or "").strip() == ref_brand]
                        if same_brand:
                            name_cands = same_brand
                    name_cands.sort(key=lambda t: t.get("id") or 0)
                    return name_cands[0]

    return _fallback_uncat()


def _competition_label_matches_event(ev_label: str, entity_label: str) -> bool:
    """
    True when event competition text matches entity name.

    ``domain_events`` often stores a short label (e.g. ``Bundesliga``) while competitions.csv
    uses disambiguation (e.g. ``Bundesliga (Germany)``). Strict equality would miss margin
    assignments for that league.
    """
    a = (ev_label or "").strip()
    b = (entity_label or "").strip()
    if not a or not b:
        return False
    if a.casefold() == b.casefold():
        return True
    af, bf = a.casefold(), b.casefold()
    if bf.startswith(af + " (") or bf.startswith(af + "("):
        return True
    if af.startswith(bf + " (") or af.startswith(bf + "("):
        return True
    return False


def _event_competition_domain_id(ev: dict) -> str | None:
    """Domain competition id for margin assignment; uses CSV ``competition_id`` or resolves from names."""
    raw = ev.get("competition_id")
    if raw is not None and str(raw).strip() != "":
        k = _margin_scope_competition_key(raw)
        return k if k else None
    sport_name = (ev.get("sport") or "").strip()
    comp_name = (ev.get("competition") or "").strip()
    if not comp_name:
        return None
    sport_id = None
    for s in DOMAIN_ENTITIES.get("sports", []):
        if (s.get("name") or "").strip() == sport_name:
            sport_id = s.get("domain_id")
            break
    if sport_id is None:
        return None
    matches = [
        c
        for c in DOMAIN_ENTITIES.get("competitions", [])
        if entity_ids_equal(c.get("sport_id"), sport_id)
        and _competition_label_matches_event(comp_name, (c.get("name") or "").strip())
    ]
    if not matches:
        return None
    exact = next((c for c in matches if (c.get("name") or "").strip() == comp_name), None)
    pick = exact if exact is not None else matches[0]
    cid = pick.get("domain_id")
    if cid is None:
        return None
    k = _margin_scope_competition_key(cid)
    return k if k else None


def _pm_pct_from_margin_template_row(t: dict | None) -> tuple[float | None, str | None]:
    """Numeric PM%% and display name from one margin template row, or (None, None) if unset/invalid."""
    if not t:
        return None, None
    raw = (t.get("pm_margin") or "").strip().replace(",", ".")
    if raw == "":
        return None, None
    try:
        return float(raw), (t.get("name") or "").strip() or "—"
    except ValueError:
        return None, None


def _prematch_pm_pct_single_brand_key(ev: dict, brand_key: str) -> tuple[float | None, str | None]:
    """Resolve PM %% from margin templates for ``brand_key`` ('' = Global) × event sport + competition."""
    sport_id = _event_sport_id(ev)
    if sport_id is None:
        return None, None
    comp_id = _event_competition_domain_id(ev)
    bks = str(brand_key).strip() if brand_key is not None else ""
    if bks == "":
        tpls = _load_margin_templates(None, sport_id, for_event_global_pricing=True)
    else:
        tpls = _load_margin_templates(bks, sport_id, for_event_global_pricing=False)
    if not tpls:
        return None, None
    scope_sk = _margin_scope_sport_key(sport_id)
    t = _pick_margin_template_for_event_scope(tpls, comp_id, scope_sport_key=scope_sk)
    pm, name = _pm_pct_from_margin_template_row(t)
    if pm is not None:
        return pm, name
    # Same logical template can exist on multiple rows (e.g. partner id on assignment vs Global row
    # with PM%% filled). Prefer Global (empty brand_id) then stable id order.
    tnm = ((t or {}).get("name") or "").strip().lower()
    if tnm:
        alts = [x for x in tpls if (x.get("name") or "").strip().lower() == tnm]
        alts.sort(key=lambda x: (1 if (x.get("brand_id") or "").strip() else 0, x.get("id") or 0))
        for alt in alts:
            pm, name = _pm_pct_from_margin_template_row(alt)
            if pm is not None:
                return pm, name
    return None, None


def _prematch_pm_pct_and_template_name(brand_id_int: int, ev: dict) -> tuple[float | None, str | None]:
    """Resolve PM margin %% and template display name for a brand on this event (prematch)."""
    for brand_key in (str(int(brand_id_int)), ""):
        pm, name = _prematch_pm_pct_single_brand_key(ev, brand_key)
        if pm is not None:
            return pm, name
    return None, None


def _margin_templates_by_sport_for_event_navigator(
    page_events: list,
    brand_key: str | int | None,
) -> dict[int, list]:
    """One `_load_margin_templates` call per distinct sport on the page (same scope rules as prematch PM%)."""
    sids = {sid for sid in (_event_sport_id(e) for e in page_events) if sid is not None}
    out: dict[int, list] = {}
    bks = str(brand_key).strip() if brand_key is not None else ""
    for sid in sids:
        if bks == "":
            out[sid] = _load_margin_templates(None, sid, for_event_global_pricing=True)
        else:
            out[sid] = _load_margin_templates(bks, sid, for_event_global_pricing=False)
    return out


def _event_risk_class_from_margin_template(
    ev: dict,
    brand_key: str | int | None,
    tpl_by_sport: dict[int, list],
) -> dict | None:
    """Event Navigator CLASS: same resolved margin template as prematch for this brand (letter from that row)."""
    sport_id = _event_sport_id(ev)
    if sport_id is None:
        return None
    tpls = tpl_by_sport.get(sport_id) or []
    comp_id = _event_competition_domain_id(ev)
    scope_sk = _margin_scope_sport_key(sport_id)
    t = _pick_margin_template_for_event_scope(tpls, comp_id, scope_sport_key=scope_sk)
    if not t:
        return None
    rc = t.get("risk_class")
    return rc if rc else None


def _prematch_pm_pct_for_pricing_scope(ev: dict, pricing_brand_id: int | None) -> tuple[float | None, str | None]:
    """Event overview / single-brand pricing: ``None`` = Global scope first; else that brand then Global."""
    if pricing_brand_id is None:
        pm, name = _prematch_pm_pct_single_brand_key(ev, "")
        if pm is not None:
            return pm, name
        # Global merge can resolve to a partner row with blank PM%% while a strict partner scope has
        # Tier margins — same situation Brand Overview rows already exploit via per-brand keys.
        for br in _load_brands():
            bid = br.get("id")
            if bid is None:
                continue
            try:
                bk = str(int(bid))
            except (TypeError, ValueError):
                continue
            pm, name = _prematch_pm_pct_single_brand_key(ev, bk)
            if pm is not None:
                return pm, name
        return None, None
    pm, name = _prematch_pm_pct_single_brand_key(ev, str(int(pricing_brand_id)))
    if pm is not None:
        return pm, name
    return _prematch_pm_pct_single_brand_key(ev, "")


def _pick_feed_odds_row_for_line(feed_rows: list[dict], line_q: str | None) -> dict | None:
    """When multiple lines exist for one feed, pick the row matching ``line_q`` (★ stripped), else first."""
    if not feed_rows:
        return None
    if line_q and len(feed_rows) > 1:

        def _strip_star(s: str) -> str:
            return (s or "").replace("★", "").strip()

        lq = _strip_star(line_q)
        for cand in feed_rows:
            if _strip_star(str(cand.get("line") or "")) == lq:
                return cand
        return feed_rows[0]
    return feed_rows[0]


def _decimal_odds_from_feed_row(row: dict | None) -> list[float | None]:
    if not row:
        return []
    out: list[float | None] = []
    for o in row.get("outcomes") or []:
        try:
            out.append(float(str(o.get("price") or "").replace(",", ".")))
        except (TypeError, ValueError):
            out.append(None)
    return out


def _imlog_true_prices_for_event_market(
    domain_event_id: str,
    domain_market_id: str,
    line: str | None,
) -> tuple[list[float | None], bool, int]:
    """
    Basis for Brand Overview / markets overview (center column).

    When **Pricing Feed** order is configured (global All Sports), walk feeds in that order;
    use the first feed with a full set of positive outcome decimals, **log de-vig** to fair
    odds, then callers apply **log2** margining from margin templates.

    When no pricing order is configured, legacy behavior: **IMLog** decimals are used as the
    basis for log2 (no de-vig), same as before.
    """
    from backend.internal_pricing.transforms.log_function import true_odds_and_probs_from_decimal_odds

    eid = str(domain_event_id).strip()
    line_q = (line or "").strip() or None
    all_ln = line_q is None
    rows = _get_feed_odds_for_event_market(eid, domain_market_id, line_q, all_lines=all_ln)
    order_ids = _feeder_config_pricing_feed_order_ids()

    if order_ids:
        for fid in order_ids:
            fr = [r for r in rows if r.get("feed_provider_id") == fid]
            row = _pick_feed_odds_row_for_line(fr, line_q)
            decs = _decimal_odds_from_feed_row(row)
            if not decs or any(x is None or x <= 0 for x in decs):
                continue
            to = true_odds_and_probs_from_decimal_odds([float(x) for x in decs])
            if not to:
                continue
            true_odds, _probs = to
            tp: list[float | None] = [float(x) for x in true_odds]
            n_sel = len(tp)
            return tp, True, n_sel
        return [], False, 0

    im_rows = [r for r in rows if (r.get("feed_name") or "").strip().lower() == "imlog"]
    im_row = _pick_feed_odds_row_for_line(im_rows, line_q)
    true_prices = _decimal_odds_from_feed_row(im_row)
    im_used = bool(true_prices and any(x is not None and x > 0 for x in true_prices))
    n_sel = sum(1 for x in true_prices if x is not None and x > 0)
    return true_prices, im_used, n_sel


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
    volley = isinstance(sport_id, str) and sport_id.startswith("S-") and sport_id[2:].isdigit() and int(sport_id[2:]) == 8
    volley = volley or sport_id == 8
    if len(candidates) > 1 and volley and template == "CORRECT_SCORE":
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


def _markets_by_group(sport_id: str | int | None = None) -> list[dict]:
    """Build list of { group, markets } for event details left column. If sport_id is set, only include markets created for that sport.
    Only includes groups that have at least one market (so e.g. HALF, CORNERS, CARDS are hidden when they have no markets for that sport)."""
    market_groups = _load_market_groups()
    markets = DOMAIN_ENTITIES.get("markets") or []
    if sport_id is not None:
        markets = [m for m in markets if entity_ids_equal(m.get("sport_id"), sport_id)]
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


def _load_countries() -> list[dict]:
    """Load countries from data/countries/countries.json (shape: { success, results: [ { cc, name } ] ).
    Always prepends a synthetic 'None' option (code '-') for entities with no country (e.g. international scope)."""
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
    # Prepend None option for no country / international scope (e.g. Champions League)
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
            created_by = (r.get("created_by") or "").strip()
            out.append({
                "user_id": uid or 0,
                "login": (r.get("login") or "").strip(),
                "email": (r.get("email") or "").strip(),
                "display_name": (r.get("display_name") or "").strip(),
                "active": (r.get("active") or "1").strip().lower() in ("1", "true", "yes"),
                "partner_id": pid,
                "created_by": created_by,
                "updated_by": (r.get("updated_by") or "").strip(),
                "created_at": (r.get("created_at") or "").strip(),
                "updated_at": (r.get("updated_at") or "").strip(),
                "last_login": (r.get("last_login") or "").strip(),
                "online": (r.get("online") or "0").strip().lower() in ("1", "true", "yes"),
                "is_superadmin": (r.get("is_superadmin") or "0").strip().lower() in ("1", "true", "yes"),
                "login_pin": (r.get("login_pin") or "").strip(),
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
                "created_by": (u.get("created_by") or "").strip(),
                "updated_by": (u.get("updated_by") or "").strip(),
                "created_at": u.get("created_at", ""),
                "updated_at": u.get("updated_at", ""),
                "last_login": u.get("last_login", ""),
                "online": "1" if u.get("online", False) else "0",
                "is_superadmin": "1" if u.get("is_superadmin", False) else "0",
                "login_pin": (u.get("login_pin") or "").strip(),
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
                "is_master": (r.get("is_master") or "0").strip().lower() in ("1", "true", "yes"),
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
                "is_master": "1" if row.get("is_master", False) else "0",
                "created_at": row.get("created_at", ""),
                "updated_at": row.get("updated_at", ""),
            })


def _clear_master_flag_same_partner(roles: list[dict], partner_id: int | None, except_role_id: int | None = None) -> None:
    for r in roles:
        if except_role_id is not None and r.get("role_id") == except_role_id:
            continue
        if r.get("is_master") and _rbac_partner_scope_match(r.get("partner_id"), partner_id):
            r["is_master"] = False


def _get_master_role_for_partner(roles: list[dict], partner_id: int | None) -> dict | None:
    for r in roles:
        if r.get("is_master") and _rbac_partner_scope_match(r.get("partner_id"), partner_id):
            return r
    return None


def _permission_codes_for_role_id(role_id: int) -> set[str]:
    return {
        (p.get("permission_code") or "").strip()
        for p in _load_rbac_role_permissions()
        if p.get("role_id") == role_id and (p.get("permission_code") or "").strip()
    }


def _rbac_sign_in_pin_valid(user: dict, pin_submitted: str) -> bool:
    p = (pin_submitted or "").strip()
    if user.get("is_superadmin"):
        secret = (config.GMP_SUPERADMIN_PIN or "").strip()
        if not secret:
            return False
        return p == secret
    expected = (user.get("login_pin") or "").strip() or config.GMP_DEFAULT_USER_PIN
    return p == expected


def _raise_if_partner_master_exceeds_platform(
    roles: list[dict],
    partner_id: int | None,
    codes_set: set[str],
    bypass: bool,
) -> None:
    """Partner-scoped Master role permissions must be a subset of Platform Master (and Platform Master must exist)."""
    if bypass or partner_id is None or not codes_set:
        return
    plat = _get_master_role_for_partner(roles, None)
    if not plat:
        raise HTTPException(
            status_code=400,
            detail="Create a Platform Master role (Platform scope) before adding or editing a Partner Master.",
        )
    pcap = _permission_codes_for_role_id(int(plat["role_id"]))
    over = codes_set - pcap
    if over:
        raise HTTPException(
            status_code=400,
            detail=f"Permissions exceed Platform Master role «{plat.get('name', plat['role_id'])}»: {sorted(over)}",
        )


def _access_rights_ceiling_codes(request: Request) -> set[str] | None:
    """None = show full permission tree (SuperAdmin). Else cap set for Access Rights UI."""
    if not config.GMP_DEV_LOGIN:
        return None
    uid = _rbac_actor_user_id_from_request(request)
    if uid is None:
        return None
    if _rbac_actor_is_superadmin(request):
        return None
    users = _load_rbac_users()
    u = next((x for x in users if x.get("user_id") == uid), None)
    if not u or not u.get("active", True):
        return frozenset()
    ur = _load_rbac_user_roles()
    rid = next((x["role_id"] for x in ur if x["user_id"] == uid), None)
    if rid is None:
        return frozenset()
    roles = _load_rbac_roles()
    role = next((r for r in roles if r.get("role_id") == rid), None)
    if not role:
        return frozenset()
    if role.get("is_master"):
        return _permission_codes_for_role_id(int(rid))
    master = _get_master_role_for_partner(roles, role.get("partner_id"))
    if master:
        return _permission_codes_for_role_id(int(master["role_id"]))
    return _permission_codes_for_role_id(int(rid))


def _filter_permission_tree_nodes(nodes: list[dict], allowed: set[str] | None) -> list[dict]:
    if allowed is None:
        return copy.deepcopy(nodes)
    out: list[dict] = []
    for node in nodes:
        one = _filter_one_permission_tree_node(node, allowed)
        if one is not None:
            out.append(one)
    return out


def _filter_one_permission_tree_node(node: dict, allowed: set[str]) -> dict | None:
    new_perms = []
    for p in node.get("permissions") or []:
        code = (p.get("code") or "").strip()
        if p.get("always_granted") or code in allowed:
            new_perms.append(p)
    new_children = []
    for ch in node.get("children") or []:
        fc = _filter_one_permission_tree_node(ch, allowed)
        if fc is not None:
            new_children.append(fc)
    if not new_perms and not new_children:
        return None
    d: dict = {"label": node["label"]}
    if new_perms:
        d["permissions"] = new_perms
    if new_children:
        d["children"] = new_children
    return d


def _user_without_secret_fields(u: dict) -> dict:
    return {k: v for k, v in u.items() if k != "login_pin"}


def _auth_exempt_path(path: str) -> bool:
    if path.startswith("/static/") or path == "/static":
        return True
    if path == "/dev/login" or path.startswith("/dev/login/"):
        return True
    if path == "/dev/logout" or path.startswith("/dev/logout/"):
        return True
    return False


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


def _rbac_audit_append(
    actor_user_id: int | None,
    action: str,
    target_type: str,
    target_id: str,
    *,
    was: str = "",
    now: str = "",
    details: str = "",
) -> None:
    """Append one row to rbac_audit_log.csv. Append-only. Use was/now for before→after; details kept for legacy rows."""
    created = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
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
            "created_at": created,
            "actor_user_id": actor_user_id if actor_user_id is not None else "",
            "action": action,
            "target_type": target_type,
            "target_id": str(target_id),
            "was": was,
            "now": now,
            "details": details,
        })


def _migrate_rbac_users_manage_to_granular_permissions() -> None:
    """Replace legacy rbac.users.manage with rbac.users.create/edit/audit on each role that had it."""
    perms = _load_rbac_role_permissions()
    roles_with_manage = {p["role_id"] for p in perms if (p.get("permission_code") or "").strip() == "rbac.users.manage"}
    if not roles_with_manage:
        return
    new_perms = [p for p in perms if (p.get("permission_code") or "").strip() != "rbac.users.manage"]
    existing = {(p["role_id"], (p.get("permission_code") or "").strip()) for p in new_perms}
    for rid in roles_with_manage:
        for code in ("rbac.users.create", "rbac.users.edit", "rbac.users.audit"):
            if (rid, code) not in existing:
                new_perms.append({"role_id": rid, "permission_code": code})
                existing.add((rid, code))
    _save_rbac_role_permissions(new_perms)


def _migrate_rbac_entities_page_action_permissions() -> None:
    """Align role_permissions with Entities tab actions: sport + category/competition/team page-action codes."""
    from collections import defaultdict

    perms = _load_rbac_role_permissions()
    if not perms:
        return
    role_codes: dict[int, set[str]] = defaultdict(set)
    for p in perms:
        try:
            rid = int(p.get("role_id"))
        except (TypeError, ValueError):
            continue
        c = (p.get("permission_code") or "").strip()
        if c:
            role_codes[rid].add(c)
    changed = False
    tab_bases = (
        ("entity.sport", ("entity.sport.remove_mappings", "entity.sport.active_inactive"), True),
        ("entity.category", ("entity.category.remove_mappings", "entity.category.active_inactive"), False),
        ("entity.competition", ("entity.competition.remove_mappings", "entity.competition.active_inactive"), False),
        ("entity.team", ("entity.team.remove_mappings", "entity.team.active_inactive"), False),
    )
    for codes in role_codes.values():
        for base, extras, is_sport in tab_bases:
            del_c = f"{base}.delete"
            upd = f"{base}.update"
            ed = f"{base}.edit"
            if del_c in codes:
                codes.discard(del_c)
                changed = True
            if upd in codes:
                codes.discard(upd)
                codes.add(ed)
                changed = True
            if is_sport:
                if f"{base}.create" in codes:
                    codes.discard(f"{base}.create")
                    changed = True
            if ed in codes:
                for ex in extras:
                    if ex not in codes:
                        codes.add(ex)
                        changed = True
    if not changed:
        return
    new_rows: list[dict] = []
    for rid in sorted(role_codes.keys()):
        for c in sorted(role_codes[rid]):
            new_rows.append({"role_id": rid, "permission_code": c})
    _save_rbac_role_permissions(new_rows)


def _migrate_rbac_audit_was_now_if_needed() -> None:
    """Add was/now columns to rbac_audit_log.csv if missing (preserve details)."""
    if not RBAC_AUDIT_LOG_PATH.exists():
        return
    with open(RBAC_AUDIT_LOG_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    if "was" in fieldnames and "now" in fieldnames:
        return
    want = list(config.RBAC_AUDIT_LOG_FIELDS)
    for row in rows:
        row.setdefault("was", "")
        row.setdefault("now", "")
        row.setdefault("details", row.get("details", ""))
    with open(RBAC_AUDIT_LOG_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=want, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in want})


@app.on_event("startup")
def _run_rbac_seed_after_audit_helpers() -> None:
    _seed_rbac_if_empty()


def _load_market_type_mappings() -> list[dict]:
    """Load market_type_mappings.csv (domain_market_id, feed_provider_id, feed_market_id, feed_market_name, phase)."""
    if not MARKET_TYPE_MAPPINGS_PATH.exists():
        return []
    rows = []
    with open(MARKET_TYPE_MAPPINGS_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            row["domain_market_id"] = str(row["domain_market_id"]).strip()
            row["feed_provider_id"] = int(row["feed_provider_id"])
            rows.append(row)
    return rows


def _load_1xbet_market_names() -> dict[str, str]:
    """Load 1xbet_market_names.csv → { G (string) → name }. Empty name = fall back to synthetic GE label in parser."""
    if not ONEXBET_MARKET_NAMES_PATH.exists():
        return {}
    out: dict[str, str] = {}
    with open(ONEXBET_MARKET_NAMES_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if not row:
                continue
            g = str(row.get("G") or row.get("g") or "").strip()
            if not g:
                continue
            name = (row.get("name") or row.get("Name") or "").strip()
            out[g] = name
    return out


def _market_type_feed_counts_by_domain_id() -> dict[str, dict[str, int]]:
    """Per domain market type: how many feed mappings in prematch vs live (from market_type_mappings phase)."""
    out: dict[str, dict[str, int]] = {}
    for m in _load_market_type_mappings():
        dmid = fid_str(m.get("domain_market_id") or "")
        if not dmid:
            continue
        phase = (m.get("phase") or "").strip().lower().replace("-", "_")
        bucket = out.setdefault(dmid, {"prematch": 0, "live": 0})
        if phase in ("live", "inplay", "in_play"):
            bucket["live"] += 1
        else:
            bucket["prematch"] += 1
    return out


def _save_market_type_mappings_for_domain(domain_market_id: str, prematch: list[dict], live: list[dict]) -> None:
    """Replace all mappings for domain_market_id with the given prematch and live lists. phase = prematch | live."""
    all_mappings = _load_market_type_mappings()
    dmid = fid_str(domain_market_id)
    rest = [m for m in all_mappings if fid_str(m.get("domain_market_id")) != dmid]
    new_rows = []
    for item in prematch:
        new_rows.append({
            "domain_market_id": dmid,
            "feed_provider_id": int(item["feed_provider_id"]),
            "feed_market_id": str(item.get("id", item.get("feed_market_id", ""))),
            "feed_market_name": (item.get("name") or item.get("feed_market_name") or "").strip(),
            "phase": "prematch",
        })
    for item in live:
        new_rows.append({
            "domain_market_id": dmid,
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
                row.setdefault("country", COUNTRY_CODE_NONE)
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)


def _migrate_entity_country_column_if_needed() -> None:
    """Rename legacy `jurisdiction` column to `country` for categories/competitions/teams, or add `country` if missing."""
    for etype in ("categories", "competitions", "teams"):
        path = DATA_DIR / f"{etype}.csv"
        if not path.exists():
            continue
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            fieldnames = list(reader.fieldnames or [])
        if "country" in fieldnames and "jurisdiction" not in fieldnames:
            continue
        fields = _ENTITY_FIELDS[etype]
        for row in rows:
            val = (row.get("country") or row.get("jurisdiction") or "").strip() or COUNTRY_CODE_NONE
            row["country"] = val
            row.pop("jurisdiction", None)
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


def _migrate_entity_active_column_if_needed() -> None:
    """One-time: add active (1/0) column to entity CSVs if missing. Existing rows default to active."""
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
        if "active" in fieldnames:
            continue
        fields = _ENTITY_FIELDS[etype]
        for row in rows:
            row["active"] = "1"
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)


def _coerce_entity_active_bool(raw) -> bool:
    s = str(raw if raw is not None else "").strip().lower()
    if s in ("0", "false", "no", "inactive", "off"):
        return False
    return True


def _coerce_entity_fk(val) -> str | None:
    """Sport/category FKs on entities: stored as prefixed strings (S-1, G-2)."""
    s = str(val or "").strip()
    return s if s else None


def _load_entities() -> dict:
    """Load all entity CSVs into memory. domain_id and entity FKs are strings (S-/G-/C-/P-/M-)."""
    store: dict[str, list[dict]] = {k: [] for k in _ENTITY_FIELDS if k != "feeds"}
    for etype in store:
        path = DATA_DIR / f"{etype}.csv"
        if path.exists():
            with open(path, newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    did = str(row.get("domain_id") or "").strip()
                    if not did:
                        continue
                    row["domain_id"] = did
                    for fk in ("sport_id", "category_id"):
                        if fk in row:
                            row[fk] = _coerce_entity_fk(row.get(fk))
                    if etype == "markets":
                        row["sport_id"] = _coerce_entity_fk(row.get("sport_id"))
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
                        row["country"] = (row.get("country") or row.get("jurisdiction") or "").strip() or COUNTRY_CODE_NONE
                        row.pop("jurisdiction", None)
                    if etype in ("sports", "categories", "competitions", "teams", "markets"):
                        row["active"] = _coerce_entity_active_bool(row.get("active"))
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


def _ensure_imlog_feed_row() -> None:
    """Ensure feeds.csv lists IMLog (synthetic Bwin-shaped feed) so market mappings and Feed Odds can use it."""
    global FEEDS
    if any((f.get("code") or "").strip().lower() == "imlog" for f in FEEDS):
        return
    next_id = max((f["domain_id"] for f in FEEDS), default=0) + 1
    row = {"domain_id": next_id, "code": "imlog", "name": "IMLog"}
    _save_entity("feeds", row)
    FEEDS.append({"domain_id": int(next_id), "code": "imlog", "name": "IMLog"})


def _update_entity_name(
    etype: str,
    domain_id: str,
    new_name: str,
    updated_at: str,
    country: str | None = None,
    baseid: str | None = None,
    participant_type_id: int | None = None,
    underage_category_id: int | None = None,
    is_amateur: bool | None = None,
) -> None:
    """
    Update name and optionally country, baseid, participant_type_id (teams), underage_category_id (teams), is_amateur (teams), and updated_at for a single entity row.
    """
    path = DATA_DIR / f"{etype}.csv"
    if not path.exists():
        return
    fields = _ENTITY_FIELDS[etype]
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    want = fid_str(domain_id)
    for row in rows:
        row_id = fid_str(row.get("domain_id"))
        if not row_id:
            continue
        if etype in ("sports", "categories", "competitions", "teams"):
            row.setdefault("baseid", "")
            row.setdefault("active", "1")
        if etype in ("categories", "competitions", "teams"):
            row.setdefault("country", COUNTRY_CODE_NONE)
        if etype == "teams":
            row.setdefault("underage_category_id", "")
            row.setdefault("is_amateur", "0")
        if etype == "competitions":
            row.setdefault("underage_category_id", "")
            row.setdefault("is_amateur", "0")
        if row_id == want:
            row["name"] = new_name
            row["updated_at"] = updated_at
            if etype in ("categories", "competitions", "teams") and country is not None:
                row["country"] = (country or "").strip() or COUNTRY_CODE_NONE
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


def _update_entity_country(etype: str, domain_id: str, country: str, updated_at: str) -> None:
    """Update country code and updated_at for a single entity row. etype: categories, competitions, or teams."""
    path = DATA_DIR / f"{etype}.csv"
    if not path.exists():
        return
    fields = _ENTITY_FIELDS[etype]
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    want = fid_str(domain_id)
    for row in rows:
        row_id = fid_str(row.get("domain_id"))
        if not row_id:
            continue
        if etype in ("categories", "competitions", "teams"):
            row.setdefault("country", COUNTRY_CODE_NONE)
            row.setdefault("active", "1")
        if row_id == want:
            row["country"] = (country or "").strip() or COUNTRY_CODE_NONE
            row["updated_at"] = updated_at
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _update_entity_market(domain_id: str, updated_at: str, **kwargs: str | bool | None) -> None:
    """Update a single market row in markets.csv and in DOMAIN_ENTITIES. kwargs: name, code, abb, market_type, market_group, template, period_type, score_type, side_type, score_dependant, active."""
    path = DATA_DIR / "markets.csv"
    if not path.exists():
        return
    fields = _ENTITY_FIELDS["markets"]
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    want = fid_str(domain_id)
    for row in rows:
        row_id = fid_str(row.get("domain_id"))
        if not row_id:
            continue
        if row_id == want:
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
            if "active" in kwargs and kwargs["active"] is not None:
                row["active"] = "1" if kwargs["active"] else "0"
            row["updated_at"] = updated_at
            break
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    # Update in-memory
    bucket = DOMAIN_ENTITIES.get("markets") or []
    for m in bucket:
        if entity_ids_equal(m.get("domain_id"), domain_id):
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
            if "active" in kwargs and kwargs["active"] is not None:
                m["active"] = bool(kwargs["active"])
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
            # Older files: header omits sport_id/category_id/competition_id but rows append them.
            # csv.DictReader puts overflow columns in row[None] as a list.
            rest = row.pop(None, None)
            tail: list[str] = []
            if isinstance(rest, (list, tuple)):
                tail = [str(x).strip() if x is not None else "" for x in rest]
            while len(tail) < 3:
                tail.append("")
            sid = (row.get("sport_id") or "").strip() or tail[0]
            cid = (row.get("category_id") or "").strip() or tail[1]
            compid = (row.get("competition_id") or "").strip() or tail[2]
            rows.append({
                "id":              row["domain_id"],
                "sport":           row.get("sport", ""),
                "category":        row.get("category", ""),
                "competition":     row.get("competition", ""),
                "home":            row.get("home", ""),
                "home_id":         row.get("home_id", ""),
                "away":            row.get("away", ""),
                "away_id":         row.get("away_id", ""),
                "start_time":      row.get("start_time", ""),
                "sport_id":        sid,
                "category_id":     cid,
                "competition_id":  compid,
            })
        return rows

def _sync_domain_events_entity_names() -> None:
    """
    One-time sync: update domain_events.csv to use current entity names from competitions/categories/sports.
    Fixes cases where entities were renamed but domain_events.csv still has old names.
    """
    if not DOMAIN_EVENTS_PATH.exists():
        return
    # Build name maps: entity_id -> current_name
    comp_id_to_name = {c["domain_id"]: (c.get("name") or "").strip() for c in DOMAIN_ENTITIES.get("competitions", []) if c.get("domain_id")}
    cat_id_to_name = {c["domain_id"]: (c.get("name") or "").strip() for c in DOMAIN_ENTITIES.get("categories", []) if c.get("domain_id")}
    sport_id_to_name = {s["domain_id"]: (s.get("name") or "").strip() for s in DOMAIN_ENTITIES.get("sports", []) if s.get("domain_id")}
    # Also build reverse: name -> id (for lookup by name in domain_events)
    comp_name_to_id = {}
    for c in DOMAIN_ENTITIES.get("competitions", []):
        name = (c.get("name") or "").strip()
        if name:
            comp_name_to_id[name] = c.get("domain_id")
    cat_name_to_id = {}
    for c in DOMAIN_ENTITIES.get("categories", []):
        name = (c.get("name") or "").strip()
        if name:
            cat_name_to_id[name] = c.get("domain_id")
    sport_name_to_id = {}
    for s in DOMAIN_ENTITIES.get("sports", []):
        name = (s.get("name") or "").strip()
        if name:
            sport_name_to_id[name] = s.get("domain_id")
    # Build competition lookup by (sport_id, category_id) -> list of competitions
    comps_by_sport_cat: dict[tuple[str, str], list[dict]] = {}
    for c in DOMAIN_ENTITIES.get("competitions", []):
        sport_id = c.get("sport_id")
        cat_id = c.get("category_id")
        sk, ck = fid_str(sport_id), fid_str(cat_id)
        if sk and ck:
            key = (sk, ck)
            if key not in comps_by_sport_cat:
                comps_by_sport_cat[key] = []
            comps_by_sport_cat[key].append(c)
    rows = []
    updated = False
    with open(DOMAIN_EVENTS_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Check competition: first try direct name match, then try sport+category match
            comp_name = (row.get("competition") or "").strip()
            if comp_name:
                comp_id = comp_name_to_id.get(comp_name)
                if comp_id and comp_id in comp_id_to_name:
                    current_name = comp_id_to_name[comp_id]
                    if comp_name != current_name:
                        row["competition"] = current_name
                        updated = True
                elif comp_id is None:
                    # Name doesn't exist in current competitions - try to match by sport+category
                    sport_name = (row.get("sport") or "").strip()
                    cat_name = (row.get("category") or "").strip()
                    if sport_name and cat_name:
                        sport_id = sport_name_to_id.get(sport_name)
                        cat_id = cat_name_to_id.get(cat_name)
                        if sport_id is not None and cat_id is not None:
                            key = (fid_str(sport_id), fid_str(cat_id))
                            matching_comps = comps_by_sport_cat.get(key, [])
                            # If exactly one competition for this sport+category, assume it's the renamed one
                            if len(matching_comps) == 1:
                                new_comp_name = (matching_comps[0].get("name") or "").strip()
                                if new_comp_name and new_comp_name != comp_name:
                                    row["competition"] = new_comp_name
                                    updated = True
            # Same for category: direct name match
            cat_name = (row.get("category") or "").strip()
            if cat_name:
                cat_id = cat_name_to_id.get(cat_name)
                if cat_id and cat_id in cat_id_to_name:
                    current_name = cat_id_to_name[cat_id]
                    if cat_name != current_name:
                        row["category"] = current_name
                        updated = True
            # Same for sport: direct name match
            sport_name = (row.get("sport") or "").strip()
            if sport_name:
                sport_id = sport_name_to_id.get(sport_name)
                if sport_id and sport_id in sport_id_to_name:
                    current_name = sport_id_to_name[sport_id]
                    if sport_name != current_name:
                        row["sport"] = current_name
                        updated = True
            rows.append(row)
    if updated:
        with open(DOMAIN_EVENTS_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=_DOMAIN_EVENT_FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        global DOMAIN_EVENTS
        DOMAIN_EVENTS = _load_domain_events()


def _update_domain_events_entity_name(entity_type: str, old_name: str, new_name: str) -> None:
    """
    Update domain_events.csv when a sport, category, or competition is renamed.
    Replaces old_name with new_name in the corresponding column (sport/category/competition).
    """
    if entity_type not in ("sports", "categories", "competitions"):
        return
    if not DOMAIN_EVENTS_PATH.exists():
        return
    column = entity_type[:-1]  # "sports" -> "sport", "categories" -> "category", "competitions" -> "competition"
    rows = []
    updated = False
    with open(DOMAIN_EVENTS_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if (row.get(column) or "").strip() == old_name:
                row[column] = new_name
                updated = True
            rows.append(row)
    if updated:
        with open(DOMAIN_EVENTS_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=_DOMAIN_EVENT_FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        global DOMAIN_EVENTS
        DOMAIN_EVENTS = _load_domain_events()


def _save_domain_event(event: dict) -> None:
    """Append one domain event row to domain_events.csv (no feeder info)."""
    row = {
        "domain_id":       event["id"],
        "sport":           event.get("sport", ""),
        "category":        event.get("category", ""),
        "competition":     event.get("competition", ""),
        "home":            event.get("home", ""),
        "home_id":         event.get("home_id", ""),
        "away":            event.get("away", ""),
        "away_id":         event.get("away_id", ""),
        "start_time":      event.get("start_time", ""),
        "sport_id":        event.get("sport_id", ""),
        "category_id":     event.get("category_id", ""),
        "competition_id":  event.get("competition_id", ""),
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
        row["domain_id"] = str(row["domain_id"]).strip()
        row["feed_provider_id"] = int(row["feed_provider_id"])
        if not (row.get("domain_name") or str(row.get("domain_name", "")).strip()):
            try:
                bucket = DOMAIN_ENTITIES.get(row["entity_type"], [])
                ent = next((e for e in bucket if entity_ids_equal(e["domain_id"], row["domain_id"])), None)
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
                    "domain_id": str(row["domain_id"]).strip(),
                    "feed_provider_id": int(row["feed_provider_id"]),
                    "feed_id": row.get("feed_id", ""),
                    "domain_name": (row.get("domain_name") or "").strip(),
                })
            except (KeyError, TypeError, ValueError):
                continue
    return out


def _domain_entity_name(entity_type: str, domain_id: str) -> str:
    """Return display name for a domain entity (from DOMAIN_ENTITIES). Empty if not found or not yet loaded."""
    try:
        bucket = DOMAIN_ENTITIES.get(entity_type, [])
        ent = next((e for e in bucket if entity_ids_equal(e["domain_id"], domain_id)), None)
        return (ent.get("name") or "").strip() if ent else ""
    except NameError:
        return ""

def _save_entity_feed_mapping(entity_type: str, domain_id: str, feed_provider_id: int, feed_id: str, domain_name: str | None = None) -> None:
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


def _ensure_entity_feed_mapping(entity_type: str, domain_id: str, feed_provider_id: int, feed_id: str) -> None:
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
        and mapping_feed_id_key(m.get("feed_id")) == mapping_feed_id_key(feed_id_str)
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

FEEDS: list[dict] = _load_feeds()
_ensure_imlog_feed_row()
_migrate_entity_feed_mappings_if_needed()
_migrate_sport_aliases_to_entity_feed_mappings()
_migrate_entity_created_updated_if_needed()
_migrate_entity_country_column_if_needed()
_migrate_entity_baseid_if_needed()
_migrate_entity_underage_participant_amateur_if_needed()
_migrate_entity_active_column_if_needed()
migrate_prefixed_domain_ids_if_needed()
DOMAIN_ENTITIES: dict[str, list[dict]] = _load_entities()
ENTITY_FEED_MAPPINGS: list[dict] = _load_entity_feed_mappings()
SPORT_FEED_MAPPINGS: list[dict] = _load_sport_feed_mappings()
DOMAIN_EVENTS: list[dict] = _load_domain_events()


def _deduplicate_sport_feed_mappings() -> None:
    """One-time: keep at most one sport mapping per (domain_id, feed_provider_id), preferring numeric feed_id."""
    seen: dict[tuple[str, int], dict] = {}
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

def _next_entity_id(entity_type: str) -> str:
    bucket = DOMAIN_ENTITIES[entity_type]
    return next_entity_domain_id(entity_type, bucket)

def _sport_name(sport_id: str | int | None) -> str:
    s = next((s for s in DOMAIN_ENTITIES["sports"] if entity_ids_equal(s["domain_id"], sport_id)), None)
    return s["name"] if s else ""

def _category_name(cat_id: str | int | None) -> str:
    c = next((c for c in DOMAIN_ENTITIES["categories"] if entity_ids_equal(c["domain_id"], cat_id)), None)
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
            return next((s for s in DOMAIN_ENTITIES["sports"] if entity_ids_equal(s["domain_id"], m["domain_id"])), None)
        if mid.lower() == incoming_lower:
            return next((s for s in DOMAIN_ENTITIES["sports"] if entity_ids_equal(s["domain_id"], m["domain_id"])), None)
    return None


# Register for use in feeder_events template (sport green check)
def _register_sport_feed_id_filter():
    templates.env.filters["normalize_sport_feed_id"] = lambda v: _normalize_sport_feed_id(v)
_register_sport_feed_id_filter()


def _mapped_category_feed_ids_by_sport() -> set[tuple[int, str, str]]:
    """Set of (feed_provider_id, feed_category_id, domain_sport_id) so category green is only for same sport."""
    out: set[tuple[int, str, str]] = set()
    for m in ENTITY_FEED_MAPPINGS:
        if m.get("entity_type") != "categories":
            continue
        cat = next((c for c in DOMAIN_ENTITIES["categories"] if entity_ids_equal(c.get("domain_id"), m.get("domain_id"))), None)
        if cat is not None:
            sid = cat.get("sport_id")
            if sid is not None:
                sk = fid_str(sid)
                if sk:
                    out.add((int(m["feed_provider_id"]), mapping_feed_id_key(m.get("feed_id")), sk))
    return out


def _mapped_comp_feed_ids_by_sport() -> set[tuple[int, str, str]]:
    """Set of (feed_provider_id, feed_comp_id, domain_sport_id) so competition green is only for same sport."""
    out: set[tuple[int, str, str]] = set()
    for m in ENTITY_FEED_MAPPINGS:
        if m.get("entity_type") != "competitions":
            continue
        comp = next((c for c in DOMAIN_ENTITIES["competitions"] if entity_ids_equal(c.get("domain_id"), m.get("domain_id"))), None)
        if comp is not None:
            sid = comp.get("sport_id")
            if sid is not None:
                sk = fid_str(sid)
                if sk:
                    out.add((int(m["feed_provider_id"]), mapping_feed_id_key(m.get("feed_id")), sk))
    return out


def _get_sport_slug(domain_sport_id: str | int | None) -> str:
    """Return lowercase sport name with no spaces for sport-specific feed filenames (e.g. volleyball)."""
    sports = DOMAIN_ENTITIES.get("sports") or []
    sport = next((s for s in sports if entity_ids_equal(s.get("domain_id"), domain_sport_id)), None)
    if not sport:
        return ""
    name = (sport.get("name") or "").strip()
    return name.lower().replace(" ", "") if name else ""


def _feed_sport_id_values_equal(a, b) -> bool:
    """True if two feed sport id representations match (int 91 vs str '91')."""
    if a is None or b is None:
        return False
    sa, sb = str(a).strip(), str(b).strip()
    if not sa or not sb:
        return False
    if sa == sb:
        return True
    try:
        return int(float(sa)) == int(float(sb))
    except (TypeError, ValueError):
        return False


def _event_declared_feed_sport_ids(ev: dict) -> list:
    """Sport identifiers present on a feed event / odds payload (Bet365/Bwin/1xbet shapes)."""
    out: list = []
    for key in ("sport_id", "SportId", "sport_key"):
        v = ev.get(key)
        if v is None or v == "":
            continue
        out.append(v)
    value = ev.get("Value") or ev.get("value")
    if isinstance(value, dict):
        for key in ("sport_id", "SportId"):
            v = value.get(key)
            if v is None or v == "":
                continue
            out.append(v)
        # 1xbet event detail: sport id on Value (e.g. SI: 6 = Volleyball)
        si = value.get("SI")
        if si is not None and si != "":
            out.append(si)
    return out


def _event_matches_feed_sport_filter(ev: dict, fsid: int | None) -> bool:
    """
    True if ev should count toward markets for this feed sport.
    When fsid is set, require a declared sport id on the payload that matches fsid.
    Events with no sport fields are excluded (avoids mixing Football cached details into Volleyball).
    """
    if fsid is None:
        return True
    declared = _event_declared_feed_sport_ids(ev)
    if not declared:
        return False
    return any(_feed_sport_id_values_equal(v, fsid) for v in declared)


def _load_feed_markets_from_event_details(
    feed_code: str, feed_sport_id: int, domain_sport_id: str | int | None
) -> list[dict]:
    """
    Load unique markets from stored event-details JSONs (feed_event_details/{feed_code}/*.json).
    Only includes events whose declared feed sport id matches feed_sport_id (strict — no sport id => excluded).
    Does not fall back to "all cached events" (that previously leaked other sports into the mapper).
    """
    feed_lower = (feed_code or "").strip().lower()
    if feed_lower not in ("bwin", "bet365", "1xbet", "imlog"):
        return []
    details_dir = config.FEED_EVENT_DETAILS_DIR / feed_lower
    if not details_dir.exists():
        return []

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
                parent_sport = raw.get("sport_id") or raw.get("SportId")
                if "results" in raw and isinstance(raw["results"], list):
                    for ev in raw["results"]:
                        if not isinstance(ev, dict):
                            continue
                        for_match = ev
                        if parent_sport is not None and not _event_declared_feed_sport_ids(ev):
                            for_match = {**ev, "sport_id": parent_sport}
                        if _event_matches_feed_sport_filter(for_match, feed_sport_id):
                            out.append(ev)
                    continue
                if "result" in raw and isinstance(raw["result"], dict):
                    inner = raw["result"]
                    for_match = inner
                    if parent_sport is not None and not _event_declared_feed_sport_ids(inner):
                        for_match = {**inner, "sport_id": parent_sport}
                    if isinstance(for_match, dict) and _event_matches_feed_sport_filter(for_match, feed_sport_id):
                        out.append(inner)
                    continue
                event = raw
            if isinstance(event, dict) and _event_matches_feed_sport_filter(event, feed_sport_id):
                out.append(event)
        return out

    results = _collect_events()
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
    # bwin + imlog (Bwin-shaped JSON, string templateId for IMLog markets)
    return _with_sport_dedupe(_parse_bwin_feed_markets, feed_sport_id, True)


def _load_feed_markets_for_sport(
    feed_code: str, feed_sport_id: int, domain_sport_id: str | int | None = None
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
    # IMLog: synthetic feed — if no JSON matches SportId vs sport_feed_mappings.feed_id, still offer fixed ids
    # (avoids empty mapper when files used fallback SportId 18 before mapping existed).
    if feed_lower == "imlog":
        from backend.internal_pricing.imlog_sync import imlog_markets_for_configuration_mapper

        static_list = [dict(m) for m in imlog_markets_for_configuration_mapper()]
        sport_display = _get_feed_sport_name(feed_lower, feed_sport_id)
        for m in static_list:
            m.setdefault("sport_name", sport_display)
        return static_list

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
        markets = _parse_bet365_feed_markets(data, None if used_sport_specific else feed_sport_id)
    elif feed_lower == "1xbet":
        markets = _parse_1xbet_feed_markets(data, None if used_sport_specific else feed_sport_id)
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
        if not skip_sport_filter and not _feed_sport_id_values_equal(event.get("SportId"), feed_sport_id):
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
                mid = str(template_id).strip()
                if not mid:
                    continue
            if mid in by_key:
                continue
            name = (item.get("name") or {}).get("value") or ""
            if not name:
                name = (tc.get("name") or {}).get("value") or ""
            name = (name or "").strip() or ("(id " + str(mid) + ")")
            by_key[mid] = {"id": mid, "name": name, "is_prematch": is_prematch, "line": None}  # id: int (Bwin) or str (IMLog)
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
# Mappings CSV sometimes stores Game/Set 1 Lines submarkets as 9100001..3 / 9102041..3 instead of 910000_1..3 (JSON block id is 910000 / 910204).
_BET365_COMPACT_SUBMARKET_IDS: dict[str, str] = {
    "9100001": "910000_1",
    "9100002": "910000_2",
    "9100003": "910000_3",
    "9102041": "910204_1",
    "9102042": "910204_2",
    "9102043": "910204_3",
}
# Set-score **name** is from that side's perspective (3-0 = that team wins 3-0); **header** 1=home / 2=away.
_BET365_SET_SCORE_HOME_AWAY_ORDER: dict[str, list[tuple[int, int]]] = {
    "910201": [(3, 0), (3, 1), (3, 2), (2, 3), (1, 3), (0, 3)],
    "910211": [(2, 0), (1, 1), (0, 2)],
    "910212": [(3, 0), (2, 1), (1, 2), (0, 3)],
}


def _bet365_header_str(header: object) -> str:
    if header is None:
        return ""
    return str(header).strip()


def _bet365_home_away_from_score_name_and_header(name: str, header: object) -> tuple[int, int] | None:
    """Map Bet365 row **name** (e.g. ``3-0``) + **header** to (home_sets, away_sets)."""
    n = (name or "").strip()
    m = re.match(r"^(\d+)\s*[-:]\s*(\d+)$", n)
    if not m:
        return None
    a, b = int(m.group(1)), int(m.group(2))
    h = _bet365_header_str(header)
    if h == "1":
        return (a, b)
    if h == "2":
        return (b, a)
    return (a, b)


def _bet365_set_score_outcomes_ordered(sub: list, base_id: str) -> list[dict] | None:
    """Order set-score odds to match domain columns (home 3-x first, then away 3-x as 2:3 / 1:3 / 0:3)."""
    order = _BET365_SET_SCORE_HOME_AWAY_ORDER.get(base_id)
    if not order:
        return None
    items: list[tuple[tuple[int, int], dict]] = []
    for o in sub:
        if not isinstance(o, dict) or o.get("odds") is None:
            continue
        ha = _bet365_home_away_from_score_name_and_header(str(o.get("name") or ""), o.get("header"))
        if ha is None:
            return None
        items.append((ha, o))
    if not items:
        return None

    def _sk(ha: tuple[int, int]) -> tuple:
        try:
            return (0, order.index(ha), 0)
        except ValueError:
            return (1, ha[0], ha[1])

    items.sort(key=lambda it: _sk(it[0]))
    return [{"name": f"{h}:{a}", "price": str(c["odds"])} for (h, a), c in items]


def _normalize_bet365_feed_market_id(fid: str) -> str:
    f = (fid or "").strip()
    return _BET365_COMPACT_SUBMARKET_IDS.get(f, f)


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


def _parse_bet365_feed_markets(data: dict | list, feed_sport_id: int | None = None) -> list[dict]:
    """Extract unique market types from Bet365 results (main.sp + others[].sp). Game Lines (910000) and Set 1 Lines (910204) split into Winner/Handicap/Total.
    When feed_sport_id is set, only events whose declared sport id matches are used (multi-sport JSON files)."""
    if isinstance(data, list):
        results = data
        parent_sport = None
    else:
        results = data.get("results") or []
        parent_sport = data.get("sport_id") or data.get("SportId")
    if feed_sport_id is not None:
        filtered: list[dict] = []
        for e in results:
            if not isinstance(e, dict):
                continue
            eff = e
            if parent_sport is not None and not _event_declared_feed_sport_ids(e):
                eff = {**e, "sport_id": parent_sport}
            if _event_matches_feed_sport_filter(eff, feed_sport_id):
                filtered.append(e)
        results = filtered
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


def _collect_1xbet_ge_blocks(obj: object) -> list[dict]:
    """Collect all {G, E, ...} outcome groups from 1xbet Value (and nested dicts e.g. SG.*.GE if present)."""
    out: list[dict] = []
    if isinstance(obj, dict):
        ge = obj.get("GE")
        if isinstance(ge, list):
            for item in ge:
                if isinstance(item, dict) and item.get("G") is not None:
                    out.append(item)
        for k, v in obj.items():
            if k == "GE":
                continue
            out.extend(_collect_1xbet_ge_blocks(v))
    elif isinstance(obj, list):
        for x in obj:
            out.extend(_collect_1xbet_ge_blocks(x))
    return out


def _summarize_1xbet_ge_block(block: dict) -> tuple[int, bool, list]:
    """Return (row_count, has_any_P, sorted_distinct_T)."""
    e = block.get("E") or []
    n_rows = 0
    ts: list = []
    seen_t: set = set()
    has_p = False
    if not isinstance(e, list):
        return 0, False, []
    for row in e:
        if not isinstance(row, list):
            continue
        n_rows += 1
        for cell in row:
            if not isinstance(cell, dict):
                continue
            t = cell.get("T")
            if t is not None:
                if t not in seen_t:
                    seen_t.add(t)
                    ts.append(t)
            if cell.get("P") is not None:
                has_p = True
    try:
        ts.sort(key=lambda x: (isinstance(x, (int, float)), x))
    except TypeError:
        ts.sort(key=str)
    return n_rows, has_p, ts


def _display_name_for_1xbet_ge(block: dict) -> str:
    """Synthetic label until human market names are supplied; encodes structure (rows, P, T codes)."""
    g = block.get("G")
    gid = str(g).strip() if g is not None else "?"
    n_rows, has_p, ts = _summarize_1xbet_ge_block(block)
    parts = [f"G={gid}", f"{n_rows} row(s)"]
    if has_p:
        parts.append("P (line)")
    if ts:
        shown = ",".join(str(x) for x in ts[:14])
        if len(ts) > 14:
            shown += ",…"
        parts.append(f"T: {shown}")
    return " · ".join(parts)


def _label_for_1xbet_ge_block(block: dict, name_by_g: dict[str, str]) -> str:
    """Prefer `1xbet_market_names.csv` (G → name); else synthetic GE summary."""
    g = block.get("G")
    gid = str(g).strip() if g is not None else ""
    if gid:
        custom = (name_by_g.get(gid) or "").strip()
        if custom:
            return custom
    return _display_name_for_1xbet_ge(block)


# 1xbet **P** encodes set score (not handicap/total line): int part = home sets, fractional ×1000 = away sets.
_1XBET_P_ENCODED_SCORE_MARKET_IDS = frozenset({"136", "343"})
_1XBET_CORRECT_SET_SCORE_ORDER: list[tuple[int, int]] = [(3, 0), (3, 1), (3, 2), (2, 3), (1, 3), (0, 3)]
_1XBET_SCORE_AFTER_TWO_SETS_ORDER: list[tuple[int, int]] = [(2, 0), (1, 1), (0, 2)]


def _1xbet_decode_p_set_score(p: object) -> tuple[int, int] | None:
    """Map 1xbet P (e.g. 3, 3.001, 0.003) to (home_sets, away_sets)."""
    try:
        pf = float(p)
    except (TypeError, ValueError):
        return None
    home = int(math.floor(pf + 1e-9))
    frac = pf - home
    if abs(frac) < 1e-8:
        away = 0
    else:
        away = int(round(frac * 1000))
    return (home, away)


def _1xbet_encoded_score_sort_index(gid: str, ha: tuple[int, int]) -> tuple[int, int, int]:
    """Stable sort key so outcomes align with domain column order."""
    if gid == "136":
        try:
            return (0, _1XBET_CORRECT_SET_SCORE_ORDER.index(ha), 0)
        except ValueError:
            return (1, ha[0], ha[1])
    if gid == "343":
        try:
            return (0, _1XBET_SCORE_AFTER_TWO_SETS_ORDER.index(ha), 0)
        except ValueError:
            return (1, ha[0], ha[1])
    return (1, ha[0], ha[1])


def _1xbet_encoded_score_outcomes_from_block(block: dict) -> list[dict]:
    """Flatten GE.E for G 136 / 343: one outcome per cell, names like 3:0 from **P** encoding."""
    gid = str(block.get("G") or "").strip()
    if gid not in _1XBET_P_ENCODED_SCORE_MARKET_IDS:
        return []
    rows = [r for r in (block.get("E") or []) if isinstance(r, list)]
    items: list[tuple[tuple[int, int], dict]] = []
    for row in rows:
        for cell in row:
            if not isinstance(cell, dict) or cell.get("C") is None or cell.get("P") is None:
                continue
            ha = _1xbet_decode_p_set_score(cell.get("P"))
            if ha is None:
                continue
            items.append((ha, cell))
    items.sort(key=lambda it: _1xbet_encoded_score_sort_index(gid, it[0]))
    return [{"name": f"{h}:{a}", "price": str(c["C"])} for (h, a), c in items]


def _1xbet_outcome_cell_label(cell: dict) -> str:
    """Debug-friendly outcome label from E[][] element (T / P); expand when T semantics are finalized."""
    parts: list[str] = []
    t = cell.get("T")
    if t is not None:
        parts.append(f"T={t}")
    p = cell.get("P")
    if p is not None:
        parts.append(f"P={p}")
    return " · ".join(parts) if parts else "—"


def _parse_1xbet_feed_markets(data: dict | list, feed_sport_id: int | None = None) -> list[dict]:
    """Extract unique markets from 1xbet event Value.GE: each group's **G** is the feed market id (no name in API).

    Falls back to legacy SG+MEC synthetic ids ({segmentI}_{MT}) only when no GE blocks exist.
    """
    if isinstance(data, list):
        results = data
        parent_sport = None
    else:
        results = data.get("results") or []
        parent_sport = data.get("sport_id") or data.get("SportId")
    if feed_sport_id is not None:
        filtered: list[dict] = []
        for e in results:
            if not isinstance(e, dict):
                continue
            eff = e
            if parent_sport is not None and not _event_declared_feed_sport_ids(e):
                eff = {**e, "sport_id": parent_sport}
            if _event_matches_feed_sport_filter(eff, feed_sport_id):
                filtered.append(e)
        results = filtered
    by_gid: dict[str, dict] = {}
    by_key: dict[tuple, dict] = {}
    name_by_g = _load_1xbet_market_names()
    for event in results:
        value = event.get("Value") or event.get("value") or {}
        blocks = _collect_1xbet_ge_blocks(value)
        if blocks:
            for block in blocks:
                g = block.get("G")
                if g is None:
                    continue
                gid = str(g).strip()
                if gid not in by_gid:
                    by_gid[gid] = {
                        "id": gid,
                        "name": _label_for_1xbet_ge_block(block, name_by_g),
                        "is_prematch": True,
                    }
            continue
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
    if by_gid:
        return list(by_gid.values())
    return list(by_key.values())


def _line_string_to_float(s: str | None) -> float | None:
    """Parse a UI / feed line token (e.g. '-0.5', '184,5', 'O 181.5') to float; None if not parseable."""
    if s is None:
        return None
    t = str(s).strip().replace("\u2212", "-").replace(",", ".")
    if not t:
        return None
    nums = re.findall(r"-?\d+\.?\d*|-?\.\d+", t)
    if not nums:
        return None
    try:
        return float(nums[-1])
    except ValueError:
        return None


def _float_line_close(a: float, b: float, *, abs_tol: float = 0.02) -> bool:
    """Loose match for handicap/total lines across feeds (comma decimals, float noise)."""
    return abs(a - b) <= abs_tol


def _bwin_attr_line_float(attr: str | None) -> float | None:
    if attr is None or not str(attr).strip():
        return None
    return _line_string_to_float(str(attr).strip().replace(",", "."))


def _bet365_handicap_scalar(h: str | None) -> float | None:
    """Bet365 'handicap' for side markets: '+1.5', '-0.5'. Returns None for totals like 'O 184.5'."""
    if h is None or not str(h).strip():
        return None
    s = str(h).strip().replace(",", ".")
    if re.match(r"^[OU]\s", s, re.IGNORECASE):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _bet365_total_line_float(h: str | None) -> float | None:
    """Extract total line from 'O 184.5' / 'U 184,5'."""
    if h is None or not str(h).strip():
        return None
    m = re.search(r"[OU]\s*([\d,\.]+)", str(h), re.IGNORECASE)
    if not m:
        return None
    return _line_string_to_float(m.group(1))


def _bet365_row_handicap_line_match(h: str | None, lf: float) -> bool:
    v = _bet365_handicap_scalar(h)
    if v is None:
        return False
    return _float_line_close(v, lf) or _float_line_close(v, -lf)


def _bet365_row_total_line_match(h: str | None, lf: float) -> bool:
    v = _bet365_total_line_float(h)
    if v is None:
        return False
    return _float_line_close(v, lf)


def _fmt_line_num(p: float) -> str:
    s = f"{p:.6f}".rstrip("0").rstrip(".")
    return s if s else str(p)


def _1xbet_pairing_mode(rows: list) -> str | None:
    """How to pair 1xbet GE.E rows: total (T9/T10 + P), handicap (T7/T8 or aligned P)."""
    if len(rows) < 2:
        return None
    r0, r1 = rows[0], rows[1]
    if not isinstance(r0, list) or not isinstance(r1, list) or not r0 or not r1:
        return None

    def _ts(r: list) -> set:
        return {c.get("T") for c in r if isinstance(c, dict)}

    t0, t1 = _ts(r0), _ts(r1)
    if t0 == {9} and t1 == {10}:
        return "total_9_10"
    if 7 in t0 and 8 in t1:
        return "handicap_7_8"
    if len(r0) == len(r1) and all(
        isinstance(c, dict) and c.get("P") is not None and c.get("C") is not None for c in r0 + r1
    ):
        return "handicap_index"
    return None


def _extract_1xbet_all_line_rows_from_block(block: dict) -> list[dict]:
    """All paired lines from one GE block: [{line, outcomes, is_main_line}, ...]. CE==1 marks balanced line (1xbet)."""
    gid = str(block.get("G") or "").strip()
    if gid in _1XBET_P_ENCODED_SCORE_MARKET_IDS:
        oc = _1xbet_encoded_score_outcomes_from_block(block)
        if oc:
            return [{"line": "—", "outcomes": oc, "is_main_line": False}]
        return []
    rows = [r for r in (block.get("E") or []) if isinstance(r, list)]
    out: list[dict] = []
    mode = _1xbet_pairing_mode(rows)
    if mode == "total_9_10":
        r0, r1 = rows[0], rows[1]
        over_p: dict[float, dict] = {}
        under_p: dict[float, dict] = {}
        for c in r0:
            if isinstance(c, dict) and c.get("C") is not None and c.get("P") is not None:
                try:
                    over_p[round(float(c["P"]), 4)] = c
                except (TypeError, ValueError):
                    pass
        for c in r1:
            if isinstance(c, dict) and c.get("C") is not None and c.get("P") is not None:
                try:
                    under_p[round(float(c["P"]), 4)] = c
                except (TypeError, ValueError):
                    pass
        for p in sorted(set(over_p) & set(under_p)):
            co, cu = over_p[p], under_p[p]
            dsp = _fmt_line_num(p)
            is_main = co.get("CE") == 1 or cu.get("CE") == 1
            out.append({
                "line": dsp,
                "outcomes": [
                    {"name": f"Over {dsp}", "price": str(co["C"])},
                    {"name": f"Under {dsp}", "price": str(cu["C"])},
                ],
                "is_main_line": is_main,
            })
        return out
    if mode in ("handicap_7_8", "handicap_index"):
        r0, r1 = rows[0], rows[1]
        for i in range(min(len(r0), len(r1))):
            ca, cb = r0[i], r1[i]
            if not isinstance(ca, dict) or not isinstance(cb, dict):
                continue
            if ca.get("C") is None or cb.get("C") is None:
                continue
            pb = ca.get("P")
            pa = cb.get("P")
            try:
                line_disp = _fmt_line_num(float(pb)) if pb is not None else (
                    _fmt_line_num(float(pa)) if pa is not None else str(i)
                )
            except (TypeError, ValueError):
                line_disp = str(i)
            is_main = ca.get("CE") == 1 or cb.get("CE") == 1
            out.append({
                "line": line_disp,
                "outcomes": [
                    {"name": _1xbet_outcome_cell_label(ca), "price": str(ca["C"])},
                    {"name": _1xbet_outcome_cell_label(cb), "price": str(cb["C"])},
                ],
                "is_main_line": is_main,
            })
        return out
    if len(rows) == 2 and len(rows[0]) == 1 and len(rows[1]) == 1:
        ca, cb = rows[0][0], rows[1][0]
        if isinstance(ca, dict) and isinstance(cb, dict) and ca.get("C") is not None and cb.get("C") is not None:
            out.append({
                "line": "—",
                "outcomes": [
                    {"name": _1xbet_outcome_cell_label(ca), "price": str(ca["C"])},
                    {"name": _1xbet_outcome_cell_label(cb), "price": str(cb["C"])},
                ],
                "is_main_line": bool(ca.get("CE") == 1 or cb.get("CE") == 1),
            })
    return out


def _extract_1xbet_all_line_rows(events_data: list[dict] | dict, feed_market_id: str) -> list[dict]:
    fid = str(feed_market_id).strip()
    results = events_data if isinstance(events_data, list) else (events_data.get("results") or [])
    for event in results:
        if not isinstance(event, dict):
            continue
        value = event.get("Value") or event.get("value") or {}
        for block in _collect_1xbet_ge_blocks(value):
            if str(block.get("G")).strip() != fid:
                continue
            parsed = _extract_1xbet_all_line_rows_from_block(block)
            if parsed:
                return parsed
    return []


def _bet365_total_lines_from_sub(sub: list) -> list[dict]:
    """Group Bet365 Total odds by numeric line (O/U pair per line)."""
    by_line: dict[float, dict[str, dict]] = {}
    for o in sub:
        if not isinstance(o, dict):
            continue
        v = _bet365_total_line_float(o.get("handicap"))
        if v is None:
            continue
        k = round(v, 4)
        hdr = str(o.get("header") or "").strip()
        by_line.setdefault(k, {})
        by_line[k][hdr] = o
    out: list[dict] = []
    for k in sorted(by_line.keys()):
        sides = by_line[k]
        if "1" not in sides or "2" not in sides:
            continue
        o1, o2 = sides["1"], sides["2"]
        h1 = str(o1.get("handicap") or "")
        h2 = str(o2.get("handicap") or "")
        if re.search(r"^U", h1, re.I) and re.search(r"^O", h2, re.I):
            o1, o2 = o2, o1
        dsp = _fmt_line_num(k)
        p1 = o1.get("odds")
        p2 = o2.get("odds")
        if p1 is None or p2 is None:
            continue
        out.append({
            "line": dsp,
            "outcomes": [
                {"name": str(o1.get("header") or "1").strip() or "1", "price": str(p1)},
                {"name": str(o2.get("header") or "2").strip() or "2", "price": str(p2)},
            ],
            "is_main_line": False,
        })
    return out


def _bet365_handicap_lines_from_sub(sub: list) -> list[dict]:
    """Group Bet365 Handicap odds by absolute line; pair + / - handicaps."""
    by_abs: dict[float, dict[str, dict]] = {}
    for o in sub:
        if not isinstance(o, dict):
            continue
        v = _bet365_handicap_scalar(o.get("handicap"))
        if v is None:
            continue
        a = round(abs(v), 4)
        sign = "+" if v > 0 else ("-" if v < 0 else "0")
        by_abs.setdefault(a, {})
        by_abs[a][sign] = o
    out: list[dict] = []
    for a in sorted(by_abs.keys()):
        sides = by_abs[a]
        op = sides.get("+") or sides.get("0")
        om = sides.get("-")
        if op is None or om is None:
            continue
        h_neg = str(om.get("handicap") or "").strip()
        line_disp = h_neg if h_neg else _fmt_line_num(-a)
        p1 = op.get("odds")
        p2 = om.get("odds")
        if p1 is None or p2 is None:
            continue
        out.append({
            "line": line_disp,
            "outcomes": [
                {"name": str(op.get("header") or "1").strip() or "1", "price": str(p1)},
                {"name": str(om.get("header") or "2").strip() or "2", "price": str(p2)},
            ],
            "is_main_line": False,
        })
    return out


def _extract_bet365_all_line_rows(events_data: list[dict] | dict, feed_market_id: str) -> list[dict]:
    fid = _normalize_bet365_feed_market_id(str(feed_market_id).strip())
    _, suffix = (fid.split("_", 1) + [""])[:2]
    if suffix not in ("2", "3"):
        return []
    base_id = fid.split("_", 1)[0]
    results = events_data if isinstance(events_data, list) else (events_data.get("results") or [])

    def pull_sub(sp: dict) -> list | None:
        if not sp:
            return None
        for block in (sp or {}).values():
            if not isinstance(block, dict):
                continue
            if str(block.get("id") or "").strip() != base_id:
                continue
            odds_list = block.get("odds") or []
            if suffix == "2":
                sub = [o for o in odds_list if isinstance(o, dict) and (o.get("name") or "").strip() == "Handicap"]
            else:
                sub = [o for o in odds_list if isinstance(o, dict) and (o.get("name") or "").strip() == "Total"]
            return sub
        return None

    for event in results:
        if not isinstance(event, dict):
            continue
        main_sp = (event.get("main") or {}).get("sp") or {}
        sub = pull_sub(main_sp)
        if sub:
            return _bet365_handicap_lines_from_sub(sub) if suffix == "2" else _bet365_total_lines_from_sub(sub)
        for other in event.get("others") or []:
            if not isinstance(other, dict):
                continue
            sub = pull_sub(other.get("sp") or {})
            if sub:
                return _bet365_handicap_lines_from_sub(sub) if suffix == "2" else _bet365_total_lines_from_sub(sub)
    return []


def _bwin_market_outcomes_and_attr(m: dict) -> tuple[list[dict], str]:
    outcomes = []
    for r in m.get("results") or []:
        if not isinstance(r, dict):
            continue
        name = (r.get("name") or {}).get("value") or (r.get("sourceName") or {}).get("value") or ""
        odds = r.get("odds")
        if odds is not None:
            outcomes.append({"name": str(name).strip() or "—", "price": str(odds)})
    attr_line = (m.get("attr") or "").strip() or ""
    if not attr_line and len(outcomes) >= 2:
        first_name = (outcomes[0].get("name") or "").strip()
        match = re.search(r"(?:Over|Under)\s+([\d,\.]+)", first_name, re.IGNORECASE)
        if match:
            attr_line = match.group(1).strip()
    return outcomes, attr_line


def _extract_bwin_all_line_rows(events_data: list[dict] | dict, feed_market_id: str) -> list[dict]:
    results = events_data if isinstance(events_data, list) else (events_data.get("results") or [])
    fid = str(feed_market_id).strip()

    def _market_matches(m: dict) -> bool:
        template_id = m.get("templateId")
        if template_id is not None and str(template_id).strip() == fid:
            return True
        tc = m.get("templateCategory")
        cid = m.get("categoryId")
        tid = (tc.get("id") if isinstance(tc, dict) else None) or cid
        return tid is not None and str(tid).strip() == fid

    for event in results:
        if not isinstance(event, dict):
            continue
        candidates = [m for m in (event.get("Markets") or []) + (event.get("optionMarkets") or []) if _market_matches(m)]
        if not candidates:
            continue
        out: list[dict] = []
        for m in candidates:
            oc, attr_line = _bwin_market_outcomes_and_attr(m)
            if len(oc) < 2:
                continue
            disp = attr_line.replace(",", ".") if attr_line else "—"
            out.append({"line": disp, "outcomes": oc, "is_main_line": False})
        if out:
            return out
    return []


def _pick_1xbet_cells_for_line(rows: list, target: float) -> tuple[list[dict], str] | None:
    """Pick two outcome cells for a handicap/total line from 1xbet GE.E rows (P / T structure)."""
    flat: list[dict] = []
    for row in rows:
        if not isinstance(row, list):
            continue
        for c in row:
            if isinstance(c, dict) and c.get("C") is not None and c.get("P") is not None:
                try:
                    float(c["P"])
                except (TypeError, ValueError):
                    continue
                flat.append(c)
    if not flat:
        return None

    def fmt_disp(x: float) -> str:
        s = f"{x:.6f}".rstrip("0").rstrip(".")
        return s if s else str(x)

    # Totals: same P, two different T (e.g. 9 / 10) on one line
    by_p: dict[float, list[dict]] = {}
    for c in flat:
        p = float(c["P"])
        key = round(p, 4)
        by_p.setdefault(key, []).append(c)
    for rk, cells in by_p.items():
        if not _float_line_close(rk, target):
            continue
        if len(cells) >= 2:
            tset = {c.get("T") for c in cells}
            if len(tset) >= 2:
                ordered = sorted(cells, key=lambda x: (x.get("T") is None, x.get("T")))
                return ordered[:2], fmt_disp(rk)

    # Handicap: one side P≈target, other P≈-target (e.g. -0.5 / +0.5)
    def _pick_main(cs: list[dict]) -> dict:
        mains = [x for x in cs if x.get("CE") == 1]
        return mains[0] if mains else cs[0]

    neg_side = [c for c in flat if _float_line_close(float(c["P"]), target)]
    pos_side = [c for c in flat if _float_line_close(float(c["P"]), -target)]
    if neg_side and pos_side:
        pair = sorted([_pick_main(neg_side), _pick_main(pos_side)], key=lambda x: x.get("T", 0))
        return pair, fmt_disp(target)

    return None


def _extract_bwin_market_odds(
    events_data: list[dict] | dict, feed_market_id: str, line: str | None = None
) -> dict:
    """From Bwin event details, extract outcomes and line (attr) for market by templateId (or categoryId for legacy). Returns {outcomes: [...], line: str}.
    When ``line`` is set, pick the market instance whose attr matches that line (multi-line handicap/total templates)."""
    results = events_data if isinstance(events_data, list) else (events_data.get("results") or [])
    fid = str(feed_market_id).strip()
    line_f = _line_string_to_float(line) if (line and str(line).strip()) else None

    def _market_matches(m: dict) -> bool:
        template_id = m.get("templateId")
        if template_id is not None and str(template_id).strip() == fid:
            return True
        tc = m.get("templateCategory")
        cid = m.get("categoryId")
        tid = (tc.get("id") if isinstance(tc, dict) else None) or cid
        return tid is not None and str(tid).strip() == fid

    def _outcomes_for(m: dict) -> tuple[list[dict], str]:
        outcomes = []
        for r in m.get("results") or []:
            name = (r.get("name") or {}).get("value") or (r.get("sourceName") or {}).get("value") or ""
            odds = r.get("odds")
            if odds is not None:
                outcomes.append({"name": str(name).strip() or "—", "price": str(odds)})
        attr_line = (m.get("attr") or "").strip() or ""
        if not attr_line and len(outcomes) >= 2:
            first_name = (outcomes[0].get("name") or "").strip()
            match = re.search(r"(?:Over|Under)\s+([\d,\.]+)", first_name, re.IGNORECASE)
            if match:
                attr_line = match.group(1).strip()
        return outcomes, attr_line

    for event in results:
        candidates = [m for m in (event.get("Markets") or []) + (event.get("optionMarkets") or []) if _market_matches(m)]
        if not candidates:
            continue
        chosen = candidates[0]
        if line_f is not None:
            best = None
            for m in candidates:
                af = _bwin_attr_line_float(m.get("attr"))
                if af is None:
                    oc, _ = _outcomes_for(m)
                    if oc:
                        fn = (oc[0].get("name") or "").strip()
                        match = re.search(r"(?:Over|Under)\s+([\d,\.]+)", fn, re.IGNORECASE)
                        if match:
                            af = _line_string_to_float(match.group(1))
                if af is not None and (
                    _float_line_close(af, line_f)
                    or _float_line_close(af, -line_f)
                    or _float_line_close(abs(af), abs(line_f))
                ):
                    best = m
                    break
            if best is not None:
                chosen = best
        outcomes, attr_line = _outcomes_for(chosen)
        disp = (line or "").strip() or attr_line
        if line_f is not None and attr_line:
            af = _bwin_attr_line_float(attr_line)
            if af is not None and (
                _float_line_close(af, line_f)
                or _float_line_close(af, -line_f)
                or _float_line_close(abs(af), abs(line_f))
            ):
                disp = attr_line.replace(",", ".")
        return {"outcomes": outcomes, "line": disp}
    return {"outcomes": [], "line": ""}


def _extract_bet365_market_odds(
    events_data: list[dict] | dict, feed_market_id: str, line: str | None = None
) -> dict:
    """From Bet365 event details, extract outcomes for market. Handles 910000_1/2/3 (Game Lines) and 910204_1/2/3 (Set 1 Lines) submarkets.
    Correct set score (910201) and score-after-N-sets (910211, 910212): **name** repeats 3-0/3-1/… per side; **header** 1=home / 2=away — we map to home:away and sort like domain outcomes.
    When ``line`` is set, restrict Handicap/Total odds to that line."""
    results = events_data if isinstance(events_data, list) else (events_data.get("results") or [])
    fid = _normalize_bet365_feed_market_id(str(feed_market_id).strip())
    base_id, suffix = (fid.split("_", 1) + [""])[:2]  # e.g. "910000_1" -> base "910000", suffix "1"
    line_f = _line_string_to_float(line) if (line and str(line).strip()) else None

    def from_sp(sp: dict) -> tuple[list[dict], str]:
        if not sp:
            return [], ""
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
            disp_line = ""
            if line_f is not None and suffix == "2":
                filt = [
                    o for o in sub
                    if isinstance(o, dict) and _bet365_row_handicap_line_match(o.get("handicap"), line_f)
                ]
                if len(filt) >= 2:
                    sub = filt
                    disp_line = (line or "").strip()
            elif line_f is not None and suffix == "3":
                filt = [
                    o for o in sub
                    if isinstance(o, dict) and _bet365_row_total_line_match(o.get("handicap"), line_f)
                ]
                if len(filt) >= 2:
                    sub = filt
                    disp_line = (line or "").strip()
            if base_id in _BET365_SET_SCORE_HOME_AWAY_ORDER:
                scored = _bet365_set_score_outcomes_ordered(sub, base_id)
                if scored is not None:
                    return scored, ""
            outcomes = []
            for o in sub:
                if not isinstance(o, dict):
                    continue
                header = str(o.get("header") or "").strip()
                price = o.get("odds")
                if price is not None:
                    outcomes.append({"name": header or "—", "price": str(price)})
            if not disp_line and sub and isinstance(sub[0], dict):
                h0 = sub[0].get("handicap")
                if suffix == "2":
                    v = _bet365_handicap_scalar(h0)
                    if v is not None:
                        disp_line = str(h0).strip()
                elif suffix == "3":
                    v = _bet365_total_line_float(h0)
                    if v is not None:
                        disp_line = str(v).replace(".", ",") if isinstance(v, float) else str(h0)
            return outcomes, disp_line
        return [], ""

    for event in results:
        main_sp = (event.get("main") or {}).get("sp") or {}
        out, dl = from_sp(main_sp)
        if out:
            return {"outcomes": out, "line": dl}
        for other in event.get("others") or []:
            out, dl = from_sp((other or {}).get("sp") or {})
            if out:
                return {"outcomes": out, "line": dl}
    return {"outcomes": [], "line": ""}


def _extract_1xbet_market_odds(
    events_data: list[dict] | dict, feed_market_id: str, line: str | None = None
) -> dict:
    """From 1xbet event details: find Value.GE group with G == feed_market_id; flatten E[][] to outcomes.

    When ``line`` is set, return the two sides for that handicap/total line only (via **P** / **T**).
    """
    fid = str(feed_market_id).strip()
    line_f = _line_string_to_float(line) if (line and str(line).strip()) else None
    results = events_data if isinstance(events_data, list) else (events_data.get("results") or [])
    for event in results:
        if not isinstance(event, dict):
            continue
        value = event.get("Value") or event.get("value") or {}
        for block in _collect_1xbet_ge_blocks(value):
            if str(block.get("G")).strip() != fid:
                continue
            gid = str(block.get("G") or "").strip()
            if gid in _1XBET_P_ENCODED_SCORE_MARKET_IDS:
                oc = _1xbet_encoded_score_outcomes_from_block(block)
                return {"outcomes": oc, "line": ""}
            rows = [r for r in (block.get("E") or []) if isinstance(r, list)]
            if line_f is not None:
                picked = _pick_1xbet_cells_for_line(rows, line_f)
                if picked:
                    cells, disp = picked
                    outcomes = [{"name": _1xbet_outcome_cell_label(c), "price": str(c["C"])} for c in cells]
                    return {"outcomes": outcomes, "line": disp}
            outcomes = []
            for row in rows:
                for cell in row:
                    if not isinstance(cell, dict):
                        continue
                    c = cell.get("C")
                    if c is None:
                        continue
                    outcomes.append({"name": _1xbet_outcome_cell_label(cell), "price": str(c)})
            if outcomes:
                return {"outcomes": outcomes, "line": ""}
    return {"outcomes": [], "line": ""}


def _get_feed_odds_for_event_market(
    domain_event_id: str,
    domain_market_id: str | int,
    line: str | None = None,
    all_lines: bool = True,
    exclude_feed_codes: frozenset[str] | None = None,
) -> list[dict]:
    """Return list of rows from cached event details and market type mappings.

    Each row: ``feed_provider_id``, ``feed_name``, ``feed_market_id``, ``outcomes``, ``line``, ``is_main_line`` (e.g. 1xbet CE==1).

    With ``all_lines`` true (default), multi-line feeds return one row per offered line (paired Over/Under or
    handicap sides). With ``all_lines`` false, ``line`` selects a single line like the legacy UI behavior.

    ``exclude_feed_codes``: lowercase feed codes to skip (e.g. ``frozenset({"imlog"})`` when building IMLog from other feeds).
    """
    eid_key = str(domain_event_id).strip()
    event_mappings = [m for m in _load_event_mappings() if (m.get("domain_event_id") or "").strip() == eid_key]
    # IMLog JSON is always written as feed_event_details/imlog/{domain_event_id}.json. If that file exists but
    # event_mappings has no imlog row yet, still include imlog so Feed Odds works once market_type_mappings exist.
    if not any((m.get("feed_provider") or "").strip().lower() == "imlog" for m in event_mappings):
        imlog_feed = next((f for f in FEEDS if (f.get("code") or "").strip().lower() == "imlog"), None)
        if imlog_feed and (config.FEED_EVENT_DETAILS_DIR / "imlog" / f"{eid_key}.json").exists():
            event_mappings = list(event_mappings) + [
                {"domain_event_id": eid_key, "feed_provider": "imlog", "feed_valid_id": eid_key},
            ]
    dmid = fid_str(domain_market_id)
    mt_mappings = [m for m in _load_market_type_mappings() if fid_str(m.get("domain_market_id")) == dmid]
    feed_by_id = {f["domain_id"]: f for f in FEEDS}
    code_by_id = {f["domain_id"]: (f.get("code") or "").strip().lower() for f in FEEDS}
    result: list[dict] = []
    for em in event_mappings:
        feed_provider_str = (em.get("feed_provider") or "").strip().lower()
        if exclude_feed_codes and feed_provider_str in exclude_feed_codes:
            continue
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
            result.append({
                "feed_provider_id": feed_provider_id,
                "feed_name": feed_name,
                "feed_market_id": "",
                "outcomes": [],
                "line": "—",
                "is_main_line": False,
            })
            continue
        feed_market_id = str(mt.get("feed_market_id") or "").strip()
        if feed_provider_str == "bet365":
            feed_market_id = _normalize_bet365_feed_market_id(feed_market_id)
            if feed_market_id == "910000":
                feed_market_id = "910000_1"
            if feed_market_id == "910204":
                feed_market_id = "910204_1"
        path = config.FEED_EVENT_DETAILS_DIR / feed_provider_str / f"{feed_valid_id}.json"
        if not path.exists():
            result.append({
                "feed_provider_id": feed_provider_id,
                "feed_name": feed_name,
                "feed_market_id": feed_market_id,
                "outcomes": [],
                "line": "—",
                "is_main_line": False,
            })
            continue
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            result.append({
                "feed_provider_id": feed_provider_id,
                "feed_name": feed_name,
                "feed_market_id": feed_market_id,
                "outcomes": [],
                "line": "—",
                "is_main_line": False,
            })
            continue
        events_list = data.get("results") if isinstance(data, dict) else (data if isinstance(data, list) else [])
        payload = events_list or data

        def _append_single_bwin() -> None:
            bwin_data = _extract_bwin_market_odds(payload, feed_market_id, line)
            outcomes = bwin_data.get("outcomes") or []
            row_line = (bwin_data.get("line") or "").strip() or "—"
            result.append({
                "feed_provider_id": feed_provider_id,
                "feed_name": feed_name,
                "feed_market_id": feed_market_id,
                "outcomes": outcomes,
                "line": row_line,
                "is_main_line": False,
            })

        def _append_single_b365() -> None:
            b365 = _extract_bet365_market_odds(payload, feed_market_id, line)
            outcomes = b365.get("outcomes") or []
            row_line = (b365.get("line") or "").strip() or "—"
            result.append({
                "feed_provider_id": feed_provider_id,
                "feed_name": feed_name,
                "feed_market_id": feed_market_id,
                "outcomes": outcomes,
                "line": row_line,
                "is_main_line": False,
            })

        def _append_single_1xbet() -> None:
            ox = _extract_1xbet_market_odds(payload, feed_market_id, line)
            outcomes = ox.get("outcomes") or []
            row_line = (ox.get("line") or "").strip() or "—"
            result.append({
                "feed_provider_id": feed_provider_id,
                "feed_name": feed_name,
                "feed_market_id": feed_market_id,
                "outcomes": outcomes,
                "line": row_line,
                "is_main_line": False,
            })

        if feed_provider_str in ("bwin", "imlog"):
            if all_lines:
                multi = _extract_bwin_all_line_rows(payload, feed_market_id)
                if multi:
                    for mr in multi:
                        result.append({
                            "feed_provider_id": feed_provider_id,
                            "feed_name": feed_name,
                            "feed_market_id": feed_market_id,
                            "outcomes": mr.get("outcomes") or [],
                            "line": (mr.get("line") or "—"),
                            "is_main_line": bool(mr.get("is_main_line")),
                        })
                else:
                    _append_single_bwin()
            else:
                _append_single_bwin()
        elif feed_provider_str == "bet365":
            if all_lines:
                multi = _extract_bet365_all_line_rows(payload, feed_market_id)
                if multi:
                    for mr in multi:
                        result.append({
                            "feed_provider_id": feed_provider_id,
                            "feed_name": feed_name,
                            "feed_market_id": feed_market_id,
                            "outcomes": mr.get("outcomes") or [],
                            "line": (mr.get("line") or "—"),
                            "is_main_line": bool(mr.get("is_main_line")),
                        })
                else:
                    _append_single_b365()
            else:
                _append_single_b365()
        elif feed_provider_str == "1xbet":
            if all_lines:
                multi = _extract_1xbet_all_line_rows(payload, feed_market_id)
                if multi:
                    for mr in multi:
                        result.append({
                            "feed_provider_id": feed_provider_id,
                            "feed_name": feed_name,
                            "feed_market_id": feed_market_id,
                            "outcomes": mr.get("outcomes") or [],
                            "line": (mr.get("line") or "—"),
                            "is_main_line": bool(mr.get("is_main_line")),
                        })
                else:
                    _append_single_1xbet()
            else:
                _append_single_1xbet()
        else:
            result.append({
                "feed_provider_id": feed_provider_id,
                "feed_name": feed_name,
                "feed_market_id": feed_market_id,
                "outcomes": [],
                "line": "—",
                "is_main_line": False,
            })
    return result


def _resolve_entity(etype: str, feed_id: str, feed_provider_id: int, domain_sport_id: str | int | None = None) -> dict | None:
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
        if etype in ("categories", "competitions"):
            row_keys = mapping_related_feed_id_keys(feed_id_str)
        else:
            k = mapping_feed_id_key(feed_id_str)
            row_keys = [k] if k else []
        mapping = None
        for fk in row_keys:
            mapping = next(
                (
                    m
                    for m in ENTITY_FEED_MAPPINGS
                    if m["entity_type"] == etype
                    and m["feed_provider_id"] == int(feed_provider_id)
                    and mapping_feed_id_key(m.get("feed_id")) == fk
                ),
                None,
            )
            if mapping is not None:
                break
    if not mapping:
        return None
    entity = next((e for e in DOMAIN_ENTITIES[etype] if entity_ids_equal(e["domain_id"], mapping["domain_id"])), None)
    if not entity:
        return None
    # Categories and competitions are sport-scoped: only match if the entity's sport is the event's sport
    if domain_sport_id is not None and etype in ("categories", "competitions"):
        if not entity_ids_equal(entity.get("sport_id"), domain_sport_id):
            return None
    return entity


def _feeder_event_feed_category_mapped(e: dict, feed_provider_id: int | None) -> bool:
    """True when this feed row's native category (e.g. Bwin region) resolves to a mapped domain category."""
    if not feed_provider_id:
        return False
    r = _resolve_sport_alias(feed_provider_id, e.get("sport_id"))
    dsid = r["domain_id"] if r else None
    if not dsid:
        return False
    id_candidates: list[str] = []
    for src in (e.get("category_id"), e.get("category")):
        t = str(src or "").strip()
        if t and t.upper().startswith("COMP:"):
            continue
        if t and t not in id_candidates:
            id_candidates.append(t)
    for s in id_candidates:
        if _resolve_entity("categories", s, feed_provider_id, domain_sport_id=dsid) is not None:
            return True
    name = (e.get("category") or "").strip()
    if not name:
        return False
    if name.upper().startswith("COMP:"):
        return False
    cat_ent = next(
        (
            c
            for c in DOMAIN_ENTITIES["categories"]
            if entity_ids_equal(c.get("sport_id"), dsid) and (c.get("name") or "").strip().lower() == name.lower()
        ),
        None,
    )
    if not cat_ent:
        return False
    return any(
        m.get("entity_type") == "categories"
        and int(m["feed_provider_id"]) == int(feed_provider_id)
        and entity_ids_equal(m.get("domain_id"), cat_ent["domain_id"])
        for m in ENTITY_FEED_MAPPINGS
    )


def _feeder_event_feed_competition_mapped(e: dict, feed_provider_id: int | None) -> bool:
    """True when league id or name resolves to a mapped domain competition for this sport + provider."""
    if not feed_provider_id:
        return False
    r = _resolve_sport_alias(feed_provider_id, e.get("sport_id"))
    dsid = r["domain_id"] if r else None
    if not dsid:
        return False
    raw_lid = e.get("raw_league_id")
    if raw_lid is not None and str(raw_lid).strip() != "":
        if _resolve_entity("competitions", str(raw_lid).strip(), feed_provider_id, domain_sport_id=dsid) is not None:
            return True
    name = (e.get("raw_league_name") or "").strip()
    if not name:
        return False
    comps = [
        c
        for c in DOMAIN_ENTITIES["competitions"]
        if entity_ids_equal(c.get("sport_id"), dsid) and (c.get("name") or "").strip().lower() == name.lower()
    ]
    for c in comps:
        if any(
            m.get("entity_type") == "competitions"
            and int(m["feed_provider_id"]) == int(feed_provider_id)
            and entity_ids_equal(m.get("domain_id"), c["domain_id"])
            for m in ENTITY_FEED_MAPPINGS
        ):
            return True
    return False


def _feeder_event_team_side_mapped(e: dict, side: str, feed_provider_id: int | None) -> bool:
    if not feed_provider_id:
        return False
    raw_id = e.get("raw_home_id" if side == "home" else "raw_away_id")
    raw_name = (e.get("raw_home_name" if side == "home" else "raw_away_name") or "").strip()
    if raw_id is not None and str(raw_id).strip() != "":
        if _resolve_entity("teams", str(raw_id).strip(), feed_provider_id) is not None:
            return True
    if raw_name and _resolve_entity("teams", raw_name, feed_provider_id) is not None:
        return True
    return False


def _feeder_events_attach_row_mapping_flags(page_events: list[dict], selected_feed_pid: int | None) -> None:
    """Align list-row green checks with _resolve_entity / mappings (ids, numeric forms, name fallbacks)."""
    for e in page_events:
        e["feed_category_mapped"] = _feeder_event_feed_category_mapped(e, selected_feed_pid)
        e["feed_competition_mapped"] = _feeder_event_feed_competition_mapped(e, selected_feed_pid)
        e["feed_home_team_mapped"] = _feeder_event_team_side_mapped(e, "home", selected_feed_pid)
        e["feed_away_team_mapped"] = _feeder_event_team_side_mapped(e, "away", selected_feed_pid)
        e["feeder_competition_filter_token"] = _feeder_competition_filter_token_for_event(e)


def _acronym_word_initials_score(short: str, long_text: str) -> int:
    """
    When short looks like an acronym of long_text's words (e.g. psg vs Paris Saint-Germain),
    return a high score; otherwise 0. Guards two-letter noise unless there are exactly two words.
    """
    if not short or not long_text:
        return 0
    short = short.strip().lower()
    long_text = long_text.strip().lower()
    if len(short) < 2 or len(long_text) < len(short) + 3:
        return 0
    words = re.findall(r"[a-z0-9]+", long_text)
    if len(words) < 2:
        return 0
    initials = "".join(w[0] for w in words if w)
    if not initials:
        return 0
    if initials == short:
        if len(short) >= 3:
            return 92
        return 88 if len(words) == 2 else 0
    return 0


def _fuzzy_score(a: str, b: str) -> int:
    """Return similarity 0-100 between two strings (case-insensitive)."""
    if not a or not b:
        return 0
    a0, b0 = a.strip(), b.strip()
    a, b = a0.lower(), b0.lower()
    if a == b:
        return 100
    base = int(round(100 * difflib.SequenceMatcher(None, a, b).ratio()))
    ac = 0
    if len(a) <= len(b):
        ac = max(ac, _acronym_word_initials_score(a, b0))
    if len(b) <= len(a):
        ac = max(ac, _acronym_word_initials_score(b, a0))
    return min(100, max(base, ac))


def _domain_event_start_minute_key(st: str | None) -> str:
    """Normalize start_time for comparison (minute precision)."""
    if not st or not isinstance(st, str):
        return ""
    s = st.strip()
    if len(s) >= 16:
        return s[:16]
    return s


def _domain_event_start_times_equivalent(a: str | None, b: str | None) -> bool:
    if not a or not b:
        return False
    a, b = str(a).strip(), str(b).strip()
    if a == b:
        return True
    return _domain_event_start_minute_key(a) == _domain_event_start_minute_key(b)


def _domain_event_matches_competition_scope(ev: dict, dcomp: str, feed_comp: str) -> bool:
    """
    True when the domain event belongs to mapped competition dcomp: same competition_id,
    or legacy rows with empty competition_id but competition text matching feed / canonical name.
    """
    if not dcomp:
        return True
    if entity_ids_equal(ev.get("competition_id"), dcomp):
        return True
    ev_cid = ev.get("competition_id")
    if ev_cid is not None and str(ev_cid).strip() != "":
        return False
    d_comp = (ev.get("competition") or "").strip()
    if not d_comp:
        return False
    comp_ent = next(
        (c for c in DOMAIN_ENTITIES.get("competitions", []) if entity_ids_equal(c.get("domain_id"), dcomp)),
        None,
    )
    canon = (comp_ent.get("name") or "").strip() if comp_ent else ""
    for ref in (feed_comp, canon):
        if ref and _fuzzy_score(ref, d_comp) >= 78:
            return True
    return False


def _search_token_matches_field(t: str, field: str) -> bool:
    """
    True if token t appears as a whole token in field (not as a substring inside a longer word).
    Prevents e.g. 'spor' matching 'Sporting' when searching for Turkish side 'Spor Toto'.
    """
    if not t or not field:
        return False
    if len(t) <= 1:
        return False
    try:
        pat = r"(?<![a-z0-9])" + re.escape(t) + r"(?![a-z0-9])"
        return re.search(pat, field, re.IGNORECASE) is not None
    except re.error:
        return t in field


def _domain_event_matches_search_q(ev: dict, q_lower: str) -> bool:
    """Match domain event against search query: substring, per-token word-boundary match, then fuzzy on names."""
    if not q_lower:
        return True
    home = (ev.get("home") or "").lower()
    away = (ev.get("away") or "").lower()
    comp = (ev.get("competition") or "").lower()
    evid = (ev.get("id") or "").lower()
    blob = f"{home} {away} {comp}".strip()
    if q_lower in home or q_lower in away or q_lower in comp or q_lower in evid or q_lower in blob:
        return True
    for tok in q_lower.split():
        t = tok.strip().lower()
        if len(t) < 2:
            continue
        if _search_token_matches_field(t, home) or _search_token_matches_field(t, away) or _search_token_matches_field(t, comp) or _search_token_matches_field(t, evid):
            return True
        for field in (home, away):
            # Min length avoids short tokens (e.g. "spor") fuzzy-matching longer names ("Sporting").
            if len(t) >= 4 and field and _fuzzy_score(t, field) >= 60:
                return True
    if blob and _fuzzy_score(q_lower, blob) >= 48:
        return True
    return False


def _domain_event_sport_label_matches_canonical(row_sport: str, canonical_name: str) -> bool:
    """Case-insensitive match for legacy domain_events.sport text vs entity name; Soccer ↔ Football."""
    a = (row_sport or "").strip().lower()
    b = (canonical_name or "").strip().lower()
    if not a or not b:
        return False
    if a == b:
        return True
    if {a, b} <= {"soccer", "football"}:
        return True
    return False


def _domain_event_row_matches_domain_sport(ev: dict, sport_domain_id: str) -> bool:
    """
    True when a domain event row belongs to sport_domain_id.
    Uses event.sport_id plus competition and category FKs so a mis-set event.sport_id cannot surface
    e.g. a EuroLeague fixture under Football suggestions.

    Legacy domain_events.csv rows often omit sport_id; then the human-readable ``sport`` column is
    compared to the canonical sport name for ``sport_domain_id`` so Volleyball fixtures are not
    suggested when mapping Football (and vice versa).
    """
    sid = fid_str(sport_domain_id)
    if not sid:
        return True
    ev_sid = ev.get("sport_id")
    if ev_sid is not None and str(ev_sid).strip() != "":
        if not entity_ids_equal(ev_sid, sid):
            return False
    else:
        sport_ent = next(
            (s for s in DOMAIN_ENTITIES.get("sports", []) if entity_ids_equal(s.get("domain_id"), sid)),
            None,
        )
        canon = (sport_ent.get("name") or "").strip() if sport_ent else ""
        row_sport = (ev.get("sport") or "").strip()
        if canon:
            if not _domain_event_sport_label_matches_canonical(row_sport, canon):
                return False
        else:
            if row_sport:
                return False
        if not canon and not row_sport:
            return False
    cid = ev.get("competition_id")
    if cid is not None and str(cid).strip() != "":
        comp = next((c for c in DOMAIN_ENTITIES.get("competitions", []) if entity_ids_equal(c.get("domain_id"), cid)), None)
        if comp is not None:
            cs = comp.get("sport_id")
            if cs is not None and str(cs).strip() != "" and not entity_ids_equal(cs, sid):
                return False
    gid = ev.get("category_id")
    if gid is not None and str(gid).strip() != "":
        cat = next((c for c in DOMAIN_ENTITIES.get("categories", []) if entity_ids_equal(c.get("domain_id"), gid)), None)
        if cat is not None:
            gs = cat.get("sport_id")
            if gs is not None and str(gs).strip() != "" and not entity_ids_equal(gs, sid):
                return False
    return True


def _infer_domain_sport_id_from_mapped_entities(event: dict, feed_pid: int) -> str | None:
    """When feed sport is not in mappings, derive domain sport from mapped category or competition (sport-agnostic resolve)."""
    for src in (event.get("category_id"), event.get("category")):
        t = str(src or "").strip()
        if not t:
            continue
        cat_ent = _resolve_entity("categories", t, feed_pid, domain_sport_id=None)
        if cat_ent and cat_ent.get("sport_id") is not None and str(cat_ent.get("sport_id")).strip():
            return fid_str(cat_ent.get("sport_id"))
    lid = str(event.get("raw_league_id") or "").strip()
    if lid:
        comp_ent = _resolve_entity("competitions", lid, feed_pid, domain_sport_id=None)
        if comp_ent and comp_ent.get("sport_id") is not None and str(comp_ent.get("sport_id")).strip():
            return fid_str(comp_ent.get("sport_id"))
    return None


def _domain_sport_id_from_feed_display_sport(display: str | None) -> tuple[str | None, dict | None]:
    """
    Map feeder UI sport label (from feed_sports / event row) to a domain sport when there is no
    sport_feed_mappings row yet. Keeps domain-event suggestions inside the sport the user filtered on.
    """
    d = (display or "").strip()
    if not d:
        return None, None
    for s in DOMAIN_ENTITIES.get("sports", []):
        name = (s.get("name") or "").strip()
        if name and _domain_event_sport_label_matches_canonical(d, name):
            return fid_str(s.get("domain_id")), s
    return None, None


def _suggest_domain_events(
    feed_event: dict,
    *,
    domain_sport_id: str | None = None,
    domain_category_id: str | None = None,
    domain_competition_id: str | None = None,
) -> list[dict]:
    """
    Find domain events that may be the same fixture (another feed / naming variants).
    Supports reverse home/away (feed home vs domain away, feed away vs domain home).

    When sport / category / competition are already mapped on the feed row, candidates are restricted
    to domain events in that scope so scores reflect teams (and kickoff), not fuzzy competition strings
    across unrelated leagues.
    """
    if not DOMAIN_EVENTS:
        return []
    feed_home = (feed_event.get("raw_home_name") or "").strip()
    feed_away = (feed_event.get("raw_away_name") or "").strip()
    feed_comp = (feed_event.get("raw_league_name") or "").strip()
    feed_start = (feed_event.get("start_time") or "").strip()
    if not feed_home and not feed_away:
        return []

    pool: list[dict] = list(DOMAIN_EVENTS)
    dsid = fid_str(domain_sport_id) if domain_sport_id not in (None, "") else ""
    if dsid:
        pool = [ev for ev in pool if _domain_event_row_matches_domain_sport(ev, dsid)]
    dcat = fid_str(domain_category_id) if domain_category_id not in (None, "") else ""
    if dcat:
        pool = [ev for ev in pool if entity_ids_equal(ev.get("category_id"), dcat)]
    dcomp = fid_str(domain_competition_id) if domain_competition_id not in (None, "") else ""
    if dcomp:
        pool = [ev for ev in pool if _domain_event_matches_competition_scope(ev, dcomp, feed_comp)]

    scoped_comp = bool(dcomp)
    scoped_cat_only = bool(dcat and not dcomp)

    candidates: list[dict] = []
    for ev in pool:
        d_home = (ev.get("home") or "").strip()
        d_away = (ev.get("away") or "").strip()
        d_comp = (ev.get("competition") or "").strip()
        d_start = (ev.get("start_time") or "").strip()
        if feed_start and d_start and _domain_event_start_times_equivalent(feed_start, d_start):
            s_time = 100
        elif feed_start and d_start:
            s_time = 50
        else:
            s_time = 100
        # Normal: feed_home↔domain_home, feed_away↔domain_away
        s_home_n = _fuzzy_score(feed_home, d_home) if feed_home and d_home else (100 if not feed_home and not d_home else 0)
        s_away_n = _fuzzy_score(feed_away, d_away) if feed_away and d_away else (100 if not feed_away and not d_away else 0)
        # Reversed: feed_home↔domain_away, feed_away↔domain_home
        s_home_r = _fuzzy_score(feed_home, d_away) if feed_home and d_away else (100 if not feed_home and not d_away else 0)
        s_away_r = _fuzzy_score(feed_away, d_home) if feed_away and d_home else (100 if not feed_away and not d_home else 0)

        if scoped_comp:
            # League already fixed by mapping — score only teams + kickoff (no cross-league comp fuzz).
            score_n = int(round(0.46 * s_home_n + 0.46 * s_away_n + 0.08 * s_time))
            score_r = int(round(0.46 * s_home_r + 0.46 * s_away_r + 0.08 * s_time))
        elif scoped_cat_only:
            s_comp = _fuzzy_score(feed_comp, d_comp) if feed_comp or d_comp else 100
            score_n = int(round(0.38 * s_home_n + 0.38 * s_away_n + 0.19 * s_comp + 0.05 * s_time))
            score_r = int(round(0.38 * s_home_r + 0.38 * s_away_r + 0.19 * s_comp + 0.05 * s_time))
        else:
            s_comp = _fuzzy_score(feed_comp, d_comp) if feed_comp or d_comp else 100
            w_h, w_a, w_c, w_t = (0.40, 0.40, 0.15, 0.05)
            score_n = int(round(w_h * s_home_n + w_a * s_away_n + w_c * s_comp + w_t * s_time))
            score_r = int(round(w_h * s_home_r + w_a * s_away_r + w_c * s_comp + w_t * s_time))

        best_score = max(score_n, score_r)
        # When league is already fixed, allow slightly weaker team-string matches (short names / acronyms).
        min_score = 45 if scoped_comp else 50
        if best_score >= min_score:
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

def _resolve_team_country_for_create(body: CreateEntityRequest, sport_id: Optional[str]) -> str:
    """
    Use explicit country from the client when set.
    Otherwise infer from domain category/competition already in scope (e.g. England category with GB
    so teams created from the mapping modal inherit country even if the country dropdown stayed on None).
    """
    explicit = (body.country or "").strip() or COUNTRY_CODE_NONE
    if explicit != COUNTRY_CODE_NONE:
        return explicit
    if not sport_id:
        return COUNTRY_CODE_NONE
    cat_nm = (body.category or "").strip()
    if cat_nm:
        cat_row = next(
            (
                c
                for c in DOMAIN_ENTITIES.get("categories", [])
                if entity_ids_equal(c.get("sport_id"), sport_id)
                and (c.get("name") or "").strip().lower() == cat_nm.lower()
            ),
            None,
        )
        if cat_row:
            cc = (cat_row.get("country") or "").strip() or COUNTRY_CODE_NONE
            if cc != COUNTRY_CODE_NONE:
                return cc
    comp_nm = (body.competition or "").strip()
    if comp_nm:
        comp_row = next(
            (
                c
                for c in DOMAIN_ENTITIES.get("competitions", [])
                if entity_ids_equal(c.get("sport_id"), sport_id)
                and (c.get("name") or "").strip().lower() == comp_nm.lower()
            ),
            None,
        )
        if comp_row:
            cid = comp_row.get("category_id")
            if cid:
                cat_row2 = next(
                    (c for c in DOMAIN_ENTITIES.get("categories", []) if entity_ids_equal(c.get("domain_id"), cid)),
                    None,
                )
                if cat_row2:
                    cc = (cat_row2.get("country") or "").strip() or COUNTRY_CODE_NONE
                    if cc != COUNTRY_CODE_NONE:
                        return cc
            cc = (comp_row.get("country") or "").strip() or COUNTRY_CODE_NONE
            if cc != COUNTRY_CODE_NONE:
                return cc
    return COUNTRY_CODE_NONE


@app.post("/api/entities")
async def create_entity(request: Request, body: CreateEntityRequest):
    """
    Create a domain entity (sport/category/competition/team).
    Idempotent per type. Parent FKs are prefixed domain ids (S-/G-).
    """
    from fastapi import HTTPException
    bucket = DOMAIN_ENTITIES.get(body.entity_type)
    if bucket is None:
        raise HTTPException(status_code=400, detail=f"Unknown entity type: {body.entity_type}")
    _rbac_require_entity_perm(request, body.entity_type, "create")
    if body.entity_type == "sports":
        raise HTTPException(status_code=400, detail="Sports cannot be created from backoffice. Add them in code/data and map in entity feed mappings.")

    # Resolve parent FKs from names ─────────────────────────────────────────
    sport_id: Optional[str] = None
    category_id: Optional[str] = None

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
                   and entity_ids_equal(c.get("sport_id"), sport_id)), None)
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
            e = next((x for x in bucket if entity_ids_equal(x["domain_id"], already_mapped["domain_id"])), None)
            if e:
                # Only treat as "already mapped" if the entity is for the same sport (and category for competitions)
                if body.entity_type == "categories" and not entity_ids_equal(e.get("sport_id"), sport_id):
                    pass  # different sport → create new category with new id
                elif body.entity_type == "competitions" and (not entity_ids_equal(e.get("sport_id"), sport_id) or not nullable_fk_equal(e.get("category_id"), category_id)):
                    pass  # different sport/category → create new competition
                elif body.entity_type == "teams" and not entity_ids_equal(e.get("sport_id"), sport_id):
                    pass  # different sport → create new team
                else:
                    return {"domain_id": e["domain_id"], "name": e["name"], "created": False}

    # Deduplication: same name+sport (and category for comp) → link this feed to existing entity
    if body.entity_type == "sports":
        existing = next((e for e in bucket if e["name"].lower() == body.name.lower()), None)
    elif body.entity_type == "markets":
        existing = next((e for e in bucket if entity_ids_equal(e.get("sport_id"), sport_id) and (e.get("name") or "").strip().lower() == (body.name or "").strip().lower()), None)
    elif body.entity_type == "categories":
        existing = next((e for e in bucket if entity_ids_equal(e.get("sport_id"), sport_id)
                         and e["name"].lower() == body.name.lower()), None)
    elif body.entity_type == "competitions":
        existing = next((e for e in bucket if entity_ids_equal(e.get("sport_id"), sport_id)
                         and nullable_fk_equal(e.get("category_id"), category_id)
                         and e["name"].lower() == body.name.lower()), None)
    else:  # teams
        existing = next((e for e in bucket if entity_ids_equal(e.get("sport_id"), sport_id)
                         and e["name"].lower() == body.name.lower()), None)

    if existing and body.entity_type in ("categories", "competitions", "teams", "markets") and body.feed_id and body.feed_provider_id:
        # Link this feed to the existing domain entity (multi-feed reference)
        already_in_mappings = any(
            m["entity_type"] == body.entity_type and entity_ids_equal(m["domain_id"], existing["domain_id"])
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

    if body.entity_type in ("categories", "competitions", "teams", "markets"):
        entity["active"] = True

    if body.entity_type in ("sports", "markets"):
        pass  # name only for sports; markets have code and sport_id set above
    elif body.entity_type in ("categories", "teams"):
        entity["sport_id"] = sport_id
        if body.entity_type == "teams":
            entity["country"] = _resolve_team_country_for_create(body, sport_id)
        else:
            entity["country"] = (body.country or "").strip() or COUNTRY_CODE_NONE
        if body.entity_type == "teams":
            entity["underage_category_id"] = body.underage_category_id
            entity["participant_type_id"] = body.participant_type_id
            entity["is_amateur"] = bool(body.is_amateur) if body.is_amateur is not None else False
    elif body.entity_type == "competitions":
        entity["sport_id"]         = sport_id
        entity["category_id"]      = category_id
        entity["country"] = (body.country or "").strip() or COUNTRY_CODE_NONE
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
    if body.entity_type in ("categories", "competitions", "teams", "markets"):
        save_row["active"] = "1"
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
async def update_entity_name(request: Request, body: UpdateEntityNameRequest):
    """
    Rename an existing domain entity (sports/categories/competitions/teams) from the Entities UI.
    Only the display name (and updated_at) is changed; relationships stay the same.
    """
    from fastapi import HTTPException

    allowed_types = ("sports", "categories", "competitions", "teams")
    if body.entity_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Renaming is only supported for sports, categories, competitions, and teams.")
    _entity_tab_edit_perm = {
        "sports": "entity.sport.edit",
        "categories": "entity.category.edit",
        "competitions": "entity.competition.edit",
        "teams": "entity.team.edit",
    }
    _rbac_require_permission_code(request, _entity_tab_edit_perm[body.entity_type])

    new_name = (body.name or "").strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="Name is required")

    bucket = DOMAIN_ENTITIES.get(body.entity_type) or []
    entity = next((e for e in bucket if entity_ids_equal(e["domain_id"], body.domain_id)), None)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    old_name = (entity.get("name") or "").strip()
    _now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
    country_val: str | None = None
    baseid_val: str | None = None

    if body.entity_type in ("categories", "competitions", "teams") and body.country is not None:
        country_val = (body.country or "").strip() or COUNTRY_CODE_NONE
        entity["country"] = country_val

    if body.entity_type in ("sports", "categories", "competitions", "teams") and body.baseid is not None:
        baseid_val = (body.baseid or "").strip()
        if baseid_val:
            other = next((e for e in bucket if not entity_ids_equal(e["domain_id"], body.domain_id) and (e.get("baseid") or "").strip() == baseid_val), None)
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
        country=country_val,
        baseid=baseid_val,
        participant_type_id=body.participant_type_id if body.entity_type == "teams" else None,
        underage_category_id=body.underage_category_id if body.entity_type in ("teams", "competitions") else None,
        is_amateur=body.is_amateur if body.entity_type in ("teams", "competitions") else None,
    )

    for m in ENTITY_FEED_MAPPINGS:
        if m["entity_type"] == body.entity_type and entity_ids_equal(m["domain_id"], body.domain_id):
            m["domain_name"] = new_name

    # Update domain_events.csv when competition or category is renamed (they store names, not IDs)
    if body.entity_type in ("competitions", "categories", "sports") and old_name != new_name:
        _update_domain_events_entity_name(body.entity_type, old_name, new_name)
        # Reload DOMAIN_EVENTS so Event Navigator shows updated names immediately
        global DOMAIN_EVENTS
        DOMAIN_EVENTS = _load_domain_events()

    return {"domain_id": body.domain_id, "name": new_name, "country": country_val, "baseid": baseid_val}


@app.post("/api/entities/country")
async def update_entity_country(request: Request, body: UpdateEntityCountryRequest):
    """Update country (ISO code or '-') for a category, competition, or team."""
    from fastapi import HTTPException

    if body.entity_type not in ("categories", "competitions", "teams"):
        raise HTTPException(status_code=400, detail="Country is only supported for categories, competitions, and teams.")
    _country_edit_perm = {
        "categories": "entity.category.edit",
        "competitions": "entity.competition.edit",
        "teams": "entity.team.edit",
    }
    _rbac_require_permission_code(request, _country_edit_perm[body.entity_type])

    country = (body.country or "").strip() or COUNTRY_CODE_NONE
    bucket = DOMAIN_ENTITIES.get(body.entity_type) or []
    entity = next((e for e in bucket if entity_ids_equal(e["domain_id"], body.domain_id)), None)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found.")

    _now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
    entity["country"] = country
    entity["updated_at"] = _now
    _update_entity_country(body.entity_type, body.domain_id, country, _now)
    return {"domain_id": body.domain_id, "country": country}


@app.get("/api/entities/markets/{domain_id:path}")
async def get_market(request: Request, domain_id: str):
    """Return a single market by domain_id for edit form."""
    from fastapi import HTTPException

    _rbac_require_entity_perm(request, "markets", "view")
    bucket = DOMAIN_ENTITIES.get("markets") or []
    entity = next((e for e in bucket if entity_ids_equal(e["domain_id"], domain_id)), None)
    if not entity:
        raise HTTPException(status_code=404, detail="Market not found.")
    return entity


@app.patch("/api/entities/markets/{domain_id:path}")
async def update_market(request: Request, domain_id: str, body: UpdateMarketRequest):
    """Update a market type by domain_id. All fields optional."""
    from fastapi import HTTPException

    _rbac_require_entity_perm(request, "markets", "update")
    bucket = DOMAIN_ENTITIES.get("markets") or []
    entity = next((e for e in bucket if entity_ids_equal(e["domain_id"], domain_id)), None)
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
    if body.active is not None:
        kwargs["active"] = body.active

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


def _resolve_domain_sport_id_for_entity_mapping(domain_ev: dict, feeder_ev: dict, feed_pid: int | None) -> str | None:
    """
    Domain sport id for linking feeder IDs to entity_feed_mappings.
    Prefer domain event sport name; then feed sport_id alias; then feeder display sport (Soccer/Football).
    """
    sport_name = (domain_ev.get("sport") or "").strip()
    if sport_name:
        sport_ent = next(
            (s for s in DOMAIN_ENTITIES["sports"] if (s.get("name") or "").strip().lower() == sport_name.lower()),
            None,
        )
        if sport_ent:
            return sport_ent["domain_id"]
    if feed_pid is not None:
        r = _resolve_sport_alias(feed_pid, feeder_ev.get("sport_id"))
        if r:
            return r["domain_id"]
        fs = (feeder_ev.get("sport") or "").strip()
        if fs:
            sport_ent2 = next(
                (s for s in DOMAIN_ENTITIES["sports"] if (s.get("name") or "").strip().lower() == fs.lower()),
                None,
            )
            if sport_ent2:
                return sport_ent2["domain_id"]
            if fs.lower() == "soccer":
                sport_ent3 = next(
                    (s for s in DOMAIN_ENTITIES["sports"] if (s.get("name") or "").strip().lower() == "football"),
                    None,
                )
                if sport_ent3:
                    return sport_ent3["domain_id"]
            if fs.lower() == "football":
                sport_ent3 = next(
                    (s for s in DOMAIN_ENTITIES["sports"] if (s.get("name") or "").strip().lower() == "soccer"),
                    None,
                )
                if sport_ent3:
                    return sport_ent3["domain_id"]
    return None


def _sync_entity_feed_mappings_from_feeder_domain(domain_ev: dict, feeder_ev: dict | None, feeder_provider: str) -> None:
    """
    After a feeder event is mapped to a domain event, persist feed IDs on sports/categories/competitions/teams
    so Entities and Feeder Events green checks see bwin (etc.) mappings.
    """
    if not feeder_ev:
        return
    feed_obj = next((f for f in FEEDS if (f.get("code") or "").lower() == (feeder_provider or "").lower()), None)
    feed_pid = int(feed_obj["domain_id"]) if feed_obj else None
    if feed_pid is None:
        return
    sport_domain_id = _resolve_domain_sport_id_for_entity_mapping(domain_ev, feeder_ev, feed_pid)
    _raw_sport_id = feeder_ev.get("sport_id")
    if sport_domain_id and (_raw_sport_id not in (None, "") or (feeder_ev.get("sport") or "").strip()):
        _feed_sport_val = str(_raw_sport_id).strip() if _raw_sport_id not in (None, "") else (feeder_ev.get("sport") or "").strip()
        if _feed_sport_val:
            _ensure_entity_feed_mapping("sports", sport_domain_id, feed_pid, _feed_sport_val)
    cat_name = (domain_ev.get("category") or "").strip()
    category_domain_id = None
    if sport_domain_id and cat_name:
        cat_ent = next(
            (
                c
                for c in DOMAIN_ENTITIES["categories"]
                if entity_ids_equal(c.get("sport_id"), sport_domain_id)
                and (c.get("name") or "").strip().lower() == cat_name.lower()
            ),
            None,
        )
        category_domain_id = cat_ent["domain_id"] if cat_ent else None
    if category_domain_id:
        feed_cat_id = (feeder_ev.get("category_id") or feeder_ev.get("category") or "").strip() or None
        if feed_cat_id:
            _ensure_entity_feed_mapping("categories", category_domain_id, feed_pid, feed_cat_id)
    comp_name = (domain_ev.get("competition") or "").strip()
    competition_domain_id = None
    if sport_domain_id and comp_name:
        comp_l = comp_name.lower()
        candidates = [
            c
            for c in DOMAIN_ENTITIES["competitions"]
            if (c.get("name") or "").strip().lower() == comp_l and entity_ids_equal(c.get("sport_id"), sport_domain_id)
        ]
        comp_ent = None
        if category_domain_id:
            comp_ent = next(
                (c for c in candidates if entity_ids_equal(c.get("category_id"), category_domain_id)),
                None,
            )
        if comp_ent is None and len(candidates) == 1:
            comp_ent = candidates[0]
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
        raw_id = domain_ev.get(team_key)
        if raw_id is not None and str(raw_id).strip():
            rs = str(raw_id).strip()
            team_domain_id = next(
                (t["domain_id"] for t in DOMAIN_ENTITIES["teams"] if fid_str(t["domain_id"]) == rs),
                None,
            )
        if team_domain_id is None and sport_domain_id is not None:
            team_name = (domain_ev.get(name_key) or "").strip()
            if team_name:
                team_name_norm = _normalize(team_name)
                team_ent = next(
                    (
                        t
                        for t in DOMAIN_ENTITIES["teams"]
                        if entity_ids_equal(t.get("sport_id"), sport_domain_id)
                        and _normalize(t.get("name") or "") == team_name_norm
                    ),
                    None,
                )
                if team_ent:
                    team_domain_id = team_ent["domain_id"]
        feed_team_id_raw = feeder_ev.get(feed_id_key) or feeder_ev.get(feed_name_key)
        feed_team_id = (str(feed_team_id_raw).strip() if feed_team_id_raw is not None else "") or None
        if team_domain_id is not None and feed_team_id:
            _ensure_entity_feed_mapping("teams", team_domain_id, feed_pid, feed_team_id)


def _feeder_config_value_for_setting_key(feed_pid: int, sid: Any, cid: Any, comp_id: Any, setting_key: str) -> str:
    """Most specific matching scope wins; returns 'Yes' or 'No' (default No)."""
    sk = (setting_key or "").strip()
    rows = _load_feeder_config()
    best_rank = -1
    best_val = "No"
    rank_order = {"competition": 3, "category": 2, "sport": 1, "all_sports": 0}
    for r in rows:
        if (r.get("setting_key") or "").strip() != sk:
            continue
        try:
            if int(r.get("feed_provider_id") or -1) != int(feed_pid):
                continue
        except (TypeError, ValueError):
            continue
        lvl = (r.get("level") or "").strip()
        if lvl == "league":
            lvl = "competition"
        rsid, rcid, rcomp = r.get("sport_id"), r.get("category_id"), r.get("competition_id")
        empty = lambda x: x is None or str(x).strip() == ""
        applies = False
        if lvl == "all_sports":
            applies = empty(rsid) and empty(rcid) and empty(rcomp)
        elif lvl == "sport" and sid is not None:
            applies = entity_ids_equal(rsid, sid) and empty(rcid) and empty(rcomp)
        elif lvl == "category" and sid is not None and cid is not None:
            applies = entity_ids_equal(rsid, sid) and entity_ids_equal(rcid, cid) and empty(rcomp)
        elif lvl == "competition" and sid is not None and cid is not None and comp_id is not None:
            applies = entity_ids_equal(rsid, sid) and entity_ids_equal(rcid, cid) and entity_ids_equal(rcomp, comp_id)
        if not applies:
            continue
        rk = rank_order.get(lvl, -1)
        if rk > best_rank:
            best_rank = rk
            best_val = _feeder_config_yes_no_value(r.get("value"))
    return best_val


def _feeder_config_value_auto_create_events(feed_pid: int, sid: Any, cid: Any, comp_id: Any) -> str:
    """Most specific matching scope wins; returns 'Yes' or 'No' (default No)."""
    return _feeder_config_value_for_setting_key(feed_pid, sid, cid, comp_id, "auto_create_events")


def _feeder_config_value_auto_map_events(feed_pid: int, sid: Any, cid: Any, comp_id: Any) -> str:
    """Same scope rules as auto_create_events; separate setting key."""
    return _feeder_config_value_for_setting_key(feed_pid, sid, cid, comp_id, "auto_map_events")


def _feeder_domain_scope_ids_for_config(feeder_ev: dict, feed_pid: int) -> tuple[Any, Any, Any]:
    """Domain (sport_id, category_id, competition_id) for feeder config scope matching."""
    dsid = _resolve_domain_sport_id_for_entity_mapping(
        {"sport": (feeder_ev.get("sport") or "").strip(), "category": "", "competition": ""},
        feeder_ev,
        feed_pid,
    )
    cid = None
    comp_id = None
    cat_cell = (feeder_ev.get("category") or "").strip()
    raw_lid = str(feeder_ev.get("raw_league_id") or "").strip()
    if dsid and raw_lid:
        comp_res = _resolve_entity("competitions", raw_lid, feed_pid, domain_sport_id=dsid)
        if isinstance(comp_res, dict) and comp_res.get("domain_id") is not None:
            comp_id = comp_res["domain_id"]
            cid = comp_res.get("category_id")
    if dsid and cat_cell and not cat_cell.upper().startswith("COMP:"):
        cat_ent = next(
            (
                c
                for c in DOMAIN_ENTITIES["categories"]
                if entity_ids_equal(c.get("sport_id"), dsid) and (c.get("name") or "").strip().lower() == cat_cell.lower()
            ),
            None,
        )
        if cat_ent:
            cid = cat_ent["domain_id"]
    comp_name = (feeder_ev.get("raw_league_name") or "").strip()
    if dsid and comp_id is None and comp_name:
        comp_l = comp_name.lower()
        candidates = [
            c
            for c in DOMAIN_ENTITIES["competitions"]
            if (c.get("name") or "").strip().lower() == comp_l and entity_ids_equal(c.get("sport_id"), dsid)
        ]
        comp_ent = None
        if cid:
            comp_ent = next((c for c in candidates if entity_ids_equal(c.get("category_id"), cid)), None)
        if comp_ent is None and len(candidates) == 1:
            comp_ent = candidates[0]
        if comp_ent is None:
            pool = [c for c in DOMAIN_ENTITIES["competitions"] if entity_ids_equal(c.get("sport_id"), dsid)]
            if cid:
                pool = [c for c in pool if entity_ids_equal(c.get("category_id"), cid)]
            best_c = None
            best_sc = -1
            for c in pool:
                cn = (c.get("name") or "").strip().lower()
                if not cn:
                    continue
                sc = _fuzzy_score(comp_l, cn)
                if sc > best_sc:
                    best_sc = sc
                    best_c = c
            if best_c is not None and best_sc >= 90:
                comp_ent = best_c
        if comp_ent:
            comp_id = comp_ent["domain_id"]
    return dsid, cid, comp_id


def _resolve_domain_sport_id_from_domain_event_sport_display(sport_display: str | None) -> Any:
    """Resolve domain_events.sport text to sports.domain_id; treats Soccer/Football as aliases when both names exist."""
    if not sport_display or not str(sport_display).strip():
        return None
    sl = str(sport_display).strip().lower()
    for ent in DOMAIN_ENTITIES["sports"]:
        if (ent.get("name") or "").strip().lower() == sl:
            return ent["domain_id"]
    if sl == "soccer":
        for ent in DOMAIN_ENTITIES["sports"]:
            if (ent.get("name") or "").strip().lower() == "football":
                return ent["domain_id"]
    if sl == "football":
        for ent in DOMAIN_ENTITIES["sports"]:
            if (ent.get("name") or "").strip().lower() == "soccer":
                return ent["domain_id"]
    return None


def _normalize_league_label_for_compare(s: str) -> str:
    """1xbet-style 'England. Premier League' → tokens comparable to domain 'Premier League' / 'England Premier League'."""
    t = (s or "").strip().casefold().replace(".", " ")
    return " ".join(t.split())


def _competition_labels_match_auto_map(feed_norm: str, domain_norm: str) -> bool:
    """League label match after normalizing dots/spaces; suffix, containment, or fuzzy."""
    fn = _normalize_league_label_for_compare(feed_norm) if feed_norm else ""
    dn = _normalize_league_label_for_compare(domain_norm) if domain_norm else ""
    if not fn or not dn:
        return False
    if fn == dn:
        return True
    if len(dn) >= 6 and fn.endswith(dn):
        return True
    if len(fn) >= 6 and dn.endswith(fn):
        return True
    if len(dn) >= 8 and dn in fn:
        return True
    if len(fn) >= 8 and fn in dn:
        return True
    return _fuzzy_score(fn, dn) >= 92


def _feed_domain_category_aligned_for_auto_map(feed_cat: str, dcat: str) -> bool:
    """Align optional feed category label with domain event category when both are present; if feed has no category, pass."""
    fc = (feed_cat or "").strip().casefold()
    dc = (dcat or "").strip().casefold()
    if not fc or not dc:
        return True
    if fc == dc:
        return True
    if fc.startswith("comp:") or dc.startswith("comp:"):
        return True
    if "." in fc:
        first = fc.split(".")[0].strip()
        if first == dc or fc.startswith(dc + ".") or (len(dc) >= 3 and first.startswith(dc)):
            return True
    fn = _normalize_league_label_for_compare(fc)
    dn = _normalize_league_label_for_compare(dc)
    if fn == dn or (len(dn) >= 4 and dn in fn) or (len(fn) >= 4 and fn in dn):
        return True
    return False


def _lookup_team_domain_id_by_exact_name(name: str | None, sport_domain_id: Any) -> str | None:
    """Resolve P-* from team display name within sport (exact name, case-insensitive)."""
    nm = (name or "").strip()
    if not nm or sport_domain_id is None or str(sport_domain_id).strip() == "":
        return None
    nml = nm.casefold()
    for t in DOMAIN_ENTITIES.get("teams", []):
        if not entity_ids_equal(t.get("sport_id"), sport_domain_id):
            continue
        if (t.get("name") or "").strip().casefold() == nml:
            tid = str(t.get("domain_id") or "").strip()
            return tid or None
    return None


def _domain_event_resolved_team_pair_ids(domain_ev: dict, sport_domain_id: Any) -> tuple[str, str]:
    """Home/away P-* from domain event row; missing CSV ids filled by exact entity name under sport."""
    hid = str(domain_ev.get("home_id") or "").strip()
    aid = str(domain_ev.get("away_id") or "").strip()
    if not hid:
        hid = _lookup_team_domain_id_by_exact_name(domain_ev.get("home"), sport_domain_id) or ""
    if not aid:
        aid = _lookup_team_domain_id_by_exact_name(domain_ev.get("away"), sport_domain_id) or ""
    return hid, aid


def _domain_event_resolved_category_competition_ids(domain_ev: dict, sport_domain_id: Any) -> tuple[str | None, str | None]:
    """Category / competition domain ids from CSV or exact entity name under sport."""
    cid = str(domain_ev.get("category_id") or "").strip() or None
    compid = str(domain_ev.get("competition_id") or "").strip() or None
    if not cid:
        cn = (domain_ev.get("category") or "").strip()
        if cn and sport_domain_id:
            for c in DOMAIN_ENTITIES.get("categories", []):
                if entity_ids_equal(c.get("sport_id"), sport_domain_id) and (c.get("name") or "").strip().casefold() == cn.casefold():
                    cid = str(c.get("domain_id") or "").strip() or None
                    break
    if not compid:
        cpn = (domain_ev.get("competition") or "").strip()
        if cpn and sport_domain_id:
            pool = [x for x in DOMAIN_ENTITIES.get("competitions", []) if entity_ids_equal(x.get("sport_id"), sport_domain_id)]
            if cid:
                pool = [x for x in pool if entity_ids_equal(x.get("category_id"), cid)]
            for c in pool:
                if (c.get("name") or "").strip().casefold() == cpn.casefold():
                    compid = str(c.get("domain_id") or "").strip() or None
                    break
    return cid, compid


# Auto-map only: allow small clock skew between feed API timestamps and domain_events.csv (e.g. UTC vs published local).
_AUTO_MAP_START_TIME_MAX_DELTA_SEC = 3 * 3600


def _event_start_times_match_auto_map(a: str, b: str) -> bool:
    """Same kickoff to the minute, or same calendar date with naive times within _AUTO_MAP_START_TIME_MAX_DELTA_SEC."""
    sa, sb = (a or "").strip(), (b or "").strip()
    if bool(sa) != bool(sb):
        return False
    if not sa:
        return True
    if len(sa) >= 16 and len(sb) >= 16 and sa[:16] == sb[:16]:
        return True
    if sa == sb:
        return True
    if len(sa) >= 16 and len(sb) >= 16 and sa[:10] == sb[:10]:
        try:
            ta = datetime.strptime(sa[:16], "%Y-%m-%d %H:%M")
            tb = datetime.strptime(sb[:16], "%Y-%m-%d %H:%M")
            if abs((ta - tb).total_seconds()) <= _AUTO_MAP_START_TIME_MAX_DELTA_SEC:
                return True
        except ValueError:
            pass
    return False


def _explain_auto_map_feed_vs_domain_row(feeder_ev: dict, feed_pid: int, domain_ev: dict, swapped: bool) -> dict:
    """Structured checklist for auto-map rule evaluation (same as _domain_event_row_matches_feed_for_auto_map)."""
    dsid = _resolve_domain_sport_id_for_entity_mapping({"sport": ""}, feeder_ev, feed_pid)
    ev_dsid = _resolve_domain_sport_id_from_domain_event_sport_display(domain_ev.get("sport"))
    sport_ok = bool(dsid and entity_ids_equal(ev_dsid, dsid))

    def norm(x: Any) -> str:
        return (str(x) if x is not None else "").strip().casefold()

    feed_comp_name = norm(feeder_ev.get("raw_league_name"))
    feed_cat_cell = (feeder_ev.get("category") or "").strip()
    feed_start = (feeder_ev.get("start_time") or "").strip()
    _, feed_cid, feed_comp_id = _feeder_domain_scope_ids_for_config(feeder_ev, feed_pid)
    dom_cid, dom_comp_id = _domain_event_resolved_category_competition_ids(domain_ev, ev_dsid)

    if feed_comp_id is not None and str(feed_comp_id).strip() and dom_comp_id:
        comp_ok = entity_ids_equal(feed_comp_id, dom_comp_id)
        comp_mode = "id"
    else:
        comp_ok = _competition_labels_match_auto_map(feed_comp_name, norm(domain_ev.get("competition")))
        comp_mode = "label_fallback"

    if feed_cid is not None and str(feed_cid).strip() and dom_cid:
        cat_ok = entity_ids_equal(feed_cid, dom_cid)
        cat_mode = "id"
    else:
        cat_ok = _feed_domain_category_aligned_for_auto_map(feed_cat_cell, domain_ev.get("category"))
        cat_mode = "label_fallback"

    ds = (domain_ev.get("start_time") or "").strip()
    time_ok = _event_start_times_match_auto_map(feed_start, ds)

    fh, fa = _resolve_domain_team_ids_for_feed_row(feeder_ev, feed_pid)
    dh, da = _domain_event_resolved_team_pair_ids(domain_ev, ev_dsid)
    teams_resolved = bool(fh and fa and dh and da)
    if swapped:
        pair_ok = bool(teams_resolved and entity_ids_equal(fh, da) and entity_ids_equal(fa, dh))
    else:
        pair_ok = bool(teams_resolved and entity_ids_equal(fh, dh) and entity_ids_equal(fa, da))

    return {
        "swapped": swapped,
        "sport_ok": sport_ok,
        "category_ok": cat_ok,
        "category_mode": cat_mode,
        "competition_ok": comp_ok,
        "competition_mode": comp_mode,
        "time_ok": time_ok,
        "teams_resolved": teams_resolved,
        "team_pair_ok": pair_ok,
        "resolved_feed_home_id": fh or None,
        "resolved_feed_away_id": fa or None,
        "resolved_domain_home_id": dh or None,
        "resolved_domain_away_id": da or None,
        "feed_start_time": feed_start,
        "domain_start_time": ds,
        "scope_feed_category_id": str(feed_cid) if feed_cid is not None and str(feed_cid).strip() else None,
        "scope_feed_competition_id": str(feed_comp_id) if feed_comp_id is not None and str(feed_comp_id).strip() else None,
        "domain_category_id": dom_cid,
        "domain_competition_id": dom_comp_id,
        "match": bool(sport_ok and comp_ok and cat_ok and time_ok and teams_resolved and pair_ok),
    }


def _domain_event_row_matches_feed_for_auto_map(
    feeder_ev: dict, feed_pid: int, dsid: Any, domain_ev: dict, swapped: bool
) -> bool:
    """True if domain_ev is the same fixture as feeder_ev (sport, scope, kickoff, team P-* ids)."""
    if not dsid:
        return False
    return bool(_explain_auto_map_feed_vs_domain_row(feeder_ev, feed_pid, domain_ev, swapped)["match"])


def _collect_domain_events_auto_map_candidates(feeder_ev: dict, feed_pid: int, feed_provider_code: str) -> list[dict]:
    """Domain events that match this feeder row on sport/scope/time/team ids.

    A domain row may already have another valid_id from the same feed (e.g. duplicate API rows); we still
    consider it so we map here instead of creating a second E-*.
    """
    dsid = _resolve_domain_sport_id_for_entity_mapping({"sport": ""}, feeder_ev, feed_pid)
    if not dsid:
        return []
    matches: list[dict] = []
    for ev in DOMAIN_EVENTS:
        eid = str(ev.get("id") or "").strip()
        if not eid:
            continue
        if _domain_event_row_matches_feed_for_auto_map(feeder_ev, feed_pid, dsid, ev, False) or _domain_event_row_matches_feed_for_auto_map(
            feeder_ev, feed_pid, dsid, ev, True
        ):
            matches.append(ev)
    return matches


def _domain_event_id_sort_key_for_pick(ev: dict) -> tuple:
    """Sort key for choosing among multiple matching domain events: lowest numeric E-* suffix (E-97 before E-200)."""
    eid = str(ev.get("id") or "").strip()
    m = re.match(r"^E-(\d+)$", eid, re.IGNORECASE)
    if m:
        return (0, int(m.group(1)))
    return (1, eid.casefold())


def _find_domain_event_for_auto_map(feeder_ev: dict, feed_pid: int, feed_provider_code: str) -> dict | None:
    """
    Domain event that matches this feeder row: same domain sport, category/competition domain ids when
    resolvable (else label fallback), same kickoff, and same home/away team domain ids (P-*) from
    entity_feed_mappings — not display-name fuzzy matching. Swapped home/away allowed.
    Lowest numeric E-* suffix if several match (same fixture may already hold another feed valid_id for this provider).
    """
    matches = _collect_domain_events_auto_map_candidates(feeder_ev, feed_pid, feed_provider_code)
    if not matches:
        return None
    if len(matches) == 1:
        return matches[0]
    matches.sort(key=_domain_event_id_sort_key_for_pick)
    return matches[0]


def _apply_map_feed_row_to_existing_domain(
    feeder_ev: dict,
    domain_ev: dict,
    feed_provider_code: str,
    *,
    log_source: str = "auto_map",
) -> None:
    """Persist map-to-existing (same side effects as /api/map-event without HTML)."""
    domain_id = str(domain_ev.get("id") or "").strip()
    vid = str(feeder_ev.get("valid_id") or "").strip()
    fp = (feed_provider_code or "").strip()
    if not domain_id or not vid or not fp:
        return
    existing = _load_event_mappings()
    already = any(
        (m.get("feed_provider") or "").strip() == fp and str(m.get("feed_valid_id") or "").strip() == vid
        for m in existing
    )
    mapping_new = False
    if not already:
        _save_event_mapping(domain_id, fp, vid)
        mapping_new = True
    if config.BETSAPI_TOKEN and vid:
        asyncio.create_task(_fetch_and_save_event_details(fp, vid))
    if mapping_new:
        _record_feed_domain_mapping_link(fp, vid, domain_id, source=log_source)
    feeder_ev["mapping_status"] = "MAPPED"
    feeder_ev["domain_id"] = domain_id
    _sync_entity_feed_mappings_from_feeder_domain(domain_ev, feeder_ev, fp)
    _remove_valid_id_from_feed_dashboard_new(fp.lower(), vid)


def _run_auto_map_domain_events_for_feed(feed_provider_code: str) -> int:
    """
    Map unmapped feeder rows to existing domain events when auto_map_events is Yes for the scope,
    entities are fully mapped for the row, and exactly one domain fixture matches (names + time).
    """
    fp_lc = (feed_provider_code or "").strip().lower()
    feed_obj = next((f for f in FEEDS if (f.get("code") or "").lower() == fp_lc), None)
    if not feed_obj:
        return 0
    feed_pid = int(feed_obj["domain_id"])
    code = (feed_obj.get("code") or feed_provider_code).strip()
    total = 0
    for _ in range(40):
        mapped_this_pass = 0
        for e in list(DUMMY_EVENTS):
            if (e.get("feed_provider") or "").strip().lower() != fp_lc:
                continue
            if (e.get("mapping_status") or "") == "MAPPED":
                continue
            if (e.get("mapping_status") or "") == "IGNORED":
                continue
            if e.get("is_outright"):
                continue
            if not _feeder_event_fully_entity_mapped_for_auto(e, feed_pid):
                continue
            sid, cid, comp_id = _feeder_domain_scope_ids_for_config(e, feed_pid)
            if _feeder_config_value_auto_map_events(feed_pid, sid, cid, comp_id) != "Yes":
                continue
            domain_ev = _find_domain_event_for_auto_map(e, feed_pid, code)
            if not domain_ev:
                continue
            _apply_map_feed_row_to_existing_domain(e, domain_ev, code)
            mapped_this_pass += 1
            total += 1
        if mapped_this_pass == 0:
            break
    return total


def _run_auto_map_then_create_domain_events_for_feed(feed_provider_code: str) -> tuple[int, int]:
    """Run auto-map (config) first, then auto-create; create path maps to existing domain if unique match (no duplicate E-*)."""
    n_map = _run_auto_map_domain_events_for_feed(feed_provider_code)
    n_new, n_link = _run_auto_create_domain_events_for_feed(feed_provider_code)
    return n_map + n_link, n_new


# Shown after manual map/create success while auto-map/auto-create runs in the background (see _schedule_post_map_auto_map_then_create).
_POST_MAP_BACKGROUND_NOTE_HTML = (
    '<p class="text-slate-500 text-xs mt-3 max-w-sm leading-relaxed">'
    "If <strong>Auto map Events</strong> / <strong>Auto create Events</strong> are enabled for this feed, other eligible rows may still "
    "be processed in the background—refresh Feeder Events shortly to see updates.</p>"
)


def _schedule_post_map_auto_map_then_create(feed_provider: str) -> None:
    """Defer heavy auto-map/auto-create so Confirm Mapping / Create & Map respond immediately."""
    fp = (feed_provider or "").strip()
    if not fp:
        return

    async def _runner() -> None:
        try:
            await asyncio.to_thread(_run_auto_map_then_create_domain_events_for_feed, fp)
        except Exception:
            logging.getLogger("uvicorn.error").exception(
                "Background auto-map/auto-create failed for feed=%s", fp
            )
        finally:
            try:
                _invalidate_dashboard_feed_stats_cache()
            except Exception:
                logging.getLogger("uvicorn.error").exception(
                    "Dashboard cache invalidation after background auto-map failed feed=%s", fp
                )

    try:
        asyncio.get_running_loop().create_task(_runner())
    except RuntimeError:
        pass


def _resolve_domain_team_ids_for_feed_row(feeder_ev: dict, feed_pid: int) -> tuple[str, str]:
    """Resolve domain team ids (P-*) from feeder raw_home/raw_away id or name via entity_feed_mappings."""

    def one(raw: Any, name: str | None) -> str:
        if raw is not None and str(raw).strip():
            ent = _resolve_entity("teams", str(raw).strip(), feed_pid)
            if isinstance(ent, dict) and ent.get("domain_id") is not None:
                return str(ent["domain_id"]).strip()
        nm = (name or "").strip()
        if nm:
            ent = _resolve_entity("teams", nm, feed_pid)
            if isinstance(ent, dict) and ent.get("domain_id") is not None:
                return str(ent["domain_id"]).strip()
        return ""

    hid = one(feeder_ev.get("raw_home_id"), feeder_ev.get("raw_home_name"))
    aid = one(feeder_ev.get("raw_away_id"), feeder_ev.get("raw_away_name"))
    return hid, aid


def _feeder_event_fully_entity_mapped_for_auto(feeder_ev: dict, feed_pid: int) -> bool:
    """Sport, competition and both teams resolve to mapped domain entities for this feed (feed category optional)."""
    if feeder_ev.get("is_outright"):
        return False
    if _resolve_sport_alias(feed_pid, feeder_ev.get("sport_id")) is None and _resolve_sport_alias(feed_pid, feeder_ev.get("sport") or "") is None:
        return False
    if not _feeder_event_feed_competition_mapped(feeder_ev, feed_pid):
        return False
    if not _feeder_event_team_side_mapped(feeder_ev, "home", feed_pid):
        return False
    if not _feeder_event_team_side_mapped(feeder_ev, "away", feed_pid):
        return False
    return True


def _create_and_map_domain_event_from_feed_row(feeder_ev: dict, feeder_provider_code: str) -> str | None:
    """Create domain event + mapping + entity_feed sync for one feeder row (used by auto-create). Returns new E-id or None
    if domain sport or both team P-* ids cannot be resolved from the feed row."""
    feed_obj = next((f for f in FEEDS if (f.get("code") or "").lower() == (feeder_provider_code or "").lower()), None)
    feed_pid = int(feed_obj["domain_id"]) if feed_obj else None
    if feed_pid is None:
        return None
    dsid = _resolve_domain_sport_id_for_entity_mapping(
        {"sport": (feeder_ev.get("sport") or "").strip(), "category": "", "competition": ""},
        feeder_ev,
        feed_pid,
    )
    if not dsid:
        return None
    hid, aid = _resolve_domain_team_ids_for_feed_row(feeder_ev, feed_pid)
    if not (hid and aid):
        return None
    sport_display = _sport_name(dsid)
    _, scope_cid, scope_comp_id = _feeder_domain_scope_ids_for_config(feeder_ev, feed_pid)
    new_id = next_event_domain_id(DOMAIN_EVENTS)
    new_event = {
        "id": new_id,
        "sport": sport_display,
        "category": (feeder_ev.get("category") or "").strip(),
        "competition": (feeder_ev.get("raw_league_name") or "").strip(),
        "home": (feeder_ev.get("raw_home_name") or "").strip(),
        "home_id": hid,
        "away": (feeder_ev.get("raw_away_name") or "").strip(),
        "away_id": aid,
        "start_time": (feeder_ev.get("start_time") or "").strip(),
        "sport_id": str(dsid).strip() if dsid not in (None, "") else "",
        "category_id": str(scope_cid).strip() if scope_cid not in (None, "") else "",
        "competition_id": str(scope_comp_id).strip() if scope_comp_id not in (None, "") else "",
    }
    DOMAIN_EVENTS.append(new_event)
    _save_domain_event(new_event)
    _save_event_mapping(new_id, feeder_provider_code, str(feeder_ev.get("valid_id")))
    if config.BETSAPI_TOKEN and feeder_ev.get("valid_id"):
        asyncio.create_task(_fetch_and_save_event_details(feeder_provider_code, str(feeder_ev.get("valid_id"))))
    feeder_ev["mapping_status"] = "MAPPED"
    feeder_ev["domain_id"] = new_id
    _sync_entity_feed_mappings_from_feeder_domain(new_event, feeder_ev, feeder_provider_code)
    _record_feed_domain_mapping_link(
        feeder_provider_code,
        str(feeder_ev.get("valid_id")),
        new_id,
        source="auto_create",
    )
    _remove_valid_id_from_feed_dashboard_new(feeder_provider_code, str(feeder_ev.get("valid_id")))
    return new_id


def _run_auto_create_domain_events_for_feed(feed_provider_code: str) -> tuple[int, int]:
    """
    After a manual map/create, for unmapped feed rows with auto_create_events Yes: if a unique domain fixture
    already exists (_find_domain_event_for_auto_map), map to it instead of creating a duplicate domain event.
    Returns (new_domain_events_created, feed_rows_linked_to_existing_domain).
    """
    fp_lc = (feed_provider_code or "").strip().lower()
    feed_obj = next((f for f in FEEDS if (f.get("code") or "").lower() == fp_lc), None)
    if not feed_obj:
        return 0, 0
    feed_pid = int(feed_obj["domain_id"])
    code = (feed_obj.get("code") or feed_provider_code).strip()
    created = 0
    linked = 0
    for _ in range(40):
        progressed = 0
        for e in list(DUMMY_EVENTS):
            if (e.get("feed_provider") or "").strip().lower() != fp_lc:
                continue
            if (e.get("mapping_status") or "") == "MAPPED":
                continue
            if (e.get("mapping_status") or "") == "IGNORED":
                continue
            if e.get("is_outright"):
                continue
            if not _feeder_event_fully_entity_mapped_for_auto(e, feed_pid):
                continue
            sid, cid, comp_id = _feeder_domain_scope_ids_for_config(e, feed_pid)
            if _feeder_config_value_auto_create_events(feed_pid, sid, cid, comp_id) != "Yes":
                continue
            dup_ev = _find_domain_event_for_auto_map(e, feed_pid, code)
            if dup_ev is not None:
                _apply_map_feed_row_to_existing_domain(e, dup_ev, code, log_source="auto_link")
                linked += 1
                progressed += 1
                continue
            nid = _create_and_map_domain_event_from_feed_row(e, code)
            if nid:
                created += 1
                progressed += 1
        if progressed == 0:
            break
    return created, linked


@app.post("/api/domain-events")
async def create_domain_event(body: CreateDomainEventRequest):
    """
    API Endpoint: Create a new domain event from feed data and auto-map the feeder event.
    """
    fp_lc = (body.feeder_provider or "").strip().lower()
    feed_obj = next((f for f in FEEDS if (f.get("code") or "").lower() == fp_lc), None)
    feed_pid = int(feed_obj["domain_id"]) if feed_obj else None
    feeder_ev = None
    for e in DUMMY_EVENTS:
        if (e.get("feed_provider") or "").strip().lower() == fp_lc and str(e.get("valid_id")) == str(body.feeder_valid_id):
            feeder_ev = e
            break

    hid = (body.home_id or "").strip() if body.home_id else ""
    aid = (body.away_id or "").strip() if body.away_id else ""
    if feeder_ev is not None and feed_pid is not None:
        rh, ra = _resolve_domain_team_ids_for_feed_row(feeder_ev, feed_pid)
        if not hid:
            hid = rh
        if not aid:
            aid = ra
    if not hid or not aid:
        return HTMLResponse("""
            <div class="p-6 text-center text-red-400 text-sm max-w-md mx-auto">
                <i class="fa-solid fa-triangle-exclamation mr-2"></i>
                Cannot create a domain event without both home and away team domain ids (P-*).
                Map the teams for this feed first, or ensure the modal sends home_id and away_id.
            </div>
        """)

    vid_s = str(body.feeder_valid_id or "").strip()
    for m in _load_event_mappings():
        if (m.get("feed_provider") or "").strip().lower() == fp_lc and str(m.get("feed_valid_id") or "").strip() == vid_s:
            prev_eid = str(m.get("domain_event_id") or "").strip()
            return HTMLResponse(f"""
            <div class="p-6 text-center text-amber-300 text-sm max-w-md mx-auto">
                <i class="fa-solid fa-link mr-2"></i>
                This feed row is already linked to domain event
                <span class="font-mono text-white">{prev_eid}</span>.
                Close the modal and open that event, or remove the mapping first if you meant to remap.
            </div>
            """)

    sid_csv, cat_csv, comp_csv = "", "", ""
    if feeder_ev is not None and feed_pid is not None:
        d0, c_v, co_v = _feeder_domain_scope_ids_for_config(feeder_ev, feed_pid)
        sid_csv = str(d0).strip() if d0 not in (None, "") else ""
        cat_csv = str(c_v).strip() if c_v not in (None, "") else ""
        comp_csv = str(co_v).strip() if co_v not in (None, "") else ""
    elif (body.sport or "").strip():
        r0 = _resolve_domain_sport_id_from_domain_event_sport_display(body.sport)
        sid_csv = str(r0).strip() if r0 not in (None, "") else ""

    dup_ev = _find_duplicate_domain_event_snapshot(
        sport_id=sid_csv,
        category_id=cat_csv,
        competition_id=comp_csv,
        home_id=hid,
        away_id=aid,
        start_time=body.start_time,
    )
    if dup_ev:
        deid = str(dup_ev.get("id") or "").strip()
        return HTMLResponse(f"""
            <div class="p-6 text-center text-amber-300 text-sm max-w-md mx-auto">
                <i class="fa-solid fa-clone mr-2"></i>
                A domain event with the same sport, scope, teams and start time already exists:
                <span class="font-mono text-white">{deid}</span>.
                Use <strong>Confirm Mapping</strong> to link this feed row to that event instead of creating a duplicate.
            </div>
            """)

    for m in _load_event_mappings():
        if (m.get("feed_provider") or "").strip().lower() == fp_lc and str(m.get("feed_valid_id") or "").strip() == vid_s:
            prev_eid = str(m.get("domain_event_id") or "").strip()
            return HTMLResponse(f"""
            <div class="p-6 text-center text-amber-300 text-sm max-w-md mx-auto">
                <i class="fa-solid fa-link mr-2"></i>
                This feed row was just linked to
                <span class="font-mono text-white">{prev_eid}</span> (another request may have completed first).
            </div>
            """)

    # Sequential domain event id (E-*), distinct from category ids (G-*)
    new_id = next_event_domain_id(DOMAIN_EVENTS)

    # Build the in-memory event dict (empty string for missing IDs so CSV and lookups work)
    new_event = {
        "id":              new_id,
        "sport":           body.sport,
        "category":        body.category,
        "competition":     body.competition,
        "home":            body.home,
        "home_id":         hid,
        "away":            body.away,
        "away_id":         aid,
        "start_time":      body.start_time,
        "sport_id":        sid_csv,
        "category_id":     cat_csv,
        "competition_id":  comp_csv,
    }
    DOMAIN_EVENTS.append(new_event)
    # Persist clean domain event to domain_events.csv
    _save_domain_event(new_event)
    # Record the originating feed mapping in event_mappings.csv (join table)
    _save_event_mapping(new_id, body.feeder_provider, body.feeder_valid_id)
    _record_feed_domain_mapping_link(body.feeder_provider, body.feeder_valid_id, new_id, source="manual_create")

    # Fetch event details in background (BetsAPI token from .env) so we have markets for mapping modal
    if config.BETSAPI_TOKEN and body.feeder_provider and body.feeder_valid_id:
        asyncio.create_task(_fetch_and_save_event_details(body.feeder_provider, body.feeder_valid_id))

    # Also mark the feeder event as MAPPED in memory; sync entity_feed_mappings (same as map-to-existing).
    if feeder_ev:
        feeder_ev["mapping_status"] = "MAPPED"
        feeder_ev["domain_id"] = new_id
        _sync_entity_feed_mappings_from_feeder_domain(new_event, feeder_ev, body.feeder_provider)

    _remove_valid_id_from_feed_dashboard_new(fp_lc, str(body.feeder_valid_id))

    _schedule_post_map_auto_map_then_create(body.feeder_provider)
    _invalidate_dashboard_feed_stats_cache()

    event_label = f"{body.home} vs {body.away}" if (body.home and body.away) else (body.home or "Outright Event")

    return HTMLResponse(f"""
        <div class="p-6 bg-slate-800 text-center flex flex-col items-center justify-center h-full">
            <div class="text-emerald-400 text-4xl mb-4"><i class="fa-solid fa-circle-check"></i></div>
            <h3 class="text-white text-lg font-medium">Domain Event Created &amp; Mapped!</h3>
            <p class="text-slate-400 text-sm mt-2">
                <span class="font-mono text-secondary bg-secondary/10 px-2 py-0.5 rounded">{new_id}</span>
            </p>
            <p class="text-slate-500 text-xs mt-1">{event_label}</p>
            {_POST_MAP_BACKGROUND_NOTE_HTML}
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

    # Check not already mapped (same feed row cannot point at two domain events)
    fp_lc_map = (feeder_provider or "").strip().lower()
    vid_map = str(feeder_valid_id or "").strip()
    existing = _load_event_mappings()
    prev_eid = next(
        (
            str(m.get("domain_event_id") or "").strip()
            for m in existing
            if (m.get("feed_provider") or "").strip().lower() == fp_lc_map and str(m.get("feed_valid_id") or "").strip() == vid_map
        ),
        "",
    )
    already = bool(prev_eid)
    if already and prev_eid and prev_eid != str(domain_id_selected).strip():
        return HTMLResponse(f"""
            <div class="p-6 text-center text-amber-300 text-sm max-w-md mx-auto">
                <i class="fa-solid fa-link mr-2"></i>
                This feed row is already linked to
                <span class="font-mono text-white">{prev_eid}</span>.
                Remove that mapping first if you want to link it here instead.
            </div>
        """)
    mapping_new = False
    if not already:
        _save_event_mapping(domain_id_selected, feeder_provider, feeder_valid_id)
        mapping_new = True
    # Fetch event details in background (BetsAPI token from .env) so we have markets for mapping modal
    if config.BETSAPI_TOKEN and feeder_provider and feeder_valid_id:
        asyncio.create_task(_fetch_and_save_event_details(feeder_provider, feeder_valid_id))
    if mapping_new:
        _record_feed_domain_mapping_link(feeder_provider, feeder_valid_id, domain_id_selected, source="manual_map")

    # Mark feeder event as MAPPED in memory
    feeder_ev = None
    fp_lc = (feeder_provider or "").strip().lower()
    for e in DUMMY_EVENTS:
        if (e.get("feed_provider") or "").strip().lower() == fp_lc and str(e.get("valid_id")) == str(feeder_valid_id):
            e["mapping_status"] = "MAPPED"
            e["domain_id"] = domain_id_selected
            feeder_ev = e
            break

    if feeder_ev:
        _sync_entity_feed_mappings_from_feeder_domain(domain_ev, feeder_ev, feeder_provider)

    _remove_valid_id_from_feed_dashboard_new(fp_lc, str(feeder_valid_id))

    _schedule_post_map_auto_map_then_create(feeder_provider)
    _invalidate_dashboard_feed_stats_cache()

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
            {_POST_MAP_BACKGROUND_NOTE_HTML}
            <button onclick="closeModal(true)" class="mt-6 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white text-sm rounded transition-all">
                Close
            </button>
        </div>
    """)

@app.get("/api/search-domain-events", response_class=HTMLResponse)
async def search_domain_events(q: str = "", sport_id: str = ""):
    """Search DOMAIN_EVENTS by home/away/competition name for the mapping modal. Optional sport_id scopes to one domain sport."""
    sid = fid_str(sport_id) if (sport_id or "").strip() else ""
    pool = DOMAIN_EVENTS
    if sid:
        pool = [e for e in DOMAIN_EVENTS if _domain_event_row_matches_domain_sport(e, sid)]
    q_lower = q.strip().lower()
    if q_lower:
        results = [e for e in pool if _domain_event_matches_search_q(e, q_lower)]
    else:
        results = list(pool)

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


@app.post("/api/feeder-run-auto-map")
async def api_feeder_run_auto_map(feed_provider: str = Form(...)):
    """Reload domain/entity CSV from disk, sync feeder mapping flags, run auto-map then auto-create (no API pull)."""
    fp = (feed_provider or "").strip().lower()
    global DOMAIN_EVENTS, ENTITY_FEED_MAPPINGS, DOMAIN_ENTITIES
    DOMAIN_EVENTS = _load_domain_events()
    ENTITY_FEED_MAPPINGS = _load_entity_feed_mappings()
    DOMAIN_ENTITIES = _load_entities()
    _sync_feeder_events_mapping_status()
    am, ac = _run_auto_map_then_create_domain_events_for_feed(fp)
    _invalidate_dashboard_feed_stats_cache()
    return JSONResponse({"ok": True, "feed_provider": fp, "auto_mapped_domain_events": am, "auto_created_domain_events": ac})


# --- Views ---

def _parse_feeder_start_time_utc(st: str | None) -> datetime | None:
    """Parse feeder event start_time (UTC, 'YYYY-MM-DD HH:MM:SS' from loaders). Returns None if missing."""
    if not st or not isinstance(st, str):
        return None
    s = st.strip()
    if not s or s in ("—", "-"):
        return None
    try:
        return datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def _feeder_event_is_future_for_dashboard(e: dict) -> bool:
    dt = _parse_feeder_start_time_utc(e.get("start_time"))
    if dt is None:
        return False
    return dt > datetime.now(timezone.utc)


def _valid_ids_for_feed(feed_provider_code: str) -> set[str]:
    fp = (feed_provider_code or "").strip().lower()
    return {str(e.get("valid_id")) for e in DUMMY_EVENTS if (e.get("feed_provider") or "").strip().lower() == fp}


def _load_feed_dashboard_new_ids() -> dict[str, set[str]]:
    path = FEED_DASHBOARD_STATE_PATH
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}
    raw = data.get("feeds") or {}
    out: dict[str, set[str]] = {}
    for k, v in raw.items():
        fc = (str(k) or "").strip().lower()
        if not fc:
            continue
        if isinstance(v, list):
            out[fc] = {str(x) for x in v if x is not None and str(x).strip()}
        elif isinstance(v, dict):
            out[fc] = {str(x) for x in (v.get("new_valid_ids") or []) if x is not None and str(x).strip()}
    return out


def _write_feed_dashboard_new_ids(feed_to_ids: dict[str, set[str]]) -> None:
    path = FEED_DASHBOARD_STATE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    serial = {"feeds": {k: sorted(v) for k, v in sorted(feed_to_ids.items()) if v}}
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(serial, f, indent=2)
    tmp.replace(path)


def _set_feed_dashboard_new_ids_for_feed(feed_provider: str, new_ids: set[str]) -> None:
    fp = (feed_provider or "").strip().lower()
    with _feed_dashboard_state_lock:
        all_ids = _load_feed_dashboard_new_ids()
        all_ids[fp] = {str(x) for x in new_ids if x is not None and str(x).strip()}
        if not all_ids[fp]:
            all_ids.pop(fp, None)
        _write_feed_dashboard_new_ids(all_ids)


def _remove_valid_id_from_feed_dashboard_new(feed_provider: str, valid_id: str) -> None:
    fp = (feed_provider or "").strip().lower()
    vid = str(valid_id).strip()
    if not fp or not vid:
        return
    with _feed_dashboard_state_lock:
        all_ids = _load_feed_dashboard_new_ids()
        s = all_ids.get(fp)
        if not s or vid not in s:
            return
        s.discard(vid)
        if not s:
            all_ids.pop(fp, None)
        _write_feed_dashboard_new_ids(all_ids)


def _prune_feed_dashboard_new_ids_persisted() -> None:
    """Drop stale IDs and mapped/ignored rows from persisted 'new since last pull' sets."""
    idx: dict[tuple[str, str], str] = {}
    for e in DUMMY_EVENTS:
        fp = (e.get("feed_provider") or "").strip().lower()
        vid = str(e.get("valid_id", "")).strip()
        if fp and vid:
            idx[(fp, vid)] = (e.get("mapping_status") or "").strip().upper()

    with _feed_dashboard_state_lock:
        all_ids = _load_feed_dashboard_new_ids()
        new_all: dict[str, set[str]] = {}
        for fp, ids in all_ids.items():
            keep = {vid for vid in ids if idx.get((fp, vid)) == "UNMAPPED"}
            if keep:
                new_all[fp] = keep
        if new_all != all_ids:
            _write_feed_dashboard_new_ids(new_all)


def _record_feed_dashboard_new_ids_after_pull(feed_provider: str, old_valid_ids: set[str]) -> None:
    """Replace this feed's 'new' set with valid_ids that appeared since old_valid_ids (last pull window)."""
    fp = (feed_provider or "").strip().lower()
    cur = _valid_ids_for_feed(fp)
    _set_feed_dashboard_new_ids_for_feed(fp, cur - old_valid_ids)


def _feed_max_last_pull_iso(feed_provider_code: str) -> str | None:
    fp = (feed_provider_code or "").strip().lower()
    last_pulls = _load_feed_last_pulls()
    best: datetime | None = None
    best_iso: str | None = None
    for (f, _sid), iso in last_pulls.items():
        if f != fp or not (iso or "").strip():
            continue
        try:
            dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            continue
        if best is None or dt > best:
            best = dt
            best_iso = iso.strip()
    return best_iso


def _invalidate_dashboard_feed_stats_cache() -> None:
    global _dashboard_feed_stats_cache_mono, _dashboard_feed_stats_cache_rows
    with _dashboard_feed_stats_cache_lock:
        _dashboard_feed_stats_cache_mono = 0.0
        _dashboard_feed_stats_cache_rows = None


def _build_dashboard_feed_stats() -> list[dict]:
    """Per-feed counts from DUMMY_EVENTS: future fixtures only (UNMAPPED+MAPPED); New = unmapped in last-pull id set."""
    _prune_feed_dashboard_new_ids_persisted()
    new_ids_map = _load_feed_dashboard_new_ids()
    feed_ids_with_sport_mappings = {m["feed_provider_id"] for m in SPORT_FEED_MAPPINGS}
    feeds_for_dashboard = [f for f in FEEDS if f.get("domain_id") in feed_ids_with_sport_mappings]
    stats: list[dict] = []
    now_iso = datetime.now(timezone.utc).isoformat()
    for feed in feeds_for_dashboard:
        code = (feed.get("code") or "").strip().lower()
        name = (feed.get("name") or feed.get("code") or code) or "—"
        events = [e for e in DUMMY_EVENTS if (e.get("feed_provider") or "").strip().lower() == code]
        future = [
            e
            for e in events
            if _feeder_event_is_future_for_dashboard(e)
            and (e.get("mapping_status") or "") in ("UNMAPPED", "MAPPED")
        ]
        total = len(future)
        mapped = sum(1 for e in future if e.get("mapping_status") == "MAPPED")
        unmapped = sum(1 for e in future if e.get("mapping_status") == "UNMAPPED")
        new_set = new_ids_map.get(code, set())
        new_count = sum(
            1
            for e in future
            if e.get("mapping_status") == "UNMAPPED" and str(e.get("valid_id")) in new_set
        )
        last_iso = _feed_max_last_pull_iso(code)
        stats.append(
            {
                "feed_name": name,
                "feed_code": code,
                "total": total,
                "mapped": mapped,
                "unmapped": unmapped,
                "new": new_count,
                "last_pull_display": _format_last_pull(last_iso),
                "last_pull_iso": last_iso or "",
                "as_of": now_iso,
            }
        )
    return stats


def _get_dashboard_feed_stats_cached() -> list[dict]:
    """In-memory TTL cache so dashboard SSR and JSON poll avoid recomputing on every request."""
    now = time.monotonic()
    with _dashboard_feed_stats_cache_lock:
        global _dashboard_feed_stats_cache_mono, _dashboard_feed_stats_cache_rows
        if (
            _dashboard_feed_stats_cache_rows is not None
            and (now - _dashboard_feed_stats_cache_mono) < DASHBOARD_FEED_STATS_TTL_SEC
        ):
            return _dashboard_feed_stats_cache_rows
        rows = _build_dashboard_feed_stats()
        _dashboard_feed_stats_cache_rows = rows
        _dashboard_feed_stats_cache_mono = now
        return rows


def _dashboard_feed_stats() -> list[dict]:
    """Same data as _get_dashboard_feed_stats_cached() (used by dashboard template)."""
    return _get_dashboard_feed_stats_cached()


def _changelog_date_display(raw: str | None, *, today: date) -> str:
    """
    Human-readable date for the What's new panel.
    Use date="live" for the current tip release so it always shows the server's local calendar date when viewed.
    ISO YYYY-MM-DD is formatted (e.g. 31 March 2026); other non-empty strings are shown as stored.
    """
    fmt = "%d %B %Y"
    if isinstance(raw, str) and raw.strip().lower() == "live":
        return today.strftime(fmt)
    if raw is None:
        return ""
    s = str(raw).strip()
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        try:
            y, m, d = int(s[0:4]), int(s[5:7]), int(s[8:10])
            return date(y, m, d).strftime(fmt)
        except ValueError:
            pass
    return s


# Changelog for dashboard (new features / bugs fixed per version). Edit here or move to a file.
# Tip release may use "date": "live" so the dashboard shows today's real calendar date (server local time).
DASHBOARD_CHANGELOG = [
    {"version": "1.2.7", "date": "live", "items": [
        "Feeder Configuration: Auto map Events (per feed/scope, multiselect) links unmapped feeder rows to an existing domain fixture when all entities are mapped and exactly one domain event matches names and start time; runs after pulls and after map/create from Feeder Events, before Auto create Events.",
        "Dashboard per-feed summary: counts are future fixtures only; New column lists unmapped events first seen on the latest pull (auto or manual; cleared on the next pull or when mapped); Last pull shows the latest sport pull time per feed. Summary is server-cached for 10 minutes and the table re-fetches on the same interval.",
        "UI / theming: light mode uses cream-tinted surfaces and stronger contrast on muted text; top bar in light mode uses a warm espresso tone instead of a cool blue strip.",
        "Tables: shared `gmp-data-table` styling and surface tokens for headers and rows across major grids; Feeder Events rows are no longer zebra-striped. Event Navigator event names use the same medium weight as Feeder Events.",
        "Page chrome: removed generic page subtitles under main headings; slightly tighter page header padding.",
        "Light mode fixes: inputs, entity names, and other surfaces no longer force white text where it was unreadable on pale backgrounds (risk disks and primary actions still use white where intended).",
        "Theme switcher: Light/Dark is only in the profile menu (removed from the top bar and mobile drawer). Clicks inside the menu are handled correctly so the choice applies immediately.",
        "Early theme class on `<html>` via `gmp_theme_boot.html` in the document head reduces light/dark flash before CSS loads.",
    ]},
    {"version": "1.2.6", "date": "2026-04-11", "items": [
        "Event details → Feed odds: multi-line markets list every line each feed offers (1xbet, Bet365 handicap/total, Bwin); API query `all_lines` (default true). Center domain line buttons unchanged; L column shows feed lines and a ★ on 1xbet’s CE “main” line where present.",
        "1xbet G=136 (Correct Set Score) and G=343 (Score After 2 Sets): **P** encodes the score (e.g. 3.001 → 3:1), not a handicap/total line; outcomes are flattened and ordered to match domain column order (same idea as before for best-of-five 3:0…0:3).",
        "Bet365 910201 / 910211 / 910212: set-score rows use **name** from each side’s perspective and **header** 1=home / 2=away; we map to home:away and sort so away 3-set wins show as 2:3, 1:3, 0:3 under the right headers.",
        "Docs/script: optional E-53 feed markets & odds reference (`docs/E-53_feed_markets_odds_dump.md`, `scripts/generate_e53_feed_markets_md.py`). 1xbet market names CSV for GE labels (`backend/data/markets/1xbet_market_names.csv`).",
    ]},
    {"version": "1.2.5", "date": "2026-04-01", "items": [
        "RBAC: Internal / platform users (no partner) now get the full configured permission set for navigation and page access, merged with their role CSV rows. Fixes lockout when server role_permissions had no menu.*.view entries; partner-scoped users are unchanged.",
    ]},
    {"version": "1.2.4", "date": "2026-04-01", "items": [
        "Access Rights → View now drives the top navigation (desktop and mobile): menu items and Configuration / Betting Program children only appear when the role grants the matching menu.*.view codes.",
        "Direct URL access matches the same rules: opening a page or HTMX fragment without the required view permission redirects to the dashboard (403 + HX-Redirect for HTMX). SuperAdmin is unchanged (full access).",
        "Always-granted views (Dashboard, Notifications, Profile) are merged with role permissions so those areas stay available without storing redundant codes in every role.",
    ]},
    {"version": "1.2.3", "date": "2026-04-01", "items": [
        "Admin Management: partner-scoped sign-in sees only that partner’s users, roles, and brands (UI + RBAC APIs). Platform / Internal User accounts still see all tenants.",
        "Admin: tenant label “Internal User” replaces “Platform” for users and roles with no partner; Partner column uses plain white for Internal User rows.",
        "Admin → Roles & Permissions: Actions column is a kebab menu (Edit + Duplicate role). Duplicate creates a role with the same access rights; pick name and target partner (shortcut when onboarding a new partner).",
        "Admin table: Online reflects recent activity (in-memory; configurable RBAC_ONLINE_IDLE_SECONDS). Last login is persisted on successful /dev/login; /dev/logout clears online immediately for that session.",
        "Last login column: shows date/time for the first seven full days, then “N days”; 15+ days is red and bold to highlight stale accounts for hygiene / deactivation reviews.",
        "Deploy: backend/data/rbac/*.csv stays environment-local (.gitignore). server-protect-data.sh lists those paths so servers can skip-worktree if needed; never copy prod roles/users from another machine—bootstrap each environment in Admin or via server CSV backup.",
    ]},
    {"version": "1.2.2", "date": "2026-04-01", "items": [
        "Admin → Roles & Permissions: optional Master role per partner (and one for Platform). Exactly one Master per scope; other roles’ permissions cannot exceed the Master’s for that partner. CSV column roles.is_master; migration on startup.",
    ]},
    {"version": "1.2.1", "date": "2026-04-01", "items": [
        "Starlette 1.x / current pip: all Jinja2 TemplateResponse calls use TemplateResponse(request, name, context). Fixes Internal Server Error on dashboard and every HTML page when the container installs a recent Starlette (old name-first signature was removed). requirements.txt pins minimum FastAPI/Starlette.",
    ]},
    {"version": "1.2", "date": "2026-04-01", "items": [
        "Mobile navigation: hamburger menu opens a right-side drawer with the same routes as the desktop bar (including Configuration accordions). Desktop layout is unchanged from the md breakpoint upward.",
        "Configuration: Compliance & Regulations page added at /compliance (placeholder shell for upcoming content).",
        "Entities: CSV column jurisdiction → country for categories, competitions, and teams (ISO code or '-' for international). Brands keep jurisdiction for compliance. UI labels read Country; domain ID cells no longer use a leading #.",
        "Mapping modal and partial-create flows use country, with backward compatibility if older rows still expose jurisdiction in memory.",
        "Feeder configuration: League filter renamed to Competition (form field competition_id); sport/category/competition dropdowns respect prefixed domain IDs; page description clarifies that sports are not auto-created here.",
        "Event details: market checkboxes and group logic use string domain market IDs (M-…) with numeric-aware sorting.",
        "Margin: assign-competition and copy-from-brand API payloads use string domain IDs for sport and competition (C-…, S-…).",
        "Backend: domain_ids helpers; optional one-time prefixed-ID migration (see v1.1 notes). Schemas and config ENTITY_FIELDS updated for country and string domain IDs where needed.",
        ".gitignore: migration marker .domain_ids_prefixed_v1; per-environment backend/data/notes/platform_notes.csv and backend/data/countries/countries.json.",
        "Documentation: GMP dark theme design baseline (docs/UI docs) expanded with mapping/grid colors and primary vs emerald usage; feeder QNX doc and entities / mapping-modal specs refreshed.",
    ]},
    {"version": "1.1", "date": "2026-03-31", "items": [
        "Typed domain IDs: S sports, G categories, C competitions, P teams/players, M markets, E events. Legacy numeric IDs migrate once on first startup after upgrade (back up backend/data on production before deploying if you want an easy rollback).",
        "Entities → Markets: sport filter works with prefixed sport IDs.",
        "Entities: tables and create messages show domain IDs without a leading #.",
    ]},
    {"version": "1.0", "date": "2026-03", "items": [
        "Market type mappings per environment (local vs server).",
        "Markets tab: require sport selection before showing markets.",
        "Feed mapper: sport name in Available markets (Bwin, Bet365, 1xbet); mapper feed list from sport mappings only.",
    ]},
]


def _dashboard_changelog_rows() -> list[dict]:
    today = date.today()
    return [{**row, "date_display": _changelog_date_display(row.get("date"), today=today)} for row in DASHBOARD_CHANGELOG]


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """
    Main Dashboard View. Shows per-feed mapped/unmapped summary and changelog.
    """
    return templates.TemplateResponse(request, "index.html", {
        "request": request,
        "section": "dashboard",
        "feed_stats": _dashboard_feed_stats(),
        "changelog": _dashboard_changelog_rows(),
    })


@app.get("/api/dashboard-feed-stats")
async def api_dashboard_feed_stats():
    """JSON for dashboard per-feed summary (cached ~10 minutes; invalidated on pull/map)."""
    rows = _get_dashboard_feed_stats_cached()
    return {"feeds": rows}


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
    return templates.TemplateResponse(request, "pull_feeds.html", {
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
        old_ids = _valid_ids_for_feed(feed_provider)
        _save_feed_last_pull(feed_provider, feed_sport_id)
        result["last_pull_display"] = _format_last_pull(datetime.now(timezone.utc).isoformat())
        global DUMMY_EVENTS, DOMAIN_EVENTS, ENTITY_FEED_MAPPINGS, DOMAIN_ENTITIES
        DUMMY_EVENTS = load_all_mock_data()
        _enrich_feed_events_sport_names()
        DOMAIN_EVENTS = _load_domain_events()
        ENTITY_FEED_MAPPINGS = _load_entity_feed_mappings()
        DOMAIN_ENTITIES = _load_entities()
        _sync_feeder_events_mapping_status()
        _record_feed_dashboard_new_ids_after_pull(feed_provider, old_ids)
        am, ac = _run_auto_map_then_create_domain_events_for_feed(feed_provider)
        result["auto_mapped_domain_events"] = am
        result["auto_created_domain_events"] = ac
        _prune_feed_dashboard_new_ids_persisted()
        _invalidate_dashboard_feed_stats_cache()
    return result


async def _pull_all_sports_for_feed_internal(
    feed_provider: str,
    token: str,
    concurrency: int = 5,
) -> dict:
    """
    Pull all sports for one feed (same as /api/pull-feed-all but callable from scheduler).
    Uses token from argument (e.g. BETSAPI_TOKEN). Reloads DUMMY_EVENTS on success.
    """
    feed_provider = (feed_provider or "").strip().lower()
    token = (token or "").strip()
    if not token:
        return {"ok": False, "results": [], "error": "Please enter API key"}
    if feed_provider not in ("bet365", "betfair", "1xbet", "bwin"):
        return {"ok": False, "results": [], "error": f"Unsupported feed: {feed_provider}"}
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
        old_ids = _valid_ids_for_feed(feed_provider)
        now_iso = datetime.now(timezone.utc).isoformat()
        result["last_pull_display"] = _format_last_pull(now_iso)
        for sid, _ in sports:
            _save_feed_last_pull(feed_provider, sid)
        global DUMMY_EVENTS, DOMAIN_EVENTS, ENTITY_FEED_MAPPINGS, DOMAIN_ENTITIES
        DUMMY_EVENTS = load_all_mock_data()
        _enrich_feed_events_sport_names()
        DOMAIN_EVENTS = _load_domain_events()
        ENTITY_FEED_MAPPINGS = _load_entity_feed_mappings()
        DOMAIN_ENTITIES = _load_entities()
        _sync_feeder_events_mapping_status()
        _record_feed_dashboard_new_ids_after_pull(feed_provider, old_ids)
        am, ac = _run_auto_map_then_create_domain_events_for_feed(feed_provider)
        result["auto_mapped_domain_events"] = am
        result["auto_created_domain_events"] = ac
        _prune_feed_dashboard_new_ids_persisted()
        _invalidate_dashboard_feed_stats_cache()
    return result


async def _scheduled_feed_pull_worker() -> None:
    """
    One full pull-all-sports per UTC hour, rotating feeds (bet365 → betfair → 1xbet → bwin → …).
    Only runs when SCHEDULED_FEED_PULL=1 and BETSAPI_TOKEN is set. Intended for server deploys.
    """
    log = logging.getLogger("uvicorn.error")
    if not getattr(config, "SCHEDULED_FEED_PULL_ENABLED", False):
        return
    token = (getattr(config, "BETSAPI_TOKEN", None) or "").strip()
    feeds = tuple(getattr(config, "SCHEDULED_FEED_PULL_ORDER", ()) or ())
    if not feeds:
        log.warning("Scheduled feed pull: SCHEDULED_FEED_PULL_ORDER is empty; worker not started")
        return
    if not token:
        log.warning("Scheduled feed pull enabled but BETSAPI_TOKEN is empty; worker not started")
        return
    conc = int(getattr(config, "SCHEDULED_FEED_PULL_CONCURRENCY", 5) or 5)
    delay = int(getattr(config, "SCHEDULED_FEED_PULL_START_DELAY_SEC", 60) or 0)
    log.info(
        "Scheduled feed pull worker will start in %ss (one feed per UTC hour, order=%s)",
        delay,
        ",".join(feeds),
    )
    await asyncio.sleep(max(0, delay))
    while True:
        try:
            now = datetime.now(timezone.utc)
            hour_bucket = int(now.timestamp() // 3600)
            idx = hour_bucket % len(feeds)
            feed = feeds[idx]
            log.info(
                "Scheduled feed pull: %s (UTC hour bucket %s, slot %s/%s)",
                feed,
                hour_bucket,
                idx + 1,
                len(feeds),
            )
            res = await _pull_all_sports_for_feed_internal(feed, token, conc)
            if res.get("ok"):
                log.info("Scheduled feed pull finished OK: %s", feed)
            else:
                log.warning("Scheduled feed pull failed for %s: %s", feed, res.get("error"))
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("Scheduled feed pull worker error")
            await asyncio.sleep(60)
        now2 = datetime.now(timezone.utc)
        next_boundary = now2.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        wait_sec = max(1.0, (next_boundary - now2).total_seconds())
        log.debug("Scheduled feed pull: sleeping %.0fs until next UTC hour", wait_sec)
        await asyncio.sleep(wait_sec)


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
    concurrency = max(1, min(concurrency, 10))
    return await _pull_all_sports_for_feed_internal(feed_provider, token, concurrency)


@app.on_event("startup")
async def _startup_scheduled_feed_pull() -> None:
    if getattr(config, "SCHEDULED_FEED_PULL_ENABLED", False):
        asyncio.create_task(_scheduled_feed_pull_worker())


@app.get("/admin/dump-csv-data", response_class=HTMLResponse)
async def dump_csv_data_page(request: Request):
    """SuperAdmin only. Data & CSV tools (destructive reset + future read-only previews)."""
    _rbac_require_superadmin(request)
    return templates.TemplateResponse(
        request,
        "admin/dump_csv_data.html",
        {"section": "admin_data_tools"},
    )


@app.post("/api/dump-csv-data", response_class=HTMLResponse)
async def dump_csv_data(request: Request):
    """
    SuperAdmin only. Clear all entity and relation CSVs (header-only). feeds.csv is not touched.
    Reloads in-memory state; redirects to /users when RBAC shell applies to SuperAdmin, else /.
    """
    _rbac_require_superadmin(request)
    _dump_entity_and_relation_csvs()
    global DOMAIN_EVENTS, DOMAIN_ENTITIES, ENTITY_FEED_MAPPINGS, SPORT_FEED_MAPPINGS
    DOMAIN_EVENTS = _load_domain_events()
    DOMAIN_ENTITIES = _load_entities()
    ENTITY_FEED_MAPPINGS = _load_entity_feed_mappings()
    SPORT_FEED_MAPPINGS = _load_sport_feed_mappings()
    # Feeder rows (DUMMY_EVENTS) keep stale MAPPED until re-synced from event_mappings.csv; dashboard counts use those.
    _sync_feeder_events_mapping_status()
    _invalidate_dashboard_feed_stats_cache()
    _admin_audit_append(
        request,
        resource="superadmin.data_tools",
        action="dump_entity_csvs",
        subject=json.dumps({"tool": "dump_entity_and_relation_csvs"}, separators=(",", ":")),
        was="live DOMAIN_ENTITIES / DOMAIN_EVENTS / mappings",
        now="entity+relation CSVs rewritten header-only; in-memory reloaded",
        details="feeds.csv, sports.csv, sport_feed_mappings.csv unchanged",
    )
    after = (
        "/users"
        if _rbac_nav_enforced(request) and _rbac_actor_is_superadmin(request)
        else "/"
    )
    return RedirectResponse(url=after, status_code=303)


@app.get("/api/superadmin/csv-files")
async def api_superadmin_csv_files(request: Request):
    """SuperAdmin only. List whitelisted CSVs under data/ with size and existence."""
    _rbac_require_superadmin(request)
    files: list[dict] = []
    for key, pth, label in _SUPERADMIN_CSV_CATALOG:
        exists = pth.exists()
        size = int(pth.stat().st_size) if exists else 0
        files.append({"key": key, "label": label, "exists": exists, "size": size})
    return JSONResponse({"files": files})


@app.get("/api/superadmin/csv-preview")
async def api_superadmin_csv_preview(request: Request, key: str = "", offset: int = 0, limit: int = 100):
    """SuperAdmin only. Paginated CSV rows (header + data rows) for a catalog key."""
    _rbac_require_superadmin(request)
    key = (key or "").strip()
    if not key:
        raise HTTPException(status_code=400, detail="Missing query parameter: key")
    pth = _superadmin_csv_path_for_key(key)
    if pth is None:
        raise HTTPException(status_code=404, detail="Unknown file key")
    label = next((lb for k, _, lb in _SUPERADMIN_CSV_CATALOG if k == key), key)
    prev = _superadmin_read_csv_preview(pth, offset, limit)
    prev["key"] = key
    prev["label"] = label
    return JSONResponse(prev)


def _feeder_category_key(e: dict) -> str:
    """Canonical category value for a feeder event (for filter dropdown and matching)."""
    return (e.get("category") or str(e.get("category_id") or "")).strip()


def _feeder_competition_key(e: dict) -> str:
    """Canonical competition value for a feeder event."""
    return (e.get("raw_league_name") or str(e.get("raw_league_id") or "")).strip()


# Bwin competition filter tokens are "category\x1fcompetition" so region + league stay unique in the UI.
_FEEDER_COMP_FILTER_SEP = "\x1f"


def _feeder_competition_filter_token_for_event(e: dict) -> str:
    """Value submitted for competition multiselect (composite for bwin when category exists)."""
    feed_l = (e.get("feed_provider") or "").strip().lower()
    comp = _feeder_competition_key(e)
    if not comp:
        return ""
    if feed_l == "bwin":
        cat = _feeder_category_key(e)
        if cat:
            return f"{cat}{_FEEDER_COMP_FILTER_SEP}{comp}"
    return comp


def _feeder_competition_filter_label_for_event(e: dict) -> str:
    """Dropdown / chip label; bwin uses [Category] Competition when category exists."""
    feed_l = (e.get("feed_provider") or "").strip().lower()
    comp = _feeder_competition_key(e)
    if not comp:
        return "—"
    if feed_l == "bwin":
        cat = _feeder_category_key(e)
        if cat:
            return f"[{cat}] {comp}"
    return comp


def _feeder_competition_filter_options(feed: str, sports: list[str] | None) -> list[dict[str, str]]:
    """Competition filter rows: {value, label}, sorted by category then competition (case-insensitive)."""
    if not sports:
        return []
    feed_l = (feed or "").strip().lower()
    sport_set = set(sports)
    rows: list[tuple[tuple[str, str], str, str]] = []
    seen: set[str] = set()
    for e in DUMMY_EVENTS:
        if (e.get("feed_provider") or "").strip().lower() != feed_l or e.get("sport") not in sport_set:
            continue
        tok = _feeder_competition_filter_token_for_event(e)
        if not tok or tok in seen:
            continue
        seen.add(tok)
        comp = _feeder_competition_key(e)
        cat = (_feeder_category_key(e) if feed_l == "bwin" else "") or ""
        lbl = _feeder_competition_filter_label_for_event(e)
        rows.append(((cat.lower(), comp.lower()), tok, lbl))
    rows.sort(key=lambda r: r[0])
    return [{"value": r[1], "label": r[2]} for r in rows]


def _feeder_event_matches_selected_competitions(e: dict, selected: list[str]) -> bool:
    """True if event matches multiselect: composite tokens, or legacy plain league keys when none composite."""
    if not selected:
        return True
    sel = {str(s).strip() for s in selected if str(s).strip()}
    tok = _feeder_competition_filter_token_for_event(e)
    if tok in sel:
        return True
    if any(_FEEDER_COMP_FILTER_SEP in s for s in sel):
        return False
    comp = _feeder_competition_key(e)
    return bool(comp and comp in sel)


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


# --- Feeder event log (appeared, mapped, domain_created, note_added, ignored, unignored) ---
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
    """Append one log entry. action_type: appeared, mapped, domain_created, note_added, ignored, unignored."""
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


# --- Domain event log (created, feed_linked) — mirrors feeder_event_log for map/create links ---
_DOMAIN_EVENT_LOG_FIELDS = ["domain_event_id", "action_type", "details", "created_at"]
_MAPPING_LOG_SOURCES_NEW_DOMAIN = frozenset({"manual_create", "auto_create"})


def _append_domain_event_log(domain_event_id: str, action_type: str, details: str | None = None) -> None:
    """Append one domain-side log row (e.g. feed_linked, created)."""
    if not DOMAIN_EVENT_LOG_PATH:
        return
    deid = (domain_event_id or "").strip()
    created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    row = {
        "domain_event_id": deid,
        "action_type": (action_type or "").strip(),
        "details": (details or "").strip(),
        "created_at": created,
    }
    DOMAIN_EVENT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    file_exists = DOMAIN_EVENT_LOG_PATH.exists()
    with open(DOMAIN_EVENT_LOG_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=_DOMAIN_EVENT_LOG_FIELDS)
        if not file_exists:
            w.writeheader()
        w.writerow(row)


def _load_domain_event_log() -> list[dict]:
    if not DOMAIN_EVENT_LOG_PATH or not DOMAIN_EVENT_LOG_PATH.exists():
        return []
    out = []
    with open(DOMAIN_EVENT_LOG_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out.append({k: row.get(k, "") for k in _DOMAIN_EVENT_LOG_FIELDS})
    return out


def _get_domain_event_log_entries(domain_event_id: str) -> list[dict]:
    """Log rows for this domain event id, newest first."""
    did = (domain_event_id or "").strip()
    rows = [r for r in _load_domain_event_log() if (r.get("domain_event_id") or "").strip() == did]
    rows.sort(key=lambda r: (r.get("created_at") or ""), reverse=True)
    return rows


def _record_feed_domain_mapping_link(
    feed_provider: str,
    feed_valid_id: str,
    domain_event_id: str,
    *,
    source: str,
) -> None:
    """Write feeder_event_log + domain_event_log for one new feed↔domain mapping or domain-created-from-feed."""
    fp = (feed_provider or "").strip()
    vid = str(feed_valid_id or "").strip()
    deid = str(domain_event_id or "").strip()
    src = (source or "").strip()
    if not fp or not vid or not deid or not src:
        return
    detail_feed = f"{deid}|{src}"
    detail_dom = f"{fp}:{vid}|{src}"
    if src in _MAPPING_LOG_SOURCES_NEW_DOMAIN:
        _append_feeder_event_log(fp, vid, "domain_created", details=detail_feed)
        _append_domain_event_log(deid, "created", details=detail_dom)
    else:
        _append_feeder_event_log(fp, vid, "mapped", details=detail_feed)
        _append_domain_event_log(deid, "feed_linked", details=detail_dom)


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


def _feeder_feed_sports_live(selected_feed: str) -> list[str]:
    """Sport names offered for feeder-events filters for this feed (CSV + events + defaults)."""
    sf = (selected_feed or KNOWN_FEEDS[0]).strip().lower()
    events_for_feed = [e for e in DUMMY_EVENTS if (e.get("feed_provider") or "").strip().lower() == sf]
    csv_sports = _get_sports_for_feed(sf, events_for_feed) or []
    event_sports = sorted({e.get("sport") for e in events_for_feed if e.get("sport")})
    feed_sports = sorted(set(csv_sports + event_sports)) if (csv_sports or event_sports) else SPORTS_BY_FEED.get(sf, KNOWN_SPORTS)
    if not feed_sports:
        feed_sports = SPORTS_BY_FEED.get(sf, KNOWN_SPORTS)
    return feed_sports


def _feeder_sport_scope(sport_param: str | None, feed_sports: list[str]) -> list[str]:
    """Filter scope: one sport when valid; otherwise full list (all sports)."""
    s = (sport_param or "").strip()
    fs = list(feed_sports) if feed_sports else []
    if not s or not fs or s not in set(fs):
        return fs
    return [s]


@app.get("/feeder-events", response_class=HTMLResponse)
async def feeder_events_view(
    request: Request,
    feed_provider: str = None,
    date: str = None,
    date_from: str = None,
    date_to: str = None,
    sport: str = None,
    competitions: List[str] = Query(default=None),
    statuses: List[str] = Query(default=None),
    live_only: str = "0",
    notes_only: str = "0",
):
    _sync_feeder_events_mapping_status()
    _enrich_feed_events_sport_names()
    selected_feed = (feed_provider or KNOWN_FEEDS[0]).strip().lower()
    selected_feed_pid = next((f["domain_id"] for f in FEEDS if (f.get("code") or "").strip().lower() == selected_feed), None)
    feed_sports_live = _feeder_feed_sports_live(selected_feed)
    selected_sport = (sport or "").strip()
    if selected_sport and selected_sport not in set(feed_sports_live):
        selected_sport = ""
    selected_sports = _feeder_sport_scope(selected_sport or None, feed_sports_live)
    selected_competitions = competitions or []
    selected_statuses = statuses or []
    live_only_active = (live_only or "").strip() in ("1", "true", "yes")
    notes_only_active = (notes_only or "").strip() in ("1", "true", "yes")
    filtered = [
        e for e in DUMMY_EVENTS
        if (e.get("feed_provider") or "").strip().lower() == selected_feed
        and e.get("sport") in selected_sports
    ]
    if selected_competitions:
        filtered = [e for e in filtered if _feeder_event_matches_selected_competitions(e, selected_competitions)]
    if selected_statuses:
        status_set = set(selected_statuses)
        filtered = [e for e in filtered if str(e.get("time_status") or "") in status_set]
    if live_only_active:
        filtered = [e for e in filtered if (e.get("time_status") or "0") == "1"]
    has_notes = _feeder_notes_has_set()
    if notes_only_active:
        filtered = [e for e in filtered if ((e.get("feed_provider") or "").strip(), (e.get("valid_id") or "").strip()) in has_notes]
    mapping_status_q = (request.query_params.get("mapping_status_filter") or "").strip()
    if mapping_status_q:
        filtered = [e for e in filtered if (e.get("mapping_status") or "") == mapping_status_q]
    date_filter = (date or "").strip() or "next_7_days"
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
    _feeder_events_attach_row_mapping_flags(page_events, selected_feed_pid)
    competition_filter_options = _feeder_competition_filter_options(selected_feed, selected_sports)
    _mk = lambda etype: {(m["feed_provider_id"], mapping_feed_id_key(m.get("feed_id"))) for m in ENTITY_FEED_MAPPINGS if m["entity_type"] == etype}
    _mk_sport = lambda: {(m["feed_provider_id"], _normalize_sport_feed_id(m.get("feed_id"))) for m in ENTITY_FEED_MAPPINGS if m.get("entity_type") == "sports"}
    mapped_sport_feed_ids = _mk_sport()
    mapped_category_feed_ids = _mapped_category_feed_ids_by_sport()
    mapped_comp_feed_ids    = _mapped_comp_feed_ids_by_sport()
    mapped_team_feed_ids    = _mk("teams")
    return templates.TemplateResponse(request, "feeder_events/feeder_events.html", {
        "request": request,
        "section": "feeder",
        "feeds": KNOWN_FEEDS,
        "selected_feed": selected_feed,
        "selected_feed_pid": selected_feed_pid,
        "sports": feed_sports_live,
        "selected_sport": selected_sport,
        "competition_filter_options": competition_filter_options,
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
        "feeder_mapping_status_filter": mapping_status_q,
    })

@app.get("/feeder-events/sport-options", response_class=HTMLResponse)
async def feeder_events_sport_options(request: Request, feed_provider: str = None, sport: str = ""):
    """
    HTMX: single-select sport options for the current feed (All sports + one option per sport).
    """
    _enrich_feed_events_sport_names()
    selected_feed = (feed_provider or KNOWN_FEEDS[0]).strip().lower()
    feed_sports = _feeder_feed_sports_live(selected_feed)
    sel = (sport or "").strip()
    if sel and sel not in set(feed_sports):
        sel = ""
    return templates.TemplateResponse(request, "feeder_events/_sport_select.html", {
        "request": request,
        "sports": feed_sports,
        "selected_sport": sel,
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
    sport: str = None,
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
    feed_sports = _feeder_feed_sports_live(selected_feed)
    active_sports = _feeder_sport_scope(sport, feed_sports)
    q_lower = q.strip().lower()
    notes_only_on = (notes_only or "").strip() in ("1", "true", "yes")
    has_notes_set = _feeder_notes_has_set() if notes_only_on else None

    filtered = []
    for e in DUMMY_EVENTS:
        if (e.get("feed_provider") or "").strip().lower() != selected_feed:
            continue
        if e.get("sport") not in active_sports:
            continue
        if competitions and not _feeder_event_matches_selected_competitions(e, competitions):
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

    date_filter = (date or "").strip() or "next_7_days"
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
    _feeder_events_attach_row_mapping_flags(page_events, selected_feed_pid)
    has_notes = _feeder_notes_has_set()
    _mk = lambda etype: {(m["feed_provider_id"], mapping_feed_id_key(m.get("feed_id"))) for m in ENTITY_FEED_MAPPINGS if m["entity_type"] == etype}
    _mk_sport = lambda: {(m["feed_provider_id"], _normalize_sport_feed_id(m.get("feed_id"))) for m in ENTITY_FEED_MAPPINGS if m.get("entity_type") == "sports"}
    mapped_sport_feed_ids = _mk_sport()
    mapped_category_feed_ids = _mapped_category_feed_ids_by_sport()
    mapped_comp_feed_ids    = _mapped_comp_feed_ids_by_sport()
    mapped_team_feed_ids    = _mk("teams")

    response = templates.TemplateResponse(request, "feeder_events/_rows.html", {
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


@app.get("/feeder-events/competition-options", response_class=HTMLResponse)
async def feeder_events_competition_options(
    request: Request,
    feed_provider: str = None,
    sport: str = "",
    competitions: List[str] = Query(default=None),
):
    """HTMX: Competition checkboxes for feeder events (sport scope; no separate category filter)."""
    feed = (feed_provider or KNOWN_FEEDS[0]).strip().lower()
    feed_sports = _feeder_feed_sports_live(feed)
    sports_scope = _feeder_sport_scope(sport, feed_sports)
    comp_opts = _feeder_competition_filter_options(feed, sports_scope) if sports_scope else []
    selected = competitions or []
    return templates.TemplateResponse(request, "feeder_events/_competition_checkboxes.html", {
        "request": request,
        "competition_filter_options": comp_opts,
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
    """True only when ≥2 distinct mapped feed rows (by feed+valid_id) resolve to different kickoff minutes.

    Duplicate mapping rows for the same feed occurrence are ignored. If a mapping row has no matching
    feed event in memory (stale id), that row falls back to the domain event's golden start_time so it
    does not falsely create a second clock reading.
    """
    source = feed_events if feed_events is not None else DUMMY_EVENTS
    domain_ev = next((e for e in DOMAIN_EVENTS if str(e.get("id")) == str(domain_event_id)), None)
    domain_key = _canonical_start_minute((domain_ev or {}).get("start_time")) if domain_ev else None

    uniq: list[dict] = []
    seen_pair: set[tuple[str, str]] = set()
    for m in mappings:
        fp = (m.get("feed_provider") or "").strip().lower()
        vid = str(m.get("feed_valid_id") or "").strip()
        if not fp or not vid:
            continue
        pair = (fp, vid)
        if pair in seen_pair:
            continue
        seen_pair.add(pair)
        uniq.append(m)
    if len(uniq) < 2:
        return False

    minute_keys: set[str] = set()
    for m in uniq:
        feed_provider = (m.get("feed_provider") or "").strip()
        feed_valid_id = str(m.get("feed_valid_id") or "").strip()
        feed_ev = next(
            (
                e
                for e in source
                if (e.get("feed_provider") or "").strip().lower() == feed_provider.lower()
                and str(e.get("valid_id") or "").strip() == feed_valid_id
            ),
            None,
        )
        st = (feed_ev.get("start_time") or "").strip() if feed_ev else ""
        ck = _canonical_start_minute(st) if st else None
        if ck is None and domain_key:
            ck = domain_key
        if ck is None:
            continue
        minute_keys.add(ck)
    return len(minute_keys) > 1


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


def _find_duplicate_domain_event_snapshot(
    *,
    sport_id: str,
    category_id: str,
    competition_id: str,
    home_id: str,
    away_id: str,
    start_time: str | None,
) -> dict | None:
    """Return an existing domain event if it matches the same fixture snapshot (ids + kickoff minute)."""
    sk = _canonical_start_minute(start_time)
    for ev in DOMAIN_EVENTS:
        if sk:
            evk = _canonical_start_minute(ev.get("start_time"))
            if not evk or evk != sk:
                continue
        else:
            if (start_time or "").strip() != (ev.get("start_time") or "").strip():
                continue
        if sport_id and not entity_ids_equal(ev.get("sport_id"), sport_id):
            continue
        if category_id and not entity_ids_equal(ev.get("category_id"), category_id):
            continue
        if competition_id and not entity_ids_equal(ev.get("competition_id"), competition_id):
            continue
        if home_id and not entity_ids_equal(ev.get("home_id"), home_id):
            continue
        if away_id and not entity_ids_equal(ev.get("away_id"), away_id):
            continue
        return ev
    return None


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
    # Sync domain_events.csv entity names with current entity names (fixes renames like SHNL -> HNL)
    _sync_domain_events_entity_names()
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
    # Get brand_id for risk class lookup: "Global" -> empty string, else use first selected brand's id
    selected_brand_id = None
    if selected_brands and len(selected_brands) > 0:
        if "Global" in selected_brands:
            selected_brand_id = ""
        else:
            # Get first brand's id from brands_list
            first_brand_name = selected_brands[0]
            brand_obj = next((b for b in brands_list if (b.get("name") or "").strip() == first_brand_name), None)
            if brand_obj:
                selected_brand_id = brand_obj.get("domain_id")
    date_filter = (date or "").strip() or "next_7_days"
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
    tpl_by_sport = _margin_templates_by_sport_for_event_navigator(page_events, selected_brand_id)
    for e in page_events:
        e["risk_class"] = _event_risk_class_from_margin_template(e, selected_brand_id, tpl_by_sport)
    return templates.TemplateResponse(request, "event_navigator/event_navigator.html", {
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
    # Sync domain_events.csv entity names with current entity names (fixes renames like SHNL -> HNL)
    _sync_domain_events_entity_names()
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
    brands_list = _load_brands()
    selected_brands = brands if brands else ["Global"]
    # Get brand_id for risk class lookup: "Global" -> empty string, else use first selected brand's id
    selected_brand_id = None
    if selected_brands and len(selected_brands) > 0:
        if "Global" in selected_brands:
            selected_brand_id = ""
        else:
            # Get first brand's id from brands_list
            first_brand_name = selected_brands[0]
            brand_obj = next((b for b in brands_list if (b.get("name") or "").strip() == first_brand_name), None)
            if brand_obj:
                selected_brand_id = brand_obj.get("domain_id")
    date_filter = (date or "").strip() or "next_7_days"
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
    tpl_by_sport = _margin_templates_by_sport_for_event_navigator(page_events, selected_brand_id)
    for e in page_events:
        e["risk_class"] = _event_risk_class_from_margin_template(e, selected_brand_id, tpl_by_sport)
    response = templates.TemplateResponse(request, "event_navigator/_rows.html", {
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


def _feed_sport_id_from_sport_feed_mappings(domain_sport_id: Any, feed_code: str) -> Any | None:
    """``feed_id`` from sport_feed_mappings for (domain sport, feed) — used as ``SportId`` on IMLog JSON so market discovery matches."""
    fc = (feed_code or "").strip().lower()
    feed_obj = next((f for f in FEEDS if (f.get("code") or "").strip().lower() == fc), None)
    if not feed_obj or domain_sport_id is None:
        return None
    pid = feed_obj["domain_id"]
    row = next(
        (
            m
            for m in SPORT_FEED_MAPPINGS
            if entity_ids_equal(m.get("domain_id"), domain_sport_id) and m.get("feed_provider_id") == pid
        ),
        None,
    )
    if not row:
        return None
    fid = row.get("feed_id")
    if fid is None or str(fid).strip() == "":
        return None
    try:
        return int(str(fid).strip())
    except (TypeError, ValueError):
        return str(fid).strip()


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
    return templates.TemplateResponse(request, "event_details.html", {
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
    return templates.TemplateResponse(request, "event_navigator/modal_notes.html", {
        "request": request,
        "domain_event_id": domain_event_id,
        "event_label": event_label,
        "note_text": note_text,
    })


@app.get("/event-navigator/event-log-modal/{domain_event_id}", response_class=HTMLResponse)
async def event_navigator_event_log_modal(request: Request, domain_event_id: str):
    """Modal: domain event log (feed links, domain created from feed, etc.)."""
    did = domain_event_id.strip()
    entries = _get_domain_event_log_entries(did)
    ev = next((e for e in DOMAIN_EVENTS if str(e.get("id")) == did), None)
    event_label = ""
    if ev:
        h, a = (ev.get("home") or "").strip(), (ev.get("away") or "").strip()
        event_label = f"{h} v {a}" if (h and a) else (h or ev.get("name") or did)
    return templates.TemplateResponse(request, "event_navigator/modal_domain_event_log.html", {
        "request": request,
        "domain_event_id": did,
        "event_label": event_label,
        "entries": entries,
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
    return templates.TemplateResponse(request, "event_navigator/_category_checkboxes.html", {
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
    return templates.TemplateResponse(request, "event_navigator/_competition_checkboxes.html", {
        "request": request,
        "competitions": comp_list,
        "selected_competitions": selected,
    })


@app.get("/archived-events", response_class=HTMLResponse)
async def archived_events_view(request: Request):
    """Betting Program > Archived Events. Placeholder page; full functionality to be added later."""
    return templates.TemplateResponse(request, "archived_events/archived_events.html", {
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
    # Ensure feed sport label matches feed_sports.csv (modal is a separate GET from the feeder list).
    fp_lc = (event.get("feed_provider") or "").strip().lower()
    if fp_lc:
        event["sport"] = _get_feed_sport_name(fp_lc, event.get("sport_id"), event.get("sport"))

    # Pre-resolve entities from entity_feed_mappings (prefer feed IDs then names so we find existing mappings)
    # Sport: resolve by feed sport_id; if missing from mappings, infer from mapped category/competition sport_id.
    r_sport = None
    domain_sport_id = None
    if feed_pid:
        _sid = event.get("sport_id")
        if _sid not in (None, "") and str(_sid).strip():
            r_sport = _resolve_sport_alias(feed_pid, str(_sid).strip())
        if r_sport:
            domain_sport_id = r_sport.get("domain_id")
        if not domain_sport_id:
            domain_sport_id = _infer_domain_sport_id_from_mapped_entities(event, feed_pid)
        if not domain_sport_id and feed_pid:
            ds_disp, s_disp = _domain_sport_id_from_feed_display_sport(event.get("sport"))
            if ds_disp:
                domain_sport_id = ds_disp
                if not r_sport:
                    r_sport = s_disp
        if domain_sport_id and not r_sport:
            r_sport = next((s for s in DOMAIN_ENTITIES.get("sports", []) if entity_ids_equal(s.get("domain_id"), domain_sport_id)), None)
    # Category / competition: league id + native category cell (e.g. Bwin region); unified feeds have no category field.
    r_category = None
    r_competition = None
    if feed_pid and domain_sport_id:
        lid = str(event.get("raw_league_id") or "").strip()
        if lid:
            c2 = _resolve_entity("competitions", lid, feed_pid, domain_sport_id=domain_sport_id)
            if c2:
                r_competition = c2
        for src in (event.get("category_id"), event.get("category")):
            t = str(src or "").strip()
            if not t or t.upper().startswith("COMP:"):
                continue
            cat_ent = _resolve_entity("categories", t, feed_pid, domain_sport_id=domain_sport_id)
            if cat_ent:
                r_category = cat_ent
                break
    r_home = _resolve_entity("teams", str(event.get("raw_home_id") or event.get("raw_home_name") or ""), feed_pid) if feed_pid else None
    r_away = _resolve_entity("teams", str(event.get("raw_away_id") or event.get("raw_away_name") or ""), feed_pid) if feed_pid else None

    # Enrich resolved entities with display names
    def _enrich(e):
        if not e:
            return None
        return {**e,
                "sport_name": _sport_name(e.get("sport_id")),
                "category_name": _category_name(e.get("category_id"))}

    resolved = {
        "sport":       r_sport,
        "category":    _enrich(r_category),
        "competition": _enrich(r_competition),
        "home":        _enrich(r_home),
        "away":        _enrich(r_away),
    }
    sports_by_id = {s["domain_id"]: s["name"] for s in DOMAIN_ENTITIES["sports"]}

    # Fuzzy: suggest domain events in mapped scope only; team-heavy scoring when competition is mapped.
    suggested_domain_events = _suggest_domain_events(
        event,
        domain_sport_id=domain_sport_id,
        domain_category_id=(r_category.get("domain_id") if r_category else None),
        domain_competition_id=(r_competition.get("domain_id") if r_competition else None),
    )
    best_suggestion = suggested_domain_events[0] if suggested_domain_events else None
    suggested_domain_event = best_suggestion["event"] if best_suggestion else None
    suggested_match_score = best_suggestion["score"] if best_suggestion else 0

    # Sport: no suggestions or fuzzy when unmapped — UI shows dropdown of domain sports + Map button only
    suggested_sports = []

    # Entity suggestions: best match per field (for prefill / match %)
    sport_id_for_suggest = r_sport["domain_id"] if r_sport else (suggested_sports[0]["domain_id"] if suggested_sports else None)
    category_id_for_suggest = None

    # Category: only when the feed exposes a native category field (e.g. Bwin region); do not infer from league name.
    cat_candidates = _suggest_entity_by_name("categories", (event.get("category") or "").strip(), sport_id_for_suggest)
    raw_cat = (event.get("category") or "").strip()
    best_cat = cat_candidates[0] if cat_candidates else None
    suggested_category = best_cat if (best_cat and (best_cat.get("match_pct") or 0) >= 55) else ({"name": raw_cat, "match_pct": 0} if raw_cat else None)
    if isinstance(suggested_category, dict) and suggested_category.get("name"):
        cat_ent = next((c for c in DOMAIN_ENTITIES["categories"] if c["name"] == suggested_category["name"] and c.get("sport_id") == sport_id_for_suggest), None)
        if cat_ent:
            category_id_for_suggest = cat_ent["domain_id"]
            suggested_category = dict(suggested_category)
            suggested_category["domain_id"] = cat_ent["domain_id"]
            j = (cat_ent.get("country") or cat_ent.get("jurisdiction") or "").strip()
            if j and j != COUNTRY_CODE_NONE:
                suggested_category["country"] = j

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
                    j = (cat_ent.get("country") or cat_ent.get("jurisdiction") or "").strip()
                    if j and j != COUNTRY_CODE_NONE:
                        suggested_entities["category"]["country"] = j
        # Only override competition when feed competition matches domain event competition (≥55%)
        if feed_comp and d_comp and pct_comp >= 55:
            suggested_entities["competition"] = {"name": suggested_domain_event.get("competition") or "", "match_pct": pct_comp, "is_suggested": pct_comp == 0}
    # Ensure is_suggested when match_pct is 0 (raw feed name suggested)
    for key in ("category", "competition", "home", "away"):
        if suggested_entities.get(key):
            suggested_entities[key]["is_suggested"] = (suggested_entities[key].get("match_pct") or 0) == 0

    countries = _load_countries()
    # When feed category matches a country (e.g. Barbados) but not in domain, pre-select that country in dropdown
    if suggested_entities.get("category") and not suggested_entities["category"].get("country"):
        cat_name = (suggested_entities["category"].get("name") or "").strip()
        if cat_name:
            country_match = next((c for c in countries if (c.get("name") or "").strip().lower() == cat_name.lower()), None)
            if country_match and (country_match.get("cc") or "").strip() != COUNTRY_CODE_NONE:
                suggested_entities["category"] = dict(suggested_entities["category"])
                suggested_entities["category"]["country"] = (country_match.get("cc") or "").strip()

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

    exception_categories = [
        c for c in DOMAIN_ENTITIES["categories"]
        if (c.get("country") or c.get("jurisdiction") or "").strip() == COUNTRY_CODE_NONE
    ]

    return templates.TemplateResponse(request, "modal_mapping.html", {
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
        "mapping_domain_sport_id": domain_sport_id or "",
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
    return templates.TemplateResponse(request, "feeder_events/modal_feeder_notes.html", {
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
    """Returns the HTML partial for the Feeder Event Log modal (appeared, mapped, domain_created, notes, ignored, etc.)."""
    feed_provider = (feed_provider or "").strip()
    entries = _get_event_log_entries(feed_provider, valid_id)
    event_label = _feeder_event_label(feed_provider, valid_id)
    return templates.TemplateResponse(request, "feeder_events/modal_feeder_event_log.html", {
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
    return templates.TemplateResponse(request, "partials/notifications_unconfirmed.html", {
        "request": request,
        "notifications": items,
    })


@app.post("/api/notifications/{notification_id}/confirm")
async def api_confirm_notification(notification_id: str):
    """Mark notification as confirmed (user read and acknowledged)."""
    ok = _confirm_notification(notification_id)
    return {"ok": ok}


@app.get("/alerts", response_class=HTMLResponse)
async def alerts_history_page(
    request: Request,
    status: str | None = None,
    alert_type: str | None = None,
    feed: str | None = None,
    page: int = 1,
    per_page: int = 50,
):
    """Operational alerts queue (CSV-backed); filters are query params for dashboard deep links."""
    rows, total = alerts_csv.list_alerts_filtered(
        status=status,
        alert_type_code=alert_type,
        feed_code=feed,
        page=page,
        per_page=per_page,
    )
    open_n = alerts_csv.count_open()
    return templates.TemplateResponse(
        request,
        "alerts/history.html",
        {
            "request": request,
            "section": "alerts",
            "alerts": rows,
            "alerts_total": total,
            "alerts_page": max(1, page),
            "alerts_per_page": max(1, min(per_page, 200)),
            "filter_status": (status or "").strip(),
            "filter_alert_type": (alert_type or "").strip(),
            "filter_feed": (feed or "").strip(),
            "alerts_open_count": open_n,
            "alert_types": alerts_csv.load_types(),
        },
    )


@app.get("/api/alerts/open-count")
async def api_alerts_open_count():
    return {"open_count": alerts_csv.count_open()}


@app.get("/api/alerts")
async def api_alerts_list(
    status: str | None = None,
    alert_type: str | None = None,
    feed: str | None = None,
    page: int = 1,
    per_page: int = 50,
):
    rows, total = alerts_csv.list_alerts_filtered(
        status=status,
        alert_type_code=alert_type,
        feed_code=feed,
        page=page,
        per_page=per_page,
    )
    return {
        "items": rows,
        "total": total,
        "page": max(1, page),
        "per_page": max(1, min(per_page, 200)),
    }


@app.post("/api/alerts/{alert_id}/ack")
async def api_alerts_ack(alert_id: str):
    ok = alerts_csv.transition_alert(alert_id, "ack")
    return {"ok": ok}


@app.post("/api/alerts/{alert_id}/hide")
async def api_alerts_hide(alert_id: str):
    ok = alerts_csv.transition_alert(alert_id, "hide")
    return {"ok": ok}


@app.post("/api/alerts/{alert_id}/resolve")
async def api_alerts_resolve(alert_id: str):
    ok = alerts_csv.transition_alert(alert_id, "resolve")
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
    if is_ignored:
        _remove_valid_id_from_feed_dashboard_new((feed_provider or "").strip().lower(), str(feed_valid_id))
        _invalidate_dashboard_feed_stats_cache()
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
    domain_sport_id: str = Query(..., description="Domain sport id (e.g. S-1) to resolve feed's sport id"),
):
    """
    Return unique markets from a feed JSON for the given feed and sport.
    Resolves feed sport id from sport_feed_mappings.csv. If no mapping, returns [].
    Each item: { id, name, is_prematch, feed_name }.
    """
    mapping = next(
        (m for m in SPORT_FEED_MAPPINGS
         if entity_ids_equal(m.get("domain_id"), domain_sport_id)
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
    domain_event_id: str = Query(..., description="Domain event id (e.g. E-1)"),
    domain_market_id: str = Query(..., description="Domain market type id (e.g. M-3)"),
    line: str | None = Query(None, description="Selected line for handicap/total (e.g. -0.5, 184.5); used when all_lines is false"),
    all_lines: bool = Query(True, description="When true, return every offered line per feed (paired sides) where supported"),
):
    """Return feed odds for the selected market from each mapped feed (from cached event details)."""
    rows = _get_feed_odds_for_event_market(domain_event_id, domain_market_id, line, all_lines=all_lines)
    return {"feed_odds": rows}


@app.get("/api/event-details/brand-overview-margined")
async def api_event_details_brand_overview_margined(
    domain_event_id: str = Query(..., description="Domain event id (e.g. E-1)"),
    domain_market_id: str = Query(..., description="Domain market type id (e.g. M-3)"),
    line: str | None = Query(None, description="Same line filter as feed odds when the market has lines"),
):
    """
    Brand Overview: source fair odds (Pricing Feed order + log de-vig when configured, else IMLog basis)
    → per-brand margined decimals using PM%% from Margin templates and log2 (``internal_pricing.transforms.log2_function``).

    ``input_pm_margin_pct`` is the **configured** prematch margin from the template (used for log2 pricing).
    The event-details UI shows **M** as the implied book %% from the displayed margined odds (same formula as Feed Odds).
    """
    from backend.internal_pricing.transforms.log2_function import true_odds_to_margined_odds_log2

    eid = str(domain_event_id).strip()
    ev = next((e for e in DOMAIN_EVENTS if (e.get("id") or "").strip() == eid), None)
    if not ev:
        return JSONResponse({"ok": False, "message": "Domain event not found"}, status_code=404)
    line_q = (line or "").strip() or None
    true_prices, im_used, n_sel = _imlog_true_prices_for_event_market(eid, domain_market_id, line_q)

    brands = _load_brands()
    out: list[dict] = []
    for br in brands:
        bid = int(br["id"])
        pm, tname = _prematch_pm_pct_and_template_name(bid, ev)
        if not im_used or pm is None:
            out.append({
                "id": bid,
                "name": (br.get("name") or "").strip(),
                "input_pm_margin_pct": pm,
                "template_name": tname,
                "outcomes": [None] * len(true_prices) if true_prices else [],
            })
            continue
        margined: list[float | None] = []
        for tp in true_prices:
            if tp is None or tp <= 0:
                margined.append(None)
            else:
                mo = true_odds_to_margined_odds_log2(tp, pm, n_outcomes=(n_sel if n_sel > 0 else None))
                margined.append(mo)
        out.append({
            "id": bid,
            "name": (br.get("name") or "").strip(),
            "input_pm_margin_pct": pm,
            "template_name": tname,
            "outcomes": margined,
        })
    return {
        "conversion": "log2",
        "imlog_used": im_used,
        "pricing_feed_used": im_used,
        "brands": out,
    }


@app.get("/api/event-details/overview-margined-prices")
async def api_event_details_overview_margined_prices(
    domain_event_id: str = Query(..., description="Domain event id (e.g. E-1)"),
    domain_market_id: str = Query(..., description="Domain market type id (e.g. M-3)"),
    line: str | None = Query(None, description="Same line filter as feed odds when the market has lines"),
    pricing_brand_id: str | None = Query(
        None,
        description="Empty / omitted / 'global' = Global margin scope; else numeric brand id",
    ),
):
    """
    Markets overview (center column): fair odds from Pricing Feed order (log de-vig) when configured,
    else legacy IMLog basis → margined decimals for one brand scope (Global or a specific brand), same log2 as Brand Overview.
    """
    from backend.internal_pricing.transforms.log2_function import true_odds_to_margined_odds_log2

    eid = str(domain_event_id).strip()
    ev = next((e for e in DOMAIN_EVENTS if (e.get("id") or "").strip() == eid), None)
    if not ev:
        return JSONResponse({"ok": False, "message": "Domain event not found"}, status_code=404)
    raw = (pricing_brand_id or "").strip()
    if raw == "" or raw.lower() == "global":
        pb: int | None = None
    else:
        try:
            pb = int(raw)
        except (TypeError, ValueError):
            pb = None
    line_q = (line or "").strip() or None
    true_prices, im_used, n_sel = _imlog_true_prices_for_event_market(eid, domain_market_id, line_q)
    pm, tname = _prematch_pm_pct_for_pricing_scope(ev, pb)
    if not im_used or pm is None:
        empty = [None] * len(true_prices) if true_prices else []
        return {
            "ok": True,
            "conversion": "log2",
            "imlog_used": im_used,
            "pricing_feed_used": im_used,
            "input_pm_margin_pct": pm,
            "template_name": tname,
            "true_prices": true_prices,
            "outcomes": empty,
        }
    margined: list[float | None] = []
    for tp in true_prices:
        if tp is None or tp <= 0:
            margined.append(None)
        else:
            mo = true_odds_to_margined_odds_log2(tp, pm, n_outcomes=(n_sel if n_sel > 0 else None))
            margined.append(mo)
    return {
        "ok": True,
        "conversion": "log2",
        "imlog_used": im_used,
        "pricing_feed_used": im_used,
        "input_pm_margin_pct": pm,
        "template_name": tname,
        "true_prices": true_prices,
        "outcomes": margined,
    }


@app.get("/api/event-details/internal-model")
async def api_event_details_internal_model(
    domain_event_id: str = Query(..., description="Domain event id (e.g. E-1)"),
    domain_market_id: str = Query(..., description="Domain market id (e.g. M-12)"),
    market_name: str = Query("", description="Selected market display name (used to detect Correct Set Score)"),
    line: str | None = Query(None, description="Optional line filter (same as feed odds); strip ★ when matching"),
):
    """Volleyball + Correct Set Score: de-vig feed odds per feed, average true odds/probs; persist under data/internal_feed/."""
    from backend.internal_pricing.sports.volleyball.correct_set_score import (
        compute_correct_set_score_internal,
        is_correct_set_score_market,
        is_volleyball_sport,
    )
    from backend.internal_pricing.storage import save_snapshot

    eid = str(domain_event_id).strip()
    ev = next((e for e in DOMAIN_EVENTS if (e.get("id") or "").strip() == eid), None)
    if not ev:
        return JSONResponse({"supported": False, "message": "Domain event not found"}, status_code=404)
    sport_name = (ev.get("sport") or "").strip()
    if not is_volleyball_sport(sport_name):
        return {"supported": False, "message": "Internal model here is only implemented for Volleyball."}
    if not is_correct_set_score_market(market_name):
        return {"supported": False, "message": "Select Correct Set Score to see the internal model."}

    dmid = fid_str(domain_market_id)
    market = next((m for m in (DOMAIN_ENTITIES.get("markets") or []) if fid_str(m.get("domain_id")) == dmid), None)
    if not market:
        return {"supported": False, "message": "Market not found."}
    sid = _event_sport_id(ev)
    labels, _otype = _get_outcome_labels_for_market(market, sid)
    if not labels:
        return {
            "supported": True,
            "sport": sport_name,
            "market_model": "correct_set_score",
            "column_labels": [],
            "averaged": [],
            "per_feed": [],
            "feeds_used": 0,
            "message": "This market has no fixed outcome template; internal model needs outcome labels.",
        }

    line_clean = (line or "").strip() or None
    use_all_lines = line_clean is None
    rows = _get_feed_odds_for_event_market(
        eid, domain_market_id, line_clean, all_lines=use_all_lines, exclude_feed_codes=frozenset({"imlog"})
    )
    comp = compute_correct_set_score_internal(rows, line_clean, labels)
    averaged = comp.get("averaged_outcomes") or []
    feeds_used = int(comp.get("feeds_used") or 0)
    margin_pct = round(sum(float(x.get("true_prob") or 0) for x in averaged) * 100.0, 1) if averaged else None
    odds_margin_pct = None
    if averaged:
        odds_margin_pct = round(sum(1.0 / float(x["true_odds"]) for x in averaged) * 100.0, 1)

    save_payload = {
        "domain_event_id": eid,
        "domain_market_id": dmid,
        "line": line_clean,
        "market_name": (market_name or "").strip(),
        "sport": sport_name,
        "supported": True,
        "market_model": "correct_set_score",
        "feeds_used": feeds_used,
        "per_feed": comp.get("per_feed") or [],
        "averaged_outcomes": averaged,
        "true_prob_sum_pct": margin_pct,
        "true_odds_margin_pct": odds_margin_pct,
    }
    try:
        save_snapshot(config.INTERNAL_FEED_DATA_DIR, eid, dmid, save_payload)
    except OSError:
        pass

    if averaged:
        try:
            from backend.internal_pricing.imlog_sync import imlog_event_file_path, sync_imlog_event_json

            def _feed_odds_no_imlog(eid_: str, mid_: str | int, ln_: str | None, aln_: bool) -> list[dict]:
                return _get_feed_odds_for_event_market(
                    eid_, mid_, ln_, aln_, exclude_feed_codes=frozenset({"imlog"})
                )

            sync_imlog_event_json(
                domain_event_id=eid,
                domain_event=ev,
                markets_bucket=DOMAIN_ENTITIES.get("markets") or [],
                get_feed_odds_fn=_feed_odds_no_imlog,
                get_outcome_labels_fn=_get_outcome_labels_for_market,
                entity_ids_equal_fn=entity_ids_equal,
                sport_id=sid,
                out_path=imlog_event_file_path(config.FEED_EVENT_DETAILS_DIR, eid),
                declared_feed_sport_id=_feed_sport_id_from_sport_feed_mappings(sid, "imlog"),
            )
        except Exception:
            logging.getLogger(__name__).exception("IMLog event JSON sync failed for %s", eid)

    if not averaged:
        return {
            "supported": True,
            "sport": sport_name,
            "market_model": "correct_set_score",
            "column_labels": labels,
            "averaged": [],
            "per_feed": comp.get("per_feed") or [],
            "feeds_used": feeds_used,
            "true_prob_sum_pct": margin_pct,
            "true_odds_margin_pct": None,
            "message": "No complete feed odds to average (each feed needs all template outcomes with valid prices).",
        }

    return {
        "supported": True,
        "sport": sport_name,
        "market_model": "correct_set_score",
        "column_labels": labels,
        "averaged": averaged,
        "per_feed": comp.get("per_feed") or [],
        "feeds_used": feeds_used,
        "true_prob_sum_pct": margin_pct,
        "true_odds_margin_pct": odds_margin_pct,
    }


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
        if not fid or pid is None:
            continue
        if pid in bet365_codes:
            fid = _normalize_bet365_feed_market_id(fid)
        if pid in bet365_codes and fid == "910000":
            name = (m.get("feed_market_name") or "").strip()
            suffix = game_lines_names.get(name)
            if suffix:
                keys.add(f"{pid}|910000_{suffix}")
            else:
                keys.add(f"{pid}|910000_1")
                keys.add(f"{pid}|910000_2")
                keys.add(f"{pid}|910000_3")
        elif pid in bet365_codes and fid.startswith("910000_"):
            keys.add(f"{pid}|{fid}")
        elif pid in bet365_codes and fid == "910204":
            name = (m.get("feed_market_name") or "").strip()
            suffix = set1_lines_names.get(name)
            if suffix:
                keys.add(f"{pid}|910204_{suffix}")
            else:
                keys.add(f"{pid}|910204_1")
                keys.add(f"{pid}|910204_2")
                keys.add(f"{pid}|910204_3")
        elif pid in bet365_codes and fid.startswith("910204_"):
            keys.add(f"{pid}|{fid}")
        else:
            keys.add(f"{pid}|{fid}")
    return {"mapped_keys": list(keys)}


@app.get("/api/market-type-mappings")
async def api_get_market_type_mappings(
    domain_market_id: str = Query(..., description="Domain market type id (e.g. M-3)"),
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
    want_mid = fid_str(domain_market_id)
    for m in mappings:
        if fid_str(m.get("domain_market_id")) != want_mid:
            continue
        fid_raw = (m.get("feed_market_id") or "").strip()
        if m["feed_provider_id"] in bet365_codes:
            fid_raw = _normalize_bet365_feed_market_id(fid_raw)
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
        raise HTTPException(status_code=400, detail="The 'None' option is reserved for no country and cannot be modified.")
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


def _rbac_build_menu_branch_view_codes() -> dict[str, frozenset[str]]:
    """Top-level menu labels (with children) → all menu view codes in that branch (parent + descendants)."""

    def collect(item: dict) -> set[str]:
        s: set[str] = set()
        v = item.get("view")
        if v:
            s.add(v)
        for ch in item.get("children") or []:
            s |= collect(ch)
        return s

    out: dict[str, frozenset[str]] = {}
    for top in config.RBAC_MENU_SOURCE:
        if top.get("children"):
            out[top["label"]] = frozenset(collect(top))
    return out


RBAC_MENU_BRANCH_VIEW_CODES: dict[str, frozenset[str]] = _rbac_build_menu_branch_view_codes()

_RBAC_ADMIN_MENU_ANY = frozenset(
    {
        "menu.admin.view",
        "menu.admin.users.view",
        "menu.admin.roles_permissions.view",
    }
)

# User admin JSON APIs under /api/rbac/users (longer prefix than /api/rbac).
_RBAC_API_USERS_ANY = frozenset(
    {
        "menu.admin.view",
        "menu.admin.users.view",
        "rbac.users.create",
        "rbac.users.edit",
        "rbac.users.audit",
    }
)

# Longest prefix first: first match wins. User needs at least one code in the frozenset.
_RBAC_PATH_GATE: list[tuple[str, frozenset[str]]] = sorted(
    [
        # Not assignable in Roles & Permissions — SuperAdmin bypasses path gate in _rbac_forbidden_if_path_denied.
        ("/admin/dump-csv-data", frozenset({"__rbac.internal.superadmin_data_tools_only__"})),
        ("/notifications/unconfirmed", frozenset({"menu.notifications.view"})),
        ("/modal/feeder-event-log", frozenset({"menu.betting_program.feeder_events.view"})),
        ("/modal/feeder-event-notes", frozenset({"menu.betting_program.feeder_events.view"})),
        ("/modal/map-event", frozenset({"menu.betting_program.feeder_events.view"})),
        ("/event-navigator", frozenset({"menu.betting_program.event_navigator.view"})),
        ("/feeder-events", frozenset({"menu.betting_program.feeder_events.view"})),
        ("/archived-events", frozenset({"menu.betting_program.archived_events.view"})),
        (
            "/api/search-domain-events",
            frozenset(
                {
                    "menu.betting_program.event_navigator.view",
                    "menu.betting_program.feeder_events.view",
                }
            ),
        ),
        ("/api/rbac/users", _RBAC_API_USERS_ANY),
        ("/api/rbac", _RBAC_ADMIN_MENU_ANY),
        ("/users", _RBAC_ADMIN_MENU_ANY),
        ("/entities", frozenset({"menu.configuration.entities.view"})),
        ("/localization", frozenset({"menu.configuration.localization.view"})),
        ("/brands", frozenset({"menu.configuration.brands.view"})),
        ("/feeders", frozenset({"menu.configuration.feeders.view"})),
        ("/margin", frozenset({"menu.configuration.margin.view"})),
        ("/risk-rules", frozenset({"menu.configuration.risk_rules.view"})),
        ("/compliance", frozenset({"menu.configuration.compliance.view"})),
        ("/pull-feeds", frozenset({"menu.dashboard.view"})),
        ("/api/dashboard-feed-stats", frozenset({"menu.dashboard.view"})),
        ("/api/alerts", frozenset({"menu.alerts.view"})),
        ("/alerts", frozenset({"menu.alerts.view"})),
    ],
    key=lambda x: len(x[0]),
    reverse=True,
)


def _rbac_effective_permissions_for_uid(user_id: int) -> set[str]:
    """Role permissions plus always-granted menu views (dashboard, notifications, profile).

    Platform / Internal users (partner_id None) also receive the full configured RBAC code set so
    menu and path checks work when role_permissions.csv was never populated with menu.*.view rows
    (common on older server data). Partner-scoped users stay CSV-only plus always-granted.
    """
    raw = _get_user_permissions(user_id)
    always = set(config.RBAC_ALWAYS_GRANTED_PERMISSIONS)
    users = _load_rbac_users()
    u = next((x for x in users if x.get("user_id") == user_id), None)
    if u and u.get("active", True) and u.get("partner_id") is None:
        return set(config.rbac_all_permission_codes()) | raw | always
    return raw | always


def _rbac_required_permissions_for_path(path: str) -> frozenset[str] | None:
    """If set, the actor must hold at least one of these codes. None = no page-level RBAC rule."""
    if path == "/":
        return frozenset({"menu.dashboard.view"})
    for prefix, codes in _RBAC_PATH_GATE:
        if path.startswith(prefix):
            return codes
    return None


def _rbac_nav_enforced(request: Request) -> bool:
    return bool(config.GMP_DEV_LOGIN or config.RBAC_TRUST_ACTOR_HEADER)


def _rbac_actor_has_permission_code(request: Request, code: str) -> bool:
    if not _rbac_nav_enforced(request):
        return True
    if _rbac_actor_is_superadmin(request):
        return True
    uid = _rbac_actor_user_id_from_request(request)
    if uid is None:
        return False
    return code in _rbac_effective_permissions_for_uid(uid)


def _rbac_require_permission_code(request: Request, code: str) -> None:
    if not _rbac_actor_has_permission_code(request, code):
        raise HTTPException(status_code=403, detail=f"Missing permission: {code}")


def _rbac_require_any_permission_codes(request: Request, *codes: str) -> None:
    """Actor must hold at least one of the given permission codes."""
    if not codes:
        return
    if not _rbac_nav_enforced(request):
        return
    if _rbac_actor_is_superadmin(request):
        return
    uid = _rbac_actor_user_id_from_request(request)
    if uid is None:
        raise HTTPException(status_code=403, detail="Missing permission")
    perms = _rbac_effective_permissions_for_uid(uid)
    if any(c in perms for c in codes):
        return
    raise HTTPException(status_code=403, detail=f"Missing one of: {', '.join(codes)}")


def _rbac_require_superadmin(request: Request) -> None:
    """Break-glass tools (e.g. CSV reset). Not an assignable permission — only users with is_superadmin."""
    if not _rbac_actor_is_superadmin(request):
        raise HTTPException(status_code=403, detail="SuperAdmin only.")


def _build_superadmin_csv_catalog() -> list[tuple[str, Path, str]]:
    """(api_key, resolved_path, display_label) — only paths under data/ for read-only preview."""
    root = config.DATA_DIR.resolve()
    out: list[tuple[str, Path, str]] = []

    def add(key: str, path: Path | None, label: str) -> None:
        if path is None:
            return
        try:
            rp = path.resolve()
        except (OSError, RuntimeError):
            return
        rroot = str(root) + os.sep
        rs = str(rp)
        if rp != root and not rs.startswith(rroot):
            return
        out.append((key, rp, label))

    add("feeds", config.FEEDS_PATH, "feeds.csv")
    add("sports", config.DATA_DIR / "sports.csv", "sports.csv")
    add("categories", config.DATA_DIR / "categories.csv", "categories.csv")
    add("competitions", config.DATA_DIR / "competitions.csv", "competitions.csv")
    add("teams", config.DATA_DIR / "teams.csv", "teams.csv")
    add("markets", config.DATA_DIR / "markets.csv", "markets.csv")
    add("domain_events", config.DOMAIN_EVENTS_PATH, "domain_events.csv")
    add("event_mappings", config.EVENT_MAPPINGS_PATH, "event_mappings.csv")
    add("entity_feed_mappings", config.ENTITY_FEED_MAPPINGS_PATH, "entity_feed_mappings.csv")
    add("sport_feed_mappings", config.SPORT_FEED_MAPPINGS_PATH, "sport_feed_mappings.csv")
    add("partners", config.PARTNERS_PATH, "partners.csv")
    add("brands", config.BRANDS_PATH, "brands.csv")
    add("languages", config.LANGUAGES_PATH, "languages.csv")
    add("translations", config.TRANSLATIONS_PATH, "translations.csv")
    add("feed_sports", config.FEED_SPORTS_PATH, "feed_sports.csv")
    add("feed_time_statuses", config.FEED_TIME_STATUSES_PATH, "feed_time_statuses.csv")
    add("feed_last_pull", config.FEED_LAST_PULL_PATH, "feed_last_pull.csv")
    add("feeder_config", config.FEEDER_CONFIG_PATH, "feeder_config.csv")
    add("feeder_incidents", config.FEEDER_INCIDENTS_PATH, "feeder_incidents.csv")
    add("feeder_ignored_events", config.FEEDER_IGNORED_EVENTS_PATH, "feeder_ignored_events.csv")
    add("feeder_event_notes", config.FEEDER_EVENT_NOTES_PATH, "feeder_event_notes.csv")
    add("margin_templates", config.MARGIN_TEMPLATES_PATH, "margin_templates.csv")
    add("margin_template_competitions", config.MARGIN_TEMPLATE_COMPETITIONS_PATH, "margin_template_competitions.csv")
    add("participant_type", config.PARTICIPANT_TYPE_PATH, "countries/participant_type.csv")
    add("underage_categories", config.UNDERAGE_CATEGORIES_PATH, "countries/underage_categories.csv")
    add("market_templates", config.MARKET_TEMPLATES_PATH, "markets/market_templates.csv")
    add("market_period_type", config.MARKET_PERIOD_TYPE_PATH, "markets/market_period_type.csv")
    add("market_score_type", config.MARKET_SCORE_TYPE_PATH, "markets/market_score_type.csv")
    add("market_groups", config.MARKET_GROUPS_PATH, "markets/market_groups.csv")
    add("market_type_mappings", config.MARKET_TYPE_MAPPINGS_PATH, "markets/market_type_mappings.csv")
    add("market_outcomes", config.MARKET_OUTCOMES_PATH, "markets/market_outcomes.csv")
    add("onexbet_market_names", config.ONEXBET_MARKET_NAMES_PATH, "markets/1xbet_market_names.csv")
    add("rbac_users", config.RBAC_USERS_PATH, "rbac/users.csv")
    add("rbac_roles", config.RBAC_ROLES_PATH, "rbac/roles.csv")
    add("rbac_user_roles", config.RBAC_USER_ROLES_PATH, "rbac/user_roles.csv")
    add("rbac_role_permissions", config.RBAC_ROLE_PERMISSIONS_PATH, "rbac/role_permissions.csv")
    add("rbac_user_brands", config.RBAC_USER_BRANDS_PATH, "rbac/user_brands.csv")
    add("rbac_audit_log", config.RBAC_AUDIT_LOG_PATH, "rbac/rbac_audit_log.csv")
    add("platform_notes", config.NOTES_PATH, "notes/platform_notes.csv")
    add("platform_notifications", config.NOTIFICATIONS_PATH, "notes/platform_notifications.csv")
    add("alert_types", config.ALERT_TYPES_PATH, "notes/alert_types.csv")
    add("alerts", config.ALERTS_PATH, "notes/alerts.csv")
    add("event_navigator_notes", config.EVENT_NAVIGATOR_NOTES_PATH, "notes/event_navigator_notes.csv")
    add("admin_audit_log", config.ADMIN_AUDIT_LOG_PATH, "audit/admin_audit_log.csv")
    add("feeder_event_log", config.FEEDER_EVENT_LOG_PATH, "audit/feeder_event_log.csv")
    add("domain_event_log", config.DOMAIN_EVENT_LOG_PATH, "audit/domain_event_log.csv")
    leg = getattr(config, "NOTES_PATH_LEGACY", None)
    if leg:
        add("platform_notes_legacy", leg, "platform_notes.csv (legacy)")
    return out


_SUPERADMIN_CSV_CATALOG: list[tuple[str, Path, str]] = _build_superadmin_csv_catalog()


def _superadmin_csv_path_for_key(key: str) -> Path | None:
    for k, p, _ in _SUPERADMIN_CSV_CATALOG:
        if k == key:
            return p
    return None


def _superadmin_read_csv_preview(path: Path, offset: int, limit: int) -> dict:
    """Read UTF-8 CSV slice; offset/limit apply to data rows after header."""
    offset = max(0, min(int(offset), 500_000))
    limit = max(1, min(int(limit), 200))
    if not path.exists():
        return {
            "ok": False,
            "error": "file_not_found",
            "headers": [],
            "rows": [],
            "offset": offset,
            "limit": limit,
            "has_more": False,
        }
    headers: list[str] = []
    rows: list[list[str]] = []
    has_more = False
    data_idx = 0
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f)
        headers = next(reader, [])
        for row in reader:
            if data_idx < offset:
                data_idx += 1
                continue
            if len(rows) >= limit:
                has_more = True
                break
            rows.append(row)
            data_idx += 1
    return {
        "ok": True,
        "headers": headers,
        "rows": rows,
        "offset": offset,
        "limit": limit,
        "has_more": has_more,
    }


def _rbac_superadmin_shell_redirect_if_needed(request: Request) -> RedirectResponse | None:
    """SuperAdmin day-to-day shell: only dashboard, user admin, data tools, dev auth, static, notifications HTMX, APIs."""
    if not _rbac_nav_enforced(request):
        return None
    if not _rbac_actor_is_superadmin(request):
        return None
    method = (request.method or "GET").upper()
    if method not in ("GET", "HEAD"):
        return None
    path = request.url.path
    if path.startswith("/api/"):
        return None
    if path.startswith("/static/"):
        return None
    if path in frozenset({"/", "/users", "/admin/dump-csv-data"}):
        return None
    if path.startswith("/dev/"):
        return None
    if path.startswith("/notifications/unconfirmed"):
        return None
    if path in ("/favicon.ico",):
        return None
    return RedirectResponse(url="/users", status_code=303)


# Plural entity_type from /api/entities* → RBAC prefix (matches RBAC_ENTITY_CRUD / tree).
_ENTITY_TYPE_TO_PERM_PREFIX: dict[str, str] = {
    "sports": "entity.sport",
    "categories": "entity.category",
    "competitions": "entity.competition",
    "teams": "entity.team",
    "markets": "entity.markets",
}


def _rbac_require_entity_perm(request: Request, entity_type_plural: str, action: str) -> None:
    prefix = _ENTITY_TYPE_TO_PERM_PREFIX.get(entity_type_plural)
    if prefix is None:
        raise HTTPException(status_code=400, detail=f"Unknown entity type: {entity_type_plural}")
    _rbac_require_permission_code(request, f"{prefix}.{action}")


def _rbac_enforce_api_permissions(request: Request) -> None:
    """Granular RBAC for JSON/HTML API routes. Skips when RBAC not enforced; /api/entities* uses body-aware checks in handlers."""
    if not _rbac_nav_enforced(request):
        return
    path = request.url.path
    method = (request.method or "GET").upper()
    if not path.startswith("/api/"):
        return
    if path.startswith("/api/entities"):
        return
    if method in ("OPTIONS", "HEAD"):
        return

    # --- Admin: RBAC users ---
    if re.fullmatch(r"/api/rbac/users", path):
        if method == "GET":
            _rbac_require_permission_code(request, "menu.admin.users.view")
        elif method == "POST":
            _rbac_require_permission_code(request, "rbac.users.create")
        else:
            raise HTTPException(status_code=403, detail=f"Missing permission for {method} {path}")
        return
    if re.fullmatch(r"/api/rbac/users/\d+/audit", path):
        if method == "GET":
            _rbac_require_permission_code(request, "rbac.users.audit")
        else:
            raise HTTPException(status_code=403, detail=f"Missing permission for {method} {path}")
        return
    if re.fullmatch(r"/api/rbac/users/\d+", path):
        if method == "GET":
            _rbac_require_permission_code(request, "rbac.users.edit")
        elif method in ("PUT", "DELETE"):
            _rbac_require_permission_code(request, "rbac.users.edit")
        else:
            raise HTTPException(status_code=403, detail=f"Missing permission for {method} {path}")
        return

    # --- Admin: roles & audit log ---
    if re.fullmatch(r"/api/rbac/roles", path):
        if method == "GET":
            _rbac_require_any_permission_codes(
                request,
                "menu.admin.view",
                "menu.admin.users.view",
                "menu.admin.roles_permissions.view",
            )
        elif method == "POST":
            _rbac_require_permission_code(request, "rbac.roles.manage")
        else:
            raise HTTPException(status_code=403, detail=f"Missing permission for {method} {path}")
        return
    if re.fullmatch(r"/api/rbac/roles/\d+/permissions", path) and method == "PUT":
        _rbac_require_permission_code(request, "rbac.roles.manage")
        return
    if re.fullmatch(r"/api/rbac/roles/\d+", path) and method == "PUT":
        _rbac_require_permission_code(request, "rbac.roles.manage")
        return
    if re.fullmatch(r"/api/rbac/audit-log", path) and method == "GET":
        _rbac_require_permission_code(request, "rbac.audit.view")
        return

    # --- Margin ---
    if re.fullmatch(r"/api/margin-templates/competitions/assign", path) and method == "POST":
        _rbac_require_permission_code(request, "config.margin.update")
        return
    if re.fullmatch(r"/api/margin-templates/copy-from", path) and method == "POST":
        _rbac_require_permission_code(request, "config.margin.create")
        return
    if re.fullmatch(r"/api/margin-templates/copy-sources", path) and method == "GET":
        _rbac_require_permission_code(request, "config.margin.view")
        return
    if re.fullmatch(r"/api/margin-templates/\d+/competitions", path) and method == "GET":
        _rbac_require_permission_code(request, "config.margin.view")
        return
    if re.fullmatch(r"/api/margin-templates/\d+", path) and method == "PATCH":
        _rbac_require_permission_code(request, "config.margin.update")
        return
    if re.fullmatch(r"/api/margin-templates", path) and method == "POST":
        _rbac_require_permission_code(request, "config.margin.create")
        return

    # --- Partners & brands ---
    if re.fullmatch(r"/api/partners", path) and method == "POST":
        _rbac_require_permission_code(request, "config.partners.create")
        return
    if re.fullmatch(r"/api/partners/\d+", path) and method == "PUT":
        _rbac_require_permission_code(request, "config.partners.update")
        return
    if re.fullmatch(r"/api/brands", path) and method == "POST":
        _rbac_require_permission_code(request, "config.brands.create")
        return
    if re.fullmatch(r"/api/brands/\d+", path) and method == "PUT":
        _rbac_require_permission_code(request, "config.brands.update")
        return

    # --- Localization (upsert endpoints) ---
    if re.fullmatch(r"/api/localization/countries", path) and method == "POST":
        _rbac_require_any_permission_codes(request, "config.localization.create", "config.localization.update")
        return
    if re.fullmatch(r"/api/localization/languages", path) and method == "POST":
        _rbac_require_any_permission_codes(request, "config.localization.create", "config.localization.update")
        return
    if re.fullmatch(r"/api/localization/translations", path) and method == "POST":
        _rbac_require_any_permission_codes(request, "config.localization.create", "config.localization.update")
        return

    # --- Market type mappings ---
    if re.fullmatch(r"/api/market-type-mappings/all-mapped", path) and method == "GET":
        _rbac_require_permission_code(request, "entity.market_type.view")
        return
    if re.fullmatch(r"/api/market-type-mappings", path) and method == "GET":
        _rbac_require_permission_code(request, "entity.market_type.view")
        return
    if re.fullmatch(r"/api/market-type-mappings", path) and method == "POST":
        _rbac_require_permission_code(request, "entity.market_type.update")
        return

    # --- Entities (market groups) ---
    if re.fullmatch(r"/api/market-groups", path) and method == "POST":
        _rbac_require_permission_code(request, "entity.markets.create")
        return

    # --- Domain events & mapping (feeder modal) ---
    if re.fullmatch(r"/api/domain-events", path) and method == "POST":
        _rbac_require_permission_code(request, "entity.event.create")
        return
    if re.fullmatch(r"/api/map-event", path) and method == "POST":
        _rbac_require_permission_code(request, "mapping.update")
        return
    if re.fullmatch(r"/api/search-domain-events", path) and method == "GET":
        _rbac_require_permission_code(request, "betting.feeder_events.view")
        return
    if re.fullmatch(r"/api/feeder-run-auto-map", path) and method == "POST":
        _rbac_require_permission_code(request, "config.feeders.update")
        return

    if re.fullmatch(r"/api/dashboard-feed-stats", path) and method == "GET":
        _rbac_require_permission_code(request, "menu.dashboard.view")
        return

    # --- Alerts (CSV-backed queue) ---
    if re.fullmatch(r"/api/alerts/open-count", path) and method == "GET":
        _rbac_require_permission_code(request, "menu.alerts.view")
        return
    if re.fullmatch(r"/api/alerts", path) and method == "GET":
        _rbac_require_permission_code(request, "menu.alerts.view")
        return
    if re.fullmatch(r"/api/alerts/[^/]+/(ack|hide|resolve)", path) and method == "POST":
        _rbac_require_permission_code(request, "menu.alerts.view")
        return

    # --- Pull feeds (dashboard / feeder tooling) ---
    if re.fullmatch(r"/api/pull-feed", path) and method == "POST":
        _rbac_require_permission_code(request, "config.feeders.update")
        return
    if re.fullmatch(r"/api/pull-feed-all", path) and method == "POST":
        _rbac_require_permission_code(request, "config.feeders.update")
        return

    # --- SuperAdmin: destructive CSV reset (not role-grantable) ---
    if re.fullmatch(r"/api/dump-csv-data", path) and method == "POST":
        _rbac_require_superadmin(request)
        return

    # --- SuperAdmin: read-only CSV catalog / preview (not role-grantable) ---
    if path.startswith("/api/superadmin/"):
        _rbac_require_superadmin(request)
        if re.fullmatch(r"/api/superadmin/csv-files", path) and method == "GET":
            return
        if path.startswith("/api/superadmin/csv-preview") and method == "GET":
            return
        raise HTTPException(status_code=404, detail="Unknown superadmin API endpoint")

    # --- Event navigator ---
    if re.fullmatch(r"/api/event-navigator/notes", path) and method == "POST":
        _rbac_require_permission_code(request, "betting.event_navigator.update")
        return

    # --- Notifications (menu view is always granted but explicit for API) ---
    if re.fullmatch(r"/api/notifications/[^/]+/confirm", path) and method == "POST":
        _rbac_require_permission_code(request, "menu.notifications.view")
        return

    # --- Feeder events ---
    if re.fullmatch(r"/api/feeder-events/set-ignored", path) and method == "POST":
        _rbac_require_permission_code(request, "betting.feeder_events.update")
        return
    if re.fullmatch(r"/api/feed-markets", path) and method == "GET":
        _rbac_require_permission_code(request, "betting.feeder_events.view")
        return
    if re.fullmatch(r"/api/event-details/feed-odds", path) and method == "GET":
        _rbac_require_permission_code(request, "betting.feeder_events.view")
        return
    if re.fullmatch(r"/api/event-details/brand-overview-margined", path) and method == "GET":
        _rbac_require_permission_code(request, "betting.feeder_events.view")
        return
    if re.fullmatch(r"/api/event-details/overview-margined-prices", path) and method == "GET":
        _rbac_require_permission_code(request, "betting.feeder_events.view")
        return
    if re.fullmatch(r"/api/event-details/internal-model", path) and method == "GET":
        _rbac_require_permission_code(request, "betting.feeder_events.view")
        return

    # --- Platform notes (customization.*) ---
    if re.fullmatch(r"/api/notes/[^/]+/delete", path) and method == "POST":
        _rbac_require_permission_code(request, "customization.delete")
        return
    if re.fullmatch(r"/api/notes/[^/]+", path) and method == "PATCH":
        _rbac_require_permission_code(request, "customization.update")
        return
    if re.fullmatch(r"/api/notes", path) and method == "POST":
        _rbac_require_permission_code(request, "customization.create")
        return

    # --- Feeder configuration ---
    if re.fullmatch(r"/api/feed-sports", path) and method == "POST":
        _rbac_require_permission_code(request, "config.feeders.update")
        return
    if re.fullmatch(r"/api/admin/audit-log", path) and method == "GET":
        _rbac_require_permission_code(request, "config.feeders.audit")
        return
    if re.fullmatch(r"/api/feeder-config/row", path) and method == "POST":
        _rbac_require_permission_code(request, "config.feeders.update")
        return
    if re.fullmatch(r"/api/feeder-config", path) and method == "POST":
        _rbac_require_permission_code(request, "config.feeders.update")
        return
    if re.fullmatch(r"/api/feeder-incidents", path) and method == "POST":
        _rbac_require_permission_code(request, "config.feeders.update")
        return

    raise HTTPException(
        status_code=403,
        detail=f"RBAC: no permission rule for API {method} {path}",
    )


def _rbac_forbidden_if_path_denied(request: Request):
    """403 / redirect when an identified actor lacks view permission for this path."""
    if not _rbac_nav_enforced(request):
        return None
    path = request.url.path
    if path.startswith("/static"):
        return None
    if _auth_exempt_path(path):
        return None
    uid = _rbac_actor_user_id_from_request(request)
    if uid is None:
        return None
    if _rbac_actor_is_superadmin(request):
        return None
    need = _rbac_required_permissions_for_path(path)
    if need is None:
        return None
    perms = _rbac_effective_permissions_for_uid(uid)
    if perms & need:
        return None
    denied_url = "/?rbac_denied=1"
    if (request.headers.get("hx-request") or "").lower() == "true":
        return JSONResponse(
            {"detail": "Forbidden"},
            status_code=403,
            headers={"HX-Redirect": denied_url},
        )
    return RedirectResponse(url=denied_url, status_code=303)


def _template_rbac_can_any(request: Request, *codes: str) -> bool:
    if not _rbac_nav_enforced(request):
        return True
    uid = _rbac_actor_user_id_from_request(request)
    if uid is None:
        return True
    if _rbac_actor_is_superadmin(request):
        return True
    perms = _rbac_effective_permissions_for_uid(uid)
    return any(c in perms for c in codes)


def _template_rbac_menu_branch_visible(request: Request, branch_label: str) -> bool:
    if not _rbac_nav_enforced(request):
        return True
    uid = _rbac_actor_user_id_from_request(request)
    if uid is None:
        return True
    if _rbac_actor_is_superadmin(request):
        return True
    codes = RBAC_MENU_BRANCH_VIEW_CODES.get(branch_label, frozenset())
    perms = _rbac_effective_permissions_for_uid(uid)
    return bool(perms & codes)


templates.env.globals["rbac_can_any"] = _template_rbac_can_any
templates.env.globals["rbac_menu_branch_visible"] = _template_rbac_menu_branch_visible
templates.env.globals["rbac_is_superadmin"] = _rbac_actor_is_superadmin


@app.get("/api/rbac/users")
async def list_rbac_users(request: Request, partner_id: Optional[int] = None):
    """List users. If partner_id given, filter to that partner. Partner-scoped sign-in ignores query and only sees own partner."""
    users = _load_rbac_users()
    enf = _rbac_actor_enforced_partner_id(request)
    eff_pid = enf if enf is not None else partner_id
    if eff_pid is not None:
        users = [u for u in users if u.get("partner_id") == eff_pid]
    roles = _load_rbac_roles()
    user_roles = _load_rbac_user_roles()
    role_by_id = {r["role_id"]: r for r in roles}
    partners = _load_partners()
    partner_by_id = {p["id"]: p for p in partners}
    out_users = []
    for u in users:
        row = {**u}
        row["roles"] = [
            role_by_id[ur["role_id"]]
            for ur in user_roles
            if ur["user_id"] == u["user_id"] and ur["role_id"] in role_by_id
        ]
        row["partner_name"] = partner_by_id.get(u["partner_id"], {}).get("name", "") if u.get("partner_id") else config.RBAC_PLATFORM_SCOPE_LABEL
        row["online"] = _rbac_user_presence_online(row.get("user_id"))
        ld, lst = _rbac_last_login_display_and_stale(row.get("last_login"))
        row["last_login_display"] = ld
        row["last_login_stale"] = lst
        row["modified_by_display"] = _rbac_user_modified_by_display(u)
        out_users.append(_user_without_secret_fields(row))
    return {"users": out_users}


@app.get("/api/rbac/users/{user_id:int}")
async def get_rbac_user(request: Request, user_id: int):
    users = _load_rbac_users()
    user = next((u for u in users if u.get("user_id") == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    _rbac_assert_actor_may_access_user_row(request, user)
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
    pid = user.get("partner_id")
    if pid is None:
        user["partner_name"] = config.RBAC_PLATFORM_SCOPE_LABEL
    else:
        user["partner_name"] = next((p["name"] for p in partners if p["id"] == pid), None) or "—"
    user["online"] = _rbac_user_presence_online(user.get("user_id"))
    ld, lst = _rbac_last_login_display_and_stale(user.get("last_login"))
    user["last_login_display"] = ld
    user["last_login_stale"] = lst
    user["modified_by_display"] = _rbac_user_modified_by_display(user)
    return {"user": _user_without_secret_fields(user)}


def _rbac_audit_actor_label_from_id(actor_user_id: int | None) -> str:
    if actor_user_id is None:
        return "System"
    u = next((x for x in _load_rbac_users() if x.get("user_id") == actor_user_id), None)
    if not u:
        return f"user#{actor_user_id}"
    return ((u.get("email") or u.get("login") or str(actor_user_id)) or "").strip() or f"user#{actor_user_id}"


def _rbac_audit_entries_for_user(user_id: int) -> list[dict]:
    """Chronological audit rows for target_type=user and this user_id (oldest first)."""
    if not RBAC_AUDIT_LOG_PATH.exists():
        return []
    with open(RBAC_AUDIT_LOG_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    uid_str = str(user_id)
    filtered = [
        r
        for r in rows
        if (r.get("target_type") or "").strip() == "user" and (r.get("target_id") or "").strip() == uid_str
    ]
    filtered.sort(key=lambda r: (r.get("created_at") or ""))
    out: list[dict] = []
    for r in filtered:
        aid = _int_or_none(r.get("actor_user_id"))
        was = (r.get("was") or "").strip()
        now = (r.get("now") or "").strip()
        legacy = (r.get("details") or "").strip()
        if not was and not now and legacy:
            was, now = "—", legacy
        out.append({
            "id": r.get("id"),
            "created_at": r.get("created_at") or "",
            "action": r.get("action") or "",
            "was": was or "—",
            "now": now or "—",
            "actor_user_id": aid,
            "actor_label": _rbac_audit_actor_label_from_id(aid),
        })
    return out


@app.get("/api/rbac/users/{user_id:int}/audit")
async def get_rbac_user_audit_log(request: Request, user_id: int):
    users = _load_rbac_users()
    user = next((u for u in users if u.get("user_id") == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    _rbac_assert_actor_may_access_user_row(request, user)
    return {"entries": _rbac_audit_entries_for_user(user_id)}


@app.post("/api/rbac/users")
async def create_rbac_user(request: Request, body: CreateRbacUserRequest):
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
    want_super = bool(body.is_superadmin) if body.is_superadmin is not None else False
    enf = _rbac_actor_enforced_partner_id(request)
    if enf is not None:
        if body.partner_id is not None and int(body.partner_id) != enf:
            raise HTTPException(status_code=403, detail="Cannot create users outside your partner scope")
        if want_super:
            raise HTTPException(status_code=403, detail="Partner-scoped admins cannot create SuperAdmin users")
        effective_partner_id = enf
    else:
        effective_partner_id = body.partner_id
    _rbac_assert_partner_actor_role_and_brand_ids(request, role_ids, body.brand_ids)
    if want_super and not _rbac_can_assign_superadmin(request):
        raise HTTPException(
            status_code=403,
            detail="Only an existing SuperAdmin (X-RBAC-Actor-User-Id) can grant SuperAdmin, or bootstrap when none exists yet.",
        )
    actor_label = _rbac_actor_audit_label(request)
    actor_id = _rbac_actor_user_id_from_request(request)
    new_user = {
        "user_id": uid,
        "login": login,
        "email": email,
        "display_name": (body.display_name or "").strip() or login,
        "active": body.active if body.active is not None else True,
        "partner_id": effective_partner_id,
        "created_by": actor_label,
        "updated_by": actor_label,
        "created_at": now,
        "updated_at": now,
        "last_login": "",
        "online": False,
        "is_superadmin": want_super,
        "login_pin": ""
        if want_super
        else ((body.login_pin or "").strip() or config.GMP_DEFAULT_USER_PIN),
    }
    users.append(new_user)
    _save_rbac_users(users)
    user_roles = _load_rbac_user_roles()
    for rid in role_ids:
        user_roles.append({
            "user_id": uid,
            "role_id": rid,
            "assigned_at": now,
            "assigned_by_user_id": actor_id,
        })
    _save_rbac_user_roles(user_roles)
    if body.brand_ids:
        user_brands = _load_rbac_user_brands()
        for bid in body.brand_ids:
            user_brands.append({"user_id": uid, "brand_id": bid})
        _save_rbac_user_brands(user_brands)
    partner_note = config.RBAC_PLATFORM_SCOPE_LABEL if effective_partner_id is None else f"partner_id={effective_partner_id}"
    role_note = f"role_id={role_ids[0]}" if role_ids else "role=none"
    now_summary = f"email={email}; {partner_note}; {role_note}"
    if body.brand_ids:
        now_summary += f"; brand_ids={sorted(body.brand_ids)}"
    if want_super:
        now_summary += "; is_superadmin=true"
    _rbac_audit_append(actor_id, "user.create", "user", str(uid), was="—", now=now_summary)
    return {"ok": True, "user": _user_without_secret_fields(new_user)}


@app.put("/api/rbac/users/{user_id:int}")
async def update_rbac_user(request: Request, user_id: int, body: UpdateRbacUserRequest):
    users = _load_rbac_users()
    user = next((u for u in users if u.get("user_id") == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    _rbac_assert_actor_may_access_user_row(request, user)
    snap_email = user.get("email")
    snap_login = user.get("login")
    snap_display = user.get("display_name")
    snap_active = bool(user.get("active", True))
    snap_partner = user.get("partner_id")
    snap_sa = bool(user.get("is_superadmin"))
    snap_pin = user.get("login_pin") or ""
    ur0 = _load_rbac_user_roles()
    old_role_ids = sorted([ur["role_id"] for ur in ur0 if ur["user_id"] == user_id])
    ub0 = _load_rbac_user_brands()
    old_brand_ids = sorted([ub["brand_id"] for ub in ub0 if ub["user_id"] == user_id])
    actor_label = _rbac_actor_audit_label(request)
    actor_id = _rbac_actor_user_id_from_request(request)
    enf = _rbac_actor_enforced_partner_id(request)
    if enf is not None:
        if body.partner_id is not None and int(body.partner_id) != enf:
            raise HTTPException(status_code=403, detail="Cannot move users outside your partner scope")
        if body.is_superadmin is True:
            raise HTTPException(status_code=403, detail="Partner-scoped admins cannot grant SuperAdmin")
    if body.role_ids is not None or body.brand_ids is not None:
        _rbac_assert_partner_actor_role_and_brand_ids(
            request,
            list(body.role_ids) if body.role_ids is not None else None,
            list(body.brand_ids) if body.brand_ids is not None else None,
        )
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
    if body.is_superadmin is not None:
        old_sa = bool(user.get("is_superadmin"))
        new_sa = bool(body.is_superadmin)
        if new_sa != old_sa and not _rbac_can_assign_superadmin(request):
            raise HTTPException(
                status_code=403,
                detail="Only SuperAdmin (X-RBAC-Actor-User-Id) can change the SuperAdmin flag after one exists.",
            )
        user["is_superadmin"] = new_sa
    if body.login_pin is not None and not user.get("is_superadmin"):
        user["login_pin"] = (body.login_pin or "").strip() or config.GMP_DEFAULT_USER_PIN
    if body.role_ids is not None:
        role_ids = list(body.role_ids)
        if len(role_ids) > 1:
            raise HTTPException(status_code=400, detail="Each user may have only one role.")
        role_ids = role_ids[:1]
        user_roles = _load_rbac_user_roles()
        user_roles = [ur for ur in user_roles if ur["user_id"] != user_id]
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        for rid in role_ids:
            user_roles.append({
                "user_id": user_id,
                "role_id": rid,
                "assigned_at": now,
                "assigned_by_user_id": actor_id,
            })
        _save_rbac_user_roles(user_roles)
    if body.brand_ids is not None:
        user_brands = _load_rbac_user_brands()
        user_brands = [ub for ub in user_brands if ub["user_id"] != user_id]
        for bid in body.brand_ids:
            user_brands.append({"user_id": user_id, "brand_id": bid})
        _save_rbac_user_brands(user_brands)
    user["updated_by"] = actor_label
    user["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    _save_rbac_users(users)
    ur1 = _load_rbac_user_roles()
    new_role_ids = sorted([ur["role_id"] for ur in ur1 if ur["user_id"] == user_id])
    ub1 = _load_rbac_user_brands()
    new_brand_ids = sorted([ub["brand_id"] for ub in ub1 if ub["user_id"] == user_id])
    def _pl(pid):
        return config.RBAC_PLATFORM_SCOPE_LABEL if pid is None else str(pid)

    was_parts: list[str] = []
    now_parts: list[str] = []
    if body.email is not None and (snap_email or "") != (user.get("email") or ""):
        was_parts.append(f"email={snap_email or '—'}")
        now_parts.append(f"email={user.get('email')}")
    if body.login is not None and (snap_login or "") != (user.get("login") or ""):
        was_parts.append(f"login={snap_login or '—'}")
        now_parts.append(f"login={user.get('login')}")
    if body.display_name is not None and (snap_display or "") != (user.get("display_name") or ""):
        was_parts.append(f"display_name={snap_display or '—'}")
        now_parts.append(f"display_name={user.get('display_name') or '—'}")
    if body.active is not None and snap_active != bool(user.get("active", True)):
        was_parts.append(f"active={snap_active}")
        now_parts.append(f"active={user.get('active')}")
    if body.partner_id is not None and snap_partner != user.get("partner_id"):
        was_parts.append(f"partner={_pl(snap_partner)}")
        now_parts.append(f"partner={_pl(user.get('partner_id'))}")
    if body.is_superadmin is not None and snap_sa != bool(user.get("is_superadmin")):
        was_parts.append(f"is_superadmin={snap_sa}")
        now_parts.append(f"is_superadmin={user.get('is_superadmin')}")
    if body.role_ids is not None and old_role_ids != new_role_ids:
        was_parts.append(f"role_ids={old_role_ids}")
        now_parts.append(f"role_ids={new_role_ids}")
    if body.brand_ids is not None and old_brand_ids != new_brand_ids:
        was_parts.append(f"brand_ids={old_brand_ids}")
        now_parts.append(f"brand_ids={new_brand_ids}")
    if (
        body.login_pin is not None
        and (body.login_pin or "").strip()
        and not user.get("is_superadmin")
        and snap_pin != (user.get("login_pin") or "")
    ):
        was_parts.append("sign-in PIN=(previous)")
        now_parts.append("sign-in PIN=(updated)")
    if was_parts:
        was_str = "; ".join(was_parts)
        now_str = "; ".join(now_parts) if now_parts else "—"
    else:
        was_str = "—"
        now_str = "— (no tracked field changes)"
    _rbac_audit_append(actor_id, "user.update", "user", str(user_id), was=was_str, now=now_str)
    return {"ok": True, "user": _user_without_secret_fields(user)}


@app.delete("/api/rbac/users/{user_id:int}")
async def delete_rbac_user(request: Request, user_id: int):
    users = _load_rbac_users()
    user = next((u for u in users if u.get("user_id") == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    _rbac_assert_actor_may_access_user_row(request, user)
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
    em = (user.get("email") or "").strip()
    _rbac_audit_append(
        _rbac_actor_user_id_from_request(request),
        "user.delete",
        "user",
        str(user_id),
        was=f"inactive user; email={em}" if em else "inactive user",
        now="Removed from system",
    )
    return {"ok": True}


@app.get("/api/rbac/roles")
async def list_rbac_roles(request: Request):
    roles = _load_rbac_roles()
    enf = _rbac_actor_enforced_partner_id(request)
    if enf is not None:
        roles = [r for r in roles if r.get("partner_id") == enf]
    perms = _load_rbac_role_permissions()
    perms_by_role = {}
    for p in perms:
        perms_by_role.setdefault(p["role_id"], []).append(p["permission_code"])
    for r in roles:
        r["permission_codes"] = perms_by_role.get(r["role_id"], [])
    return {"roles": roles}


@app.post("/api/rbac/roles")
async def create_rbac_role(request: Request, body: CreateRbacRoleRequest):
    """Create a new role. partner_id optional (null = Platform). New roles are non-system."""
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    enf = _rbac_actor_enforced_partner_id(request)
    eff_partner_id = body.partner_id
    if enf is not None:
        if body.partner_id is not None and int(body.partner_id) != enf:
            raise HTTPException(status_code=403, detail="Cannot create roles outside your partner scope")
        eff_partner_id = enf
    roles = _load_rbac_roles()
    next_id = max((r.get("role_id") or 0 for r in roles), default=0) + 1
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    is_master = bool(body.is_master)
    codes_set = {(c or "").strip() for c in (body.permission_codes or []) if (c or "").strip()}
    master_existing = _get_master_role_for_partner(roles, eff_partner_id)
    if not _rbac_request_bypasses_master_caps(request) and not is_master and master_existing is not None and codes_set:
        cap = _permission_codes_for_role_id(int(master_existing["role_id"]))
        over = codes_set - cap
        if over:
            raise HTTPException(
                status_code=400,
                detail=f"Permissions exceed Master role «{master_existing.get('name', master_existing['role_id'])}» for this partner: {sorted(over)}",
            )
    if not _rbac_request_bypasses_master_caps(request) and is_master and eff_partner_id is not None:
        _raise_if_partner_master_exceeds_platform(roles, eff_partner_id, codes_set, False)
    if is_master:
        _clear_master_flag_same_partner(roles, eff_partner_id, except_role_id=None)
    new_role = {
        "role_id": next_id,
        "name": name,
        "active": body.active if body.active is not None else True,
        "is_system": False,
        "partner_id": eff_partner_id,
        "is_master": is_master,
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
    pnote = config.RBAC_PLATFORM_SCOPE_LABEL if eff_partner_id is None else f"partner_id={eff_partner_id}"
    _rbac_audit_append(
        _rbac_actor_user_id_from_request(request),
        "role.create",
        "role",
        str(next_id),
        was="—",
        now=f"name={name}; {pnote}; master={is_master}; permission_count={len(body.permission_codes or [])}",
    )
    return {"ok": True, "role_id": next_id}


@app.put("/api/rbac/roles/{role_id:int}")
async def update_rbac_role(request: Request, role_id: int, body: UpdateRbacRoleRequest):
    """Update role name, active, and/or master flag. Setting is_master true clears master on other roles for the same partner."""
    roles = _load_rbac_roles()
    idx = next((i for i, r in enumerate(roles) if r.get("role_id") == role_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="Role not found")
    row = roles[idx]
    _rbac_assert_actor_may_access_role_row(request, row)
    snap_name = row.get("name")
    snap_active = bool(row.get("active", True))
    snap_master = bool(row.get("is_master"))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    if body.name is not None:
        n = (body.name or "").strip()
        if not n:
            raise HTTPException(status_code=400, detail="Name is required")
        row["name"] = n
    if body.active is not None:
        row["active"] = body.active
    if body.is_master is not None:
        if body.is_master:
            _clear_master_flag_same_partner(roles, row.get("partner_id"), except_role_id=role_id)
            row["is_master"] = True
        else:
            row["is_master"] = False
    row["updated_at"] = now
    _save_rbac_roles(roles)
    was_rp: list[str] = []
    now_rp: list[str] = []
    if body.name is not None and snap_name != row.get("name"):
        was_rp.append(f"name={snap_name}")
        now_rp.append(f"name={row.get('name')}")
    if body.active is not None and snap_active != bool(row.get("active", True)):
        was_rp.append(f"active={snap_active}")
        now_rp.append(f"active={row.get('active')}")
    if body.is_master is not None and snap_master != bool(row.get("is_master")):
        was_rp.append(f"master={snap_master}")
        now_rp.append(f"master={row.get('is_master')}")
    _rbac_audit_append(
        _rbac_actor_user_id_from_request(request),
        "role.update",
        "role",
        str(role_id),
        was="; ".join(was_rp) if was_rp else "—",
        now="; ".join(now_rp) if now_rp else "—",
    )
    return {"ok": True, "role": row}


@app.put("/api/rbac/roles/{role_id:int}/permissions")
async def update_rbac_role_permissions(request: Request, role_id: int, body: UpdateRolePermissionsRequest):
    """Replace all permissions for a role. Sends full list (including always-granted).
    Non-master roles cannot exceed the Master role's permissions for the same partner.
    Shrinking a Master role cannot leave other roles with permissions outside the new set."""
    roles = _load_rbac_roles()
    role = next((r for r in roles if r.get("role_id") == role_id), None)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    _rbac_assert_actor_may_access_role_row(request, role)
    codes = [c.strip() for c in (body.permission_codes or []) if (c or "").strip()]
    codes_set = set(codes)
    partner_id = role.get("partner_id")
    master = _get_master_role_for_partner(roles, partner_id)

    if not _rbac_request_bypasses_master_caps(request) and role.get("is_master"):
        for r2 in roles:
            if r2.get("role_id") == role_id or r2.get("is_master"):
                continue
            if not _rbac_partner_scope_match(r2.get("partner_id"), partner_id):
                continue
            other = _permission_codes_for_role_id(int(r2["role_id"]))
            overflow = other - codes_set
            if overflow:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot remove permissions still required by non-master role «{r2.get('name', r2['role_id'])}»: {sorted(overflow)}",
                )
        if partner_id is not None:
            _raise_if_partner_master_exceeds_platform(roles, partner_id, codes_set, False)
    elif not _rbac_request_bypasses_master_caps(request) and master is not None:
        master_id = int(master["role_id"])
        cap = _permission_codes_for_role_id(master_id)
        over = codes_set - cap
        if over:
            raise HTTPException(
                status_code=400,
                detail=f"Permissions exceed Master role «{master.get('name', master_id)}» for this partner: {sorted(over)}",
            )

    perms = _load_rbac_role_permissions()
    old_codes = sorted([p["permission_code"] for p in perms if p["role_id"] == role_id])
    perms = [p for p in perms if p["role_id"] != role_id]
    for code in codes:
        perms.append({"role_id": role_id, "permission_code": code})
    _save_rbac_role_permissions(perms)
    new_codes = sorted(codes)

    def _codes_audit_blob(codes_list: list[str], max_chars: int = 1200) -> str:
        s = ", ".join(codes_list)
        if len(s) <= max_chars:
            return f"{len(codes_list)}: {s}" if codes_list else "0: (none)"
        return f"{len(codes_list)}: " + s[: max_chars - 3] + "…"

    _rbac_audit_append(
        _rbac_actor_user_id_from_request(request),
        "role.permissions.update",
        "role",
        str(role_id),
        was=_codes_audit_blob(old_codes),
        now=_codes_audit_blob(new_codes),
    )
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
    # Fresh disk read so saves are not based on a stale list (e.g. vs. auto-create Uncategorized).
    rows = _read_margin_templates_csv_rows()
    if not rows:
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
        sport_key,
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


def _template_ids_for_scope(brand_id: int | None, sport_id: str | int | None) -> list[int]:
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
    List competitions for the Add/Remove Competitions modal (current brand × sport scope).

    * Uncategorized template: left = default bucket; right = competitions assigned to other templates.
    * Any other template: left = in this template; right = **Uncategorized bucket only** (unassigned or
      explicit Uncategorized) so tiers are not listed as addable from here—move between tiers from
      the left column on the source template.
    """
    from fastapi import HTTPException
    b = (brand_id or "").strip()
    s = (sport_id or "").strip()
    sport_key = s if s else None
    brand_id_int = None
    if b:
        try:
            brand_id_int = int(b)
        except (TypeError, ValueError):
            pass
    scope_templates = _load_margin_templates(brand_id_int, sport_key)
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
        if c.get("domain_id") is not None and entity_ids_equal(c.get("sport_id"), sport_key)
    ] if sport_key else []
    scope_ids_set = set(scope_template_ids)
    catalog_by_id = {t["id"]: t for t in _load_margin_templates() if t.get("id") is not None}
    comp_to_template: dict[str, int] = {}
    for c in sport_competitions:
        ck = _margin_scope_competition_key(c.get("competition_id"))
        if not ck:
            continue
        picked = _margin_assignment_pick_template_id(ck, scope_ids_set, catalog_by_id=catalog_by_id)
        if picked is not None:
            comp_to_template[ck] = picked

    def _tpl_for_comp(c: dict) -> int | None:
        return comp_to_template.get(_margin_scope_competition_key(c.get("competition_id")))

    is_uncategorized = (template_name_by_id.get(template_id) or "").strip().lower() == "uncategorized"
    unc_tid = next((t["id"] for t in scope_templates if (t.get("name") or "").strip().lower() == "uncategorized" and t.get("id") is not None), None)
    unc_display = (template_name_by_id.get(unc_tid) or "Uncategorized") if unc_tid is not None else "Uncategorized"

    if is_uncategorized:
        # Default bucket: in_template = explicitly in Uncategorized or not in any scope template
        in_template = [
            {"competition_id": c["competition_id"], "name": c["name"], "category_name": c.get("category_name", "—")}
            for c in sport_competitions
            if _tpl_for_comp(c) == template_id or _tpl_for_comp(c) is None
        ]
        not_in_template = [
            {
                "competition_id": c["competition_id"],
                "name": c["name"],
                "category_name": c.get("category_name", "—"),
                "current_template_name": template_name_by_id.get(_tpl_for_comp(c), "—"),
            }
            for c in sport_competitions
            if _tpl_for_comp(c) is not None and _tpl_for_comp(c) != template_id
        ]
    else:
        in_template = [
            {"competition_id": c["competition_id"], "name": c["name"], "category_name": c.get("category_name", "—")}
            for c in sport_competitions
            if _tpl_for_comp(c) == template_id
        ]
        # Right column: only Uncategorized bucket (explicit Uncategorized row or no assignment yet).
        # Tiers already on another named template are moved via "In this template" on that template, not from here.
        def _in_uncategorized_bucket(c: dict) -> bool:
            tid = _tpl_for_comp(c)
            if tid is None:
                return True
            if unc_tid is not None:
                return tid == unc_tid
            return False

        not_in_template = sorted(
            (
                {
                    "competition_id": c["competition_id"],
                    "name": c["name"],
                    "category_name": c.get("category_name", "—"),
                    "current_template_name": unc_display,
                }
                for c in sport_competitions
                if _in_uncategorized_bucket(c)
            ),
            key=lambda d: (d.get("name") or "").strip().casefold(),
        )
    other_templates = [{"id": t["id"], "name": (t.get("name") or "").strip() or "—"} for t in scope_templates if t.get("id") != template_id]
    return {
        "template_id": template_id,
        "template_name": template_name_by_id.get(template_id, "—"),
        "in_template": in_template,
        "not_in_template": not_in_template,
        "other_templates": other_templates,
        "hide_current_template_on_add": not is_uncategorized,
    }


@app.post("/api/margin-templates/competitions/assign")
async def assign_competition_to_template(body: AssignCompetitionToTemplateRequest):
    """
    Move a competition into a margin template (within current scope).
    Removes every existing row for that competition (any template / scope), then adds the new assignment.
    """
    from fastapi import HTTPException
    scope_templates = _load_margin_templates(body.brand_id, body.sport_id)
    scope_template_ids = [t["id"] for t in scope_templates if t.get("id") is not None]
    if body.template_id not in scope_template_ids:
        raise HTTPException(status_code=400, detail="Template not in current scope")
    competitions = DOMAIN_ENTITIES.get("competitions", [])
    comp = next((c for c in competitions if entity_ids_equal(c.get("domain_id"), body.competition_id)), None)
    if not comp or (body.sport_id is not None and not entity_ids_equal(comp.get("sport_id"), body.sport_id)):
        raise HTTPException(status_code=400, detail="Competition not found or not in selected sport")
    rows = _load_margin_template_competitions()
    cid_key = _margin_scope_competition_key(body.competition_id)
    cid_store = cid_key if cid_key else str(body.competition_id).strip()
    # One domain competition → one template row; remove stale assignments from other scopes.
    rows = [r for r in rows if _margin_scope_competition_key(r.get("competition_id")) != cid_store]
    rows.append({"template_id": body.template_id, "competition_id": cid_store})
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
    # Reload from CSV so manual edits to sports / mappings (e.g. in git) show without restarting the app.
    global DOMAIN_ENTITIES, ENTITY_FEED_MAPPINGS, SPORT_FEED_MAPPINGS
    DOMAIN_ENTITIES = _load_entities()
    ENTITY_FEED_MAPPINGS = _load_entity_feed_mappings()
    SPORT_FEED_MAPPINGS = _load_sport_feed_mappings()

    sports_list = list(DOMAIN_ENTITIES["sports"])
    sort_asc = (sort_sports or "asc").strip().lower() != "desc"
    sports_list.sort(key=lambda e: (e.get("name") or "").strip().lower(), reverse=not sort_asc)
    markets_list = list(DOMAIN_ENTITIES["markets"])
    selected_market_sport_id: str | None = None
    if market_sport_id and str(market_sport_id).strip():
        ms = fid_str(market_sport_id)
        selected_market_sport_id = ms
        markets_list = [m for m in markets_list if entity_ids_equal(m.get("sport_id"), ms)]
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
    # Per-entity list of feed refs from entity_feed_mappings.csv (reload from disk so manual edits are visible).
    # Deduplicate by (feed_provider_id, normalized feed_id) so duplicate CSV rows do not repeat chips.
    mappings = _load_entity_feed_mappings()
    entity_feed_refs_by_key: dict[str, list[dict]] = {}
    _seen_ref: dict[str, set[tuple[int, str]]] = {}
    for m in mappings:
        k = f"{m['entity_type']}:{m['domain_id']}"
        fpid = int(m["feed_provider_id"])
        raw_fid = str(m.get("feed_id") or "").strip()
        fk = mapping_feed_id_key(raw_fid)
        dedupe_key = (fpid, fk)
        if dedupe_key in _seen_ref.setdefault(k, set()):
            continue
        _seen_ref[k].add(dedupe_key)
        entity_feed_refs_by_key.setdefault(k, []).append({
            "feed_provider_id": fpid,
            "feed_id": raw_fid,
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

    mt_feed_counts_raw = _market_type_feed_counts_by_domain_id()
    market_feed_counts_by_market_id: dict = {}
    for mkt in markets_list:
        mk = mkt.get("domain_id")
        if mk is None or (isinstance(mk, str) and not mk.strip()):
            continue
        market_feed_counts_by_market_id[mk] = mt_feed_counts_raw.get(
            fid_str(mk), {"prematch": 0, "live": 0}
        )

    return templates.TemplateResponse(request, "configuration/entities.html", {
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
        "market_feed_counts_by_market_id": market_feed_counts_by_market_id,
        "market_templates": market_templates,
        "market_period_types": market_period_types,
        "market_score_types": market_score_types,
        "market_groups": market_groups,
        "participant_types_by_id": participant_types_by_id,
        "market_sport_id": selected_market_sport_id,
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


# Feeder Configuration: (setting_key, label, optional_hint, ui_mode).
# ui_mode: exclusive = at most one Yes; multiselect = any subset Yes; priority = ordered list (see per-key save rules).
FEEDER_SYSTEM_ACTIONS = [
    ("auto_create_category", "Auto create Category", None, "exclusive"),
    ("auto_create_competitions", "Auto create Competitions", None, "exclusive"),
    ("auto_create_teams", "Auto create Teams", None, "exclusive"),
    (
        "auto_create_events",
        "Auto create Events",
        "Only when sport, competition and teams are mappable in the domain; a feed-level category field is not required (e.g. Bet365/Betfair/1xBet have no region in the list row).",
        "priority",
    ),
    (
        "auto_map_events",
        "Auto map Events",
        "When enabled for this feed and scope, unmapped rows with sport, competition and both teams mapped to the domain are linked to an existing domain event if exactly one fixture matches (competition by feed league id or name, teams, start time; home/away swap allowed). Feeds with a native category/region (e.g. Bwin) may still use it for filters but it is optional for matching.",
        "multiselect",
    ),
    (
        "pricing_feed",
        "Pricing Feed",
        "Global (All Sports) only for now. Event-level choice of which feed supplies prices: top of the ordered list is primary; Add builds fallback order for later use. If the primary feed has no odds for a market, the system does not fall back to the next feed for that market (per-market fallback is out of scope). Per-brand pricing selection will come later.",
        "priority",
    ),
]


def _feeder_setting_ui_mode(setting_key: str) -> str:
    for k, _lbl, _h, m in FEEDER_SYSTEM_ACTIONS:
        if k == setting_key:
            return (m or "multiselect").strip().lower()
    return "multiselect"


def _feeder_allowed_setting_keys() -> frozenset[str]:
    return frozenset(t[0] for t in FEEDER_SYSTEM_ACTIONS)


def _feeder_config_yes_no_value(raw: str | None) -> str:
    """Normalize stored feeder config toggle to exactly 'Yes' or 'No' (default No)."""
    v = (raw or "").strip().casefold()
    return "Yes" if v == "yes" else "No"


def _feeder_config_grid_display(setting_key: str, raw: str | None) -> str:
    """Table cell text for feeder configuration grid (Yes/No). ``pricing_feed`` stores rank 1..n per feed column."""
    if (setting_key or "").strip() == "pricing_feed":
        s = (raw or "").strip().lower()
        if s in ("yes", "1"):
            return "1"
        if s.isdigit():
            n = int(s)
            if n >= 2:
                return str(n)
        return "—"
    return _feeder_config_yes_no_value(raw)


def _feeder_config_pricing_feed_order_ids() -> list[int]:
    """Global ``pricing_feed`` rows: feed ids ordered by stored rank (1 = primary). Excludes rank 0 / missing."""
    rows = _load_feeder_config()
    scored: list[tuple[int, int]] = []
    for r in rows:
        if (r.get("level") or "").strip() != "all_sports":
            continue
        if r.get("sport_id") is not None or r.get("category_id") is not None or r.get("competition_id") is not None:
            continue
        if (r.get("setting_key") or "").strip() != "pricing_feed":
            continue
        fid = r.get("feed_provider_id")
        if fid is None:
            continue
        try:
            rk = int(str(r.get("value") or "0").strip() or "0")
        except (TypeError, ValueError):
            rk = 0
        if rk < 1:
            continue
        try:
            scored.append((int(fid), rk))
        except (TypeError, ValueError):
            continue
    scored.sort(key=lambda x: x[1])
    return [fid for fid, _ in scored]


def _feeder_scope_id(raw: Any) -> str | int | None:
    """Parse sport/category/competition id from query or JSON (supports S-1 / G-2 / C-3 and legacy numeric)."""
    if raw is None:
        return None
    if isinstance(raw, int):
        return raw
    s = str(raw).strip()
    if not s:
        return None
    if s.isdigit():
        return int(s)
    return s


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
    return templates.TemplateResponse(request, "configuration/risk_rules.html", {
        "request": request,
        "section": "risk_rules",
        "brands": brands,
        "risk_config_rows": risk_config_rows,
        "risk_classes": risk_classes,
        "risk_categories": risk_categories,
    })


@app.get("/compliance", response_class=HTMLResponse)
async def compliance_view(request: Request):
    """Configuration > Compliance (placeholder)."""
    return templates.TemplateResponse(request, "configuration/compliance.html", {
        "request": request,
        "section": "compliance",
    })


@app.get("/feeders", response_class=HTMLResponse)
async def feeders_view(
    request: Request,
    sport_id: str | None = None,
    category_id: str | None = None,
    competition_id: str | None = None,
    league_id: str | None = None,
):
    """
    Configuration > Feeder page.
    Filters: Sport, Category, Competition (cascading). Main grid: Auto create Category / Competitions / Teams / Events,
    Auto map Events, etc. per feed. When sport selected: Feeder Incidents Configuration section at bottom.
    """
    def _entity_sort_key(e: dict) -> tuple[str, str]:
        return ((e.get("name") or "").strip().lower(), str(e.get("domain_id") or ""))

    sports = sorted(DOMAIN_ENTITIES["sports"], key=_entity_sort_key)
    categories = sorted(DOMAIN_ENTITIES["categories"], key=_entity_sort_key)
    competitions = sorted(DOMAIN_ENTITIES["competitions"], key=_entity_sort_key)
    sports_by_id = {s["domain_id"]: s["name"] for s in sports}
    categories_by_id = {c["domain_id"]: c["name"] for c in categories}
    competitions_by_id = {c["domain_id"]: c["name"] for c in competitions}
    feeder_config_rows = _load_feeder_config()
    feeder_incident_rows = _load_feeder_incidents()

    # Handle "all" for All Sports (special value). Sport/category/competition ids may be prefixed (S-1, G-2, C-3).
    is_all_sports = sport_id and sport_id.strip().lower() == "all"
    sid_key = None if is_all_sports else _feeder_scope_id(sport_id)
    cid_key = _feeder_scope_id(category_id)
    comp_key = _feeder_scope_id((competition_id or league_id or "").strip() or None)
    level = "all_sports" if is_all_sports else (
        "competition" if comp_key is not None else "category" if cid_key is not None else "sport" if sid_key is not None else None
    )

    config_lookup = {}
    feeder_config_raw: dict[tuple[Any, str], str] = {}
    for r in feeder_config_rows:
        rsid, rcid, rcomp = r.get("sport_id"), r.get("category_id"), r.get("competition_id")
        if level == "all_sports" and rsid is None and rcid is None and rcomp is None:
            fid, key = r.get("feed_provider_id"), r.get("setting_key")
            if fid is not None and key:
                raw_v = (r.get("value") or "").strip()
                feeder_config_raw[(fid, key)] = raw_v
                config_lookup[(fid, key)] = _feeder_config_grid_display(key, r.get("value"))
        elif level == "sport" and sid_key is not None and entity_ids_equal(rsid, sid_key) and rcid is None and rcomp is None:
            fid, key = r.get("feed_provider_id"), r.get("setting_key")
            if fid is not None and key:
                raw_v = (r.get("value") or "").strip()
                feeder_config_raw[(fid, key)] = raw_v
                config_lookup[(fid, key)] = _feeder_config_grid_display(key, r.get("value"))
        elif level == "category" and sid_key is not None and cid_key is not None and entity_ids_equal(rsid, sid_key) and entity_ids_equal(rcid, cid_key) and rcomp is None:
            fid, key = r.get("feed_provider_id"), r.get("setting_key")
            if fid is not None and key:
                raw_v = (r.get("value") or "").strip()
                feeder_config_raw[(fid, key)] = raw_v
                config_lookup[(fid, key)] = _feeder_config_grid_display(key, r.get("value"))
        elif (
            level == "competition"
            and sid_key is not None
            and cid_key is not None
            and comp_key is not None
            and entity_ids_equal(rsid, sid_key)
            and entity_ids_equal(rcid, cid_key)
            and entity_ids_equal(rcomp, comp_key)
        ):
            fid, key = r.get("feed_provider_id"), r.get("setting_key")
            if fid is not None and key:
                raw_v = (r.get("value") or "").strip()
                feeder_config_raw[(fid, key)] = raw_v
                config_lookup[(fid, key)] = _feeder_config_grid_display(key, r.get("value"))

    incident_lookup = {}
    # Feeder Incidents only shown for specific sport (not All Sports)
    if sid_key is not None and not is_all_sports:
        for r in feeder_incident_rows:
            if entity_ids_equal(r.get("sport_id"), sid_key):
                fid, itype = r.get("feed_provider_id"), r.get("incident_type")
                if fid is not None and itype:
                    incident_lookup[(fid, itype)] = r.get("enabled", False)

    feed_sports = _load_feed_sports_rows()
    feed_sports_count = len(feed_sports)

    return templates.TemplateResponse(request, "configuration/feeders.html", {
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
        "feeder_config_raw": feeder_config_raw,
        "feeder_incident_lookup": incident_lookup,
        "feeder_settings": [
            {"key": k, "label": lbl, "hint": (h or ""), "ui_mode": m}
            for k, lbl, h, m in FEEDER_SYSTEM_ACTIONS
        ],
        "incident_types": FEEDER_INCIDENT_TYPES,
        "selected_sport_id": "all" if is_all_sports else sid_key,
        "selected_category_id": cid_key,
        "selected_competition_id": comp_key,
        "config_level": level,
        "feed_sports": feed_sports,
        "feed_sports_count": feed_sports_count,
        "can_feeder_update": _rbac_actor_has_permission_code(request, "config.feeders.update"),
        "can_feeder_audit": _rbac_actor_has_permission_code(request, "config.feeders.audit"),
    })


@app.post("/api/feeder-config")
async def api_save_feeder_config(request: Request):
    """Save feeder configuration for the given level (sport/category/competition). Replaces existing rows for that level."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"detail": "Invalid JSON"}, status_code=400)
    level = (body.get("level") or "").strip()
    if level == "league":
        level = "competition"
    sport_id = body.get("sport_id")
    category_id = body.get("category_id")
    competition_id = body.get("competition_id")
    if competition_id is None and body.get("league_id") is not None:
        competition_id = body.get("league_id")
    settings = body.get("settings") or []
    is_all_sports = level == "all_sports"
    if level not in ("all_sports", "sport", "category", "competition"):
        return JSONResponse({"detail": "level must be all_sports, sport, category, or competition"}, status_code=400)
    if is_all_sports:
        sid, cid, comp_id = None, None, None
    else:
        if sport_id is None:
            return JSONResponse({"detail": "sport_id required for sport/category/competition level"}, status_code=400)
        sid = _feeder_scope_id(sport_id)
        cid = _feeder_scope_id(category_id)
        comp_id = _feeder_scope_id(competition_id)
        if sid is None:
            return JSONResponse({"detail": "sport_id required for sport/category/competition level"}, status_code=400)
        if level == "category" and cid is None:
            return JSONResponse({"detail": "category_id required for category level"}, status_code=400)
        if level == "competition" and (cid is None or comp_id is None):
            return JSONResponse({"detail": "category_id and competition_id required for competition level"}, status_code=400)
    existing = _load_feeder_config()
    def match_row(r):
        rsid, rcid, rcomp = r.get("sport_id"), r.get("category_id"), r.get("competition_id")
        if level == "all_sports":
            return rsid is None and rcid is None and rcomp is None
        if level == "sport":
            return entity_ids_equal(rsid, sid) and rcid is None and rcomp is None
        if level == "category":
            return entity_ids_equal(rsid, sid) and entity_ids_equal(rcid, cid) and rcomp is None
        return entity_ids_equal(rsid, sid) and entity_ids_equal(rcid, cid) and entity_ids_equal(rcomp, comp_id)
    kept = [r for r in existing if not match_row(r)]
    for s in settings or []:
        if (s.get("setting_key") or "").strip() == "pricing_feed" and not is_all_sports:
            return JSONResponse({"detail": "Pricing Feed is only configurable at All Sports (global) scope."}, status_code=400)
    new_rows = []
    for s in settings:
        fid = s.get("feed_provider_id")
        key = (s.get("setting_key") or "").strip()
        val = _feeder_config_yes_no_value(s.get("value"))
        if fid is None or not key:
            continue
        new_rows.append({
            "level": level,
            "sport_id": sid,
            "category_id": cid,
            "competition_id": comp_id,
            "feed_provider_id": int(fid),
            "setting_key": key,
            "value": val,
        })
    all_rows = kept + new_rows
    _save_feeder_config(all_rows)
    return {"ok": True}


@app.post("/api/feeder-config/row")
async def api_save_feeder_config_row(request: Request):
    """Save one setting row for the current scope (merge). Other settings at this scope are unchanged."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"detail": "Invalid JSON"}, status_code=400)
    level = (body.get("level") or "").strip()
    if level == "league":
        level = "competition"
    sport_id = body.get("sport_id")
    category_id = body.get("category_id")
    competition_id = body.get("competition_id")
    if competition_id is None and body.get("league_id") is not None:
        competition_id = body.get("league_id")
    is_all_sports = level == "all_sports"
    if level not in ("all_sports", "sport", "category", "competition"):
        return JSONResponse({"detail": "level must be all_sports, sport, category, or competition"}, status_code=400)
    if is_all_sports:
        sid, cid, comp_id = None, None, None
    else:
        if sport_id is None:
            return JSONResponse({"detail": "sport_id required for sport/category/competition level"}, status_code=400)
        sid = _feeder_scope_id(sport_id)
        cid = _feeder_scope_id(category_id)
        comp_id = _feeder_scope_id(competition_id)
        if sid is None:
            return JSONResponse({"detail": "sport_id required for sport/category/competition level"}, status_code=400)
        if level == "category" and cid is None:
            return JSONResponse({"detail": "category_id required for category level"}, status_code=400)
        if level == "competition" and (cid is None or comp_id is None):
            return JSONResponse({"detail": "category_id and competition_id required for competition level"}, status_code=400)

    setting_key = (body.get("setting_key") or "").strip()
    if setting_key not in _feeder_allowed_setting_keys():
        return JSONResponse({"detail": "unknown setting_key"}, status_code=400)
    if setting_key in ("auto_create_category", "auto_create_competitions", "auto_create_teams"):
        return JSONResponse({"detail": "This setting is not available in MVP."}, status_code=400)
    if setting_key == "pricing_feed" and not is_all_sports:
        return JSONResponse({"detail": "Pricing Feed is only configurable at All Sports (global) scope."}, status_code=400)
    mode = _feeder_setting_ui_mode(setting_key)
    existing = _load_feeder_config()
    was_map = _feeder_config_snapshot_setting(existing, level, sid, cid, comp_id, setting_key)
    allowed_ids = {int(f["domain_id"]) for f in FEEDS}
    by_fid: dict[int, str] = {fid: "No" for fid in allowed_ids}

    if mode == "priority":
        order = body.get("ordered_feed_ids") or []
        if not isinstance(order, list):
            return JSONResponse({"detail": "ordered_feed_ids must be a list"}, status_code=400)
        try:
            order_ids = [int(x) for x in order]
        except (TypeError, ValueError):
            return JSONResponse({"detail": "ordered_feed_ids must be integers"}, status_code=400)
        for fid in order_ids:
            if fid not in allowed_ids:
                return JSONResponse({"detail": "unknown feed_provider_id in ordered_feed_ids"}, status_code=400)
        if setting_key == "pricing_feed":
            by_fid = {fid: "0" for fid in allowed_ids}
            for pos, fid in enumerate(order_ids, start=1):
                if fid in by_fid:
                    by_fid[fid] = str(pos)
        elif order_ids:
            by_fid[order_ids[0]] = "Yes"
    else:
        values = body.get("values") or []
        if not isinstance(values, list):
            return JSONResponse({"detail": "values must be a list"}, status_code=400)
        for v in values:
            fid = v.get("feed_provider_id")
            if fid is None:
                continue
            try:
                ifid = int(fid)
            except (TypeError, ValueError):
                continue
            if ifid not in allowed_ids:
                return JSONResponse({"detail": "unknown feed_provider_id"}, status_code=400)
            by_fid[ifid] = _feeder_config_yes_no_value(v.get("value"))
        yes_n = sum(1 for x in by_fid.values() if x == "Yes")
        if mode == "exclusive" and yes_n > 1:
            return JSONResponse({"detail": "this setting allows at most one feed set to Yes"}, status_code=400)

    kept = [
        r for r in existing
        if not (_feeder_config_row_matches_scope(r, level, sid, cid, comp_id) and (r.get("setting_key") or "").strip() == setting_key)
    ]
    new_rows = []
    for fid, val in by_fid.items():
        new_rows.append({
            "level": level,
            "sport_id": sid,
            "category_id": cid,
            "competition_id": comp_id,
            "feed_provider_id": fid,
            "setting_key": setting_key,
            "value": val,
        })
    _save_feeder_config(kept + new_rows)
    now_map = {str(k): v for k, v in sorted(by_fid.items())}
    subj = json.dumps({
        "resource": "feeder_config",
        "setting_key": setting_key,
        "level": level,
        "sport_id": sid,
        "category_id": cid,
        "competition_id": comp_id,
    }, separators=(",", ":"), default=str)
    _admin_audit_append(
        request,
        resource="feeder_config",
        action="setting_row.save",
        subject=subj,
        was=json.dumps(was_map, sort_keys=True, separators=(",", ":")),
        now=json.dumps(now_map, sort_keys=True, separators=(",", ":")),
    )
    return {"ok": True}


@app.get("/api/admin/audit-log")
async def api_admin_audit_log(
    request: Request,
    resource: str = "feeder_config",
    setting_key: str | None = None,
    sport_id: str | None = None,
    limit: int = 150,
):
    """Admin configuration audit (feeder_config, feeder_incidents, …). Newest first."""
    sid_filter = _feeder_scope_id(sport_id) if (sport_id is not None and str(sport_id).strip() != "") else None
    entries = _admin_audit_entries(
        resource=(resource or "").strip() or None,
        setting_key=(setting_key or "").strip() or None,
        sport_id_filter=sid_filter,
        limit=limit,
    )
    return {"entries": entries}


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
    sid = _feeder_scope_id(sport_id)
    if sid is None:
        return JSONResponse({"detail": "sport_id required"}, status_code=400)
    existing = _load_feeder_incidents()
    prev_rows = [dict(r) for r in existing if entity_ids_equal(r.get("sport_id"), sid)]
    kept = [r for r in existing if not entity_ids_equal(r.get("sport_id"), sid)]
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
    subj_inc = json.dumps({"resource": "feeder_incidents", "sport_id": sid}, separators=(",", ":"), default=str)
    _admin_audit_append(
        request,
        resource="feeder_incidents",
        action="matrix.save",
        subject=subj_inc,
        was=_admin_audit_clip(json.dumps(prev_rows, default=str)),
        now=_admin_audit_clip(json.dumps(new_rows, default=str)),
    )
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
    sports = sorted(
        DOMAIN_ENTITIES.get("sports", []),
        key=lambda s: (s.get("name") or "").strip().casefold(),
    )

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
    default_sport_id = fid_str(football["domain_id"]) if football and football.get("domain_id") is not None else None

    selected_sport_id = default_sport_id
    if applied and sport_id and str(sport_id).strip():
        selected_sport_id = fid_str(sport_id)
        if not any(fid_str(s.get("domain_id")) == selected_sport_id for s in sports):
            selected_sport_id = default_sport_id

    if not applied:
        return templates.TemplateResponse(request, "margin/margin.html", {
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
        fid_str(c["domain_id"]) for c in DOMAIN_ENTITIES.get("competitions", [])
        if c.get("domain_id") is not None and entity_ids_equal(c.get("sport_id"), selected_sport_id)
    } if selected_sport_id else set()
    scope_template_ids = [t["id"] for t in margin_templates if t.get("id") is not None]
    scope_ids_set = set(scope_template_ids)
    catalog_by_id = {t["id"]: t for t in _load_margin_templates() if t.get("id") is not None}
    comp_keys_norm = {_margin_scope_competition_key(cid) for cid in competition_ids_for_sport if cid}
    comp_to_scope_template: dict[str, int] = {}
    for ck in comp_keys_norm:
        picked = _margin_assignment_pick_template_id(ck, scope_ids_set, catalog_by_id=catalog_by_id)
        if picked is not None:
            comp_to_scope_template[ck] = picked
    uncategorized_ids = {t["id"] for t in margin_templates if (t.get("name") or "").strip().lower() == "uncategorized"}
    for t in margin_templates:
        tid = t.get("id")
        if tid in uncategorized_ids:
            unassigned = sum(1 for ck in comp_keys_norm if comp_to_scope_template.get(ck) is None)
            assigned_here = sum(1 for ck in comp_keys_norm if comp_to_scope_template.get(ck) == tid)
            t["leagues_count"] = assigned_here + unassigned
        else:
            t["leagues_count"] = sum(1 for ck in comp_keys_norm if comp_to_scope_template.get(ck) == tid)
        t["markets_count"] = 0
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

    return templates.TemplateResponse(request, "margin/margin.html", {
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

    return templates.TemplateResponse(request, "configuration/localization.html", {
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
    return templates.TemplateResponse(request, "configuration/brands.html", {
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
    enforced = _rbac_actor_enforced_partner_id(request)
    users = _load_rbac_users()
    roles = _load_rbac_roles()
    user_roles = _load_rbac_user_roles()
    user_brands = _load_rbac_user_brands()
    partners_all = _load_partners()
    partners = partners_all
    brands = _load_brands()
    if enforced is not None:
        users = [u for u in users if u.get("partner_id") == enforced]
        roles = [r for r in roles if r.get("partner_id") == enforced]
        partners = [p for p in partners_all if p.get("id") == enforced]
        brands = [b for b in brands if b.get("partner_id") == enforced]
    brand_by_id = {b["id"]: b for b in brands}
    partner_by_id = {p["id"]: p for p in partners_all}
    for r in roles:
        r["partner_name"] = (partner_by_id.get(r.get("partner_id"), {}).get("name") or "—") if r.get("partner_id") else config.RBAC_PLATFORM_SCOPE_LABEL
    role_by_id = {r["role_id"]: r for r in roles}
    from collections import Counter
    role_user_count = Counter(ur["role_id"] for ur in user_roles)
    for r in roles:
        r["active_admins"] = role_user_count.get(r["role_id"], 0)
    # Roles & Permissions panel: filter roles by partner (All / Platform / Partner X); partner sign-in is fixed to own tenant
    if enforced is not None:
        roles_filtered = roles
        rp_partner_id_for_template = str(enforced)
    else:
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
        u["partner_name"] = (partner_by_id.get(u["partner_id"], {}).get("name") or "—") if u.get("partner_id") else config.RBAC_PLATFORM_SCOPE_LABEL

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
    if enforced is not None:
        _partner_id_raw = str(enforced)
        _partner_id = enforced
    else:
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
    for u in filtered:
        u["online"] = _rbac_user_presence_online(u.get("user_id"))
        ld, lst = _rbac_last_login_display_and_stale(u.get("last_login"))
        u["last_login_display"] = ld
        u["last_login_stale"] = lst
        u["modified_by_display"] = _rbac_user_modified_by_display(u)
        u.pop("login_pin", None)
    perm_ceiling = _access_rights_ceiling_codes(request)
    permission_tree = _filter_permission_tree_nodes(config.RBAC_PERMISSION_TREE, perm_ceiling)
    return templates.TemplateResponse(request, "configuration/users.html", {
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
        "filter_rp_partner_id": (str(enforced) if enforced is not None else (rp_partner_id or "")),
        "rbac_enforced_partner_id": enforced,
        "rbac_enforced_partner_name": (partner_by_id.get(enforced, {}).get("name", "") if enforced is not None else ""),
        "rbac_platform_scope_label": config.RBAC_PLATFORM_SCOPE_LABEL,
        "rbac_trust_actor_header": config.RBAC_TRUST_ACTOR_HEADER,
    })


def _dev_login_users_for_form() -> list[dict]:
    users = _load_rbac_users()
    partners = _load_partners()
    partner_by_id = {p["id"]: p for p in partners}
    for u in users:
        pid = u.get("partner_id")
        u["partner_label"] = (partner_by_id.get(pid, {}).get("name") or "—") if pid else config.RBAC_PLATFORM_SCOPE_LABEL
    return sorted(users, key=lambda u: ((not u.get("active", True)), (u.get("email") or "").lower()))


@app.get("/dev/login", response_class=HTMLResponse)
async def dev_login_page(request: Request):
    if not config.GMP_DEV_LOGIN:
        raise HTTPException(status_code=404, detail="Not found")
    return templates.TemplateResponse(request, "dev_login.html", {
        "request": request,
        "users": _dev_login_users_for_form(),
        "error": "",
    })


@app.post("/dev/login")
async def dev_login_submit(request: Request, pin: str = Form(""), user_id: int = Form(...)):
    if not config.GMP_DEV_LOGIN:
        raise HTTPException(status_code=404, detail="Not found")
    users = _load_rbac_users()
    u = next((x for x in users if x.get("user_id") == user_id), None)
    users_form = _dev_login_users_for_form()

    def render_err(msg: str):
        return templates.TemplateResponse(request, "dev_login.html", {
            "request": request,
            "users": users_form,
            "error": msg,
        })

    if not u or not u.get("active", True):
        return render_err("User not found or inactive.")
    if not _rbac_sign_in_pin_valid(u, pin):
        return render_err("Invalid PIN.")
    request.session["dev_actor_user_id"] = user_id
    _rbac_persist_last_login(user_id)
    _rbac_presence_touch(user_id)
    return RedirectResponse(url="/", status_code=303)


@app.get("/dev/logout")
async def dev_logout(request: Request):
    if not config.GMP_DEV_LOGIN:
        raise HTTPException(status_code=404, detail="Not found")
    uid = request.session.get("dev_actor_user_id")
    if uid is not None:
        try:
            _rbac_presence_clear(int(uid))
        except (TypeError, ValueError):
            pass
    request.session.pop("dev_actor_user_id", None)
    return RedirectResponse(url="/dev/login", status_code=303)


class _DevActorMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.dev_login_enabled = bool(config.GMP_DEV_LOGIN)
        request.state.dev_actor = None
        if config.GMP_DEV_LOGIN:
            uid = request.session.get("dev_actor_user_id")
            if uid is not None:
                try:
                    uid_int = int(uid)
                except (TypeError, ValueError):
                    uid_int = None
                if uid_int is not None:
                    users = _load_rbac_users()
                    u = next((x for x in users if x.get("user_id") == uid_int), None)
                    if u and u.get("active", True):
                        request.state.dev_actor = u
                    else:
                        request.session.pop("dev_actor_user_id", None)
        if config.GMP_DEV_LOGIN and not _auth_exempt_path(request.url.path):
            if request.state.dev_actor is None:
                if request.url.path.startswith("/api/"):
                    return JSONResponse({"detail": "Unauthorized"}, status_code=401)
                if (request.headers.get("hx-request") or "").lower() == "true":
                    return JSONResponse(
                        {"detail": "Unauthorized"},
                        status_code=401,
                        headers={"HX-Redirect": "/dev/login"},
                    )
                return RedirectResponse(url="/dev/login", status_code=303)
        denied = _rbac_forbidden_if_path_denied(request)
        if denied is not None:
            return denied
        shell_redir = _rbac_superadmin_shell_redirect_if_needed(request)
        if shell_redir is not None:
            return shell_redir
        try:
            _rbac_enforce_api_permissions(request)
        except HTTPException as e:
            detail = e.detail
            if isinstance(detail, str):
                return JSONResponse({"detail": detail}, status_code=e.status_code)
            return JSONResponse({"detail": str(detail)}, status_code=e.status_code)
        # Presence for Admin “Online” (and optional trusted-header actor)
        if getattr(request.state, "dev_actor", None):
            _rbac_presence_touch(request.state.dev_actor.get("user_id"))
        elif config.RBAC_TRUST_ACTOR_HEADER:
            raw = (request.headers.get("x-rbac-actor-user-id") or request.headers.get("X-RBAC-Actor-User-Id") or "").strip()
            if raw:
                try:
                    _rbac_presence_touch(int(raw))
                except ValueError:
                    pass
        return await call_next(request)


app.add_middleware(_DevActorMiddleware)
if config.GMP_DEV_LOGIN:
    _session_secret = (
        (config.GMP_DEV_SESSION_SECRET or "").strip()
        or "gmp-dev-insecure-local-default-change-GMP_DEV_SESSION_SECRET"
    )
    app.add_middleware(
        SessionMiddleware,
        secret_key=_session_secret,
        session_cookie="gmp_dev_session",
        max_age=86400 * 7,
        same_site="lax",
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
