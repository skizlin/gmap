# Feeder Events — Confluence (module overview)

**Module:** Feeder Events  
**Page:** Betting Program → Feeder Events

---

## Purpose

View **raw events from feed providers** (e.g. bwin, bet365). Operators select a feed, apply filters, see mapping status (Mapped / Unmapped / Ignored), and open the Mapping Modal to map feed events to domain events. Related: Mapping Modal, Event Navigator (domain events), Entities (entity_feed_mappings for green highlighting).

---

## Page and layout

- **Page title:** Feeder Events  
- **Description:** Incoming events from feed providers. Filter by feed, sport, category and competition, then map to domain events.  
- **Filter bar:** Date, Feed (dropdown), Sport (multiselect), Category (multiselect), Competition (multiselect), Status (multiselect), Live match toggle, Notes toggle, Mapping status filter, Outright filter, Text search. Active filter chips with remove; **Clear All** to remove all filters.  
- **Table:** Scrollable; header row with bulk-select checkbox.  
- **Footer:** Bulk Update button (left), “Showing X events”, Previous / Next (pagination placeholders).

---

## Table columns

| Column        | Description |
|---------------|-------------|
| Checkbox      | Row bulk-select; header checkbox selects/deselects all. |
| Feed Source   | Feed provider badge (e.g. bwin, bet365). |
| Feed ID       | Feed event ID (e.g. valid_id); optional BetRadar badge. Muted when ignored. |
| ID / Status   | **Mapped:** domain event ID (green). **Unmapped:** red “Unmapped”. **Ignored:** grey “Ignored”. |
| Start Time    | Event start (from feed). Muted when ignored. |
| Sport         | Sport name; clickable filter shortcut. Green if mapped for this feed. Muted when ignored. |
| Category      | Category; clickable filter shortcut. Green if mapped. Muted when ignored. |
| Competition   | Competition/league; clickable filter shortcut. Green if mapped. Muted when ignored. |
| Event         | Home vs Away (or Outright label + M-BOOK if applicable). Team names green if mapped. Muted when ignored. |
| Status        | Feed status (e.g. Open, Closed, Resulted, Cancelled, Abandoned). Muted when ignored. |
| #MKT          | Number of markets (placeholder). Muted when ignored. |
| Notes         | Note icon if event has note(s); “—” otherwise. |
| Action        | Kebab menu. |

---

## Action menu (kebab)

| Action | Description | Not visible when |
|--------|--------------|------------------|
| Map Event | Opens Mapping Modal to map this feed event to a domain event. | Event is **ignored**. |
| Copy Feed ID | Copies feed event ID to clipboard; shows green toast "Feed ID copied to clipboard". | — |
| Event Log | Opens modal with action history (appeared, mapped, note_added, ignored, unignored) and timestamps. | — |
| Ignore Mapping / Un-ignore | Toggle ignored state; no data deleted. Label shows "Ignore Mapping" when not ignored, "Un-ignore" when ignored. ID/Status shows "Ignored" when set. | — |
| Notes | Opens Notes modal (add/view/edit/delete notes; platform notes; optional "confirm read" notification). | — |

---

## Filters

| Name | Type | Description |
|------|------|--------------|
| Date | Date picker | Single date; no range. |
| Feed | Dropdown (single select) | Select one feed; table shows only that feed's events. |
| Sport | Multi-select dropdown | Checkboxes in panel; options from current feed. Shows chip(s) when selected. |
| Category | Multi-select dropdown | Checkboxes; options depend on selected sport(s). Disabled until at least one sport selected. Chip(s) when selected. |
| Competition | Multi-select dropdown | Checkboxes; options from feed (sport/category scoped). Chip(s) when selected. |
| Status | Multi-select dropdown | Checkboxes; e.g. Open, Closed, Resulted, Cancelled, Abandoned. Chip(s) when selected. |
| Live match | Toggle (icon button) | Off = all events; On = only live events. Icon colour change when on (e.g. red). |
| Notes | Toggle (icon button) | Off = all events; On = only events that have at least one note. Icon colour when on (e.g. amber). |
| Outright | Button group | All / Outright / Regular. No chip. |
| Mapping status | Button group | Unmapped / Mapped / All. No chip. |
| Search | Text input | Free text; searches sport, category, competition, event label. Debounced. |
| Active filter chips | Chips + Clear All | One chip per selected value (sport, category, competition, status). Click chip to remove; **Clear All** clears all filters. |

---

## Business rules

- **Feed scope:** Table shows only the **selected feed**. Filters use that feed’s distinct values.  
- **Mapping status:** From `event_mappings.csv`. Synced on load and after mapping; overridden to **Ignored** if event is in `feeder_ignored_events.csv`.  
- **Green highlighting:** Sport/Category/Competition/Team cells are green only if there is an `entity_feed_mappings` row for (entity_type, domain_id, **this feed’s** feed_provider_id, feed_id).  
- **Ignored:** Stored in `feeder_ignored_events.csv`. Ignored events: Map Event hidden; ID/Status grey “Ignored”; columns Feed ID → #MKT use muted (darker grey) styling; Feed Source, Notes, Action unchanged.  
- **Event log:** Entries in `feeder_event_log.csv` (appeared, mapped, note_added, ignored, unignored) with timestamps; “appeared” written when event first appears in table (batch).  

