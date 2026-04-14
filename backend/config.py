"""
Application configuration: paths, directory layout, and CSV/entity schema constants.
No runtime state (no loaded data); safe to import from any module.
"""
import os
from pathlib import Path

# ── Directories ─────────────────────────────────────────────────────────────
_BACKEND_DIR = Path(__file__).resolve().parent
BASE_DIR = _BACKEND_DIR
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
DATA_DIR = BASE_DIR / "data"
PROJECT_ROOT = BASE_DIR.parent

# Load .env from project root so BETSAPI_TOKEN and others are available
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

# API token for event-details (BetsAPI/b365api). Used when creating/mapping domain events. Set in .env.
BETSAPI_TOKEN = (os.environ.get("BETSAPI_TOKEN") or "").strip()


def _env_truthy(name: str, default: bool = False) -> bool:
    v = (os.environ.get(name) or "").strip().lower()
    if v in ("1", "true", "yes", "on"):
        return True
    if v in ("0", "false", "no", "off"):
        return False
    return default


# Server-only: background task pulls one feed per UTC hour, rotating through SCHEDULED_FEED_PULL_ORDER.
# Local: leave unset or false; use Pull Feeds Data UI with manual API key entry.
SCHEDULED_FEED_PULL_ENABLED = _env_truthy("SCHEDULED_FEED_PULL", False)
_scheduled_feeds_raw = (os.environ.get("SCHEDULED_FEED_PULL_FEEDS") or "bet365,betfair,1xbet,bwin").strip()
SCHEDULED_FEED_PULL_ORDER: tuple[str, ...] = tuple(
    x.strip().lower() for x in _scheduled_feeds_raw.split(",") if x.strip()
) or ("bet365", "betfair", "1xbet", "bwin")
try:
    SCHEDULED_FEED_PULL_CONCURRENCY = max(1, min(int(os.environ.get("SCHEDULED_FEED_PULL_CONCURRENCY") or "5"), 10))
except (TypeError, ValueError):
    SCHEDULED_FEED_PULL_CONCURRENCY = 5
# Seconds to wait after app startup before the first scheduled pull (lets the process settle).
try:
    SCHEDULED_FEED_PULL_START_DELAY_SEC = max(0, int(os.environ.get("SCHEDULED_FEED_PULL_START_DELAY_SEC") or "60"))
except (TypeError, ValueError):
    SCHEDULED_FEED_PULL_START_DELAY_SEC = 60
FEED_JSON_DIR = PROJECT_ROOT / "designs" / "feed_json_examples"
FEED_DATA_DIR = DATA_DIR / "feed_data"  # Pulled feed events (e.g. bet365 from API); used instead of feed_json_examples when present
FEED_EVENT_DETAILS_DIR = DATA_DIR / "feed_event_details"  # Cached event-details API responses (per feed + feed_valid_id)
DATA_COUNTRIES_DIR = DATA_DIR / "countries"
DATA_MARKETS_DIR = DATA_DIR / "markets"

# Ensure data dirs exist (idempotent)
DATA_DIR.mkdir(exist_ok=True)
FEED_DATA_DIR.mkdir(exist_ok=True)
FEED_EVENT_DETAILS_DIR.mkdir(exist_ok=True)
DATA_COUNTRIES_DIR.mkdir(exist_ok=True)
DATA_MARKETS_DIR.mkdir(exist_ok=True)

