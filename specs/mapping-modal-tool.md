# Mapping Modal Tool — Spec

---

## Feature

The **Mapping Modal** is the tool to link a **feed event** to the domain: either **Confirm Mapping** (link to an existing domain event) or **Create & Map** (create a new domain event and link). It includes suggestions (fuzzy match to existing domain event), per-entity match %, entity resolution (sport, category, competition, home, away) with search/create, and persistence to `event_mappings.csv` and entity CSVs / `entity_feed_mappings.csv`.

**Related:** Feeder Events (entry: Action → Map Event), Domain Events (target list; created events appear there), Entities (entity creation and feed links).

---

## Problem Statement

- Feed events must be explicitly mapped to domain events for a single golden copy and multi-feed aggregation.
- Users need suggestions, match quality indication, and the ability to create missing entities without leaving the flow.
- Without a clear flow and validation, wrong mappings and duplicate domain events occur.

---

## Proposed Solution

- **Entry:** Feeder Events table → Action → “Map Event” → modal opens for that feed event.
- **Modal sections:**
  - **Find Existing Domain Event:** Suggested one (fuzzy match by home/away/competition/start time, score ≥ threshold e.g. 50%); overall match %. Search box to find another; select one → **Confirm Mapping**.
  - **Build new / edit:** Sport (required first), Category, Competition, Home Team, Away Team, Start Time. Each entity: search/select or **Create** (creates entity and adds row to entity_feed_mappings for current feed). Per-entity match % (feed value vs domain value). When Competition and both teams resolved → **Create & Map** enabled.
- **Persistence:** Confirm Mapping → one row in `event_mappings.csv`. Create & Map → one row in `domain_events.csv`, one in `event_mappings.csv`, and any new entities + entity_feed_mappings rows. New competitions auto-assigned to default margin template (e.g. Uncategorized).
- **Locked/resolved:** If sport (or entity) is already resolved (e.g. sport alias or existing entity_feed_mapping for this feed), show “Auto-matched” / “Matched” and do not show editable search for that row.

---

## Milestones

| # | Milestone | Notes |
|---|-----------|--------|
| M1 | Modal open + header | Feed name, feed event id, event label |
| M2 | Find Existing: suggestion + overall % | Fuzzy suggest one domain event; show overall match %; pre-fill form from it |
| M3 | Find Existing: search + select | Search domain events; select one; Confirm Mapping |
| M4 | Entity resolution: Sport first | Sport required; Category/Competition/Home/Away filtered by sport (and category for competitions) |
| M5 | Per-entity match % | Per field: feed value vs domain value; exact match = 100% |
| M6 | Create buttons | Create entity (sport/category/competition/team), append entity_feed_mappings (and entity CSV) |
| M7 | Confirm Mapping | Write event_mappings.csv only; no new domain event |
| M8 | Create & Map | Create domain event + event_mappings row; new competitions → default margin template |
| M9 | Locked/resolved display | Sport/entity already mapped for this feed → show Matched, no edit |

---

## User Journey / Process Flow

```
[User] Feeder Events → Action → Map Event
  → Modal opens (suggestion + pre-fill if fuzzy match ≥ threshold)
  → Path A: Select suggested or searched domain event → Confirm Mapping → done
  → Path B: Ignore suggestion; resolve Sport → Category → Competition → Home → Away (search or Create)
  → Create & Map → new domain event + mapping; new competition → Uncategorized template
  → Modal closes; Feeder Events table can refresh (MAPPED, green where applicable)
```

---

## Business Rules

- **Sport first:** Category, Competition, Home, Away are disabled until Sport is selected (or locked). Options filtered by sport (and by category for competitions).
- **Suggestions:** One suggested domain event when fuzzy score ≥ 50% (configurable). Overall match % = that score. Per-entity match % = feed vs domain for that field only.
- **Confirm Mapping:** Requires one selected domain event. Idempotent if same (feed_provider, feed_valid_id) already mapped.
- **Create & Map:** Requires Competition and both Home and Away resolved. Creates exactly one domain event and one mapping row. New competition → assign to default margin template (e.g. template_id 1).
- **Start time:** Single field; no match %. Not used for uniqueness in suggestion only; can be displayed/editable as per product.
- **Entity creation:** Create adds entity and one (entity_type, domain_id, feed_provider_id, feed_id) row. Same feed_id+feed_provider_id already mapped → idempotent.

---

## Assumptions / Constraints

- Modal is invoked with feed event id (and feed provider); backend has access to feed event payload and domain_events / entity_feed_mappings / entity CSVs.
- No removal of mapping in this spec (unmap); can be a separate action or out of scope.
- Market-level mapping and margin configuration are out of scope for this modal.

---

## NFRs

- **Accuracy:** Suggestion and per-entity % must use consistent fuzzy logic and same entity resolution as used elsewhere.
- **Responsiveness:** Modal open and search must feel instant; defer heavy work if needed.
- **Validation:** Create & Map disabled until required fields resolved; clear error if Confirm with no selection.

---

## Reporting / Compliance

- Mapping actions (Confirm / Create & Map) can be logged for audit; detailed audit trail is product-specific. This spec does not define reporting.

---

## Out of Scope

- **Feed ingestion and feed event schema:** Owned by Feed/Ingestion. Modal consumes one feed event and writes mappings/entities only.
- **Feeder Events table and filters:** See **feeder-events** spec. Modal is the tool opened from it.
- **Domain Events list and Event details:** See **domain-events** spec.
- **Entities page CRUD and bulk management:** See **entities** spec. Modal only creates entities on demand and links feed.
- **Market type mapping, Margin Configuration, Feeder Configuration, Localization:** Other platform areas.
- **Unmap / delete mapping:** Not in scope; define separately if required.
