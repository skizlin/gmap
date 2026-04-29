# Unmapped Entity Alerts — Implementation Plan (Prototype)

Source: Product brief `docs/SBP-[GM] Unmapped Entity Alerts-290426-120827.pdf`  
Goal: Ship a **working slice** in the Global Mapper prototype, then extend. Dashboard stays a **summary**; **Alerts** owns the **queue, lifecycle, and configuration**.

---

## Scaffold status (CSV prototype)

**Done in repo**

- **Persistence**: Two per-environment CSV files next to platform notes (not `platform_notifications.csv` — different lifecycle: confirm-read vs ack/resolve/hide):
  - `backend/data/notes/alert_types.csv` — columns: `code`, `name`, `abbrev`, `active`, `severity_policy_json` (see `config.ALERT_TYPES_FIELDS`).
  - `backend/data/notes/alerts.csv` — columns: `id`, `alert_type_code`, `status`, `severity`, `message`, `feed_code`, `entity_kind`, `valid_id`, `domain_id`, `created_at`, `updated_at`, `acked_at`, `resolved_at`, `meta_json` (see `config.ALERTS_FIELDS`).
- **Module**: `backend/alerts_csv.py` — `ensure_initialized()` (startup), `load_types` / `list_alerts_filtered` / `count_open` (open = `status == NEW`), `append_alert`, `transition_alert` (`ack` | `hide` | `resolve`).
- **HTTP**: `GET /alerts` (history UI), `GET /api/alerts`, `GET /api/alerts/open-count`, `POST /api/alerts/{id}/ack|hide|resolve`.
- **RBAC**: Path gate + API rules use `menu.alerts.view`.
- **Nav**: Desktop + mobile **Alerts** → `/alerts` (`layout.html`).
- **Deploy hygiene**: `.gitignore` and `scripts/server-protect-data.sh` list both CSV paths (same commit as the rule requires).
- **Deep link**: Feeder Events honours `mapping_status_filter` on first load + hidden field + toggle sync (`feeder_events_view` + `feeder_events.html`).

**Still to build**

- Emitters (start with **UEVT**), severity helper, auto-resolve on map, dashboard open-count + link, types admin UI, `EXPIRED`, optional bell badge.

---

## Principles for the prototype

1. **Persistence**: **CSV only** for this prototype — the two files above; no SQLite. Full rewrite on small updates is acceptable at prototype scale; module uses a lock around read/modify/write.
2. **Reuse**: Hook **emitters** and **auto-resolve** off code paths that already change mapping state (feeder pull, auto-map, manual map/create from Feeder Events / entities). Do not duplicate business rules in the UI only.
3. **Nav**: **Alerts** remains gated by `menu.alerts.view`.
4. **Dashboard**: Add **links and optional aggregates** after emitters populate the queue — optional polish, not blocking the CSV slice.

---

## Target UX (prototype scope)


| Area            | Prototype MVP                                                                                      | Later                                            |
| --------------- | -------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| **Alert types** | Seed fixed rows (UCMP, UEVT, UMKT, UTM, UPLR); optional `active` flag in CSV                       | Full “edit severity policy” UI from PDF          |
| **Severity**    | Store integer; compute with **simple time-to-start** rules per type (subset of PDF ladders)        | Full ladders + colours TBD                       |
| **History**     | Paginated table: time, type, message, severity, status, feed, deep link                            | Advanced filters (severity up/down, change type) |
| **Statuses**    | `NEW`, `ACKED`, `HIDDEN`, `RESOLVED`, `EXPIRED`                                                    | Match PDF transitions exactly                    |
| **Actions**     | API + buttons: Ack, Hide, Resolve                                                                  | Bulk actions                                     |
| **Auto**        | On successful map/create → set `RESOLVED`; on mapping removed → reopen `NEW` if row still unmapped | Same, extended to all entity kinds               |
| **Bell**        | Optional: badge count = open alerts (`NEW` only for current open-count)                            | Merge UX with existing notifications panel       |


---

## Data model (CSV columns)

`**alert_types`** (seeded at startup if missing or if known codes are absent)

- `code`, `name`, `abbrev`, `active`, `severity_policy_json`

`**alerts`**

- `id` (UUID string)
- `alert_type_code`, `status`, `severity`, `message`
- `feed_code`, `entity_kind`, `valid_id`, `domain_id`
- `created_at`, `updated_at`, `acked_at`, `resolved_at`, `meta_json`

