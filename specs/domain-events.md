# Domain Events — Spec

---

## Feature

**Domain Events** is the **golden copy** of events in the domain model. Each row is one domain event (sport, category, competition, home, away, start_time) with optional display of **which feeds are mapped** to it and **start-time mismatch** indication when multiple mapped feeds have different start times.

**Related:** Feeder Events (source of feed events), Mapping Modal Tool (creates/maps to domain events), Entities (entity names and resolution), event_mappings.csv.

---

## Problem Statement

- Same real-world match can come from multiple feeds with different IDs and possibly different start times or metadata.
- Operators need one canonical list of domain events and visibility into multi-feed mapping and data quality (e.g. start time discrepancies).

---

## Proposed Solution

- **Domain Events page:** Table of domain events with columns e.g. Sport, Category, Competition, Event (home/away), Start Time, Mapped Feeds (count or names), optional Event details link. Filters: date, sport, category, competition, text search.
- **Start time colour rule:** Start time is default (e.g. white/light grey). **Red** only when two or more mapped feed events for this domain event have **different** start times (discrepancy). Single feed or identical times = not red.
- **Mapped feeds:** From `event_mappings.csv` (domain_event_id, feed_provider, feed_valid_id). Feed event data (e.g. start_time) loaded fresh when needed (e.g. per request from mock JSON) so edits to feed files are reflected without server restart for mismatch detection.
- **Event details:** Optional drill-down (e.g. new tab) for one domain event: mapped feed(s), markets, etc., as defined by product.

---

## Milestones

| # | Milestone | Notes |
|---|-----------|--------|
| M1 | Domain events table + filters | Date, sport, category, competition, search; data from domain_events.csv |
| M2 | Mapped feeds column | Count and/or provider names from event_mappings.csv |
| M3 | Start time mismatch (red) | Compare start_time across mapped feed events; red only when distinct |
| M4 | Fresh feed data for mismatch | Load feed events from source on demand so file edits apply without restart |
| M5 | Event details view (optional) | Per-event drill-down; markets, mappings |

---

## User Journey / Process Flow

```
[User] → Domain Events page
  → (Optional) Set date, sport, category, competition, search
  → Table shows domain events; “Mapped Feeds” and start time (red if mismatch)
  → Click Event (or “Details”) → Event details view for that domain event
  → Mapping is created/updated from Feeder Events + Mapping Modal, not from this page
```

---

## Business Rules

- **Single source of truth:** Domain event records in `domain_events.csv`; links in `event_mappings.csv`. No duplicate domain_event_id.
- **Start time mismatch:** For a domain event with ≥2 mappings, fetch each mapped feed event’s start_time; if at least two differ, show start time in red. Otherwise default colour.
- **Read-only for mapping:** Domain Events page does not create or delete mappings; it only displays. Creation/update is via Mapping Modal from Feeder Events.

---

## Assumptions / Constraints

- Domain event has: id, sport, category, competition, home, away, home_id, away_id, start_time (and any extra fields in CSV). Feed events provide start_time in a parseable format (e.g. ISO or timestamp).
- Large lists may require pagination or virtual scroll; filtering is server-side or hybrid.

---

## NFRs

- **Accuracy:** Mismatch flag must be based on current feed data (reload when rendering Domain Events table/details).
- **Performance:** Filtering and mismatch computation should not block page load; optimize or cache if feed data is large.
- **Consistency:** Column semantics (e.g. “Mapped Feeds”, red = mismatch) documented or tooltip for users.

---

## Reporting / Compliance

- No specific reporting in scope. Domain Events list can be exported or used for downstream reporting. Audit of event creation/mapping is in Mapping Modal / API layer if required.

---

## Out of Scope

- **Feed event storage and ingestion:** Owned by Feed/Ingestion. Domain Events only reads feed event attributes (e.g. start_time) for comparison.
- **Mapping Modal UI and mapping APIs:** See **mapping-modal-tool** spec.
- **Feeder Events table and filters:** See **feeder-events** spec.
- **Entity management:** See **entities** spec. Domain Events displays entity names from domain model.
- **Margin Configuration, Feeder Configuration, Localization:** Other platform areas.
