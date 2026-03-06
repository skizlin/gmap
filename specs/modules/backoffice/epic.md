# Epic: Backoffice Shell

**Epic name:** Backoffice — Top menu, layout, notifications, profile, dashboard

**Summary:**  
The backoffice shell wraps all platform modules. Operators need a consistent top menu (logo, Admin, Configuration, Betting Program, Risk, Bets/PTLs, Alerts, Reports), notifications panel (bell icon, unconfirmed list, confirm read), profile area, dashboard (landing page with stat cards and links), toast feedback, modal container, and page header block (title + description). The shell hosts module pages (Feeder Events, Event Navigator, Configuration pages) without duplicating layout logic.

**Goals:**
- Provide a single entry point for all platform features via top navigation.
- Show notifications (unconfirmed list) with "confirm read" flow.
- Provide dashboard with overview and quick links to Feeder Events and Dump CSV.
- Provide toast feedback and modal container for module use.
- Ensure consistent page header (title + description) across modules.

**Out of scope for initial:** Auth (login/logout), profile menu, full profile/settings. Profile avatar is placeholder.

**Dependencies:** Feeder Events, Event Navigator, Configuration modules; Mapping Modal; platform notes/notifications.
