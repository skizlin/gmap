# Epic: Backoffice Phase 1 Shell

**Epic name:** Backoffice Phase 1 — Shell for Feeder Events, Event Navigator, Entities, Mapping Modal

**Summary:**  
Phase 1 backoffice shell supports only the 4 modules with specs: Feeder Events, Event Navigator (Domain Events), Entities, Mapping Modal Tool. It provides: navigation (Configuration → Entities; Betting Program → Event Navigator, Feeder Events, Archived Events), notifications panel (for Feeder Events notes with "confirm read"), profile placeholder, dashboard (landing with link to Feeder Events and Dump CSV), toast (for Copy Feed ID), modal container (Mapping Modal, Notes, Event Log), and page header block (title + description; Event Details can override). Everything required by those 4 modules from the backoffice is in scope.

**Goals:**
- Host Feeder Events, Event Navigator, Entities; open Mapping Modal from Feeder Events.
- Provide notifications flow for "confirm read" notes.
- Provide toast and modal container for module use.
- Provide consistent page header; allow override for Event Details.

**Out of scope for Phase 1:** Other Configuration items (Localization, Brands, Feeder, Margin, Risk Rules), Admin, Risk, Bets/PTLs, Alerts, Reports (placeholders only). Auth, full profile menu.

**Dependencies:** Feeder Events, Event Navigator, Entities, Mapping Modal specs.
