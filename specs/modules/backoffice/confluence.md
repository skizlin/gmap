# Backoffice — Confluence (shell overview)

**Module:** Backoffice  
**Scope:** Top-level shell that hosts all platform modules: top menu, layout, notifications, profile, dashboard, toast, modal container, page header.

**Phase 1:** See [Phase 1/](Phase%201/) for docs scoped to Feeder Events, Event Navigator, Entities, Mapping Modal only.

---

## Purpose

The backoffice is the **shell** that wraps all modules (Feeder Events, Event Navigator, Configuration, etc.). It provides: navigation menu, notifications panel, profile area, dashboard (landing), toast feedback, modal container, and consistent page header (title + description). Operators use it as the single entry point to access all platform features.

---

## Layout structure

- **Header:** Fixed top bar; logo (left), nav menu (center), notifications + profile (right).  
- **Toast container:** Fixed top-right below header; greenish feedback messages (e.g. "Feed ID copied to clipboard").  
- **Main content:** Page header (title + short description), then scrollable content block.  
- **Modal container:** Full-screen overlay for modals (Mapping, Notes, Event Log, etc.).  

---

## Navigation menu (top bar)

| Item | Type | Links / actions |
|------|------|-----------------|
| Logo (GMP) | Link | Home (/) |
| Admin | Link | Placeholder (e.g. #) |
| Configuration | Dropdown | Entities, Localization, Brands, Feeder, Margin, Risk Rules |
| Betting Program | Dropdown | Event Navigator, Feeder Events, Archived Events |
| Risk | Link | Placeholder |
| Bets/PTLs | Link | Placeholder |
| Alerts | Link | Placeholder |
| Reports | Link | Placeholder |
| Notifications | Icon button | Opens panel with unconfirmed list |
| Profile | Avatar | Placeholder (e.g. "A") |

Active section highlights nav item (e.g. text-primary for current section).

---

## Notifications

| Element | Description |
|---------|-------------|
| Bell icon | Top-right; opens notifications panel. Badge shows count of unconfirmed. Badge hidden when zero. |
| Panel | Dropdown below bell; title "Confirm you read"; list of unconfirmed notifications (HTMX load from /notifications/unconfirmed). |
| Notification card | Amber styling; message snippet; timestamp; button "I've read and understood". |
| Confirm | POST to /api/notifications/{id}/confirm; list refreshes; badge updates. |
| Triggers | Load on open; also on notificationAdded / notificationsRefresh (e.g. when user adds a note with "confirm read"). |

---

## Profile

- **Avatar:** Circular badge with initial (e.g. "A"); top-right.  
- **Behaviour:** Placeholder for now; future: profile menu, logout, settings.  

---

## Dashboard (landing page)

- **Route:** `/` (home).  
- **Page title:** Dashboard.  
- **Description:** Overview of incoming events, mapping coverage and platform status.  
- **Content:** Stat cards (Incoming Events, Mapped Successfully, Pending Action); Application stack; Welcome area with "Go to Mapping Tool" (Feeder Events) and "Dump CSV data" (clears backoffice-managed CSVs; developer-controlled files unchanged).  

---

## Toast

- **Location:** Fixed top-right, below header.  
- **Purpose:** Short-lived feedback (e.g. "Feed ID copied to clipboard").  
- **Behaviour:** `showToast(message, durationMs)`; greenish styling; auto-dismiss (e.g. 3s).  

---

## Modal container

- **Structure:** Backdrop (click closes); centered panel; content loaded via HTMX.  
- **Use:** Mapping Modal, Notes modal, Event Log modal, etc.  
- **Close:** Click backdrop or close button (module-specific).  

---

## Page header block

- **Default:** Title (h1) + short description (p) per page.  
- **Override:** Modules can override `page_header` block (e.g. Event Details page hides it).  
- **No breadcrumbs** except where explicitly added (e.g. Event Details).  

---

## User Journey / Process Flow

**Open backoffice**  
User opens app → lands on Dashboard → sees stat cards, welcome message, links to Feeder Events and Dump CSV.

**Navigate**  
User clicks Configuration or Betting Program → dropdown opens → user selects module (e.g. Feeder Events) → navigates to module page; page header shows title + description.

**Notifications**  
User sees badge on bell → clicks bell → panel opens with unconfirmed list → user reads message → clicks "I've read and understood" → notification confirmed; list refreshes; badge updates.

**Toast**  
Module triggers toast (e.g. Copy Feed ID) → greenish message appears top-right → auto-dismisses after a few seconds.

**Modal**  
User triggers action that opens modal (e.g. Map Event) → modal overlay appears → content loaded → user completes or cancels → modal closes; table may refresh.

---

## Assumptions / Constraints

- **Single user / session:** Demo assumes one user; profile and notifications are simple. Production may add auth, roles, per-user notifications.  
- **Dark theme:** UI uses dark theme (slate, darkbg).  
- **No auth in scope:** Login, logout, session management are out of scope for this shell spec; profile is placeholder.  
- **HTMX for partials:** Notifications list and modal content use HTMX; layout provides containers and triggers.  

---

## NFRs

- **Consistency:** All module pages use the same layout (header, page header block, scrollable content).  
- **Responsiveness:** Header and dropdowns should work on typical desktop widths; mobile layout may be addressed later.  
- **Accessibility:** Nav items, bell, and modals should be keyboard-accessible where practical.  

---

## Reporting / Compliance

- No specific reporting or compliance requirements for the backoffice shell itself. Notifications provide a "confirm read" audit per user; broader audit is module-specific (e.g. Event Navigator, Mapping Modal).  

---

## Related specs

- Feeder Events, Event Navigator, Archived Events — Betting Program modules.  
- Entities, Localization, Brands, Feeder, Margin, Risk Rules — Configuration modules.  
- Mapping Modal, Notes — use modal container; notes can trigger notifications.  
