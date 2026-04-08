# Epic: Entities

**Epic name:** Entities — Manage canonical domain entities (Sports, Categories, Competitions, Teams)

**Summary:**  
Operators need a single place to view and manage canonical domain entities: Sports (read-only), Categories, Competitions, and Teams. The module includes the Entities page under Configuration, entity-type tabs (Sports, Categories, Competitions, Teams), quick-add form for creating categories/competitions/teams, per-tab search and filters, tables with ID, Name, Base ID, Sport/Category/Type, Country, Mapped feeds, Created, Last edited, and row actions (Edit, Remove Mappings placeholder). Edit modal allows updating name, country, base ID, and for teams/competitions: type, amateur, age category. **Markets (market types) are out of scope** for this epic and will be specified separately. (**Country** here is the entity’s country code; **Compliance jurisdiction** on Brands is a separate concept.)

**Goals:**
- View sports, categories, competitions, and teams in separate tabs with counts and type-specific columns.
- Create new categories, competitions, and teams via quick-add form (Sport, Category for competitions, Name, optional Country, Base ID, Feed ID).
- Edit entity name and attributes (country, base ID; teams: type, amateur, age category; competitions: amateur, age category) via Edit modal.
- See which feeds are mapped to each entity (Mapped feeds column); Remove Mappings is a placeholder for later.
- Filter and search within each tab (e.g. by Sport, Amateur, Age category) and clear filters.

**Out of scope for this epic:** Markets (market types, market groups, market mapper, market-type CRUD and feed mapping). Remove Mappings behaviour (button/action can be placeholder). Sport creation from backoffice (sports are created outside).

**Dependencies:** Domain entity CSVs or DB, entity_feed_mappings, sport_feed_mappings, reference data (countries, participant types, underage categories), Mapping Modal (Create & Map flow).
