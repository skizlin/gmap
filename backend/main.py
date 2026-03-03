from __future__ import annotations

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
from datetime import datetime, timezone

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
DATA_COUNTRIES_DIR = config.DATA_COUNTRIES_DIR
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
MARKET_TEMPLATES_PATH = config.MARKET_TEMPLATES_PATH
MARKET_PERIOD_TYPE_PATH = config.MARKET_PERIOD_TYPE_PATH
MARKET_SCORE_TYPE_PATH = config.MARKET_SCORE_TYPE_PATH
MARKET_GROUPS_PATH = config.MARKET_GROUPS_PATH
MARKET_TYPE_MAPPINGS_PATH = config.MARKET_TYPE_MAPPINGS_PATH
COUNTRIES_PATH = config.COUNTRIES_PATH
PARTICIPANT_TYPE_PATH = config.PARTICIPANT_TYPE_PATH
UNDERAGE_CATEGORIES_PATH = config.UNDERAGE_CATEGORIES_PATH
LANGUAGES_PATH = config.LANGUAGES_PATH
TRANSLATIONS_PATH = config.TRANSLATIONS_PATH
BRANDS_PATH = config.BRANDS_PATH
FEEDER_CONFIG_PATH = config.FEEDER_CONFIG_PATH
FEEDER_INCIDENTS_PATH = config.FEEDER_INCIDENTS_PATH
MARGIN_TEMPLATES_PATH = config.MARGIN_TEMPLATES_PATH
MARGIN_TEMPLATE_COMPETITIONS_PATH = config.MARGIN_TEMPLATE_COMPETITIONS_PATH

# Mount Static & Templates
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


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


def _format_start_time(s: str | None) -> str:
    """Format start_time for display (DD/MM/YYYY HH:mm). Returns '' if invalid."""
    dt = _parse_start_time(s)
    return dt.strftime("%d/%m/%Y %H:%M") if dt else (s or "")


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
KNOWN_FEEDS = ["bet365", "betfair", "sbobet", "1xbet", "bwin"]

# DUMMY DATA FOR PROTOTYPE
from backend.mock_data import load_all_mock_data
DUMMY_EVENTS = load_all_mock_data()

# Derive per-feed sport lists (sorted, unique)
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
    CreateBrandRequest,
    UpdateBrandRequest,
    CreateMarketGroupRequest,
    MarketTypeMappingItem,
    SaveMarketTypeMappingsRequest,
    CountryUpsertRequest,
    LanguageUpsertRequest,
    TranslationUpsertRequest,
    CreateMarginTemplateRequest,
    UpdateMarginTemplateRequest,
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


_MARGIN_TEMPLATE_FIELDS = [
    "id", "name", "short_name", "pm_margin", "ip_margin",
    "cashout", "betbuilder", "bet_delay", "leagues_count", "markets_count", "is_default",
]