**Audit / `alert_events`**

- Optional later; add when status-change history must be queryable independently of row timestamps.

---

## Backend work (ordered)

1. **Storage module** — `**backend/alerts_csv.py`** (done): init + seed types, CRUD-style helpers, list with filters (`status`, `alert_type`, `feed`, `page`, `per_page`).
2. **Severity helper** — Pure functions: `compute_severity(alert_type_code, entity_start_time_utc, now, context_dict) -> int` — implement **UEVT** first; stub others.
3. **Emitter service** — e.g. `alerts_emit.py`: `ensure_unmapped_event_alert(...)`, `refresh_or_resolve_for_feed_row(...)` — call from feeder pull / auto-map / manual map paths.
4. **HTTP API** (JSON) — list + open-count + ack/hide/resolve (**done**); extend with `from` / `to` date filters if needed.
5. **HTML** — `**GET /alerts`** history shell (**done**); optional `GET /alerts/types` for read-only type list + toggle `active`.
6. **Expire job** (prototype **on-read**): when listing, set `EXPIRED` for finished events if needed — or nightly stub.

---

## Frontend work (Jinja + fetch)

1. `**layout.html`** — Alerts → `/alerts` (done).
2. `**backend/templates/alerts/history.html`** — filters, table, paging, actions calling JSON API (done).
3. `**index.html` (dashboard)** — “Open alerts: **N**” via `GET /api/alerts/open-count`, link `/alerts?status=NEW`; per-feed unmapped → `/alerts?feed=<code>&alert_type=UEVT`.
4. **Bell (optional)** — combine or separate from notifications badge.

---

## CTA / deep links (prototype)


| Type       | Link target                                                                                             |
| ---------- | ------------------------------------------------------------------------------------------------------- |
| UEVT       | `/feeder-events?feed_provider=<feed>&mapping_status_filter=UNMAPPED` (+ optional search when supported) |
| UCMP       | Feeder Events or future competition mapping URL + query                                                 |
| UMKT       | Feeder Events + focus market / open mapper if query params exist                                        |
| UTM / UPLR | `/entities#teams` or future player tab + `?search=` or feed id param                                    |


Start with **UEVT → Feeder Events** only; stub others with generic `/feeder-events`.

**Query contract for `/alerts`**: `status`, `alert_type`, `feed`, `page`, `per_page` (matches list API).

---

## Implementation order (suggested sprints for prototype)

1. ~~**Schema + seed types + history page + nav + API + RBAC + gitignore/server-protect**~~ (CSV scaffold — done).
2. **Emitter for unmapped events only** — first data into `alerts.csv`.
3. **Auto-resolve on map** + keep **Ack / Hide / Resolve** aligned with product rules.
4. **Dashboard link + open count** — monitoring entry point.
5. **Additional types** + severity tuning.
6. **Types admin screen** + **EXPIRED** + **bell** — polish.

---

## Files touched (reference)

- `backend/main.py` — routes, RBAC API rules, path gate, startup `ensure_initialized`, emitter hooks (emitters pending).
- `backend/config.py` — `ALERT_TYPES_PATH`, `ALERTS_PATH`, field lists.
- `backend/alerts_csv.py` — CSV access layer.
- `backend/templates/layout.html` — Alerts href + active state.
- `backend/templates/alerts/history.html` — queue UI.
- `backend/templates/feeder_events/feeder_events.html` — deep-link mapping filter UX.
- `backend/templates/index.html` — dashboard bridge (pending).
- `.gitignore` / `scripts/server-protect-data.sh` — per-environment CSV protection.

---

## Out of scope for first prototype drop

- Full PTC parity with “severity change type” audit dimensions.  
- SLA reporting dashboards.  
- Duplicate-entity detection (mentioned in PDF success metrics, not in MVP templates).  
- Exact colour system until design tokens are chosen.

---

## Definition of Done (prototype MVP)

- Traders can open **Alerts**, see **real** unmapped **event** alerts (from emitters), change status with **Ack / Hide / Resolve**, and see **auto-resolve** after mapping an event in Feeder Events.  
- **Alerts** menu works end-to-end with RBAC.  
- Dashboard exposes at least **one** clear entry point to that queue (count + link).

When this MVP is green, extend types and policies per the PDF without changing the **column set** of `alerts.csv` without a migration note.