# ── Entity CSV field schemas ────────────────────────────────────────────────
# Entity tables store domain data only; feed refs live in entity_feed_mappings.csv
# Categories/competitions/teams use column `country` (ISO code or '-' for international). Brands use `jurisdiction` (Compliance).
ENTITY_FIELDS = {
    "feeds":         ["domain_id", "code", "name"],
    "sports":        ["domain_id", "name", "baseid", "created_at", "updated_at"],
    "categories":    ["domain_id", "sport_id", "name", "baseid", "country", "created_at", "updated_at"],
    "competitions":  [
        "domain_id", "sport_id", "category_id", "name", "baseid", "country",
        "underage_category_id", "participant_type_id", "is_amateur", "created_at", "updated_at",
    ],
    "teams":         [
        "domain_id", "sport_id", "name", "baseid", "country",
        "underage_category_id", "participant_type_id", "is_amateur", "created_at", "updated_at",
    ],
    "markets":       [
        "domain_id", "sport_id", "code", "name", "abb", "market_type", "market_group",
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
    "sport_id", "category_id", "competition_id",
]
MAPPING_FIELDS = ["domain_event_id", "feed_provider", "feed_valid_id"]

# ── Paths: markets (developer-managed) ──────────────────────────────────────
MARKET_TEMPLATES_PATH = DATA_MARKETS_DIR / "market_templates.csv"
MARKET_PERIOD_TYPE_PATH = DATA_MARKETS_DIR / "market_period_type.csv"
MARKET_SCORE_TYPE_PATH = DATA_MARKETS_DIR / "market_score_type.csv"
MARKET_GROUPS_PATH = DATA_MARKETS_DIR / "market_groups.csv"
MARKET_TYPE_MAPPINGS_PATH = DATA_MARKETS_DIR / "market_type_mappings.csv"
MARKET_OUTCOMES_PATH = DATA_MARKETS_DIR / "market_outcomes.csv"
# 1xbet: feed market id = Value.GE[].G (global across sports in API); display names for mapper UI
ONEXBET_MARKET_NAMES_PATH = DATA_MARKETS_DIR / "1xbet_market_names.csv"
ONEXBET_MARKET_NAME_FIELDS = ["G", "name"]
MARKET_TYPE_MAPPING_FIELDS = ["domain_market_id", "feed_provider_id", "feed_market_id", "feed_market_name", "phase"]
MARKET_TEMPLATE_FIELDS = ["domain_id", "code", "name", "params"]

# ── Paths: localization & reference data ────────────────────────────────────
COUNTRIES_PATH = DATA_COUNTRIES_DIR / "countries.json"
PARTICIPANT_TYPE_PATH = DATA_COUNTRIES_DIR / "participant_type.csv"
UNDERAGE_CATEGORIES_PATH = DATA_COUNTRIES_DIR / "underage_categories.csv"
LANGUAGES_PATH = DATA_DIR / "languages.csv"
TRANSLATIONS_PATH = DATA_DIR / "translations.csv"
BRANDS_PATH = DATA_DIR / "brands.csv"
BRANDS_FIELDS = ["id", "name", "code", "partner_id", "jurisdiction", "language_ids", "currencies", "odds_formats", "created_at", "updated_at"]
PARTNERS_PATH = DATA_DIR / "partners.csv"
PARTNERS_FIELDS = ["id", "name", "code", "active", "created_at", "updated_at"]
FEEDS_PATH = DATA_DIR / "feeds.csv"
FEED_SPORTS_PATH = DATA_DIR / "feed_sports.csv"
# Time status codes from feeds → display labels (feeder-events Status column and filter)
FEED_TIME_STATUSES_PATH = DATA_DIR / "feed_time_statuses.csv"
FEED_LAST_PULL_PATH = DATA_DIR / "feed_last_pull.csv"
FEEDER_CONFIG_PATH = DATA_DIR / "feeder_config.csv"
FEEDER_INCIDENTS_PATH = DATA_DIR / "feeder_incidents.csv"
# Notes: own folder for current and future note CSVs
DATA_NOTES_DIR = DATA_DIR / "notes"
DATA_NOTES_DIR.mkdir(exist_ok=True)
FEEDER_EVENT_NOTES_PATH = DATA_DIR / "feeder_event_notes.csv"  # legacy; migrated to platform_notes (in notes/)
FEEDER_IGNORED_EVENTS_PATH = DATA_DIR / "feeder_ignored_events.csv"  # feed_provider, feed_valid_id — events to treat as ignored
# Audit / log files: per-environment, not in repo (backend/data/audit/ is gitignored)
DATA_AUDIT_DIR = DATA_DIR / "audit"
DATA_AUDIT_DIR.mkdir(exist_ok=True)
FEEDER_EVENT_LOG_PATH = DATA_AUDIT_DIR / "feeder_event_log.csv"  # feed_provider, feed_valid_id, action_type, details, created_at
# Append-only: configuration changes by admins (feeder config, incidents, etc.).
ADMIN_AUDIT_LOG_PATH = DATA_AUDIT_DIR / "admin_audit_log.csv"
NOTES_PATH = DATA_NOTES_DIR / "platform_notes.csv"  # + created_by, updated_by, requires_confirmation
NOTES_PATH_LEGACY = DATA_DIR / "platform_notes.csv"  # one-time move from here to NOTES_PATH if present
EVENT_NAVIGATOR_NOTES_PATH = DATA_NOTES_DIR / "event_navigator_notes.csv"  # domain_event_id, note_text, updated_at (Event Navigator screen only)
NOTIFICATIONS_PATH = DATA_NOTES_DIR / "platform_notifications.csv"  # notification_id, note_id, message_snippet, created_at, confirmed
MARGIN_TEMPLATES_PATH = DATA_DIR / "margin_templates.csv"
MARGIN_TEMPLATE_COMPETITIONS_PATH = DATA_DIR / "margin_template_competitions.csv"

# ── RBAC (users, roles, permissions, audit) ─────────────────────────────────
DATA_RBAC_DIR = DATA_DIR / "rbac"
DATA_RBAC_DIR.mkdir(exist_ok=True)
RBAC_USERS_PATH = DATA_RBAC_DIR / "users.csv"
RBAC_ROLES_PATH = DATA_RBAC_DIR / "roles.csv"
RBAC_USER_ROLES_PATH = DATA_RBAC_DIR / "user_roles.csv"
RBAC_ROLE_PERMISSIONS_PATH = DATA_RBAC_DIR / "role_permissions.csv"
RBAC_USER_BRANDS_PATH = DATA_RBAC_DIR / "user_brands.csv"
RBAC_AUDIT_LOG_PATH = DATA_RBAC_DIR / "rbac_audit_log.csv"
# Display name for RBAC rows with no partner_id (not a row in partners.csv).
RBAC_PLATFORM_SCOPE_LABEL = "Internal User"
RBAC_USERS_FIELDS = [
    "user_id", "login", "email", "display_name", "active", "partner_id",
    "created_by", "updated_by", "created_at", "updated_at", "last_login", "online", "is_superadmin",
    "login_pin",
]
RBAC_ROLES_FIELDS = ["role_id", "name", "active", "is_system", "partner_id", "is_master", "created_at", "updated_at"]
RBAC_USER_ROLES_FIELDS = ["user_id", "role_id", "assigned_at", "assigned_by_user_id"]
RBAC_ROLE_PERMISSIONS_FIELDS = ["role_id", "permission_code"]
RBAC_USER_BRANDS_FIELDS = ["user_id", "brand_id"]
RBAC_AUDIT_LOG_FIELDS = ["id", "created_at", "actor_user_id", "action", "target_type", "target_id", "was", "now", "details"]

# ── RBAC: Single source of truth for menu + permissions ─────────────────────
# When you add a new backoffice page or menu item, extend RBAC_MENU_SOURCE (and
# optionally RBAC_PAGE_ACTIONS / RBAC_ENTITY_CRUD). Do NOT edit RBAC_PERMISSION_TREE
# or build_rbac_permission_tree() output by hand — the tree is generated from
# these sources. See .cursor/rules/rbac-permissions.mdc for the full checklist.

def _perm(prefix: str, *actions: str) -> list[dict]:
    action_labels = {"view": "View", "create": "Create", "update": "Update", "delete": "Delete", "unmap": "Unmap", "pause": "Pause", "cascade": "Cascade", "manage": "Manage", "audit": "Audit log"}
    return [{"code": f"{prefix}.{a}", "label": action_labels.get(a, a.title())} for a in actions]


def _menu_view(code: str, always_granted: bool = False) -> list[dict]:
    return [{"code": code, "label": "View", "always_granted": always_granted}]


# Custom (non-CRUD) page actions: key -> list of {code, label}.
# Reference from RBAC_MENU_SOURCE via "actions": "key".
RBAC_PAGE_ACTIONS = {
    "admin_users": [
        {"code": "rbac.users.create", "label": "Add new admin"},
        {"code": "rbac.users.edit", "label": "Edit"},
        {"code": "rbac.users.audit", "label": "Audit log"},
    ],
    "admin_roles": [
        {"code": "rbac.roles.manage", "label": "Manage roles"},
        {"code": "rbac.audit.view", "label": "View audit"},
    ],
    "mapping_extra": [
        {"code": "mapping.unmap", "label": "Unmap"},
        {"code": "mapping.pause", "label": "Pause"},
        {"code": "mapping.cascade", "label": "Cascade"},
    ],
    # Sports tab: matches kebab actions (not CRUD — sports are not created in backoffice).
    "entity_sport": [
        {"code": "entity.sport.view", "label": "View"},
        {"code": "entity.sport.edit", "label": "Edit"},
        {"code": "entity.sport.remove_mappings", "label": "Remove Mappings"},
        {"code": "entity.sport.active_inactive", "label": "Active/Inactive"},
    ],
    # Categories / Competitions / Teams tabs (Entities page): list + New + kebab (no row delete in UI).
    "entity_category": [
        {"code": "entity.category.view", "label": "View"},
        {"code": "entity.category.create", "label": "Create"},
        {"code": "entity.category.edit", "label": "Edit"},
        {"code": "entity.category.remove_mappings", "label": "Remove Mappings"},
        {"code": "entity.category.active_inactive", "label": "Active/Inactive"},
    ],
    "entity_competition": [
        {"code": "entity.competition.view", "label": "View"},
        {"code": "entity.competition.create", "label": "Create"},
        {"code": "entity.competition.edit", "label": "Edit"},
        {"code": "entity.competition.remove_mappings", "label": "Remove Mappings"},
        {"code": "entity.competition.active_inactive", "label": "Active/Inactive"},
    ],
    "entity_team": [
        {"code": "entity.team.view", "label": "View"},
        {"code": "entity.team.create", "label": "Create"},
        {"code": "entity.team.edit", "label": "Edit"},
        {"code": "entity.team.remove_mappings", "label": "Remove Mappings"},
        {"code": "entity.team.active_inactive", "label": "Active/Inactive"},
    ],
}

# Entity page permissions: (prefix, label) or (prefix, label, actions) where actions is a tuple of
# "view"|"create"|"update"|"delete" — only list actions that exist in the backoffice for that tab.
# Omitted actions are not shown in Access Rights and are not in rbac_all_permission_codes().
RBAC_ENTITY_CRUD = {
    "entity_main": [
        ("entity.sport", "Sports", "page_actions:entity_sport"),
        ("entity.category", "Categories", "page_actions:entity_category"),
        ("entity.competition", "Competitions", "page_actions:entity_competition"),
        ("entity.team", "Teams", "page_actions:entity_team"),
        ("entity.markets", "Markets"),
        ("entity.market_type", "Market types"),
    ],
    "config_partners_brands": [
        ("config.partners", "Partners"),
        ("config.brands", "Brands"),
    ],
}

# Single source: backoffice menu and permission tree. Each node:
#   label, view (menu.view permission code), always_granted?, children?, entities?, actions?
# - view: permission code for "View" (submenu/menu visibility).
# - always_granted: if True, View is always on and not configurable (Dashboard, Notifications, Profile).
# - children: list of same structure (nested submenus).
# - entities: list of (prefix, label) for CRUD page actions, or key into RBAC_ENTITY_CRUD.
# - actions: key into RBAC_PAGE_ACTIONS for custom page actions.
# Adding a new menu item or page = add one entry here (and to RBAC_PAGE_ACTIONS / RBAC_ENTITY_CRUD if needed).
RBAC_MENU_SOURCE = [
    {"label": "Dashboard", "view": "menu.dashboard.view", "always_granted": True},
    {
        "label": "Admin",
        "view": "menu.admin.view",
        "children": [
            {
                "label": "Admin (users tab)",
                "view": "menu.admin.users.view",
                "actions": "admin_users",
            },
            {
                "label": "Roles & Permissions",
                "view": "menu.admin.roles_permissions.view",
                "actions": "admin_roles",
            },
        ],
    },
    {
        "label": "Configuration",
        "view": "menu.configuration.view",
        "children": [
            {"label": "Entities", "view": "menu.configuration.entities.view", "entities": "entity_main"},
            {"label": "Localization", "view": "menu.configuration.localization.view", "entities": [("config.localization", "Localization")]},
            {"label": "Brands", "view": "menu.configuration.brands.view", "entities": "config_partners_brands"},
            {"label": "Feeder", "view": "menu.configuration.feeders.view", "entities": [("config.feeders", "Feeder", ("view", "create", "update", "delete", "audit"))]},
            {"label": "Margin", "view": "menu.configuration.margin.view", "entities": [("config.margin", "Margin")]},
            {"label": "Risk Rules", "view": "menu.configuration.risk_rules.view", "entities": [("config.risk_rules", "Risk Rules")]},
            {"label": "Compliance", "view": "menu.configuration.compliance.view", "entities": [("config.compliance", "Compliance")]},
            {
                "label": "Sport Feed Mapping",
                "view": "menu.configuration.mapping.view",
                "entities": [("mapping", "Mapping")],
                "actions_extra": "mapping_extra",
            },
            {"label": "Customization", "view": "menu.configuration.customization.view", "entities": [("customization", "Customization")]},
        ],
    },
    {
        "label": "Betting Program",
        "view": "menu.betting_program.view",
        "children": [
            {"label": "Event Navigator", "view": "menu.betting_program.event_navigator.view", "entities": [("betting.event_navigator", "Event Navigator")]},
            {
                "label": "Feeder Events",
                "view": "menu.betting_program.feeder_events.view",
                "entities": [
                    ("betting.feeder_events", "Feeder Events"),
                    ("entity.event", "Domain events"),
                ],
            },
            {"label": "Archived Events", "view": "menu.betting_program.archived_events.view", "entities": [("betting.archived_events", "Archived Events")]},
        ],
    },
    {"label": "Risk", "view": "menu.risk.view", "entities": [("risk", "Risk")]},
    {"label": "Bets/PTLs", "view": "menu.bets_ptls.view", "entities": [("bets_ptls", "Bets/PTLs")]},
    {"label": "Alerts", "view": "menu.alerts.view", "entities": [("alerts", "Alerts")]},
    {"label": "Reports", "view": "menu.reports.view", "entities": [("reports", "Reports")]},
    {"label": "Notifications", "view": "menu.notifications.view", "always_granted": True},
    {"label": "Profile", "view": "menu.profile.view", "always_granted": True},
]


def _normalize_entity_entry(entry: tuple) -> tuple[str, str, tuple[str, ...] | str]:
    """(prefix, label), (prefix, label, crud_tuple), or (prefix, label, 'page_actions:key')."""
    if len(entry) == 2:
        return entry[0], entry[1], ("view", "create", "update", "delete")
    if len(entry) == 3:
        third = entry[2]
        if isinstance(third, str) and third.startswith("page_actions:"):
            return entry[0], entry[1], third
        return entry[0], entry[1], tuple(third)
    raise ValueError(f"Invalid entity entry: {entry!r}")


def _resolve_entities(entities) -> list[tuple[str, str, tuple[str, ...] | str]]:
    """Resolve to (prefix, label, crud tuple | page_actions:key)."""
    if not entities:
        return []
    if isinstance(entities, str):
        raw = RBAC_ENTITY_CRUD.get(entities, [])
    else:
        raw = list(entities)
    return [_normalize_entity_entry(tuple(row)) for row in raw]


def _permissions_for_entity_spec(
    prefix: str,
    ent_spec: tuple[str, ...] | str,
    actions_extra: str | None,
) -> list[dict]:
    """Permissions list for one entity row under Access Rights."""
    if isinstance(ent_spec, str) and ent_spec.startswith("page_actions:"):
        key = ent_spec.split(":", 1)[1]
        return list(RBAC_PAGE_ACTIONS.get(key, []))
    if not isinstance(ent_spec, tuple):
        raise TypeError(f"Expected tuple or page_actions key, got {type(ent_spec)}")
    mapping_actions: tuple[str, ...] = ("view", "create", "update") if actions_extra and prefix == "mapping" else ent_spec
    return _perms_for_entity_row(prefix, mapping_actions, actions_extra)


def _perms_for_entity_row(prefix: str, actions: tuple[str, ...], actions_extra: str | None) -> list[dict]:
    """Build permission dicts for one entity row; mapping adds unmap/pause/cascade."""
    if actions_extra and prefix == "mapping":
        base = _perm(prefix, *actions) if actions else []
        return base + RBAC_PAGE_ACTIONS.get(actions_extra, [])
    return _perm(prefix, *actions)


def _build_tree_node(item: dict) -> dict:
    """Build one node of RBAC_PERMISSION_TREE from RBAC_MENU_SOURCE item."""
    label = item["label"]
    view_code = item.get("view")
    always = item.get("always_granted", False)
    children_spec = item.get("children")
    entities = item.get("entities")
    actions_key = item.get("actions")
    actions_extra = item.get("actions_extra")

    # Leaf with only View (e.g. Dashboard, Risk, Notifications, Profile)
    if not children_spec and not entities and not actions_key:
        return {"label": label, "permissions": _menu_view(view_code, always)}

    # Node with sub-items (children and/or entities and/or actions)
    permissions = _menu_view(view_code, always) if view_code else []
    children_built = []

    if children_spec:
        for c in children_spec:
            children_built.append(_build_tree_node(c))

    if entities and not children_spec:
        resolved = _resolve_entities(entities)
        entity_children = []
        for prefix, ent_label, ent_spec in resolved:
            perms = _permissions_for_entity_spec(prefix, ent_spec, actions_extra)
            entity_children.append({"label": ent_label, "permissions": perms})
        return {
            "label": label,
            "permissions": _menu_view(view_code, always) if view_code else [],
            "children": entity_children,
        }
    if entities and children_spec:
        resolved = _resolve_entities(entities)
        entity_children = []
        for prefix, ent_label, ent_spec in resolved:
            perms = _permissions_for_entity_spec(prefix, ent_spec, actions_extra)
            entity_children.append({"label": ent_label, "permissions": perms})
        children_built.append({
            "label": label,
            "permissions": _menu_view(view_code, always) if view_code else [],
            "children": entity_children,
        })

    if actions_key and not entities:
        action_list = RBAC_PAGE_ACTIONS.get(actions_key, [])
        if actions_key == "admin_users":
            action_children = [{"label": "Users", "permissions": action_list}]
        else:
            action_children = [{"label": p["label"], "permissions": [p]} for p in action_list]
        return {
            "label": label,
            "permissions": _menu_view(view_code, always),
            "children": action_children,
        }

    if children_built and permissions:
        return {"label": label, "permissions": permissions, "children": children_built}
    if children_built:
        return {"label": label, "children": children_built}
    return {"label": label, "permissions": permissions}


def build_rbac_permission_tree():
    """Build RBAC_PERMISSION_TREE from RBAC_MENU_SOURCE. Do not edit the tree by hand."""
    return [_build_tree_node(item) for item in RBAC_MENU_SOURCE]


def _collect_always_granted(items: list, out: set) -> None:
    for item in items:
        if item.get("always_granted") and item.get("view"):
            out.add(item["view"])
        _collect_always_granted(item.get("children") or [], out)


RBAC_PERMISSION_TREE = build_rbac_permission_tree()
_always_set = set()
_collect_always_granted(RBAC_MENU_SOURCE, _always_set)
RBAC_ALWAYS_GRANTED_PERMISSIONS = frozenset(_always_set)


def rbac_find_tree_node_by_label(nodes: list, label: str) -> dict | None:
    for n in nodes:
        if n.get("label") == label:
            return n
        found = rbac_find_tree_node_by_label(n.get("children") or [], label)
        if found is not None:
            return found
    return None


def rbac_flatten_node_permission_codes(node: dict) -> set[str]:
    """All permission codes under a permission-tree node (recursive)."""
    out: set[str] = set()
    for p in node.get("permissions") or []:
        c = (p.get("code") or "").strip()
        if c:
            out.add(c)
    for ch in node.get("children") or []:
        out |= rbac_flatten_node_permission_codes(ch)
    return out


def rbac_superadmin_console_permission_codes() -> set[str]:
    """Admin menu subtree + always-granted menu items (bootstrap SuperAdmin Console role)."""
    admin = rbac_find_tree_node_by_label(RBAC_PERMISSION_TREE, "Admin")
    if not admin:
        return set(RBAC_ALWAYS_GRANTED_PERMISSIONS)
    return rbac_flatten_node_permission_codes(admin) | set(RBAC_ALWAYS_GRANTED_PERMISSIONS)


def rbac_all_permission_codes() -> frozenset[str]:
    """Every permission code declared in the RBAC tree (menus, entity CRUD, page actions)."""
    out: set[str] = set(RBAC_ALWAYS_GRANTED_PERMISSIONS)
    for node in RBAC_PERMISSION_TREE:
        out |= rbac_flatten_node_permission_codes(node)
    return frozenset(out)


# Dev / integration: when true, JSON APIs honor X-RBAC-Actor-User-Id for SuperAdmin bypass
# (master-role permission caps) and for changing is_superadmin. Disable in production
# unless behind a trusted gateway. Real auth should replace this.
RBAC_TRUST_ACTOR_HEADER = _env_truthy("RBAC_TRUST_ACTOR_HEADER", False)

# Dev-only: PIN + user picker at /dev/login, session cookie for “who am I” (RBAC actor, UI banner).
# Never enable on a public deployment.
GMP_DEV_LOGIN = _env_truthy("GMP_DEV_LOGIN", False)
# Seconds without a request before Admin “Online” shows No (in-process; resets on server restart).
try:
    RBAC_ONLINE_IDLE_SECONDS = max(30, int((os.environ.get("RBAC_ONLINE_IDLE_SECONDS") or "180").strip()))
except (TypeError, ValueError):
    RBAC_ONLINE_IDLE_SECONDS = 180
# Default PIN for normal users (per-user login_pin in CSV may override; SuperAdmin uses GMP_SUPERADMIN_PIN only).
GMP_DEFAULT_USER_PIN = (os.environ.get("GMP_DEFAULT_USER_PIN") or "1234").strip()
# SuperAdmin sign-in PIN — set only in your local .env; do not commit. Checked only for users with is_superadmin.
GMP_SUPERADMIN_PIN = (os.environ.get("GMP_SUPERADMIN_PIN") or "").strip()
GMP_DEV_SESSION_SECRET = (os.environ.get("GMP_DEV_SESSION_SECRET") or "").strip()

# ── Constants ──────────────────────────────────────────────────────────────
# Country code for "no country" / international scope in entity CSVs (e.g. Champions League). Not Compliance "jurisdiction".
COUNTRY_CODE_NONE = "-"
