"""
Application configuration: paths, directory layout, and CSV/entity schema constants.
No runtime state (no loaded data); safe to import from any module.
"""
from pathlib import Path

# ── Directories ─────────────────────────────────────────────────────────────
_BACKEND_DIR = Path(__file__).resolve().parent
BASE_DIR = _BACKEND_DIR
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
DATA_DIR = BASE_DIR / "data"
PROJECT_ROOT = BASE_DIR.parent
FEED_JSON_DIR = PROJECT_ROOT / "designs" / "feed_json_examples"
DATA_COUNTRIES_DIR = DATA_DIR / "countries"
DATA_MARKETS_DIR = DATA_DIR / "markets"

# Ensure data dirs exist (idempotent)
DATA_DIR.mkdir(exist_ok=True)
DATA_COUNTRIES_DIR.mkdir(exist_ok=True)
DATA_MARKETS_DIR.mkdir(exist_ok=True)

# ── Entity CSV field schemas ────────────────────────────────────────────────
# Entity tables store domain data only; feed refs live in entity_feed_mappings.csv
ENTITY_FIELDS = {
    "feeds":         ["domain_id", "code", "name"],
    "sports":        ["domain_id", "name", "baseid", "created_at", "updated_at"],
    "categories":    ["domain_id", "sport_id", "name", "baseid", "jurisdiction", "created_at", "updated_at"],
    "competitions":  [
        "domain_id", "sport_id", "category_id", "name", "baseid", "jurisdiction",
        "underage_category_id", "participant_type_id", "is_amateur", "created_at", "updated_at",
    ],
    "teams":         [
        "domain_id", "sport_id", "name", "baseid", "jurisdiction",
        "underage_category_id", "participant_type_id", "is_amateur", "created_at", "updated_at",
    ],
    "markets":       [
        "domain_id", "code", "name", "abb", "market_type", "market_group",
        "template", "period_type", "score_type", "side_type", "score_dependant",
        "created_at", "updated_at",
    ],
}

# ── Paths: events & mappings ────────────────────────────────────────────────
DOMAIN_EVENTS_PATH = DATA_DIR / "domain_events.csv"
EVENT_MAPPINGS_PATH = DATA_DIR / "event_mappings.csv"
ENTITY_FEED_MAPPINGS_PATH = DATA_DIR / "entity_feed_mappings.csv"
# Sport–feed mappings: developer-controlled, committed/deployed, never dumped (same on local and server)
SPORT_FEED_MAPPINGS_PATH = DATA_DIR / "sport_feed_mappings.csv"
ENTITY_FEED_MAPPING_FIELDS = ["entity_type", "domain_id", "feed_provider_id", "feed_id", "domain_name"]
DOMAIN_EVENT_FIELDS = [
    "domain_id", "sport", "category", "competition",
    "home", "home_id", "away", "away_id", "start_time",
]
MAPPING_FIELDS = ["domain_event_id", "feed_provider", "feed_valid_id"]

# ── Paths: markets (developer-managed) ──────────────────────────────────────
MARKET_TEMPLATES_PATH = DATA_MARKETS_DIR / "market_templates.csv"
MARKET_PERIOD_TYPE_PATH = DATA_MARKETS_DIR / "market_period_type.csv"
MARKET_SCORE_TYPE_PATH = DATA_MARKETS_DIR / "market_score_type.csv"
MARKET_GROUPS_PATH = DATA_MARKETS_DIR / "market_groups.csv"
MARKET_TYPE_MAPPINGS_PATH = DATA_MARKETS_DIR / "market_type_mappings.csv"
MARKET_TYPE_MAPPING_FIELDS = ["domain_market_id", "feed_provider_id", "feed_market_id", "feed_market_name", "phase"]
MARKET_TEMPLATE_FIELDS = ["domain_id", "code", "name", "params"]

# ── Paths: localization & reference data ────────────────────────────────────
COUNTRIES_PATH = DATA_COUNTRIES_DIR / "countries.json"
PARTICIPANT_TYPE_PATH = DATA_COUNTRIES_DIR / "participant_type.csv"
UNDERAGE_CATEGORIES_PATH = DATA_COUNTRIES_DIR / "underage_categories.csv"
LANGUAGES_PATH = DATA_DIR / "languages.csv"
TRANSLATIONS_PATH = DATA_DIR / "translations.csv"
BRANDS_PATH = DATA_DIR / "brands.csv"
BRANDS_FIELDS = ["id", "name", "code", "jurisdiction", "language_ids", "currencies", "odds_formats", "created_at", "updated_at"]
FEEDS_PATH = DATA_DIR / "feeds.csv"
FEED_SPORTS_PATH = DATA_DIR / "feed_sports.csv"
FEEDER_CONFIG_PATH = DATA_DIR / "feeder_config.csv"
FEEDER_INCIDENTS_PATH = DATA_DIR / "feeder_incidents.csv"
# Notes: own folder for current and future note CSVs
DATA_NOTES_DIR = DATA_DIR / "notes"
DATA_NOTES_DIR.mkdir(exist_ok=True)
FEEDER_EVENT_NOTES_PATH = DATA_DIR / "feeder_event_notes.csv"  # legacy; migrated to platform_notes (in notes/)
FEEDER_IGNORED_EVENTS_PATH = DATA_DIR / "feeder_ignored_events.csv"  # feed_provider, feed_valid_id — events to treat as ignored
FEEDER_EVENT_LOG_PATH = DATA_DIR / "feeder_event_log.csv"  # feed_provider, feed_valid_id, action_type, details, created_at
NOTES_PATH = DATA_NOTES_DIR / "platform_notes.csv"  # + created_by, updated_by, requires_confirmation
NOTES_PATH_LEGACY = DATA_DIR / "platform_notes.csv"  # one-time move from here to NOTES_PATH if present
EVENT_NAVIGATOR_NOTES_PATH = DATA_NOTES_DIR / "event_navigator_notes.csv"  # domain_event_id, note_text, updated_at (Event Navigator screen only)
NOTIFICATIONS_PATH = DATA_NOTES_DIR / "platform_notifications.csv"  # notification_id, note_id, message_snippet, created_at, confirmed
MARGIN_TEMPLATES_PATH = DATA_DIR / "margin_templates.csv"
MARGIN_TEMPLATE_COMPETITIONS_PATH = DATA_DIR / "margin_template_competitions.csv"

# ── Constants ──────────────────────────────────────────────────────────────
# Country code for "no jurisdiction" (e.g. International category, Champions League)
COUNTRY_CODE_NONE = "-"