def _load_margin_templates() -> list[dict]:
    """Load margin_templates.csv. If missing or empty, returns default list with Uncategorized only."""
    if not MARGIN_TEMPLATES_PATH.exists():
        return [{"id": 1, "name": "Uncategorized", "short_name": "", "pm_margin": "", "ip_margin": "", "cashout": "", "betbuilder": "", "bet_delay": "", "leagues_count": 0, "markets_count": 0, "is_default": 1}]
    rows = []
    with open(MARGIN_TEMPLATES_PATH, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rid = r.get("id")
            try:
                r["id"] = int(rid) if rid and str(rid).strip() else None
            except (TypeError, ValueError):
                r["id"] = None
            for k in ("leagues_count", "markets_count"):
                try:
                    r[k] = int(r.get(k) or 0)
                except (TypeError, ValueError):
                    r[k] = 0
            r["is_default"] = (r.get("is_default") or "").strip() in ("1", "true", "yes")
            rows.append(r)
    if not rows:
        return [{"id": 1, "name": "Uncategorized", "short_name": "", "pm_margin": "", "ip_margin": "", "cashout": "", "betbuilder": "", "bet_delay": "", "leagues_count": 0, "markets_count": 0, "is_default": True}]
    return rows


def _save_margin_templates(rows: list[dict]) -> None:
    """Overwrite margin_templates.csv."""
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
                "leagues_count": r.get("leagues_count") if r.get("leagues_count") is not None else 0,
                "markets_count": r.get("markets_count") if r.get("markets_count") is not None else 0,
                "is_default": "1" if r.get("is_default") else "0",
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
    """Assign a domain competition to a margin template (default Uncategorized). Idempotent."""
    rows = _load_margin_template_competitions()
    if any(r.get("template_id") == template_id and r.get("competition_id") == competition_id for r in rows):
        return
    rows.append({"template_id": template_id, "competition_id": competition_id})
    _save_margin_template_competitions(rows)


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
        out.append({
            "id": bid,
            "name": (r.get("name") or "").strip(),
            "code": (r.get("code") or "").strip(),
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
            w.writerow({
                "id": b.get("id", ""),
                "name": b.get("name", ""),
                "code": b.get("code", ""),
                "jurisdiction": b.get("jurisdiction", ""),
                "language_ids": b.get("language_ids", ""),
                "currencies": b.get("currencies", ""),
                "odds_formats": b.get("odds_formats", ""),
                "created_at": b.get("created_at", ""),
                "updated_at": b.get("updated_at", ""),
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
    """Load entity_feed_mappings.csv — feed IDs map to domain entities (sports, categories, competitions, teams)."""
    if not ENTITY_FEED_MAPPINGS_PATH.exists():
        return []
    rows = []
    with open(ENTITY_FEED_MAPPINGS_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            row["domain_id"] = int(row["domain_id"])
            row["feed_provider_id"] = int(row["feed_provider_id"])
            if not (row.get("domain_name") or str(row.get("domain_name", "")).strip()):
                try:
                    bucket = DOMAIN_ENTITIES.get(row["entity_type"], [])
                    ent = next((e for e in bucket if e["domain_id"] == row["domain_id"]), None)
                    row["domain_name"] = (ent.get("name") or "").strip() if ent else ""
                except NameError:
                    row["domain_name"] = ""
            rows.append(row)
    return rows

def _domain_entity_name(entity_type: str, domain_id: int) -> str:
    """Return display name for a domain entity (from DOMAIN_ENTITIES). Empty if not found or not yet loaded."""
    try:
        bucket = DOMAIN_ENTITIES.get(entity_type, [])
        ent = next((e for e in bucket if e["domain_id"] == domain_id), None)
        return (ent.get("name") or "").strip() if ent else ""
    except NameError:
        return ""

def _save_entity_feed_mapping(entity_type: str, domain_id: int, feed_provider_id: int, feed_id: str, domain_name: str | None = None) -> None:
    """Append one row to entity_feed_mappings.csv (one feed reference per domain entity)."""
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
    """Rewrite entity_feed_mappings.csv from current ENTITY_FEED_MAPPINGS in memory."""
    with open(ENTITY_FEED_MAPPINGS_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_ENTITY_FEED_MAPPING_FIELDS)
        writer.writeheader()
        for m in ENTITY_FEED_MAPPINGS:
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
    Clear all entity and relation CSV files (header-only). Does not touch feeds.csv.
    Caller must reload DOMAIN_EVENTS, DOMAIN_ENTITIES, ENTITY_FEED_MAPPINGS after.
    """
    with open(DOMAIN_EVENTS_PATH, "w", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=_DOMAIN_EVENT_FIELDS).writeheader()
    with open(EVENT_MAPPINGS_PATH, "w", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=_MAPPING_FIELDS).writeheader()
    with open(ENTITY_FEED_MAPPINGS_PATH, "w", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=_ENTITY_FEED_MAPPING_FIELDS).writeheader()
    for etype in _ENTITY_FIELDS:
        if etype == "feeds":
            continue
        path = DATA_DIR / f"{etype}.csv"
        with open(path, "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=_ENTITY_FIELDS[etype]).writeheader()


def _rewrite_entity_feed_mappings_with_domain_name() -> None:
    """If CSV has no domain_name column, rewrite it with new schema and backfilled domain_name."""
    if not ENTITY_FEED_MAPPINGS_PATH.exists():
        return
    with open(ENTITY_FEED_MAPPINGS_PATH, newline="", encoding="utf-8") as f:
        first_line = f.readline() or ""
    if "domain_name" in first_line:
        return
    rows = []
    for m in ENTITY_FEED_MAPPINGS:
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

def _sync_feeder_events_mapping_status() -> None:
    """Re-sync DUMMY_EVENTS mapping_status and domain_id from current event_mappings.csv (single source of truth)."""
    mapped_index = {
        (_m["feed_provider"], _m["feed_valid_id"]): _m["domain_event_id"]
        for _m in _load_event_mappings()
    }
    for _e in DUMMY_EVENTS:
        _key = (_e.get("feed_provider", ""), _e.get("valid_id", ""))
        if _key in mapped_index:
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

def _resolve_sport_alias(feed_provider_id: int, feed_sport_id_or_name: str) -> dict | None:
    """Return the domain sport dict if a sport mapping exists. Prefer match by feed sport ID, then by sport name (case-insensitive)."""
    incoming = (feed_sport_id_or_name or "").strip()
    if not incoming or feed_provider_id is None:
        return None
    incoming_lower = incoming.lower()
    # Try exact match first (for feed sport IDs), then case-insensitive (for names)
    mapping = next((m for m in ENTITY_FEED_MAPPINGS
                   if m["entity_type"] == "sports"
                   and m["feed_provider_id"] == int(feed_provider_id)
                   and ((m.get("feed_id") or "").strip() == incoming or (m.get("feed_id") or "").strip().lower() == incoming_lower)), None)
    if not mapping:
        return None
    return next((s for s in DOMAIN_ENTITIES["sports"] if s["domain_id"] == mapping["domain_id"]), None)


def _load_feed_markets_for_sport(feed_code: str, feed_sport_id: int) -> list[dict]:
    """
    Load unique markets for a sport from a feed JSON file (e.g. designs/feed_json_examples/bwin.json).
    feed_sport_id is the feed's sport id (e.g. 4 for Football in Bwin).
    Uniqueness is by templateCategory:id (feed_market_id). Display name from templateCategory:name:value.
    Returns list of { "id", "name", "is_prematch" }. If event has no IsPreMatch, treat as prematch.
    """
    path = FEED_JSON_DIR / f"{feed_code}.json"
    if not path.exists():
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []
    results = data.get("results") or []
    # Unique by (templateCategory.id, display_name) so we get 8 distinct markets when feed uses id 0 for all (e.g. Football)
    by_key: dict[tuple, dict] = {}
    for event in results:
        if event.get("SportId") != feed_sport_id:
            continue
        is_prematch = event.get("IsPreMatch", True)  # prematch if not in feed
        for item in (event.get("Markets") or []) + (event.get("optionMarkets") or []):
            tc = item.get("templateCategory")
            if not tc:
                continue
            mid = tc.get("id")
            if mid is None:
                continue
            try:
                mid = int(mid)
            except (TypeError, ValueError):
                continue
            name = (tc.get("name") or {}).get("value") or ""
            if not name:
                name = (item.get("name") or {}).get("value") or ""
            name = name or ("(id " + str(mid) + ")")
            key = (mid, name)
            if key in by_key:
                continue
            by_key[key] = {"id": mid, "name": name, "is_prematch": is_prematch}
    return list(by_key.values())


def _resolve_entity(etype: str, feed_id: str, feed_provider_id: int) -> dict | None:
    """Look up a domain entity by its raw feed_id and provider (from entity_feed_mappings)."""
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
    return next((e for e in DOMAIN_ENTITIES[etype] if e["domain_id"] == mapping["domain_id"]), None)


def _fuzzy_score(a: str, b: str) -> int:
    """Return similarity 0-100 between two strings (case-insensitive)."""
    if not a or not b:
        return 0
    a, b = a.strip().lower(), b.strip().lower()
    if a == b:
        return 100
    return int(round(100 * difflib.SequenceMatcher(None, a, b).ratio()))


def _suggest_domain_event(feed_event: dict) -> tuple[dict | None, int]:
    """
    Find best-matching domain event for this feed event (same match from another feed).
    Returns (domain_event_dict, match_score_0_100) or (None, 0).
    """
    if not DOMAIN_EVENTS:
        return None, 0
    feed_home = (feed_event.get("raw_home_name") or "").strip()
    feed_away = (feed_event.get("raw_away_name") or "").strip()
    feed_comp = (feed_event.get("raw_league_name") or "").strip()
    feed_start = (feed_event.get("start_time") or "").strip()
    if not feed_home and not feed_away:
        return None, 0
    best_ev, best_score = None, 0
    for ev in DOMAIN_EVENTS:
        d_home = (ev.get("home") or "").strip()
        d_away = (ev.get("away") or "").strip()
        d_comp = (ev.get("competition") or "").strip()
        d_start = (ev.get("start_time") or "").strip()
        s_home = _fuzzy_score(feed_home, d_home) if feed_home and d_home else (100 if not feed_home and not d_home else 0)
        s_away = _fuzzy_score(feed_away, d_away) if feed_away and d_away else (100 if not feed_away and not d_away else 0)
        s_comp = _fuzzy_score(feed_comp, d_comp) if feed_comp or d_comp else 100
        s_start = 100 if feed_start and d_start and feed_start == d_start else (50 if feed_start and d_start else 100)
        score = int(round(0.4 * s_home + 0.4 * s_away + 0.15 * s_comp + 0.05 * s_start))
        if score > best_score and score >= 50:
            best_score = score
            best_ev = ev
    return (best_ev, best_score) if best_ev else (None, 0)


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

    # Resolve parent FKs from names ─────────────────────────────────────────
    sport_id: Optional[int] = None
    category_id: Optional[int] = None

    if body.entity_type in ("categories", "competitions", "teams") and body.sport:  # markets need no sport
        sp = next((s for s in DOMAIN_ENTITIES["sports"] if s["name"].lower() == body.sport.lower()), None)
        if sp:
            sport_id = sp["domain_id"]
        else:
            raise HTTPException(status_code=400, detail=f"Sport '{body.sport}' not found. Create it in Entities first.")

    if body.entity_type == "competitions" and body.category:
        cp = next((c for c in DOMAIN_ENTITIES["categories"]
                   if c["name"].lower() == body.category.lower()
                   and c.get("sport_id") == sport_id), None)
        if cp:
            category_id = cp["domain_id"]
        else:
            raise HTTPException(status_code=400, detail=f"Category '{body.category}' not found under sport '{body.sport}'.")

    # For teams/categories/competitions/markets: check if this feed already maps to a domain entity (idempotent)
    if body.entity_type in ("categories", "competitions", "teams", "markets") and body.feed_id and body.feed_provider_id:
        already_mapped = next((m for m in ENTITY_FEED_MAPPINGS
                              if m["entity_type"] == body.entity_type
                              and m["feed_provider_id"] == body.feed_provider_id
                              and str(m["feed_id"]) == str(body.feed_id)), None)
        if already_mapped:
            e = next((x for x in bucket if x["domain_id"] == already_mapped["domain_id"]), None)
            if e:
                return {"domain_id": e["domain_id"], "name": e["name"], "created": False}

    # Deduplication: same name+sport (and category for comp) → link this feed to existing entity
    if body.entity_type == "sports":
        existing = next((e for e in bucket if e["name"].lower() == body.name.lower()), None)
    elif body.entity_type == "markets":
        existing = next((e for e in bucket if e["name"].lower() == body.name.lower()), None)
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
        pass  # name only for sports; markets have code set above
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
        home  = ev.get("home") or ""
        away  = ev.get("away") or ""
        comp  = ev.get("competition") or ""
        label = f"{home} vs {away}" if (home and away) else (home or ev_id)
        cards += f"""
        <div class="p-2 border border-primary/50 bg-primary/10 rounded flex items-center gap-2 cursor-pointer hover:bg-primary/20 transition-colors"
             onclick="selectDomainEvent('{ev_id}', '{label.replace("'", "&#39;")}')">
            <div>
                <div class="text-white text-xs font-medium">{label}</div>
                <div class="text-[10px] text-slate-400">{comp}</div>
            </div>
            <div class="text-[10px] font-mono text-primary bg-primary/20 px-1.5 py-0.5 rounded ml-auto shrink-0">{ev_id}</div>
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


@app.post("/api/dump-csv-data", response_class=HTMLResponse)
async def dump_csv_data(request: Request):
    """
    Clear all entity and relation CSVs (header-only). feeds.csv is not touched.
    Reloads in-memory state and redirects to dashboard.
    """
    _dump_entity_and_relation_csvs()
    global DOMAIN_EVENTS, DOMAIN_ENTITIES, ENTITY_FEED_MAPPINGS
    DOMAIN_EVENTS = _load_domain_events()
    DOMAIN_ENTITIES = _load_entities()
    ENTITY_FEED_MAPPINGS = _load_entity_feed_mappings()
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


@app.get("/feeder-events", response_class=HTMLResponse)
async def feeder_events_view(
    request: Request,
    feed_provider: str = None,
    sports: List[str] = Query(default=None),
    categories: List[str] = Query(default=None),
    competitions: List[str] = Query(default=None),
):
    _sync_feeder_events_mapping_status()
    selected_feed = feed_provider or KNOWN_FEEDS[0]
    selected_feed_pid = next((f["domain_id"] for f in FEEDS if f["code"] == selected_feed), None)
    feed_sports = SPORTS_BY_FEED.get(selected_feed, KNOWN_SPORTS)
    feed_sports_live = sorted({e["sport"] for e in DUMMY_EVENTS if e.get("feed_provider") == selected_feed and e.get("sport")}) or feed_sports
    selected_sports = sports if sports else feed_sports_live
    selected_categories = categories or []
    selected_competitions = competitions or []
    filtered = [
        e for e in DUMMY_EVENTS
        if e["feed_provider"] == selected_feed
        and e.get("sport") in selected_sports
    ]
    if selected_categories:
        filtered = [e for e in filtered if _feeder_category_key(e) in selected_categories]
    if selected_competitions:
        filtered = [e for e in filtered if _feeder_competition_key(e) in selected_competitions]
    available_categories = _feeder_categories(selected_feed, selected_sports)
    available_competitions = _feeder_competitions(selected_feed, selected_sports, selected_categories if selected_categories else None)
    _mk = lambda etype: {(m["feed_provider_id"], str(m["feed_id"])) for m in ENTITY_FEED_MAPPINGS if m["entity_type"] == etype}
    _mk_sport = lambda: {(m["feed_provider_id"], (m.get("feed_id") or "").strip().lower()) for m in ENTITY_FEED_MAPPINGS if m.get("entity_type") == "sports"}
    mapped_sport_feed_ids = _mk_sport()
    mapped_category_feed_ids = _mk("categories")
    mapped_comp_feed_ids     = _mk("competitions")
    mapped_team_feed_ids     = _mk("teams")
    return templates.TemplateResponse("feeder_events.html", {
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
        "events": filtered,
        "mapped_sport_feed_ids": mapped_sport_feed_ids,
        "mapped_category_feed_ids": mapped_category_feed_ids,
        "mapped_comp_feed_ids": mapped_comp_feed_ids,
        "mapped_team_feed_ids": mapped_team_feed_ids,
    })

@app.get("/feeder-events/sport-options", response_class=HTMLResponse)
async def feeder_events_sport_options(request: Request, feed_provider: str = None):
    """
    HTMX Endpoint: Returns sport checkboxes (all checked) for the given feed.
    Called when the feed filter changes so the sport list updates.
    """
    selected_feed = feed_provider or KNOWN_FEEDS[0]
    feed_sports = SPORTS_BY_FEED.get(selected_feed, KNOWN_SPORTS)
    return templates.TemplateResponse("_sport_checkboxes.html", {
        "request": request,
        "sports": feed_sports
    })

@app.get("/feeder-events/table", response_class=HTMLResponse)
async def feeder_events_table(
    request: Request,
    feed_provider: str = None,
    mapping_status_filter: str = "",
    outright_filter: str = "",
    q: str = "",
    sports: List[str] = Query(default=None),
    categories: List[str] = Query(default=None),
    competitions: List[str] = Query(default=None),
):
    """
    HTMX Endpoint: Returns filtered tbody rows only.
    Supports: feed, sports, categories, competitions, mapping status, outright, and text search.
    """
    _sync_feeder_events_mapping_status()
    selected_feed = feed_provider or KNOWN_FEEDS[0]
    feed_sports = sorted({e["sport"] for e in DUMMY_EVENTS if e.get("feed_provider") == selected_feed and e.get("sport")})
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

    filtered = []
    for e in DUMMY_EVENTS:
        if e["feed_provider"] != selected_feed:
            continue
        if e.get("sport") not in active_sports:
            continue
        if categories and _feeder_category_key(e) not in categories:
            continue
        if competitions and _feeder_competition_key(e) not in competitions:
            continue
        if mapping_status_filter and e["mapping_status"] != mapping_status_filter:
            continue
        if outright_filter == "outright" and not e.get("is_outright"):
            continue
        if outright_filter == "regular" and e.get("is_outright"):
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

    selected_feed_pid = next((f["domain_id"] for f in FEEDS if f["code"] == selected_feed), None)
    _mk = lambda etype: {(m["feed_provider_id"], str(m["feed_id"])) for m in ENTITY_FEED_MAPPINGS if m["entity_type"] == etype}
    _mk_sport = lambda: {(m["feed_provider_id"], (m.get("feed_id") or "").strip().lower()) for m in ENTITY_FEED_MAPPINGS if m.get("entity_type") == "sports"}
    mapped_sport_feed_ids = _mk_sport()
    mapped_category_feed_ids = _mk("categories")
    mapped_comp_feed_ids    = _mk("competitions")
    mapped_team_feed_ids    = _mk("teams")
    return templates.TemplateResponse("_feeder_events_rows.html", {
        "request": request,
        "events": filtered,
        "selected_feed_pid": selected_feed_pid,
        "mapped_sport_feed_ids": mapped_sport_feed_ids,
        "mapped_category_feed_ids": mapped_category_feed_ids,
        "mapped_comp_feed_ids": mapped_comp_feed_ids,
        "mapped_team_feed_ids": mapped_team_feed_ids,
    })


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
    return templates.TemplateResponse("_feeder_category_checkboxes.html", {
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
    return templates.TemplateResponse("_feeder_competition_checkboxes.html", {
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
) -> list[dict]:
    """Filter enriched domain events by optional date, sports, categories, competitions, and text search."""
    out = enriched
    if date_str and date_str.strip():
        try:
            target = datetime.strptime(date_str.strip()[:10], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            target = None
        if target is not None:
            out = [
                ev for ev in out
                if _parse_start_time(ev.get("start_time")) and _parse_start_time(ev["start_time"]).date() == target
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


@app.get("/domain-events", response_class=HTMLResponse)
async def domain_events_view(
    request: Request,
    date: str | None = None,
    sports: List[str] = Query(default=None),
    categories: List[str] = Query(default=None),
    competitions: List[str] = Query(default=None),
    q: str | None = None,
):
    """
    Domain Events Table (Golden Copy). Supports filter by date, sport, category, competition, and text search.
    """
    mappings_by_event: dict[str, list[dict]] = {}
    for m in _load_event_mappings():
        mappings_by_event.setdefault(m["domain_event_id"], []).append(m)
    # Fresh feed events from JSON so edits to bwin.json etc. are picked up without server restart
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
    filtered = _filter_domain_events(
        enriched, date, active_sports, q,
        selected_categories if selected_categories else None,
        selected_competitions if selected_competitions else None,
    )
    return templates.TemplateResponse("domain_events.html", {
        "request": request,
        "section": "domain",
        "domain_events": filtered,
        "mappings_by_event": mappings_by_event,
        "sports": domain_sports,
        "selected_sports": selected_sports,
        "available_categories": available_categories,
        "selected_categories": selected_categories,
        "available_competitions": available_competitions,
        "selected_competitions": selected_competitions,
        "selected_date": date or "",
        "search_q": q or "",
    })


@app.get("/domain-events/table", response_class=HTMLResponse)
async def domain_events_table(
    request: Request,
    date: str | None = None,
    sports: List[str] = Query(default=None),
    categories: List[str] = Query(default=None),
    competitions: List[str] = Query(default=None),
    q: str | None = None,
):
    """
    HTMX Endpoint: Returns filtered domain events table rows only.
    Supports date, sport, category, competition, and text search.
    """
    mappings_by_event: dict[str, list[dict]] = {}
    for m in _load_event_mappings():
        mappings_by_event.setdefault(m["domain_event_id"], []).append(m)
    # Fresh feed events from JSON so edits to bwin.json etc. are picked up without server restart
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
    filtered = _filter_domain_events(
        enriched, date, active_sports, q,
        categories if categories else None,
        competitions if competitions else None,
    )
    return templates.TemplateResponse("_domain_events_rows.html", {
        "request": request,
        "domain_events": filtered,
    })


def _markets_by_group() -> list[dict]:
    """Build list of { group, markets } for event details left column. Group order follows market_groups; markets use market_group (code)."""
    market_groups = _load_market_groups()
    markets = DOMAIN_ENTITIES.get("markets") or []
    group_codes = {(g.get("code") or "").strip() for g in market_groups}
    result: list[dict] = []
    for g in market_groups:
        code = (g.get("code") or "").strip()
        group_markets = [m for m in markets if (m.get("market_group") or "").strip() == code]
        result.append({"group": g, "markets": group_markets})
    orphan = [m for m in markets if (m.get("market_group") or "").strip() not in group_codes]
    if orphan:
        result.append({"group": {"domain_id": 0, "code": "", "name": "Other"}, "markets": orphan})
    return result


@app.get("/domain-events/event_details/{domain_id}", response_class=HTMLResponse)
async def domain_event_details(request: Request, domain_id: str):
    """Event details page for a single domain event. Opens in new tab from Event column."""
    from fastapi import HTTPException
    ev = next((e for e in DOMAIN_EVENTS if e.get("id") == domain_id), None)
    if not ev:
        raise HTTPException(status_code=404, detail="Domain event not found")
    mappings = [m for m in _load_event_mappings() if m.get("domain_event_id") == domain_id]
    markets_by_group = _markets_by_group()
    brands = _load_brands()
    return templates.TemplateResponse("event_details.html", {
        "request": request,
        "section": "domain",
        "event": ev,
        "mappings": mappings,
        "markets_by_group": markets_by_group,
        "brands": brands,
    })


@app.get("/domain-events/category-options", response_class=HTMLResponse)
async def domain_events_category_options(
    request: Request,
    sports: List[str] = Query(default=None),
    categories: List[str] = Query(default=None),
):
    """HTMX: Category checkboxes for domain events filter. Only categories for the given sports."""
    cat_list = _domain_events_categories(sports) if sports else []
    selected = categories or []
    return templates.TemplateResponse("_domain_category_checkboxes.html", {
        "request": request,
        "categories": cat_list,
        "selected_categories": selected,
    })


@app.get("/domain-events/competition-options", response_class=HTMLResponse)
async def domain_events_competition_options(
    request: Request,
    sports: List[str] = Query(default=None),
    categories: List[str] = Query(default=None),
    competitions: List[str] = Query(default=None),
):
    """HTMX: Competition checkboxes for domain events filter. Only competitions for given sports and categories."""
    comp_list = _domain_events_competitions(sports, categories) if (sports and categories) else []
    selected = competitions or []
    return templates.TemplateResponse("_domain_competition_checkboxes.html", {
        "request": request,
        "competitions": comp_list,
        "selected_competitions": selected,
    })


@app.post("/api/map-sport", response_class=HTMLResponse)
async def map_sport(
    request: Request,
    feeder_provider: str = Form(default=""),
    feeder_valid_id: str = Form(default=""),
    domain_sport_id: str = Form(default=""),
):
    """Map feed sport to a domain sport. Saves entity_feed_mapping and returns updated modal HTML."""
    if not domain_sport_id or not domain_sport_id.strip():
        return HTMLResponse(
            '<div class="p-6 text-center text-amber-400 text-sm">'
            '<i class="fa-solid fa-triangle-exclamation mr-2"></i>Select a sport from the dropdown first.</div>'
        )
    try:
        dom_sport_id = int(domain_sport_id.strip())
    except ValueError:
        return HTMLResponse(
            '<div class="p-6 text-center text-red-400 text-sm">Invalid domain sport.</div>'
        )
    event = next((e for e in DUMMY_EVENTS if e["valid_id"] == feeder_valid_id), None)
    if not event:
        return HTMLResponse('<div class="p-6 text-red-500">Event not found.</div>')
    feed_obj = next((f for f in FEEDS if (f.get("code") or "").lower() == (feeder_provider or "").lower()), None)
    if not feed_obj:
        return HTMLResponse('<div class="p-6 text-red-500">Feed not found.</div>')
    feed_pid = int(feed_obj["domain_id"])
    _raw_sport_id = event.get("sport_id")
    feed_sport_val = str(_raw_sport_id).strip() if _raw_sport_id not in (None, "") else ""
    if not feed_sport_val:
        return HTMLResponse(
            '<div class="p-6 text-center text-amber-400 text-sm">Event has no sport_id to map. Sport mapping uses feed sport_id only.</div>'
        )
    _ensure_entity_feed_mapping("sports", dom_sport_id, feed_pid, feed_sport_val)
    return _render_mapping_modal(request, feeder_valid_id)


def _render_mapping_modal(request: Request, event_id: str):
    """
    Build and return the Mapping Modal HTML. Used by GET modal and by POST map-sport.
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
    # Category and competition: resolve by feed ID only (not by name), so UI stays editable until user maps by ID
    r_category = None
    if feed_pid and (event.get("category_id") not in (None, "")):
        r_category = _resolve_entity("categories", str(event.get("category_id") or ""), feed_pid)
    r_competition = None
    if feed_pid and (event.get("raw_league_id") not in (None, "")):
        r_competition = _resolve_entity("competitions", str(event.get("raw_league_id") or ""), feed_pid)
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

    # Fuzzy: suggest existing domain event (same match from another feed)
    suggested_domain_event, suggested_match_score = _suggest_domain_event(event)

    # Sport: no suggestions or fuzzy when unmapped — UI shows dropdown of domain sports + Map button only
    suggested_sports = []

    # Entity suggestions: best match per field (for prefill / match %)
    sport_id_for_suggest = r_sport["domain_id"] if r_sport else (suggested_sports[0]["domain_id"] if suggested_sports else None)
    category_id_for_suggest = None
    if suggested_domain_event:
        # Prefer suggestions from the suggested domain event
        suggested_category = suggested_domain_event.get("category")
        suggested_competition = suggested_domain_event.get("competition")
        suggested_home = suggested_domain_event.get("home")
        suggested_away = suggested_domain_event.get("away")
    else:
        suggested_category = suggested_competition = suggested_home = suggested_away = None
    # When no suggested domain event, suggest by feed names within sport
    if not suggested_domain_event or not suggested_category:
        cat_candidates = _suggest_entity_by_name("categories", event.get("category") or event.get("raw_league_name") or "", sport_id_for_suggest)
        suggested_category = cat_candidates[0] if cat_candidates else {"name": (event.get("category") or "").strip(), "match_pct": 0}
        if isinstance(suggested_category, dict) and suggested_category.get("name"):
            cat_ent = next((c for c in DOMAIN_ENTITIES["categories"] if c["name"] == suggested_category["name"] and c.get("sport_id") == sport_id_for_suggest), None)
            if cat_ent:
                category_id_for_suggest = cat_ent["domain_id"]
    if not suggested_domain_event or not suggested_competition:
        comp_candidates = _suggest_entity_by_name("competitions", event.get("raw_league_name") or "", sport_id_for_suggest, category_id_for_suggest)
        suggested_competition = comp_candidates[0] if comp_candidates else {"name": (event.get("raw_league_name") or "").strip(), "match_pct": 0}
    # Teams: suggest raw feed names when no match; when mapping same match (score >= 70), pre-fill from that event
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
        suggested_home = {"name": suggested_domain_event.get("home") or "", "match_pct": pct_home, "is_suggested": pct_home == 0}
        suggested_away = {"name": suggested_domain_event.get("away") or "", "match_pct": pct_away, "is_suggested": pct_away == 0}
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
    raw_cat = (event.get("category") or "").strip()
    raw_comp = (event.get("raw_league_name") or "").strip()
    suggested_entities = {
        "category":    _norm(suggested_category, raw_cat) if (suggested_category or raw_cat) else None,
        "competition": _norm(suggested_competition, raw_comp) if (suggested_competition or raw_comp) else None,
        "home":        suggested_home,
        "away":        suggested_away,
    }
    # Only use suggested_domain_event for category/competition when it's clearly the same match (score >= 70).
    # Otherwise we would show wrong values (e.g. Argentina/Liga Profesional for a Barbados event).
    if suggested_domain_event and suggested_match_score >= 70:
        feed_cat = (event.get("category") or "").strip()
        feed_comp = (event.get("raw_league_name") or "").strip()
        d_cat = (suggested_domain_event.get("category") or "").strip()
        d_comp = (suggested_domain_event.get("competition") or "").strip()
        pct_cat = _fuzzy_score(feed_cat, d_cat)
        pct_comp = _fuzzy_score(feed_comp, d_comp)
        suggested_entities["category"] = {"name": suggested_domain_event.get("category") or "", "match_pct": pct_cat, "is_suggested": pct_cat == 0}
        suggested_entities["competition"] = {"name": suggested_domain_event.get("competition") or "", "match_pct": pct_comp, "is_suggested": pct_comp == 0}
    # Ensure is_suggested when match_pct is 0 (raw feed name suggested)
    for key in ("category", "competition", "home", "away"):
        if suggested_entities.get(key):
            suggested_entities[key]["is_suggested"] = (suggested_entities[key].get("match_pct") or 0) == 0

    countries = _load_countries()
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


@app.get("/api/feed-markets")
async def api_feed_markets(
    feed_provider_id: int = Query(..., description="Feed domain_id from feeds.csv"),
    domain_sport_id: int = Query(..., description="Domain sport id (e.g. 1 = Football) to resolve feed's sport id"),
):
    """
    Return unique markets from a feed JSON for the given feed and sport.
    Resolves feed sport id from entity_feed_mappings (sports). If no mapping, returns [].
    Each item: { id, name, is_prematch, feed_name }.
    """
    mapping = next(
        (m for m in ENTITY_FEED_MAPPINGS
         if m.get("entity_type") == "sports"
         and m.get("domain_id") == domain_sport_id
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
    markets = _load_feed_markets_for_sport(feed_code, feed_sport_id)
    for m in markets:
        m["feed_name"] = feed_name
    return {"feed_name": feed_name, "markets": markets}


@app.get("/api/market-type-mappings")
async def api_get_market_type_mappings(
    domain_market_id: int = Query(..., description="Domain market type id"),
):
    """Return prematch and live feed mappings for a domain market type."""
    mappings = _load_market_type_mappings()
    prematch = []
    live = []
    feeds_by_id = {f["domain_id"]: f.get("name") or f.get("code") or "" for f in FEEDS}
    for m in mappings:
        if m["domain_market_id"] != domain_market_id:
            continue
        fid_raw = (m.get("feed_market_id") or "").strip()
        try:
            item_id = int(fid_raw) if fid_raw.isdigit() else fid_raw or None
        except (TypeError, ValueError):
            item_id = fid_raw or None
        item = {
            "feed_provider_id": m["feed_provider_id"],
            "id": item_id,
            "name": (m.get("feed_market_name") or "").strip(),
            "feed_market_name": (m.get("feed_market_name") or "").strip(),
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
    bid = _next_brand_id(brands)
    new_brand = {
        "id": bid,
        "name": name,
        "code": code,
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


@app.post("/api/margin-templates")
async def create_margin_template(body: CreateMarginTemplateRequest):
    """Create a new margin template. Name required; other fields optional."""
    rows = _load_margin_templates()
    next_id = max((r.get("id") or 0 for r in rows), default=0) + 1
    name = (body.name or "").strip()
    if not name:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Name is required")
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
    }
    rows.append(new_template)
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
    _save_margin_templates(rows)
    return {"ok": True, "template": template}


@app.get("/entities", response_class=HTMLResponse)
async def entities_view(request: Request):
    """
    Configuration > Entities page.
    Shows Sports, Categories, Competitions, Teams, Markets tabs.
    """
    entities = {
        "sports":       DOMAIN_ENTITIES["sports"],
        "categories":   DOMAIN_ENTITIES["categories"],
        "competitions": DOMAIN_ENTITIES["competitions"],
        "teams":        DOMAIN_ENTITIES["teams"],
        "markets":      DOMAIN_ENTITIES["markets"],
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

    return templates.TemplateResponse("entities.html", {
        "participant_types": participant_types,
        "underage_categories": underage_categories,
        "underage_categories_by_id": underage_categories_by_id,
        "request": request,
        "countries": countries,
        "countries_by_cc": countries_by_cc,
        "section": "entities",
        "entities": entities,
        "stats": stats,
        "sports_by_id": sports_by_id,
        "categories_by_id": categories_by_id,
        "feeds_by_id": feeds_by_id,
        "feeds": FEEDS,
        "entity_feed_refs_by_key": entity_feed_refs_by_key,
        "market_templates": market_templates,
        "market_period_types": market_period_types,
        "market_score_types": market_score_types,
        "market_groups": market_groups,
        "participant_types_by_id": participant_types_by_id,
    })


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

    return templates.TemplateResponse("feeders.html", {
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


@app.get("/margin-config", response_class=HTMLResponse)
async def margin_config_view(
    request: Request,
    brand_id: str | None = None,
    sport_id: str | None = None,
    template_id: str | None = None,
):
    """
    Betting Program > Margin Configuration.
    Top: Brand (Global level + brands), Sport (default Football), Apply. Tables shown only after Apply.
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
        return templates.TemplateResponse("margin_config.html", {
            "request": request,
            "section": "margin_config",
            "brands": brands,
            "sports": sports,
            "selected_brand_id": selected_brand_id,
            "selected_sport_id": selected_sport_id,
            "show_tables": False,
            "margin_templates": [],
            "market_groups_with_markets": [],
            "selected_template_id": None,
            "market_templates": [],
            "period_types": [],
            "score_types": [],
        })

    # Load table data only after Apply
    margin_templates = _load_margin_templates()
    template_competitions = _load_margin_template_competitions()
    # Backfill: assign any domain competition not yet in mapping to Uncategorized (template_id=1)
    domain_competition_ids = {int(c["domain_id"]) for c in DOMAIN_ENTITIES.get("competitions", []) if c.get("domain_id") is not None}
    assigned_ids = {r["competition_id"] for r in template_competitions}
    uncategorized_id = 1
    added = 0
    for cid in domain_competition_ids:
        if cid not in assigned_ids:
            template_competitions.append({"template_id": uncategorized_id, "competition_id": cid})
            assigned_ids.add(cid)
            added += 1
    if added:
        _save_margin_template_competitions(template_competitions)
    # Competition count per template: only competitions for the selected sport
    competition_ids_for_sport = {
        int(c["domain_id"]) for c in DOMAIN_ENTITIES.get("competitions", [])
        if c.get("domain_id") is not None and c.get("sport_id") == selected_sport_id
    } if selected_sport_id else set()
    for t in margin_templates:
        tid = t.get("id")
        t["leagues_count"] = sum(
            1 for r in template_competitions
            if r.get("template_id") == tid and r.get("competition_id") in competition_ids_for_sport
        )
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

    markets = DOMAIN_ENTITIES.get("markets", [])
    market_groups_list = _load_market_groups()
    if markets:
        group_codes = {(g.get("code") or "").strip() for g in market_groups_list}
        market_groups_with_markets: list[dict] = []
        for g in market_groups_list:
            code = (g.get("code") or "").strip()
            group_markets = [{"domain_id": m.get("domain_id"), "code": m.get("code"), "name": m.get("name") or m.get("code"), "market_group": m.get("market_group")} for m in markets if (m.get("market_group") or "").strip() == code]
            market_groups_with_markets.append({"group": g, "markets": group_markets})
        orphan = [{"domain_id": m.get("domain_id"), "code": m.get("code"), "name": m.get("name") or m.get("code"), "market_group": m.get("market_group")} for m in markets if (m.get("market_group") or "").strip() not in group_codes]
        if orphan:
            market_groups_with_markets.append({"group": {"domain_id": 0, "code": "", "name": "Other"}, "markets": orphan})
    else:
        market_groups_with_markets = [{"group": {"domain_id": 0, "code": "", "name": "Main"}, "markets": [{"domain_id": t.get("domain_id"), "code": t.get("code"), "name": (t.get("name") or "").strip() or t.get("code")} for t in market_templates]}]

    selected_template_name = ""
    template_prematch_dyn = ""
    template_inplay_dyn = ""
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

    return templates.TemplateResponse("margin_config.html", {
        "request": request,
        "section": "margin_config",
        "brands": brands,
        "sports": sports,
        "selected_brand_id": selected_brand_id,
        "selected_sport_id": selected_sport_id,
        "show_tables": True,
        "margin_templates": margin_templates,
        "market_groups_with_markets": market_groups_with_markets,
        "selected_template_id": selected_template_id,
        "selected_template_name": selected_template_name,
        "template_prematch_dyn": template_prematch_dyn,
        "template_inplay_dyn": template_inplay_dyn,
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

    return templates.TemplateResponse("localization.html", {
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
    First row is Global (read-only; represents platform default / union of all brands).
    Other rows are brands from data/brands.csv with jurisdiction, languages, currencies, odds formats.
    """
    brands = _load_brands()
    countries = _load_countries()
    languages = _load_languages()
    countries_by_cc = {c.get("cc", ""): c.get("name", "") for c in countries}
    languages_by_id = {str(l.get("id")): l.get("name", "") for l in languages}
    # Resolve jurisdiction and language display names for table
    for b in brands:
        j_codes = [x.strip() for x in (b.get("jurisdiction") or "").split(",") if x.strip()]
        b["jurisdiction_display"] = ", ".join(countries_by_cc.get(cc, cc) for cc in j_codes) or "—"
        l_ids = [x.strip() for x in (b.get("language_ids") or "").split(",") if x.strip()]
        b["language_display"] = ", ".join(languages_by_id.get(lid, lid) for lid in l_ids) or "—"
    return templates.TemplateResponse("brands.html", {
        "request": request,
        "section": "brands",
        "brands": brands,
        "countries": countries,
        "languages": languages,
        "currencies": BRAND_CURRENCIES,
        "odds_formats": BRAND_ODDS_FORMATS,
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
