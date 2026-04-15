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


def mapping_feed_id_key(val: Any) -> str:
    """
    Canonical key for entity_feed_mappings feed_id (categories, competitions, teams, …).
    Strips; normalizes plain numeric strings (123 / 123.0 → "123"); for PREFIX:rest normalizes
    the rest when numeric (e.g. COMP:10070454.0 → COMP:10070454). Non-numeric strings are kept as-is.
    """
    if val is None:
        return ""
    s = str(val).strip()
    if not s:
        return ""
    if ":" in s:
        prefix, _, rest = s.partition(":")
        prefix = prefix.strip()
        rest = rest.strip()
        if not prefix:
            return s
        if not rest:
            return f"{prefix}:"
        try:
            rest_norm = str(int(float(rest)))
        except (ValueError, TypeError):
            rest_norm = rest
        return f"{prefix}:{rest_norm}"
    try:
        return str(int(float(s)))
    except (ValueError, TypeError):
        return s


def mapping_related_feed_id_keys(val: Any) -> list[str]:
    """
    Keys to try when matching a feed row value to ENTITY_FEED_MAPPINGS.feed_id for categories/competitions.

    Bet365 often sends league scope as ``COMP:10041282`` while the Entities UI may store the same id as
    ``10041282`` (or the reverse). ``mapping_feed_id_key`` keeps those distinct; this helper lists both
    so resolution matches either representation.
    """
    s = str(val).strip() if val is not None else ""
    if not s:
        return []
    keys: list[str] = []

    def _add(k: str) -> None:
        k = (k or "").strip()
        if k and k not in keys:
            keys.append(k)

    _add(mapping_feed_id_key(s))
    if ":" in s:
        prefix, _, rest = s.partition(":")
        if prefix.strip().upper() == "COMP" and rest.strip():
            try:
                _add(mapping_feed_id_key(str(int(float(rest.strip())))))
            except (ValueError, TypeError):
                pass
    else:
        try:
            num = str(int(float(s)))
            if mapping_feed_id_key(s) == num:
                _add(mapping_feed_id_key(f"COMP:{num}"))
        except (ValueError, TypeError):
            pass
    return keys


def nullable_fk_equal(a: Any, b: Any) -> bool:
    """True when both FK cells are empty or the same non-empty id (for optional category_id, etc.)."""
    return fid_str(a) == fid_str(b)
