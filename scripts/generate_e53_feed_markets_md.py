#!/usr/bin/env python3
"""Generate docs/E-53_feed_markets_odds_dump.md from feed_event_details for event E-53."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "backend" / "data"
DETAILS = DATA / "feed_event_details"
OUT = ROOT / "docs" / "E-53_feed_markets_odds_dump.md"

MAPPINGS = [
    ("bet365", "192227605"),
    ("1xbet", "710505432"),
    ("bwin", "19321761"),
]


def load_json(feed: str, fid: str) -> dict | list | None:
    p = DETAILS / feed / f"{fid}.json"
    if not p.exists():
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def md_escape(s: object) -> str:
    t = str(s) if s is not None else ""
    return t.replace("|", "\\|").replace("\n", " ")


def section_bet365(data: dict) -> list[str]:
    out: list[str] = []
    results = data.get("results") or []
    if not results:
        return ["_No results._\n"]
    for ev_idx, event in enumerate(results):
        out.append(f"### Bet365 — result index {ev_idx}\n")
        fi = event.get("FI") or event.get("event_id")
        out.append(f"- **FI / event:** `{fi}`\n")

        def walk_sp(sp: dict, source: str) -> None:
            if not sp:
                return
            for key, block in sp.items():
                if not isinstance(block, dict):
                    continue
                bid = block.get("id", "")
                bname = block.get("name") or key
                odds = block.get("odds") or []
                out.append(f"\n#### `{source}` / `{key}` → **id {bid}** — {md_escape(bname)}\n\n")
                if not odds:
                    out.append("_No odds rows._\n")
                    continue
                out.append("| # | name | header | handicap | odds |\n")
                out.append("|---:|------|--------|----------|------|\n")
                for i, o in enumerate(odds):
                    if not isinstance(o, dict):
                        continue
                    out.append(
                        f"| {i + 1} | {md_escape(o.get('name', ''))} | {md_escape(o.get('header', ''))} | "
                        f"{md_escape(o.get('handicap', ''))} | {md_escape(o.get('odds', ''))} |\n"
                    )

        main = (event.get("main") or {})
        walk_sp(main.get("sp") or {}, "main.sp")
        others = event.get("others") or []
        for j, other in enumerate(others):
            if not isinstance(other, dict):
                continue
            walk_sp(other.get("sp") or {}, f"others[{j}].sp")
    return out


def section_bwin(data: dict) -> list[str]:
    out: list[str] = []
    results = data.get("results") or []
    if not results:
        return ["_No results._\n"]
    for ev_idx, event in enumerate(results):
        out.append(f"### Bwin — result index {ev_idx}\n")
        out.append(
            f"- **Id:** `{event.get('Id')}` · **Home:** {md_escape(event.get('HomeTeam'))} · "
            f"**Away:** {md_escape(event.get('AwayTeam'))}\n"
        )
        markets = (event.get("Markets") or []) + (event.get("optionMarkets") or [])
        out.append(f"- **Market blocks:** {len(markets)}\n")
        for mi, m in enumerate(markets):
            if not isinstance(m, dict):
                continue
            tid = m.get("templateId")
            tc = m.get("templateCategory") or {}
            cid = tc.get("id") if isinstance(tc, dict) else None
            cat_key = tid if tid is not None else cid
            nm = (m.get("name") or {})
            name_val = nm.get("value") if isinstance(nm, dict) else str(nm)
            attr = m.get("attr")
            out.append(
                f"\n#### Market {mi + 1} — **templateId/categoryId:** `{cat_key}` — {md_escape(name_val)}\n\n"
            )
            if attr is not None and str(attr).strip():
                out.append(f"- **attr (line):** `{md_escape(attr)}`\n")
            rlist = m.get("results") or []
            if not rlist:
                out.append("_No results._\n")
                continue
            out.append("| # | outcome name | odds | attr |\n")
            out.append("|---:|--------------|------|------|\n")
            for ri, r in enumerate(rlist):
                if not isinstance(r, dict):
                    continue
                oname = (r.get("name") or {}).get("value", "")
                sn = (r.get("sourceName") or {}).get("value", "")
                label = oname or sn or "—"
                odds = r.get("odds")
                ra = r.get("attr")
                out.append(
                    f"| {ri + 1} | {md_escape(label)} | {md_escape(odds)} | {md_escape(ra if ra is not None else '')} |\n"
                )
    return out


def section_1xbet(data: dict) -> list[str]:
    out: list[str] = []
    results = data.get("results") or []
    if not results:
        return ["_No results._\n"]
    for ev_idx, event in enumerate(results):
        out.append(f"### 1xbet — result index {ev_idx}\n")
        eid = event.get("id")
        out.append(f"- **Event id:** `{eid}`\n")
        val = event.get("Value") or event.get("value") or {}
        ge = val.get("GE")
        if not isinstance(ge, list):
            out.append("_No Value.GE._\n")
            continue
        out.append(f"- **GE groups:** {len(ge)}\n")
        for gi, grp in enumerate(ge):
            if not isinstance(grp, dict):
                continue
            g = grp.get("G")
            e_rows = grp.get("E") or []
            out.append(f"\n#### GE group {gi + 1} — **G = {g}** (feed market id)\n\n")
            if not e_rows:
                out.append("_Empty E._\n")
                continue
            for ri, row in enumerate(e_rows):
                if not isinstance(row, list):
                    continue
                out.append(f"##### Row {ri + 1} (within E)\n\n")
                out.append("| cell | T | P | C | CV | CE | G |\n")
                out.append("|---:|---:|---:|---:|---|:-:|:-:|\n")
                for ci, cell in enumerate(row):
                    if not isinstance(cell, dict):
                        continue
                    out.append(
                        f"| {ci + 1} | {md_escape(cell.get('T', ''))} | {md_escape(cell.get('P', ''))} | "
                        f"{md_escape(cell.get('C', ''))} | {md_escape(cell.get('CV', ''))} | "
                        f"{md_escape(cell.get('CE', ''))} | {md_escape(cell.get('G', ''))} |\n"
                    )
                out.append("\n")
    return out


def main() -> int:
    lines: list[str] = []
    lines.append("# E-53 — Feed markets, lines & odds dump\n\n")
    lines.append(
        "Generated for domain event **E-53** (Suzano Volei vs Minas, Brazil SuperLiga) from cached files in "
        "`backend/data/feed_event_details/`. This is what the app reads for feed odds (no live API call).\n\n"
    )
    lines.append("| Feed | feed_valid_id | Cached JSON |\n")
    lines.append("|------|---------------|-------------|\n")
    for feed, fid in MAPPINGS:
        rel = f"`backend/data/feed_event_details/{feed}/{fid}.json`"
        lines.append(f"| {feed} | `{fid}` | {rel} |\n")
    lines.append("\n---\n\n")

    for feed, fid in MAPPINGS:
        lines.append(f"## {feed.upper()} (`{fid}.json`)\n\n")
        raw = load_json(feed, fid)
        if raw is None:
            lines.append(f"_File missing: `{DETAILS / feed / f'{fid}.json'}`_\n\n")
            continue
        if feed == "bet365":
            lines.extend(section_bet365(raw) if isinstance(raw, dict) else ["_Invalid JSON shape._\n"])
        elif feed == "bwin":
            lines.extend(section_bwin(raw) if isinstance(raw, dict) else ["_Invalid JSON shape._\n"])
        elif feed == "1xbet":
            lines.extend(section_1xbet(raw) if isinstance(raw, dict) else ["_Invalid JSON shape._\n"])
        lines.append("\n---\n\n")

    lines.append(
        "## Notes for mapping logic\n\n"
        "- **Bet365:** `main.sp.*` blocks have `id` (e.g. 910000, 910216); odds rows use `name` (Winner / Handicap / Total), "
        "`header` (1/2), `handicap` (line or `O 184.5`), `odds`.\n"
        "- **Bwin:** Each row is often one `Markets[]` entry per line (`templateId` + `attr`); outcomes in `results`.\n"
        "- **1xbet:** `Value.GE[]` — **`G`** is the market id; **`E`** is rows of outcome cells; **`P`** = line, **`T`** = outcome type, **`C`** = decimal odds.\n"
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("".join(lines), encoding="utf-8")
    print(f"Wrote {OUT}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
