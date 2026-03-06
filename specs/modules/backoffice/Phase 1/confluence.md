# Backoffice Phase 1 — Confluence

**Phase 1 scope:** Backoffice shell supporting only the **4 modules with specs:** Feeder Events, Event Navigator (Domain Events), Entities, Mapping Modal Tool.

Everything mentioned in those modules that the backoffice provides is covered here.

---

## Purpose

Phase 1 backoffice is the **shell** that hosts Feeder Events, Event Navigator, Entities, and the Mapping Modal. It provides: navigation to those modules, notifications panel (for Feeder Events notes with "confirm read"), profile placeholder, dashboard (landing with link to Feeder Events), toast (for Copy Feed ID and similar), modal container (for Mapping Modal, Notes, Event Log), and page header (title + description). Event Details page can override the page header.

---

## Layout structure

- **Header:** Fixed top bar; logo (left), nav menu (center), notifications + profile (right).
- **Toast container:** Fixed top-right below header; greenish feedback (e.g. "Feed ID copied to clipboard" from Feeder Events).
- **Main content:** Page header block (title + short description), then scrollable content.
- **Modal container:** Full-screen overlay for modals; used by Feeder Events (Mapping Modal, Notes, Event Log).

---

## Navigation menu (Phase 1)

| Item | Type | Purpose in Phase 1 |
|------|------|---------------------|
| Logo (GMP) | Link | Home (Dashboard). |
| Admin | Link | Placeholder. |
| Configuration | Dropdown | **Entities** — used by Feeder Events (green highlighting), Mapping Modal (entity resolution), Event Navigator (entity names). Other items (Localization, Brands, Feeder, Margin, Risk Rules) are placeholders for later phases. |
| Betting Program | Dropdown | **Event Navigator** (Domain Events), **Feeder Events**, Archived Events. Feeder Events is entry to Mapping Modal. Event Navigator shows domain events (golden copy). |
| Risk, Bets/PTLs, Alerts, Reports | Link | Placeholders. |
| Notifications | Icon button | Used when Feeder Events notes have "confirm read"; opens unconfirmed list. |
| Profile | Avatar | Placeholder (e.g. "A"). |

Active section highlights nav item (e.g. text-primary).

---

## Notifications (from Feeder Events)

Used when a Feeder Events note is added with "IMPORTANT! Please confirm you read and understood" checked.

| Element | Description |
|---------|-------------|
| Bell icon | Top-right; opens panel. Badge shows unconfirmed count; hidden when zero. |
| Panel | Dropdown; "Confirm you read"; list from `/notifications/unconfirmed`. |
| Card | Message snippet; timestamp; "I've read and understood" button. |
| Confirm | POST `/api/notifications/{id}/confirm`; list refreshes; badge updates. |
| Triggers | `notificationAdded`, `notificationsRefresh` (e.g. after adding note with confirm-read). |

---

## Profile

Avatar placeholder (e.g. "A"); top-right. Full profile menu out of scope for Phase 1.

---

## Dashboard (Phase 1)

- **Route:** `/` (home).
- **Page title:** Dashboard.
- **Description:** Overview of incoming events, mapping coverage and platform status.
- **Content:** Stat cards (Incoming Events, Mapped Successfully, Pending Action); Application stack; Welcome area with **"Go to Mapping Tool"** (→ Feeder Events) and **"Dump CSV data"** (clears categories, competitions, teams, domain events, event mappings, entity feed mappings; feeds.csv, sports.csv, sport_feed_mappings.csv unchanged).

---

## Toast (from Feeder Events)

- **Triggered by:** Feeder Events → Copy Feed ID.
- **Purpose:** "Feed ID copied to clipboard" (greenish).
- **Behaviour:** `showToast(message, durationMs)`; top-right; auto-dismiss (e.g. 3s).

---

## Modal container (from Feeder Events, Mapping Modal)

| Modal | Opened from | Purpose |
|-------|-------------|---------|
| Mapping Modal | Feeder Events → Action → Map Event | Map feed event to domain (Confirm Mapping / Create & Map). |
| Notes | Feeder Events → Action → Notes | Add/view/edit/delete notes; can trigger notifications. |
| Event Log | Feeder Events → Action → Event Log | Action history (appeared, mapped, note_added, ignored, unignored). |

- **Structure:** Backdrop (click closes); centered panel; content via HTMX.
- **Mapping Modal** closes → Feeder Events table can refresh (MAPPED, green cells).

---

## Page header block

- **Default:** Title (h1) + short description (p) per page. Used by Feeder Events, Event Navigator, Entities, Dashboard.
- **Override:** Event Details page (from Event Navigator) can hide or replace the page header; no breadcrumbs in Phase 1.
- **Per module:**
  - Feeder Events: "Feeder Events" + description.
  - Event Navigator: "Event Navigator" + description.
  - Entities: "Entities" + description.
  - Event Details: custom header (override).

---

## User Journey / Process Flow

**Open backoffice (Phase 1)**  
User opens app → Dashboard → sees stat cards, "Go to Mapping Tool" (Feeder Events), "Dump CSV data".

**Navigate to modules**  
User → Configuration → Entities (entity CRUD); or Betting Program → Feeder Events (map events) or Event Navigator (view domain events).

**Feeder Events → Mapping Modal**  
User on Feeder Events → Action → Map Event → modal opens (Mapping Modal) → Confirm Mapping or Create & Map → modal closes → table refreshes.

**Feeder Events → Toast**  
User → Copy Feed ID → toast "Feed ID copied to clipboard".

**Feeder Events → Notes → Notifications**  
User adds note with "confirm read" → notification created → bell badge shows count → user opens panel → "I've read and understood" → confirmed.

---

## Assumptions / Constraints

- **Phase 1 modules only:** Feeder Events, Event Navigator, Entities, Mapping Modal. Other nav items are placeholders.
- **Single user:** Demo; profile and notifications are simple.
- **Dark theme:** Slate, darkbg.
- **No auth in scope:** Profile is placeholder.
- **HTMX:** Notifications list and modal content use HTMX.

---

## NFRs

- **Consistency:** All Phase 1 module pages use same layout (header, page header, scrollable content).
- **Responsiveness:** Header and dropdowns work on typical desktop widths.
- **Accessibility:** Nav, bell, modals keyboard-accessible where practical.

---

## Reporting / Compliance

- Notifications provide "confirm read" audit for notes. Broader audit is module-specific.

---

## Related specs (Phase 1)

| Module | Spec | What backoffice provides |
|--------|------|--------------------------|
| Feeder Events | modules/feeder-events/ | Nav (Betting Program → Feeder Events), toast, modal container, notifications, page header. |
| Event Navigator | domain-events.md | Nav (Betting Program → Event Navigator), page header; Event Details can override header. |
| Entities | entities.md | Nav (Configuration → Entities), page header. |
| Mapping Modal Tool | mapping-modal-tool.md | Modal container (opened from Feeder Events → Map Event). |
