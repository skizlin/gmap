# Mapping Module — Spec

**Module:** Mapping (Feed event → Domain event)  
**Entry point:** Feeder Events table → Action menu → “Map Event” → Mapping modal.

---

## 1. Scope

This module owns:

- **Mapping modal** — UI and logic to map one feed event to the domain (existing or new domain event).
- **Suggestions** — Fuzzy matching to suggest an existing domain event (same match from another feed) and to suggest/pre-fill Sport, Category, Competition, Home Team, Away Team.
- **Match percentages** — Overall event match % and **per-entity** match % (feed value vs domain value) for Sport, Category, Competition, Home, Away.
- **Two actions:**
  - **Confirm Mapping** — Link the current feed event to the **selected** existing domain event (no new domain event created).
  - **Create & Map** — Create a **new** domain event from the form and map the current feed event to it.
- **Entity resolution** — Sport (required first), then Category, Competition, Home Team, Away Team; search/dropdown + Create; hierarchy (e.g. categories filtered by sport).
- **Persistence** — Writing to `event_mappings.csv` (feed event → domain event) and, when creating entities from the modal, to `entity_feed_mappings.csv` and entity CSVs (teams, categories, competitions).

**In scope:** Modal layout, search boxes, dropdowns, Create buttons, fuzzy suggestions, match % display, Confirm Mapping, Create & Map, validation (e.g. “Create & Map” enabled only when Competition and both teams are resolved).

---

## 2. Out of scope

- **Feed ingestion** — Where feed events come from (mock JSON, live API) is owned by the Feed/Ingestion module.
- **Domain event storage format** — Structure of `domain_events.csv` and how domain events are created/stored at the data layer is shared; this module only **calls** the create endpoint and writes mappings.
- **Entities CRUD outside the modal** — The Entities page (Configuration → Entities) is a separate module; this module only **creates** entities from the modal when the user clicks Create.
- **Feeder Events table** — The table (columns, filters, action menu) is part of the Feeder Events module; this module only owns what happens **after** “Map Event” is clicked (modal + mapping APIs).

---

## 3. User flows

### 3.1 Map to existing domain event (same match from another feed)

1. User is on Feeder Events, selects a feed event, opens the action menu, clicks **Map Event**.
2. Modal opens. Backend **suggests** an existing domain event (fuzzy match by home/away/competition/start time); if found, it is shown in **Find Existing Domain Event** with an **overall match %** (e.g. 81% match).
3. Sport, Category, Competition, Home, Away are **pre-filled** from the suggested domain event. Each field shows a **per-entity match %** (e.g. Category “Argentina” vs feed “Argentina” → 100%; Away “Instituto AC Cordoba” vs feed “Instituto AC Cordoba” → 100%).
4. User can edit any field or leave as is. User clicks **Confirm Mapping**.
5. System writes one row to `event_mappings.csv` (current feed_provider + feed_valid_id → selected domain_event_id) and updates in-memory mapping status. Modal shows success; table can refresh.

### 3.2 Create new domain event and map (first time for this match)

1. User opens the modal for a feed event. No suggested domain event (or user ignores it).
2. **Sport** — User selects from sport search (e.g. “Football” when feed says “Soccer”); or it is locked if sport alias exists. Per-entity match % shown when applicable.
3. **Category, Competition, Home, Away** — Pre-filled from feed or fuzzy match; each shows **per-entity match %**. User can search/select existing or type and click **Create** to create a new entity (and link feed to it via `entity_feed_mappings.csv`).
4. When all required fields are resolved, **Create & Map** is enabled. User clicks **Create & Map**.
5. System creates one domain event (writes to `domain_events.csv` and in-memory), writes one row to `event_mappings.csv`, and updates the feed event’s mapping status. Modal shows success.

### 3.3 Find existing domain event by search (no or different suggestion)

1. User opens the modal. User types in **Search domain events…** (Find Existing section).
2. Backend returns matching domain events (by home, away, competition, id). User clicks one.
3. **Confirm Mapping** is enabled. User clicks **Confirm Mapping** → same as 3.1 step 5.

---

## 4. Key behaviours

- **Sport first** — Until a sport is selected (or locked via alias), Category, Competition, Home Team, Away Team inputs are disabled. Options in dropdowns are filtered by selected sport (and by category for competitions).
- **Fuzzy suggestions**
  - **Suggested domain event:** One best match by home/away/competition/start time; only shown if score ≥ 50% (configurable). Overall match % is that score.
  - **Per-entity match %:** For each of Sport, Category, Competition, Home, Away, the percentage is **feed value vs domain value** for that field (e.g. exact “Argentina” vs “Argentina” → 100%). Not the overall event score.
- **Pre-fill rules**
  - If a suggested domain event exists (overall score ≥ 50%): pre-fill Sport, Category, Competition, Home, Away from that event; per-entity match % computed per field.
  - If no suggested event: pre-fill from feed names and fuzzy match against domain entities (within selected sport); per-entity match % from `_suggest_entity_by_name` / `_suggest_sport_by_feed_name`.
- **Start Time** — Plain text field; not a search box. No match %.
- **Resolved (locked)** — If an entity is already resolved (e.g. sport alias, or existing row in `entity_feed_mappings` for this feed_id + feed_provider_id), show “Auto-matched” / “Matched” and do not show an editable search box for that row.
- **Create button** — Creates the entity (sport/category/competition/team) with current feed context (feed_id, feed_provider_id, sport, category where applicable) and appends to `entity_feed_mappings` (and entity CSV). Idempotent when same feed_id+feed_provider_id already mapped; when same name exists, adds another feed reference to that entity.

