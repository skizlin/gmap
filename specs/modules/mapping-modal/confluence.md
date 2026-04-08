# Mapping Modal — Confluence (module overview)

**Module:** Mapping Modal  
**Context:** Opened from Feeder Events → Action → Map Event

---

## Purpose

Link a **feed event** to the domain: either **Confirm Mapping** (link to an existing domain event) or **Create & Map** (create a new domain event and link). The modal shows suggested domain events (fuzzy match), per-entity resolution (sport, category, competition, home, away) with **Map** or **Create** per entity, match-quality indication (55% threshold), and persistence to `domain_events.csv`, `event_mappings.csv`, and entity CSVs / `entity_feed_mappings.csv`.

---

## Entry and header

- **Entry:** Feeder Events table → Action (kebab) → Map Event. Modal opens for the selected feed event.
- **Header:** Feed name (e.g. BET365), Feed ID (e.g. #189135832), Event label (Home vs Away or Outright + badges). Participant type dropdown. Close (X) button.
- **Hidden fields:** feeder_provider, feeder_valid_id, domain_sport_name (and domain_sport_id when sport resolved).

---

## Layout: 3-column grid

- **Column 1 (Source Feed):** Feed values — Sport (with feed sport id), Category (with feed category id if present), Competition (raw league name/id), Home Team, Away Team (or Outright label), Start Time.
- **Column 2 (Field):** Label — Sport, Category, Competition, Home Team, Away Team, Start Time.
- **Column 3 (Domain Event):** Resolved or editable domain values; per row: **Map** (when entity exists in domain) or **Create** (when not); match % badge when applicable.

---

## Sport row

- **Source:** Feed sport name and feed sport id.
- **Domain:** If sport is already resolved for this feed (entity_feed_mappings / sport_feed_mappings), show resolved sport name and **ID &lt;domain_id&gt;** (format: "Name ID 123"). No editable control; "Matched" badge. If not resolved, message: "Sport must be mapped by developer before this event can be mapped." (Category/Competition/Teams disabled until sport is mapped.)

---

## Category row

- **Source:** Feed category name and optional category_id.
- **Domain:** If category is already resolved for this feed (entity_feed_mapping exists), show category name and **ID &lt;domain_id&gt;**; **Matched** badge; category textbox **editable** (user can change country/name). If not resolved: **Country** dropdown, then category search/text input; **100%** badge when suggestion matches; **Map** when a domain category exists and match ≥ 55% (or country set); **Create** when no match or &lt; 55%.
- **Suggestion rule:** Category suggestion from feed (e.g. "Barbados") → suggest Barbados (or Create). Domain suggestions (e.g. from suggested_domain_event) used only when fuzzy match ≥ 55%. Otherwise show feed value with Create.
- **Display format:** Domain entities and dropdowns use **Name ID 123** (name before ID), not "#123 Name".

---

## Competition row

- **Source:** Feed raw_league_name and optional raw_league_id.
- **Domain:** If competition resolved for this feed → name + **ID &lt;domain_id&gt;**; **Matched** badge. Else: search/datalist; **Map** when domain competition exists and selected; **Create** when not. Match % when suggestion ≥ 55%.
- **Filter:** Competitions filtered by selected sport and category.

---

## Home / Away rows

- **Source:** Feed raw_home_name, raw_home_id; raw_away_name, raw_away_id.
- **Domain:** If team resolved for this feed → name + **ID &lt;domain_id&gt;**; **Matched** badge. Else: search/datalist (teams for selected sport); **Map** when domain team selected; **Create** when not. Optional underage dropdown. Match % when suggestion ≥ 55%.
- **Outright:** Single "Home" row with suggested event name (e.g. league + market name); Create only.

---

## Start time

- **Source:** Feed start_time.
- **Domain:** Editable text; no match %. Used in Create & Map payload.

---

## Find existing domain event (suggestions + search)

- **Suggested matches:** All domain events with fuzzy score ≥ 50% (normal or reversed home/away). Shown as cards; each shows domain event id (e.g. "ID G-XXX"), start time, category, competition, match %. Sorted by score. Admin can pick one.
- **Search:** Search box to find more domain events by home/away/competition. Results same format; select one.
- **Confirm Mapping:** Button (or per-card action). Requires one selected domain event. POST to `/api/map-event` with domain_id, feeder_provider, feeder_valid_id. Writes event_mappings.csv; marks feeder event MAPPED; ensures entity_feed_mappings for this feed so entities point to same domain entities. Success: "Feed Mapped!" and modal can close/refresh.

---

## Create & Map

- **Button:** "Create & Map". **Always enabled** when Competition and both Home and Away are resolved (or outright path); not disabled when all entities are matched.
- **Action:** Collects form values (feeder_provider, feeder_valid_id, sport, category, competition, home, home_id, away, away_id, start_time). POST to `/api/domain-events`. Backend: generates new domain event id (G-XXXXXXXX), appends to domain_events.csv, appends event_mappings.csv, updates feeder event to MAPPED in memory. Success: "Domain Event Created & Mapped!" with new id; Close button.
- **Validation / errors:** If request fails (e.g. 422), modal content shows error message (not raw JSON).

---

## Fuzzy and suggestion rules

- **Threshold:** Domain suggestions (category, competition, teams) and "Map" prefill only when fuzzy match ≥ **55%**. Below 55%: show feed value and **Create**.
- **Category:** Always derive from feed first. Only use domain category when match ≥ 55%. E.g. feed "Barbados" → suggest Barbados (or Create); do not suggest Argentina at 100%.
- **Suggested domain event:** When overall match (e.g. from another feed) ≥ 70% and per-field match ≥ 55%, pre-fill category/competition/home/away from that domain event. Otherwise keep feed-derived values.
- **IDs on domain side:** Everywhere (dropdowns, tables, labels): **Name ID 123** format, not "#123 Name".

---

## Locked / resolved display

- **Resolved entity:** Already mapped for this feed (entity_feed_mapping exists). Show domain name + **ID &lt;domain_id&gt;**; **Matched** badge; no editable search (or optional edit for category only). Sport/competition/teams: locked display.
- **Create flow:** When no mapping exists, show search/datalist, **Create** button (and **Map** only when a domain entity is selected and match ≥ 55%).

---

## Business rules

- **Sport first:** Category, Competition, Home, Away depend on sport. Sport must be mapped by developer (sport_feed_mappings); no sport creation in modal.
- **Confirm Mapping:** Idempotent if (feed_provider, feed_valid_id) already mapped. One row in event_mappings.csv per link.
- **Create & Map:** Creates exactly one domain event (domain_events.csv), one event_mappings row, and any new entities + entity_feed_mappings. New domain event gets unique id G-XXXXXXXX.
- **Entity creation:** Create (category/competition/team) adds entity and (entity_type, domain_id, feed_provider_id, feed_id) row. Same feed_id+feed_provider_id already mapped → idempotent.
- **Persistence:** domain_events.csv append with newline safeguard; event_mappings.csv append; entity CSVs and entity_feed_mappings updated on Create entity.

---

## User journey / process flow

1. User opens Feeder Events → Action → Map Event → Modal opens (feed, feed id, event label in header).
2. **Path A:** User sees suggested domain events (cards). Selects one → Confirm Mapping → done; feeder event shows MAPPED.
3. **Path B:** User ignores suggestions. Resolves Sport (must be mapped). Resolves Category (country + name; Map or Create). Resolves Competition (search/select or Create). Resolves Home and Away (search/select or Create). Start time editable. Clicks **Create & Map** → new domain event + mapping; success screen; Close.
4. Modal closes or content replaces with success; Feeder Events table can refresh (MAPPED, green where applicable).

---

## Assumptions / constraints

- Modal is invoked with feed event id (and feed provider); backend has feed event payload, domain_events, entity_feed_mappings, entity CSVs.
- Sport is never created in modal; sport_feed_mappings are developer-controlled.
- Unmap / delete mapping is out of scope (separate action if required).
- Market-level mapping and margin configuration are out of scope for this modal.

---

## NFRs

- **Accuracy:** Suggestion and per-entity % use consistent fuzzy logic (55% threshold); same entity resolution as elsewhere.
- **Responsiveness:** Modal open and search feel instant.
- **Validation:** Create & Map sends all required fields; errors shown in modal (no silent fail).
- **Consistency:** Domain side always "Name ID 123"; Create & Map always allowed when competition and teams resolved.

---

## Data and tech (demo site)

| Area | Demo implementation | Production note |
|------|---------------------|-----------------|
| Modal HTML | GET with event_id; _render_mapping_modal; modal_mapping.html | Same. |
| Suggested domain events | _suggest_domain_events(event); fuzzy ≥ 50%; normal + reversed H/A | Same logic. |
| Entity suggestions | _suggest_entity_by_name; match_pct ≥ 55% for category/competition/teams | Same. |
| Confirm Mapping | POST /api/map-event (Form: domain_id, feeder_provider, feeder_valid_id) | Same API. |
| Create & Map | POST /api/domain-events (JSON: feeder_provider, feeder_valid_id, sport, category, competition, home, home_id, away, away_id, start_time) | Same API. |
| Persistence | domain_events.csv, event_mappings.csv, entity CSVs, entity_feed_mappings.csv | Same. |

---

## Out of scope for this spec

- **Feed ingestion and feed event schema:** Owned by Feed/Ingestion.
- **Feeder Events table and filters:** See feeder-events spec. Modal is opened from it.
- **Domain Events list and Event details:** See event-navigator / domain specs.
- **Entities page CRUD:** See entities spec. Modal creates entities on demand and links feed.
- **Market type mapping, Margin, Feeder Configuration, Localization:** Other platform areas.
- **Unmap / delete mapping:** Define separately if required.
- **Reverse Home/Away checkbox:** Future enhancement (suggestion already detects reversed matches).

---

## Related specs

- **Feeder Events** — Entry: Map Event opens this modal.
- **Event Navigator** — Domain events list; created events appear there.
- **Entities** — Entity creation and entity_feed_mappings; sport_feed_mappings (developer-controlled).