---

## User Journey / Process Flow

**Open and filter**  
User opens Feeder Events → selects Feed → (optional) Sport, Category, Competition, Status, Live/Notes toggles, Mapping status, Outright, Search → table shows filtered events; chips show active filters; "Showing N events" in footer.

**Map event**  
User sees unmapped event → Action → Map Event → Mapping Modal opens → user selects or creates domain event and confirms → modal closes → table refreshes; event shows Mapped (green domain ID).

**Copy Feed ID**  
User opens Action → Copy Feed ID → feed ID copied to clipboard → toast "Feed ID copied to clipboard" (top-right).

**Event log**  
User opens Action → Event Log → modal shows action history (appeared, mapped, note_added, ignored, unignored) with timestamps, newest first.

**Ignore / Un-ignore**  
User opens Action → Ignore Mapping → event marked ignored; ID/Status shows "Ignored"; row muted; Map Event hidden. To revert: Action → Un-ignore.

**Notes**  
User opens Action → Notes → Notes modal (add/view/edit/delete; platform notes; optional confirm-read). (Full behaviour out of scope for initial.)

**Clear filters**  
User has chips (sport, category, competition, status) → clicks chip to remove one, or "Clear All" → all filters cleared; table shows full set for current feed.

**Bulk select**  
User checks row checkboxes or header "select all" → selection is client-side; Bulk Update button (footer) is placeholder for later.

---

## Assumptions / Constraints

- **Feed data:** Events are loaded from a defined source (e.g. mock JSON or API); structure includes at least feed_provider, valid_id, sport, category, competition, home/away or outright label, start_time, outright flag, status, markets_count. Feed events are not persisted by this module; only mappings, ignored list, event log, and notes are persisted.
- **One feed:** One feed selected at a time. No cross-feed comparison in this view (see Event Navigator for domain-centric view).
- **Entity resolution:** Sport/category/competition/team creation and entity_feed_mappings are handled in Entities and Mapping Modal. Feeder Events only consumes mapping status and entity links for display (green, ID/Status). Sport must be mapped by developer (sport_feed_mappings) for mapping to be available.
- **Read-only feed rows:** Feed event fields are not edited on this page; only mapping, ignore, notes, and event log are written via APIs.

---

## NFRs

- **Performance:** Table and filter options should render without noticeable delay for typical feed size (e.g. thousands of events). Use server-side or hybrid filtering; avoid loading full feed client-side if not needed.
- **Consistency:** After mapping, ignore, or notes, the table (or refreshed fragment) must show updated ID/Status and green highlighting without full page reload (e.g. HTMX partial refresh).
- **Accessibility:** Filters and table should be keyboard-navigable; status and green meaning can be clarified via aria-labels or tooltips where applicable.

---

## Reporting / Compliance

- No specific reporting or compliance requirements in scope for Feeder Events. Event log (appeared, mapped, note_added, ignored, unignored) provides an audit trail per feed event. Broader audit of mapping decisions is covered in Mapping Modal / Event Navigator if required.

---

## Data and tech (demo site)

This describes what the **demo site** uses. In production you will use a **database** instead of CSVs; the behaviour and data model should align.

| Area | Demo implementation | Production note |
|------|---------------------|-----------------|
| Feed events | Loaded from mock JSON files per feed; not persisted. | Typically from feed API or ingestion layer; may be cached or stored in DB. |
| Event mappings | `event_mappings.csv` (feed_provider, feed_valid_id → domain_event_id). | Table or equivalent; same logical model. |
| Entity–feed links | `entity_feed_mappings.csv` (sport from `sport_feed_mappings.csv`). | Tables for mappings; sport–feed mappings may be config/reference data. |
| Ignored events | `feeder_ignored_events.csv` (feed_provider, feed_valid_id). | Table or flag on feed events. |
| Event log | `feeder_event_log.csv` (feed_provider, feed_valid_id, action_type, details, created_at). | Audit / log table. |
| Notes & notifications | `data/notes/platform_notes.csv`, `platform_notifications.csv`. | Notes and notification tables. |
| Table load | HTMX: GET partial returns table body; filter values sent as query params. | Same UX; backend reads from DB and returns HTML or JSON. |
| Bulk select | Client-side only (checkboxes); selection not persisted. | Same for UI; bulk actions would call APIs with selected IDs. |

---

## Out of scope for initial version (still part of module)

- **Notes (full):** Multi-note per event, “confirm read” notifications, created_by/updated_by — described above but not required for initial release.  
- **Bulk Update:** Button is present (disabled, “Bulk update – coming soon”); behaviour (bulk update of selected events) to be implemented later.

---

## Related specs

- Mapping Modal Tool — Map Event flow, Confirm Mapping / Create & Map.  
- Event Navigator (domain events) — Golden copy; mapped feeds.  
- Entities — Sports, Categories, Competitions, Teams; entity_feed_mappings; sport feed mappings (developer-controlled).
