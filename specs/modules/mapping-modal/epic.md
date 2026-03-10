# Epic: Mapping Modal

**Epic name:** Mapping Modal — Link feed events to domain events (Confirm Mapping or Create & Map)

**Summary:**  
Operators need a single flow to map a feed event to the domain: either confirm a link to an existing domain event (from suggestions or search) or create a new domain event and link. The modal shows a 3-column grid (Source Feed, Field, Domain Event), per-entity resolution for sport, category, competition, home, and away with **Map** or **Create** per entity, 55% fuzzy threshold for domain suggestions, "Name ID 123" format on domain side, and **Create & Map** always enabled when competition and teams are resolved. Persistence: domain_events.csv, event_mappings.csv, entity CSVs, entity_feed_mappings.

**Goals:**
- Open the modal from Feeder Events → Map Event and see feed event header and suggested domain events (fuzzy ≥ 50%, normal + reversed home/away).
- Confirm Mapping: select a suggested or searched domain event → one row in event_mappings.csv; feeder event MAPPED.
- Resolve sport (read-only when mapped), category (editable textbox, country dropdown, Map/Create), competition and teams (search/select or Create); see match % when ≥ 55%.
- Create & Map: submit new domain event + mapping; success screen; no disable when all entities matched.
- Consistent domain display (Name ID 123); clear errors on failed request.

**Out of scope for this epic:** Sport creation in modal; unmap/delete mapping; market-level mapping; margin configuration. Reverse Home/Away checkbox is a future enhancement.

**Dependencies:** Feeder Events (entry), Event Navigator, Entities (entity_feed_mappings, sport_feed_mappings), domain_events, event_mappings, feed event payload.
