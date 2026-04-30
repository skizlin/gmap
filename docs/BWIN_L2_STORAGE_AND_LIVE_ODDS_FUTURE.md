# Bwin L2: storage, slimming, and live odds (future build reference)

This document captures decisions and constraints discussed for **performance**, **duplicate storage**, and **live-style odds** so we can implement them when needed. It is not a commitment to build everything listed.

---

## 1. Two stores today

| Location | Role |
|----------|------|
| `backend/data/feed_data/bwin_l2.json` | Canonical **bulk prematch** store from scheduled pulls; Navigator and L2 market discovery read this first in many flows. |
| `backend/data/feed_event_details/bwin_l2/{valid_id}.json` | **Per-event snapshot**, written on map (background task). For L2, BetsAPI `/v1/bwin/event` is usually empty, so the snapshot is a **copy of the prematch row** from `feed_data`, wrapped as `{ "success": 1, "results": [ ev ], "sport_id": ... }`. |

**Implication:** For mapped L2 events that still exist in `feed_data`, the per-event file is **largely redundant** for odds: `_get_feed_odds_for_event_market` can fall back to prematch when the details file is missing or has empty `results`. If a non-empty details file exists, it is **preferred** over prematch for that read path—so stale snapshots can lag behind a fresher `feed_data` row until refreshed.

**Future options (pick when implementing):**

- Stop writing `feed_event_details/bwin_l2/*` for L2 and always resolve from `feed_data` + `valid_id`.
- Or write **only** a slim snapshot (see §4).
- Or prefer prematch whenever newer than the details file (requires comparing `updated_at` or mtimes).

Relevant code: `backend/main.py` (`_fetch_and_save_event_details`, `_get_feed_odds_for_event_market` bwin_l2 branch), `backend/feed_pull.py` (`save_event_details`, `_normalize_bwin_item`).

---

## 2. Why `bwin_l2.json` disagrees with the Feeder Events UI

The JSON file is **feed pull output**, not the enriched in-memory model.

| Field in file | Why UI differs |
|---------------|----------------|
| `mapping_status` / `domain_id` | `_normalize_bwin_item` always stores `UNMAPPED` and `domain_id: null`. **Real mappings** live in `event_mappings.csv`. On each feeder view, `_sync_feeder_events_mapping_status()` patches **`DUMMY_EVENTS`** from that CSV, so the table shows e.g. **E-102**. |
| `markets_count` | On load, `load_all_mock_data()` **recomputes** L2 `markets_count` using `_bwin_distinct_market_types_count(..., l2_dedupe_by_name=True)` and mutates objects in RAM. The **disk file is not rewritten** unless the next pull replaces that row—so the editor can still show an older number (e.g. raw row count). |
| `sport_id` vs `SportId` | **Intentional:** `sport_id` (string) is the normalized feeder row field; `SportId` is preserved from the Bwin API blob. `_event_declared_feed_sport_ids` checks both. |

---

## 3. Scaling: many mapped events + large JSON

- **Disk / parse:** Each full L2 snapshot is large (thousands of lines per event). N mapped events ⇒ N large files if we keep writing full payloads.
- **Glob / scan:** Code that scans `feed_event_details/bwin_l2/*.json` for market discovery scales with file count and size; L2 feeder market list often comes from **`feed_data`** first, but any path that glob-details must be watched.
- **1 Hz × 1000 events:** Even with smaller JSON, **poll frequency × event count** dominates (API limits, CPU, locks). File size alone is not the only bottleneck.

---

## 4. Slimming stored Bwin/L2 JSON (provider shape unchanged)

The upstream response stays the same; **we** can normalize **after** fetch, **before** `save_event_details` (and optionally when merging `feed_data`).

**Keep (required by current parsers in `main.py`):**

- Event: `Markets`, `optionMarkets`, `SportId` / `sport_id` where sport filtering applies.
- Market row: `templateId` or `templateCategory` (`id`, `name`), market `name`, row `id`, `attr`, `categoryId` as used by `_bwin_feed_market_id_matches` and `_parse_bwin_feed_markets`.
- Outcome rows (`options` / `results`): `name` / `sourceName`, **`odds`** or `price.odds`, optional **`side`**.

**Safe to drop for current extraction paths (verify with grep before shipping):** redundant `price` fields when `odds` is set (American, numerator, denominator, internal price id), `parameters`, `grouping`, `oddsKey`, `balanced`, and similar metadata not referenced by Bwin extractors in `main.py`.

**Do not** reduce to “odds only” without keeping the **market tree**—mapping and multi-line logic need market identity and `attr`.

**Implementation hook:** `backend/feed_pull.py` — `save_event_details()` or a dedicated `slim_bwin_l2_event(ev: dict) -> dict` called from `_fetch_and_save_event_details` for `bwin_l2`.

---

## 5. “Live” pattern without provider streaming

**Provider today:** HTTP snapshot (full JSON per request). No delta or push unless a **different** documented API exists.

**App-side pattern (provider-independent):**

1. Poll at an allowed interval (respect ToS / rate limits).
2. Parse once; update **in-memory** or **Redis** keyed by `valid_id` (prefer a **slim** structure).
3. Serve UI / internal APIs from that cache.
4. Persist to disk **only when needed** (throttled, on map, on shutdown)—not every tick.

**“Deltas”** = **you** diff consecutive snapshots for logging or UI; the wire format does not become incremental unless the vendor offers that.

---

## 6. Checklist when we implement

- [ ] Decide: skip L2 `feed_event_details` vs slim vs full; align read paths so odds never go stale.
- [ ] If slimming: unit-test against real L2 samples; grep `main.py` for any new field usage.
- [ ] If live cache: define TTL, max events, backoff on errors, and whether IMLog / other feeds share the same cache layer.
- [ ] Document BetsAPI rate limits and chosen poll interval in runbooks / `.env.example`.

---

## 7. Related project docs

- `docs/MARKET_FEED_INTEGRATION_STRATEGY.md`, `docs/FEED_INTEGRATION_PLAN.md` — broader feed strategy.
- `docs/BETSAPI_VS_JSON_EXAMPLES_ANALYSIS.md` — BetsAPI vs stored shapes.

---

*Last aligned with codebase discussion (March 2026). Update this file when behavior changes.*
