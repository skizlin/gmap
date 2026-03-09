# Event Navigator — Confluence (module overview)

**Module:** Event Navigator  
**Page:** Betting Program → Event Navigator

---

## Purpose

View **canonical (domain) events** — the golden copy built from mapped feed data. Operators filter by period, sport, category, competition, status, live/notes/outright, has bets, brand, and search; see which feeds are linked to each event (#FEED); add screen-only notes per event; and open event details or the action menu. Event Navigator notes are **for this screen only** and are not related to Feeder Events notes.

---

## Page and layout

- **Page title:** Event Navigator  
- **Description:** Canonical events built from mapped feed data. Filter by date, sport, category and competition.  
- **Filter bar:** Period (date-range preset dropdown), Sport (multiselect), Category (multiselect), Competition (multiselect), Status (multiselect), Live toggle (icon), Has Bets toggle ($ icon), Notes toggle (icon), All/Outright/Regular tabs, vertical divider, Search (text), vertical divider, **Brand:** multiselect dropdown (label left of dropdown). Active filter chips with remove; **Clear All** to reset all filters.  
- **Table:** Scrollable; header row with bulk-select checkbox.  
- **Footer:** Bulk Update button (left, disabled placeholder), "Showing X events", Previous / Next buttons (disabled placeholders for pagination). Pagination and page size (e.g. 20 per page) to be implemented later.

---

## Period filter (Start Time)

- **Control:** Button showing a date range (e.g. `07/03/2026 - 07/03/2026`) with calendar icon and chevron; no “Period” label.  
- **Dropdown options:** Today, Tomorrow, Next 7 Days, This Month, Next Month, Yesterday, Last 7 Days, Custom range.  
- **Behaviour:** Selecting an option updates the displayed range and highlights that option; **no filter logic** in initial version (presentation only).  
- **Default:** Today (highlighted).

---

## Filters (Sport, Category, Competition, Status, Live, Has Bets, Notes, Outright, Search, Brand)

| Name | Type | Description |
|------|------|-------------|
| Sport | Multi-select dropdown | Checkboxes; options from domain events. Select All / Deselect All. Chip(s) when selected. |
| Category | Multi-select dropdown | Checkboxes; options depend on selected sport(s). Disabled until at least one sport selected. Chip(s) when selected. |
| Competition | Multi-select dropdown | Checkboxes; options depend on sport and category. Chip(s) when selected. |
| Status | Multi-select dropdown | Checkboxes: Open, Closed, Resulted, Cancelled, Abandoned. Chip(s) when selected. |
| Live match | Toggle (icon) | Off = all events; On = only live. Icon colour (e.g. red) when on. |
| Has Bets | Toggle (icon, $) | Off = all events; On = only events that have bets. Icon colour (e.g. emerald) when on. |
| Notes | Toggle (icon) | Off = all events; On = only events that have at least one note. Icon colour (e.g. amber) when on. |
| Outright | Button group | All / Outright / Regular. One active at a time. |
| Search | Text input | Free text; searches sport, category, competition, event label. Debounced. |
| Brand | Multi-select dropdown with label | **Label “Brand:”** to the left of dropdown. Options: **Global** (first) plus one per brand from brands list. **Default:** Global selected. **Rule:** Global cannot be combined with other brands — selecting Global deselects all others; selecting any other brand deselects Global. If none selected, selection reverts to Global. |
| Active filter chips | Chips + Clear All | One chip per selected value (date, sport, category, competition, status). Click chip to remove; **Clear All** resets all filters including Period, Status, Live, Has Bets, Notes, Outright, Brand, Search. |

---

## Table columns

| Column | Description |
|--------|-------------|
| Checkbox | Row bulk-select; header checkbox selects/deselects all. |
| Id | Domain event ID (e.g. secondary colour, monospace). |
| Start Time | Event start; tooltip can show start time by feed when mapped. Red if start_time_mismatch. |
| Sport | Sport name; clickable filter shortcut. |
| Category | Category; clickable filter shortcut. |
| Competition | Competition; clickable filter shortcut. |
| Event | “Home v Away” (link to Event Details in new tab). |
| Status | e.g. Not Started (placeholder). |
| Class | Placeholder “—”. |
| CO | CashOut; placeholder “—”. |
| T/O | Placeholder “—”. |
| In charge | Placeholder “—”. |
| Has Bets | Placeholder “—”. |
| Score | Placeholder “—”. |
| #FEED | Number of feeds mapped to this domain event (e.g. 1). |
| #mkt | Placeholder “—”. |
| Notes | Note icon (amber) if event has an Event Navigator note; “—” otherwise. Click opens Notes modal (screen-only). |
| Action | Kebab menu (View Event, Edit Event, Close Event, Abandon Event, Takeover Event, Release Event, Disable CO, Release CO, Copy Event ID, View Bets, Event Log, Dynamic Templates, Notes). |

---

## Action menu (kebab)

| Action | Description |
|--------|-------------|
| View Event | Opens Event Details in new tab. |
| Edit Event | Placeholder. |
| Close Event | Placeholder. |
| Abandon Event | Placeholder. |
| Takeover Event | Placeholder. |
| Release Event | Placeholder. |
| Disable CO | Placeholder. |
| Release CO | Placeholder. |
| Copy Event ID | Placeholder. |
| View Bets | Placeholder. |
| Event Log | Placeholder. |
| Dynamic Templates | Placeholder. |
| Notes | Opens Event Navigator Notes modal for this domain event (same as clicking Notes column). |

---

## Event Navigator Notes (screen-only)

- **Scope:** Notes are **valid for this screen only**. They are **not** related to Feeder Events notes or platform notes used there.  
- **Storage:** `data/notes/event_navigator_notes.csv` — one note per domain event (domain_event_id, note_text, updated_at).  
- **Opening:** Click the Notes column (icon or “—”) or Action → Notes. Modal loads via HTMX.  
- **Modal content:** Title “Notes (Event Navigator)”; short text that notes are for this screen only; domain event label; single **Note** textarea; **IMPORTANT! Please confirm you read and understood!** checkbox; help text: “If checked, all users will see a notification (top right) until they confirm they have read it.”; Save and Cancel.  
- **IMPORTANT checkbox:** When checked and user clicks Save, a **platform notification** is created (same mechanism as Feeder notes). All users see the notification in the top-right panel until they confirm “I've read and understood”. Note text is still stored only in Event Navigator notes.  
- **After save:** Modal closes; table refreshes so the Notes column shows the note icon if a note exists.  
- **Default:** No note; textarea empty; IMPORTANT unchecked.

---

## Business rules

- **Domain events source:** Events come from the domain events store (e.g. `domain_events` from CSV or DB), enriched with mapped feed count and start-time-by-feed from event mappings.  
- **Filter scope:** Sport/Category/Competition options are derived from domain events (and possibly entity lists). Status options: Open, Closed, Resulted, Cancelled, Abandoned.  
- **Brand filter:** Global is a virtual option; other options from brands list. Global exclusive: either Global alone or one or more non-Global brands.  
- **Notes:** Stored in `event_navigator_notes.csv`; one note per domain event; overwrite on save. IMPORTANT creates a row in `platform_notifications.csv` for the confirmation flow only.  
- **Click-to-filter:** Clicking Sport/Category/Competition in a row applies that filter (shortcut).

---

## User journey / process flow

**Open and filter**  
User opens Event Navigator → (optional) selects Period preset, Sport, Category, Competition, Status, toggles Live / Has Bets / Notes, Outright, types Search, selects Brand → table shows filtered domain events; chips show active filters; “Showing N events” in footer.

**View event details**  
User clicks Event cell (e.g. “Home v Away”) → Event Details opens in new tab.

**Add or edit note**  
User clicks Notes column or Action → Notes → modal opens → user types note, optionally checks IMPORTANT → Save → note saved; if IMPORTANT, notification created; modal closes; table refreshes; note icon appears in Notes column if note exists.

**Clear filters**  
User clicks a chip to remove one filter, or “Clear All” → all filters (including Period, Status, Live, Has Bets, Notes, Outright, Brand, Search) reset; Brand resets to Global.

**Bulk select**  
User checks row checkboxes or header “select all” → selection is client-side; Bulk Update button is present but disabled (placeholder).

**Pagination (later)**  
When implemented: table shows a limited number of events per page (e.g. 20); footer shows "Showing X–Y of Z events" or equivalent; Previous/Next change the page. Initial version: Previous/Next are visible but disabled; no page limit applied.

---

## Footer and pagination (placeholders)

- **Bulk Update:** Button on the left of the footer; disabled with tooltip "Bulk update – coming soon". When implemented, will apply an action to all selected rows (e.g. bulk status change).
- **Showing count:** "Showing X events" (or, with paging: "Showing X–Y of Z events").
- **Previous / Next:** Buttons on the right of the footer; disabled with tooltip "Pagination – coming soon". When implemented: page size typically 20 events per page; Previous/Next navigate between pages.
- **Page size:** Target limit 20 events per page (to be implemented later); for now the table shows all matching events.

---

## Assumptions / constraints

- **Domain events:** Built from mapped feed data; structure includes id, sport, category, competition, home/away, start_time, and derived mapped_feed_count, start_time_mismatch, feed_start_times.  
- **Period filter:** Presentation only in initial version; no backend filtering by period yet.  
- **Has Bets / Live / Notes / Outright / Brand:** Params are sent to the table endpoint; backend may not filter by them yet (placeholder).  
- **Event Navigator notes:** Separate store and UI from Feeder Events notes; no shared note list.

---

## NFRs

- **Performance:** Table and filter options should render without noticeable delay for typical domain event count. Use server-side or hybrid filtering where applicable.  
- **Consistency:** After saving a note, the table (or refreshed fragment) must show the updated Notes column (icon vs “—”) without full page reload (e.g. HTMX partial refresh).  
- **Accessibility:** Filters and table keyboard-navigable; column meanings can be clarified via tooltips or aria-labels.

---

## Data and tech (demo site)

| Area | Demo implementation | Production note |
|------|---------------------|-----------------|
| Domain events | Loaded from domain_events store; enriched with mappings. | Typically from DB; same logical model. |
| Event mappings | event_mappings.csv (feed → domain_event_id). | Table or equivalent. |
| Event Navigator notes | event_navigator_notes.csv (domain_event_id, note_text, updated_at). | Table; screen-only scope. |
| Notifications (IMPORTANT) | platform_notifications.csv; note_id e.g. "en-{domain_event_id}". | Notification table. |
| Brands | brands.csv; Global is virtual. | Brand table or config. |
| Table load | HTMX: GET partial returns table body; filter values sent as query params. | Same UX; backend reads from DB. |
| Pagination | No paging in demo; all events shown. Page size (e.g. 20) and Previous/Next to be added later. | Offset/limit or cursor; page size configurable. |
| Bulk select | Client-side only; selection not persisted. | Same for UI; Bulk Update would call APIs with selected IDs. |

---

## Out of scope for initial version (still part of module)

- **Period filter logic:** Backend filtering by selected period (Today, Tomorrow, etc.) to be implemented later.  
- **Has Bets / Live / Notes / Outright / Brand:** Backend filtering by these params to be implemented when data is available.  
- **Action menu items:** View Event (opens Event Details) in place; Edit, Close, Abandon, Takeover, Release, Disable CO, Release CO, Copy Event ID, View Bets, Event Log, Dynamic Templates are placeholders.  
- **Bulk Update:** Button is present in the footer (disabled, "Bulk update – coming soon"); behaviour (e.g. bulk status update on selected rows) to be implemented later.  
- **Pagination:** Previous/Next buttons are present in the footer (disabled, "Pagination – coming soon"); page size (e.g. 20 per page) and navigation to be implemented later.

---

## Related specs

- **Feeder Events** — Feed events; mapping to domain events.  
- **Mapping Modal** — Map feed event to domain event; Create & Map.  
- **Entities** — Sports, Categories, Competitions, Teams; entity_feed_mappings.  
- **Backoffice (Phase 1)** — Shell, nav, Dashboard, Feeder Events, Event Navigator, Entities, Notifications, Toast, Modal container.
