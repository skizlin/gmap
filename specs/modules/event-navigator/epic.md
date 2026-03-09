# Epic: Event Navigator

**Epic name:** Event Navigator — View, filter, and manage canonical (domain) events

**Summary:**  
Operators need a single place to see canonical (domain) events — the golden copy built from mapped feed data. The module includes the Event Navigator page, filters (Period, Sport, Category, Competition, Status, Live, Has Bets, Notes, Outright, Search, Brand), table with columns Id through Action, screen-only notes per event (with optional IMPORTANT/confirm-read notification), and action menu (View Event, Edit, Close, Notes, etc.), footer with Bulk Update (placeholder) and Previous/Next pagination (placeholder; target 20 per page). Brand filter uses “Global” by default; Global cannot be combined with other brands.

**Goals:**
- View domain events with mapped feed count (#FEED), start time, sport, category, competition, event label, and action menu.
- Filter by period (preset dropdown, presentation only initially), sport, category, competition, status, live, has bets, notes, outright, search, and brand (Global exclusive).
- Add or edit a screen-only note per domain event; optionally mark note as IMPORTANT to trigger a platform notification until users confirm.
- Open Event Details from the Event cell; use action menu for View Event, Notes, and placeholder actions (Edit, Close, Abandon, etc.).

**Out of scope for initial:** Backend filtering by period, has bets, live, notes, outright, brand; full behaviour for action menu items other than View Event and Notes; Bulk Update behaviour (button present, disabled); pagination and page size (e.g. 20 per page) — Previous/Next present but disabled.

**Dependencies:** Domain events store, event mappings, Feeder Events (mapping flow), Entities (sports, categories, competitions), brands list, platform notifications (for IMPORTANT notes).
