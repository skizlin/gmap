"""
Canonical domain entity id prefixes (CSV + API + UI).

- S sports, G categories, C competitions, P teams/players, M market types, E domain events.
- Feeds, brands, partners, RBAC, market reference rows (templates/groups/period/score) keep their own id schemes.
"""
from __future__ import annotations

import re
from typing import Any

ENTITY_PREFIX: dict[str, str] = {
    "sports": "S",
    "categories": "G",
    "competitions": "C",
    "teams": "P",
    "markets": "M",
}
EVENT_PREFIX = "E"

_RE_ENTITY = {k: re.compile(rf"^{re.escape(v)}-(\d+)$") for k, v in ENTITY_PREFIX.items()}
_RE_EVENT = re.compile(rf"^{re.escape(EVENT_PREFIX)}-(\d+)$")


def format_prefixed(prefix: str, n: int) -> str:
    return f"{prefix}-{n}"


def is_prefixed_entity(domain_id: Any, entity_type: str) -> bool:
    if entity_type not in ENTITY_PREFIX:
        return False
    s = str(domain_id or "").strip()
    return bool(_RE_ENTITY[entity_type].match(s))


def is_prefixed_event(event_id: Any) -> bool:
    return bool(_RE_EVENT.match(str(event_id or "").strip()))


def max_suffix_for_prefix(values: list[Any], prefix: str) -> int:
    pfx = prefix + "-"
    best = 0
    for v in values:
        s = str(v or "").strip()
        if s.startswith(pfx):
            rest = s[len(pfx) :]
            if rest.isdigit():
                best = max(best, int(rest))
    return best


def next_entity_domain_id(entity_type: str, bucket: list[dict]) -> str:
    prefix = ENTITY_PREFIX[entity_type]
    n = max_suffix_for_prefix([e.get("domain_id") for e in bucket], prefix) + 1
    return format_prefixed(prefix, n)


def next_event_domain_id(events: list[dict]) -> str:
    n = max_suffix_for_prefix([e.get("id") for e in events], EVENT_PREFIX) + 1
    return format_prefixed(EVENT_PREFIX, n)


def fid_str(x: Any) -> str:
    """Normalize a domain entity/event id for comparisons (string strip)."""
    if x is None:
        return ""
    if isinstance(x, int):
        return str(x)
    return str(x).strip()


def entity_ids_equal(a: Any, b: Any) -> bool:
    return fid_str(a) == fid_str(b) and fid_str(a) != ""


def nullable_fk_equal(a: Any, b: Any) -> bool:
    """True when both FK cells are empty or the same non-empty id (for optional category_id, etc.)."""
    return fid_str(a) == fid_str(b)
