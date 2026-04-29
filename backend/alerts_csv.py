"""CSV-backed alert types and alert rows (prototype). See docs/UNMAPPED_ENTITY_ALERTS_IMPLEMENTATION_PLAN.md."""
from __future__ import annotations

import csv
import uuid
from datetime import datetime, timezone
from threading import Lock

from backend import config

_LOCK = Lock()
_TYPES_PATH = config.ALERT_TYPES_PATH
_ALERTS_PATH = config.ALERTS_PATH
_FIELDS_TYPES = list(config.ALERT_TYPES_FIELDS)
_FIELDS_ALERTS = list(config.ALERTS_FIELDS)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _seed_alert_types() -> list[dict[str, str]]:
    """Default catalog rows (merged on startup if codes are missing)."""
    empty_policy = "{}"
    return [
        {"code": "UEVT", "name": "Unmapped feed event", "abbrev": "Evt", "active": "1", "severity_policy_json": empty_policy},
        {"code": "UCMP", "name": "Unmapped competition", "abbrev": "Cmp", "active": "1", "severity_policy_json": empty_policy},
        {"code": "UMKT", "name": "Unmapped market", "abbrev": "Mkt", "active": "1", "severity_policy_json": empty_policy},
        {"code": "UTM", "name": "Unmapped team", "abbrev": "Tm", "active": "1", "severity_policy_json": empty_policy},
        {"code": "UPLR", "name": "Unmapped player", "abbrev": "Plr", "active": "1", "severity_policy_json": empty_policy},
    ]


def ensure_initialized() -> None:
    """Create CSVs with headers; seed alert_types if new or empty."""
    _TYPES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK:
        if not _ALERTS_PATH.exists():
            with open(_ALERTS_PATH, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=_FIELDS_ALERTS)
                w.writeheader()
        if not _TYPES_PATH.exists():
            rows = _seed_alert_types()
            with open(_TYPES_PATH, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=_FIELDS_TYPES)
                w.writeheader()
                for r in rows:
                    w.writerow({k: (r.get(k) or "") for k in _FIELDS_TYPES})
            return
        existing = load_types_unlocked()
        codes = {(r.get("code") or "").strip() for r in existing}
        seed = _seed_alert_types()
        missing = [r for r in seed if (r.get("code") or "").strip() not in codes]
        if not existing or missing:
            merged = { (r.get("code") or "").strip(): {k: (r.get(k) or "") for k in _FIELDS_TYPES} for r in existing }
            for r in seed:
                c = (r.get("code") or "").strip()
                if c and c not in merged:
                    merged[c] = {k: (r.get(k) or "") for k in _FIELDS_TYPES}
            out = [merged[k] for k in sorted(merged)]
            with open(_TYPES_PATH, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=_FIELDS_TYPES)
                w.writeheader()
                for row in out:
                    w.writerow(row)


def load_types_unlocked() -> list[dict[str, str]]:
    if not _TYPES_PATH.exists():
        return []
    out: list[dict[str, str]] = []
    with open(_TYPES_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out.append({k: (row.get(k) or "").strip() for k in _FIELDS_TYPES})
    return out


def load_types() -> list[dict[str, str]]:
    with _LOCK:
        return load_types_unlocked()


def load_alerts_unlocked() -> list[dict[str, str]]:
    if not _ALERTS_PATH.exists():
        return []
    out: list[dict[str, str]] = []
    with open(_ALERTS_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out.append({k: (row.get(k) or "").strip() for k in _FIELDS_ALERTS})
    return out


def load_alerts() -> list[dict[str, str]]:
    with _LOCK:
        return load_alerts_unlocked()


def _save_alerts_unlocked(rows: list[dict[str, str]]) -> None:
    _ALERTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_ALERTS_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=_FIELDS_ALERTS)
        w.writeheader()
        for r in rows:
            w.writerow({k: (r.get(k) or "") for k in _FIELDS_ALERTS})


def count_open_unlocked() -> int:
    """Open = status NEW (trader still owes action)."""
    n = 0
    for r in load_alerts_unlocked():
        if (r.get("status") or "").upper() == "NEW":
            n += 1
    return n


def count_open() -> int:
    with _LOCK:
        return count_open_unlocked()


def list_alerts_filtered(
    *,
    status: str | None = None,
    alert_type_code: str | None = None,
    feed_code: str | None = None,
    page: int = 1,
    per_page: int = 50,
) -> tuple[list[dict[str, str]], int]:
    st = (status or "").strip().upper() or None
    tc = (alert_type_code or "").strip().upper() or None
    fc = (feed_code or "").strip().lower() or None
    page = max(1, page)
    per_page = max(1, min(per_page, 200))
    with _LOCK:
        rows = load_alerts_unlocked()
    filtered: list[dict[str, str]] = []
    for r in rows:
        if st and (r.get("status") or "").upper() != st:
            continue
        if tc and (r.get("alert_type_code") or "").strip().upper() != tc:
            continue
        if fc and (r.get("feed_code") or "").strip().lower() != fc:
            continue
        filtered.append(r)
    filtered.sort(key=lambda x: (x.get("created_at") or ""), reverse=True)
    total = len(filtered)
    start = (page - 1) * per_page
    return filtered[start : start + per_page], total


def append_alert(
    *,
    alert_type_code: str,
    message: str,
    severity: int = 0,
    status: str = "NEW",
    feed_code: str = "",
    entity_kind: str = "",
    valid_id: str = "",
    domain_id: str = "",
    meta_json: str = "",
) -> str:
    aid = str(uuid.uuid4())
    now = _utc_now()
    row = {
        "id": aid,
        "alert_type_code": (alert_type_code or "").strip(),
        "status": (status or "NEW").strip().upper(),
        "severity": str(int(severity)),
        "message": (message or "").strip(),
        "feed_code": (feed_code or "").strip(),
        "entity_kind": (entity_kind or "").strip(),
        "valid_id": (valid_id or "").strip(),
        "domain_id": (domain_id or "").strip(),
        "created_at": now,
        "updated_at": now,
        "acked_at": "",
        "resolved_at": "",
        "meta_json": (meta_json or "").strip(),
    }
    with _LOCK:
        rows = load_alerts_unlocked()
        rows.append(row)
        _save_alerts_unlocked(rows)
    return aid


def transition_alert(alert_id: str, action: str) -> bool:
    """action: ack | hide | resolve. Returns True if row was found and updated."""
    aid = (alert_id or "").strip()
    act = (action or "").strip().lower()
    if act not in ("ack", "hide", "resolve"):
        return False
    now = _utc_now()
    with _LOCK:
        rows = load_alerts_unlocked()
        found = False
        for r in rows:
            if (r.get("id") or "").strip() != aid:
                continue
            found = True
            cur = (r.get("status") or "").upper()
            if act == "ack":
                if cur == "NEW":
                    r["status"] = "ACKED"
                    r["acked_at"] = now
            elif act == "hide":
                r["status"] = "HIDDEN"
            elif act == "resolve":
                r["status"] = "RESOLVED"
                r["resolved_at"] = now
            r["updated_at"] = now
            break
        if not found:
            return False
        _save_alerts_unlocked(rows)
    return True
