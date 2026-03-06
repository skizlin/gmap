# Epic: Feeder Events

**Epic name:** Feeder Events — View, filter, and map feed events

**Summary:**  
Operators need a single place to see raw events from each feed provider, filter by sport/category/competition/status, see mapping status (Mapped / Unmapped / Ignored), and map feed events to domain events. The module includes the Feeder Events page, filters, table with green highlighting, action menu (Map Event, Copy Feed ID, Event Log, Ignore, Notes), bulk select, and placeholder Bulk Update.

**Goals:**
- View feed events for a selected feed with clear mapping status.
- Filter by date, feed, sport, category, competition, status, live/notes toggles, mapping status, outright, and search.
- Map feed events to domain events via Mapping Modal; ignore unwanted events without deleting data.
- Copy feed ID to clipboard; view event action log; (later) notes and bulk update.

**Out of scope for initial:** Full notes workflow and “confirm read” notifications; Bulk Update behaviour (button present, disabled).

**Dependencies:** Mapping Modal, Event Navigator, Entities (entity_feed_mappings, sport_feed_mappings), feed data source (mock or API).
