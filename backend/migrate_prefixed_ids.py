"""
One-time migration: domain entity ids become S-/G-/C-/P-/M-, domain events E- (sequential).
Safe to run once per environment; uses marker file .domain_ids_prefixed_v1 under DATA_DIR.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any

from backend import config
from backend.domain_ids import ENTITY_PREFIX, EVENT_PREFIX, format_prefixed


def _row_legacy_entity(cell: str, prefix: str) -> bool:
    s = (cell or "").strip()
    if not s:
        return False
    return not re.match(rf"^{re.escape(prefix)}-\d+$", s)


def _row_legacy_event(cell: str) -> bool:
    s = (cell or "").strip()
    if not s:
        return True
    return not re.match(rf"^{re.escape(EVENT_PREFIX)}-\d+$", s)


def _sort_key_domain_row(r: dict) -> int:
    s = str(r.get("domain_id") or "").strip()
    if s.isdigit():
        return int(s)
    if "-" in s:
        tail = s.rsplit("-", 1)[-1]
        if tail.isdigit():
            return int(tail)
    return 10**12


def migrate_prefixed_domain_ids_if_needed() -> None:
    data_dir = config.DATA_DIR
    marker = data_dir / ".domain_ids_prefixed_v1"
    if marker.exists():
        return

    et_order = ["sports", "categories", "competitions", "teams", "markets"]
    raw: dict[str, list[dict[str, Any]]] = {}
    need_entity = False
    for et in et_order:
        p = data_dir / f"{et}.csv"
        rows: list[dict[str, Any]] = []
        if p.exists():
            with open(p, newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
        raw[et] = rows
        pref = ENTITY_PREFIX[et]
        for r in rows:
            if _row_legacy_entity(r.get("domain_id", ""), pref):
                need_entity = True
                break

    ev_path = config.DOMAIN_EVENTS_PATH
    ev_rows: list[dict[str, Any]] = []
    if ev_path.exists():
        with open(ev_path, newline="", encoding="utf-8") as f:
            ev_rows = list(csv.DictReader(f))
    need_event = any(_row_legacy_event(r.get("domain_id", "")) for r in ev_rows)

    if not need_entity and not need_event:
        marker.touch()
        return

    maps: dict[str, dict[str, str]] = {et: {} for et in et_order}

    if need_entity:
        spr = sorted(
            [r for r in raw["sports"] if (r.get("domain_id") or "").strip()],
            key=_sort_key_domain_row,
        )
        for i, r in enumerate(spr, start=1):
            old = str(r["domain_id"]).strip()
            maps["sports"][old] = format_prefixed(ENTITY_PREFIX["sports"], i)

        catr = sorted(
            [r for r in raw["categories"] if (r.get("domain_id") or "").strip()],
            key=_sort_key_domain_row,
        )
        for i, r in enumerate(catr, start=1):
            old = str(r["domain_id"]).strip()
            maps["categories"][old] = format_prefixed(ENTITY_PREFIX["categories"], i)

        compr = sorted(
            [r for r in raw["competitions"] if (r.get("domain_id") or "").strip()],
            key=_sort_key_domain_row,
        )
        for i, r in enumerate(compr, start=1):
            old = str(r["domain_id"]).strip()
            maps["competitions"][old] = format_prefixed(ENTITY_PREFIX["competitions"], i)

        teamr = sorted(
            [r for r in raw["teams"] if (r.get("domain_id") or "").strip()],
            key=_sort_key_domain_row,
        )
        for i, r in enumerate(teamr, start=1):
            old = str(r["domain_id"]).strip()
            maps["teams"][old] = format_prefixed(ENTITY_PREFIX["teams"], i)

        mkr = sorted(
            [r for r in raw["markets"] if (r.get("domain_id") or "").strip()],
            key=_sort_key_domain_row,
        )
        for i, r in enumerate(mkr, start=1):
            old = str(r["domain_id"]).strip()
            maps["markets"][old] = format_prefixed(ENTITY_PREFIX["markets"], i)
    else:
        for et in et_order:
            for r in raw[et]:
                old = str(r.get("domain_id") or "").strip()
                if old:
                    maps[et][old] = old

    event_map: dict[str, str] = {}
    if need_event:
        for i, r in enumerate(ev_rows, start=1):
            old = str(r.get("domain_id") or "").strip()
            if old:
                event_map[old] = format_prefixed(EVENT_PREFIX, i)
    else:
        for r in ev_rows:
            old = str(r.get("domain_id") or "").strip()
            if old:
                event_map[old] = old

    entity_fields = config.ENTITY_FIELDS

    def _map_fk(val: Any, et: str) -> str:
        s = str(val or "").strip()
        if not s:
            return ""
        return maps.get(et, {}).get(s, s)

    if need_entity:
        for et in et_order:
            p = data_dir / f"{et}.csv"
            rows = sorted(
                [r for r in raw[et] if (r.get("domain_id") or "").strip()],
                key=_sort_key_domain_row,
            )
            fields = entity_fields[et]
            for r in rows:
                oid = str(r["domain_id"]).strip()
                r["domain_id"] = maps[et][oid]
                if et == "categories":
                    r["sport_id"] = _map_fk(r.get("sport_id"), "sports")
                elif et == "competitions":
                    r["sport_id"] = _map_fk(r.get("sport_id"), "sports")
                    r["category_id"] = _map_fk(r.get("category_id"), "categories")
                elif et == "teams":
                    r["sport_id"] = _map_fk(r.get("sport_id"), "sports")
                elif et == "markets":
                    r["sport_id"] = _map_fk(r.get("sport_id"), "sports")
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
                w.writeheader()
                w.writerows(rows)

    ef_path = config.ENTITY_FEED_MAPPINGS_PATH
    if ef_path.exists():
        with open(ef_path, newline="", encoding="utf-8") as f:
            ef_rows = list(csv.DictReader(f))
        fields_ef = list(config.ENTITY_FEED_MAPPING_FIELDS)
        for r in ef_rows:
            et = (r.get("entity_type") or "").strip().lower()
            oid = str(r.get("domain_id") or "").strip()
            if et in maps and oid:
                r["domain_id"] = maps[et].get(oid, oid)
        with open(ef_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields_ef, extrasaction="ignore")
            w.writeheader()
            w.writerows(ef_rows)

    sf_path = config.SPORT_FEED_MAPPINGS_PATH
    if sf_path.exists():
        with open(sf_path, newline="", encoding="utf-8") as f:
            sf_rows = list(csv.DictReader(f))
        fields_sf = list(config.ENTITY_FEED_MAPPING_FIELDS)
        for r in sf_rows:
            oid = str(r.get("domain_id") or "").strip()
            if oid:
                r["domain_id"] = maps["sports"].get(oid, oid)
        with open(sf_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields_sf, extrasaction="ignore")
            w.writeheader()
            w.writerows(sf_rows)

    if ev_rows and (need_event or need_entity):
        new_ev = []
        for r in ev_rows:
            nr = dict(r)
            old = str(nr.get("domain_id") or "").strip()
            if old and old in event_map:
                nr["domain_id"] = event_map[old]
            for col in ("home_id", "away_id"):
                v = str(nr.get(col) or "").strip()
                if v:
                    nr[col] = maps["teams"].get(v, v)
            new_ev.append(nr)
        ev_path.parent.mkdir(parents=True, exist_ok=True)
        with open(ev_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=config.DOMAIN_EVENT_FIELDS)
            w.writeheader()
            w.writerows(new_ev)

    em_path = config.EVENT_MAPPINGS_PATH
    if em_path.exists():
        with open(em_path, newline="", encoding="utf-8") as f:
            em_rows = list(csv.DictReader(f))
        for r in em_rows:
            oid = str(r.get("domain_event_id") or "").strip()
            if oid in event_map:
                r["domain_event_id"] = event_map[oid]
        with open(em_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=config.MAPPING_FIELDS)
            w.writeheader()
            w.writerows(em_rows)

    en_path = getattr(config, "EVENT_NAVIGATOR_NOTES_PATH", None)
    if en_path and en_path.exists():
        with open(en_path, newline="", encoding="utf-8") as f:
            rd = csv.DictReader(f)
            fn = list(rd.fieldnames or [])
            en_rows = list(rd)
        for r in en_rows:
            oid = str(r.get("domain_event_id") or "").strip()
            if oid in event_map:
                r["domain_event_id"] = event_map[oid]
        with open(en_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fn, extrasaction="ignore")
            w.writeheader()
            w.writerows(en_rows)

    mtc_path = config.MARGIN_TEMPLATE_COMPETITIONS_PATH
    if mtc_path.exists():
        with open(mtc_path, newline="", encoding="utf-8") as f:
            mtc_rows = list(csv.DictReader(f))
        for r in mtc_rows:
            oid = str(r.get("competition_id") or "").strip()
            if oid:
                r["competition_id"] = maps["competitions"].get(oid, oid)
        with open(mtc_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["template_id", "competition_id"])
            w.writeheader()
            w.writerows(mtc_rows)

    mtm_path = config.MARKET_TYPE_MAPPINGS_PATH
    if mtm_path.exists():
        with open(mtm_path, newline="", encoding="utf-8") as f:
            rdr = csv.DictReader(f)
            fn = list(rdr.fieldnames or [])
            mtm_rows = list(rdr)
        for r in mtm_rows:
            oid = str(r.get("domain_market_id") or "").strip()
            if oid:
                r["domain_market_id"] = maps["markets"].get(oid, oid)
        with open(mtm_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fn, extrasaction="ignore")
            w.writeheader()
            w.writerows(mtm_rows)

    mt_path = config.MARGIN_TEMPLATES_PATH
    if mt_path.exists():
        with open(mt_path, newline="", encoding="utf-8") as f:
            rdr = csv.DictReader(f)
            fn = list(rdr.fieldnames or [])
            mt_rows = list(rdr)
        for r in mt_rows:
            sid = str(r.get("sport_id") or "").strip()
            if sid and sid.isdigit():
                r["sport_id"] = maps["sports"].get(sid, sid)
        with open(mt_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fn, extrasaction="ignore")
            w.writeheader()
            w.writerows(mt_rows)

    fc_path = config.FEEDER_CONFIG_PATH
    if fc_path.exists():
        with open(fc_path, newline="", encoding="utf-8") as f:
            rdr = csv.DictReader(f)
            fn = list(rdr.fieldnames or [])
            fc_rows = list(rdr)
        for r in fc_rows:
            for col, emap in (
                ("sport_id", "sports"),
                ("category_id", "categories"),
                ("competition_id", "competitions"),
                ("league_id", "competitions"),
            ):
                v = str(r.get(col) or "").strip()
                if v and v.isdigit():
                    r[col] = maps[emap].get(v, v)
        with open(fc_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fn, extrasaction="ignore")
            w.writeheader()
            w.writerows(fc_rows)

    fi_path = getattr(config, "FEEDER_INCIDENTS_PATH", None)
    if fi_path and fi_path.exists():
        with open(fi_path, newline="", encoding="utf-8") as f:
            rdr = csv.DictReader(f)
            fn = list(rdr.fieldnames or [])
            fi_rows = list(rdr)
        for r in fi_rows:
            v = str(r.get("sport_id") or "").strip()
            if v and v.isdigit():
                r["sport_id"] = maps["sports"].get(v, v)
        with open(fi_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fn, extrasaction="ignore")
            w.writeheader()
            w.writerows(fi_rows)

    marker.touch()