### Feeder Events table — green (mapped) highlighting

Sport, Category, Competition, and Event (home/away) columns show **green** when that cell’s value is “mapped” for **the currently selected feed only**:

- **Rule:** Green = there is a row in `entity_feed_mappings.csv` with `entity_type` (sports/categories/competitions/teams), **this feed’s** `feed_provider_id`, and this event’s `feed_id` (sport name, category id, league id, team id/name).
- **Per-feed:** The check uses `(feed_provider_id, feed_id)`. So if only feed 2 and 3 have mapped “Soccer” → Football, then when viewing feed 1 or 4 or 5, “Soccer” stays **not** green until that feed has its own sport mapping.
- **Why:** Green means “this feed’s entity is already linked to a domain entity,” so you can see per feed what still needs mapping and avoid false positives from other feeds.

---

## 5. APIs and data

### Endpoints (this module)

| Method | Path | Purpose |
|--------|------|--------|
| GET | `/modal/map-event/{event_id}` | Returns modal HTML; computes suggestions and pre-fills. |
| POST | `/api/map-event` | Confirm Mapping: body includes `domain_id_selected`, `feeder_provider`, `feeder_valid_id`. Writes to `event_mappings.csv`. |
| POST | `/api/domain-events` | Create & Map: body includes feeder_provider, feeder_valid_id, sport, category, competition, home, away, start_time. Creates domain event and one mapping row. |
| GET | `/api/search-domain-events?q=` | Find Existing: returns HTML fragment of domain event cards (by home/away/competition/id). |
| POST | `/api/entities` | Create entity from modal (sport/category/competition/team); used by Create buttons. |

### Data (CSVs)

- **event_mappings.csv** — Rows: `domain_event_id`, `feed_provider`, `feed_valid_id`. One row per feed event → domain event link.
- **domain_events.csv** — Domain event records (created by Create & Map or elsewhere).
- **entity_feed_mappings.csv** — Rows: `entity_type`, `domain_id`, `feed_provider_id`, `feed_id`. Links domain entities to feed IDs (multi-feed per entity).
- **teams.csv**, **categories.csv**, **competitions.csv** — Domain entities (no feed columns; feed links in entity_feed_mappings).
- **sport_aliases.csv** — Feed sport name → domain sport_id (for “Auto-matched” sport).

### Key backend helpers (for implementers)

- `_suggest_domain_event(feed_event)` → (domain_event | None, score 0–100).
- `_fuzzy_score(a, b)` → 0–100.
- `_suggest_entity_by_name(etype, feed_name, sport_id, category_id?)` → list of {name, domain_id, match_pct}.
- `_suggest_sport_by_feed_name(feed_sport_name)` → list of {name, domain_id, match_pct}.
- `_resolve_entity(etype, feed_id, feed_provider_id)` → domain entity or None (from entity_feed_mappings).

---

## 6. Acceptance criteria

- **AC-01** — Opening the modal for a feed event shows the correct feed and event in the header (feed name, feed ID, event label e.g. “Home vs Away”).
- **AC-02** — When a suggested domain event exists (fuzzy match ≥ 50%), the “Find Existing Domain Event” section shows exactly one suggested card with the overall match % (e.g. “81% match”), and that event is pre-selected so “Confirm Mapping” is enabled without further action.
- **AC-03** — Each of Sport, Category, Competition, Home Team, Away Team shows a **per-entity** match % when there is a value to show; exact name match (e.g. feed “Argentina” vs domain “Argentina”) shows **100%**; no other field reuses the overall event score for that badge.
- **AC-04** — Sport is a search box (when not locked); options are domain sports; selecting a sport enables Category, Competition, Home, Away and filters their options by sport (and category for competitions).
- **AC-05** — Category, Competition, Home Team, Away Team are search/dropdown fields (when not locked); options are filtered by selected sport (and by category for Competition). Each has a Create button that creates the entity and links the current feed to it (entity_feed_mappings).
- **AC-06** — “Create & Map” is disabled until Competition and both Home and Away are resolved (selected from list or locked). “Confirm Mapping” is disabled until a domain event is selected in Find Existing (or the suggested event is pre-selected).
- **AC-07** — Confirm Mapping: sends domain_id_selected + feeder_provider + feeder_valid_id; adds one row to event_mappings.csv; does not create a new domain event.
- **AC-08** — Create & Map: creates one new domain event (domain_events.csv + in-memory), adds one row to event_mappings.csv, and updates the feed event’s mapping status; modal shows success.
- **AC-09** — Start Time is a single text field (no search, no match %). Status is read-only (no input).
- **AC-10** — When an entity is already resolved (sport alias or entity_feed_mapping for this feed), the row shows the domain value and “Auto-matched” / “Matched” (lock); no editable search box for that cell.

---

## 7. References

- **Detailed modal logic and priority:** [../docs/MAPPING_MODAL_LOGIC.md](../docs/MAPPING_MODAL_LOGIC.md)
- **Feed integration (out of scope):** [../docs/FEED_INTEGRATION_PLAN.md](../docs/FEED_INTEGRATION_PLAN.md)
- **Backend entry:** `backend/main.py` (routes above; helpers in same file).
- **Modal template:** `backend/templates/modal_mapping.html`.
