# Feeder Events — Spec

---

## Feature

Feeder Events is the view of **raw events from feed providers** (e.g. bwin, bet365). Users select a feed, apply filters (sport, category, competition), search, and see mapping status (MAPPED/UNMAPPED). From here they open the **Mapping Modal** to map feed events to domain events.

**Related:** Mapping Modal Tool, Domain Events, Entities (entity_feed_mappings for green highlighting).

---

## Problem Statement

- Multiple feeds send events with different IDs, names, and structures.
- Operators need a single place to see what each feed offers and which events are already linked to the domain.
- Without per-feed filtering and mapping-status visibility, mapping and data quality work is inefficient.

---

## Proposed Solution

- **Feeder Events page** (e.g. under Feed / Feeder Events in nav): one feed selector, cascading filters (Sport → Category → Competition), optional mapping-status and outright filters, text search. Table columns: Sport, Category, Competition, Event (home/away), Start Time, Status (MAPPED/UNMAPPED), Action (e.g. Map Event).
- **Green highlighting:** Sport, Category, Competition, Event cells show green when that feed’s value is already linked to a domain entity via `entity_feed_mappings.csv` (per-feed check).
- **Mapping status** is derived from `event_mappings.csv`: if a row exists (feed_provider + feed_valid_id → domain_event_id), status = MAPPED; else UNMAPPED. Sync on load (and after mapping) so table reflects current state.
- **Data source:** Feed events from mock JSON (or live API later). No persistence of feed events themselves; only mappings and entity links are persisted.

---

## Milestones

| # | Milestone | Notes |
|---|-----------|--------|
| M1 | Feed selector + table with core columns | Sport, Category, Competition, Event, Start Time, Status |
| M2 | Cascading filters (sport, category, competition) | Options from current feed’s events |
| M3 | Mapping status filter + outright filter + search | MAPPED/UNMAPPED, outright yes/no, text q |
| M4 | Green highlighting per entity type | From entity_feed_mappings for selected feed |
| M5 | Action menu → Map Event | Opens Mapping Modal (see mapping-modal-tool spec) |

---

## User Journey / Process Flow

```
[User] → Feeder Events page
  → Select Feed (dropdown)
  → (Optional) Select Sports / Categories / Competitions
  → (Optional) Filter by Mapping Status, Outright, Search
  → Table shows filtered feed events; green = entity already mapped for this feed
  → Click Action → Map Event → Mapping Modal opens (see mapping-modal-tool)
  → After mapping, table refresh shows MAPPED and updated green cells
```

---

## Business Rules

- **Feed scope:** Table shows only events for the **selected feed**. Filters (sport, category, competition) are scoped to that feed’s distinct values.
- **Mapping status:** Single source of truth is `event_mappings.csv`. In-memory “mapping_status” and “domain_id” on feed events are synced from it on page load and after Confirm Mapping / Create & Map.
- **Green = per-feed:** A cell is green only if there is an `entity_feed_mappings` row for (entity_type, domain_id, **this feed’s** feed_provider_id, feed_id). Other feeds’ mappings do not affect this feed’s highlighting.
- **Read-only feed data:** Feed events are not edited on this page; only mapping and entity links are written (via Mapping Modal and APIs).

---

## Assumptions / Constraints

- Feed event data is loaded from a defined source (e.g. mock JSON per feed); structure includes at least: feed_provider, valid_id, sport, category, competition, home, away, start_time, outright flag.
- One feed selected at a time. No cross-feed comparison table in this view (that is Domain Events).
- Entity resolution (sport/category/competition/team) and creation are handled in **Entities** and **Mapping Modal**, not in Feeder Events logic.

---

## NFRs

- **Performance:** Table and filter options should render without noticeable delay for typical feed size (e.g. thousands of events). Use server-side or hybrid filtering if needed.
- **Consistency:** After any mapping action, Feeder Events table (or refreshed fragment) must show updated mapping status and green highlighting without full page reload if using HTMX.
- **Accessibility:** Filters and table must be keyboard-navigable; status and green meaning can be clarified via aria-labels or tooltips.

---

## Reporting / Compliance

- No specific reporting or compliance requirements in scope for Feeder Events. Audit of mapping actions is covered in Mapping Modal / Domain Events if required.

---

## Out of Scope

- **Feed ingestion / normalization:** How feed data is fetched, normalized, or stored is owned by Feed/Ingestion; this spec assumes events are available in a known shape.
- **Mapping Modal UI and logic:** See **mapping-modal-tool** spec.
- **Domain Events golden copy:** See **domain-events** spec.
- **Entity CRUD and entity_feed_mappings management:** See **entities** spec. Feeder Events only **consumes** mapping status and entity_feed_mappings for display (green, status).
- **Feeder Configuration** (system actions, incidents): Separate module; not part of Feeder Events view.
- **Margin Configuration, Localization, Market Type Sets:** Other platform areas; referenced only when relevant (e.g. domain event creation flows).
