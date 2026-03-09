# Entities — Confluence (module overview)

**Module:** Entities  
**Page:** Configuration → Entities

---

## Purpose

Manage **canonical domain entities** used across the platform: Sports (read-only in backoffice), Categories, Competitions, and Teams. Operators view entity lists by type, create new categories/competitions/teams (with optional feed ID and jurisdiction), edit name and other attributes, and see which feeds are mapped to each entity. Entity–feed mappings drive green highlighting in Feeder Events and Event Navigator. **Markets (market types) are out of scope** for this spec and will be covered separately.

---

## Page and layout

- **Page title:** Entities  
- **Description:** Manage canonical domain entities: categories, competitions, teams and markets. Sports are created outside backoffice and mapped in entity feed mappings.  
- **Quick-add form:** Collapsible; Type (Category, Competition, Team), Sport, Category (for competitions only), Jurisdiction, Base ID (optional), Name, Feed ID (blank = use name), Create / Cancel. Shown when "New Category" / "New Competition" / "New Team" is clicked or toggled.  
- **Entity type tabs:** Sports | Categories | Competitions | Teams. Each tab shows a count badge. (Markets tab exists in UI but is out of scope for this spec.)  
- **Per-tab panel:** Search box, type-specific filters (e.g. Sport, Amateur, Age category), Clear, "Showing all X" or "Showing N of M X", and for Categories/Competitions/Teams a "New …" button. Table with type-specific columns and row actions (kebab).  
- **Edit modal:** Edit Name (and for categories/competitions/teams: Jurisdiction; for sports/categories/competitions/teams: Base ID; for teams: Type, Amateur, Age category; for competitions: Amateur, Age category). Save / Cancel.

---

## Sports tab

- **Purpose:** View sports; sports are **not created** from backoffice (they are added in code/data).  
- **Filters:** Search only (client-side filter on name, base ID, mapped feed refs).  
- **Table columns:** ID, Name, Base ID, Mapped feeds, Created, Last edited, Actions.  
- **Actions (kebab):** Edit (name, base ID only). Remove Mappings and Map are not shown for sports in the same way as for other types (sport mappings are developer-controlled).  
- **No "New Sport"** — creation is out of scope for backoffice.

---

## Categories tab

- **Filters:** Search, Sport (dropdown), Clear. "New Category" button.  
- **Table columns:** ID, Name, Base ID, Sport, Jurisdiction, Mapped feeds, Created, Last edited, Actions.  
- **Quick-add / Create:** Type Category, Sport (required), Jurisdiction (optional), Base ID (optional), Name, Feed ID (optional; blank = use name). Creates category and optionally links the current feed to it (when created from Mapping Modal context) or just creates the entity.  
- **Actions (kebab):** Edit (name, jurisdiction, base ID), Remove Mappings (placeholder).

---

## Competitions tab

- **Filters:** Search, Sport, Amateur, Age category, Clear. "New Competition" button.  
- **Table columns:** ID, Name, Base ID, Sport, Category, Amateur, Age category, Jurisdiction, Mapped feeds, Created, Last edited, Actions.  
- **Quick-add / Create:** Type Competition, Sport (required), Category (required), Jurisdiction (optional), Base ID (optional), Name, Feed ID (optional).  
- **Actions (kebab):** Edit (name, jurisdiction, base ID, is_amateur, underage_category_id), Remove Mappings (placeholder).

---

## Teams tab

- **Filters:** Search, Sport, Type (participant type), Amateur, Age category, Clear. "New Team" button.  
- **Table columns:** ID, Name, Base ID, Sport, Type, Amateur, Age category, Jurisdiction, Mapped feeds, Created, Last edited, Actions.  
- **Quick-add / Create:** Type Team, Sport (required), Jurisdiction (optional), Base ID (optional), Name, Feed ID (optional).  
- **Actions (kebab):** Edit (name, jurisdiction, base ID, participant_type_id, is_amateur, underage_category_id), Remove Mappings (placeholder).

---

## Quick-add form (new entity)

- **Visibility:** Hidden by default; shown when user clicks "New Category", "New Competition", or "New Team", or toggles the form open.  
- **Type:** Dropdown — Category, Competition, Team. (Market is out of scope.)  
- **Sport:** Required for Category, Competition, Team; dropdown of existing sports.  
- **Category:** Shown only when Type = Competition; dropdown of categories for selected sport.  
- **Jurisdiction:** Optional; dropdown of countries (e.g. by country code).  
- **Base ID:** Optional (from previous platform); text input.  
- **Code:** Shown only for Market (out of scope).  
- **Name:** Required; text input.  
- **Feed ID:** Optional; blank = use name as feed_id when linking.  
- **Create:** POST to API; on success, "Created #domain_id" or "Already exists #domain_id"; page may reload. **Cancel:** Hides form.

---

## Action menu (kebab) — Sports, Categories, Competitions, Teams

| Action | Description | Visible for |
|--------|--------------|--------------|
| Edit | Opens Edit modal (name, jurisdiction, base ID; teams/competitions: type, amateur, age category). | All entity types. |
| Remove Mappings | Placeholder; removes feed mappings for this entity (to be implemented). | Categories, Competitions, Teams. Not shown for Sports in some implementations. |
| Map | Map entity to feed markets (market types only). | **Markets only — out of scope.** |
| Active/Inactive | Placeholder; toggle active state. | **Markets only — out of scope.** |

For **Sports, Categories, Competitions, Teams** the kebab shows **Edit** and **Remove Mappings** (Remove Mappings may be placeholder). Map and Active/Inactive are for market types only.

---

## Edit modal

- **Title:** "Edit Sport" / "Edit Category" / "Edit Competition" / "Edit Team".  
- **Fields:**  
  - **Name** (required) for all.  
  - **Jurisdiction** (dropdown) for Categories, Competitions, Teams.  
  - **Base ID** (optional) for Sports, Categories, Competitions, Teams.  
  - **Type** (participant type dropdown) for Teams only.  
  - **Amateur** (checkbox) for Teams and Competitions.  
  - **Age category** (dropdown) for Teams and Competitions.  
- **Save:** POST to `/api/entities/name` (or equivalent) with entity_type, domain_id, name, and optional jurisdiction, baseid, participant_type_id, is_amateur, underage_category_id. On success, modal closes and page may reload.  
- **Cancel:** Closes modal.

---

## Business rules

- **Sports:** Created and maintained outside backoffice (e.g. in code or reference data). Sport–feed mappings are in `sport_feed_mappings.csv` (developer-controlled). Entities page only allows editing name and base ID for display.  
- **Categories:** Belong to a sport. Created via quick-add or from Mapping Modal. Entity_feed_mappings link (entity_type=categories, domain_id, feed_provider_id, feed_id).  
- **Competitions:** Belong to a sport and a category. Created via quick-add or Mapping Modal. Amateur and age category are optional attributes.  
- **Teams:** Belong to a sport. Optional: participant type, amateur, age category, jurisdiction.  
- **Mapped feeds column:** Shows badges per (feed_provider, feed_id) from entity_feed_mappings for that entity. "No feeds mapped" when empty.  
- **Deduplication:** Creating an entity with same name (and sport, and category for competitions) may link the feed to an existing entity instead of creating a duplicate (idempotent behaviour).

---

## User journey / process flow

**Open and switch tabs**  
User opens Configuration → Entities → sees Sports tab by default; can switch to Categories, Competitions, or Teams. Each tab shows a table and type-specific filters.

**Create category**  
User goes to Categories → "New Category" → quick-add form appears → selects Sport, optionally Jurisdiction, Base ID, enters Name and optional Feed ID → Create → entity created (and optionally feed linked); form hides or page reloads.

**Create competition**  
User goes to Competitions → "New Competition" → form → Sport, Category, optional Jurisdiction/Base ID, Name, Feed ID → Create.

**Create team**  
User goes to Teams → "New Team" → form → Sport, optional Jurisdiction/Base ID, Name, Feed ID → Create.

**Edit entity**  
User clicks kebab on a row → Edit → Edit modal opens with current name, jurisdiction, base ID (and for teams: type, amateur, age category; for competitions: amateur, age category) → user changes fields → Save → modal closes; table reflects change (e.g. after reload).

**Filter and search**  
User selects Sport (or Amateur, Age category on Competitions/Teams) and/or types in Search → table shows only matching rows; "Showing N of M categories" (or equivalent). Clear resets filters.

---

## Assumptions / constraints

- **Markets:** Market types, market groups, market mapper, and market-type–feed mappings are **out of scope** for this spec. The Entities page may show a Markets tab in the UI; behaviour and specs for Markets will be defined separately.  
- **Sports:** No creation from UI; sport_feed_mappings are not editable from this page (developer-controlled).  
- **Entity feed mappings:** Stored in entity_feed_mappings.csv (and sport_feed_mappings.csv for sports). Creating an entity from the Mapping Modal can add a mapping in the same flow.  
- **Reference data:** Countries (jurisdiction), participant types, underage categories are loaded from configuration/countries and related CSVs.

---

## NFRs

- **Performance:** Tables and filters should remain responsive for hundreds of entities per type. Search and filters can be client-side for demo; production may use server-side.  
- **Consistency:** After Create or Edit, the list (or refreshed fragment) should show the new/updated entity; full page reload is acceptable for initial version.  
- **Accessibility:** Tabs, form controls, and table should be keyboard-navigable; labels and aria where applicable.

---

## Data and tech (demo site)

| Area | Demo implementation | Production note |
|------|---------------------|-----------------|
| Sports | sports.csv; read-only in backoffice. | Reference table; created outside backoffice. |
| Categories | categories.csv (domain_id, name, sport_id, jurisdiction, baseid, created_at, updated_at). | Same logical model. |
| Competitions | competitions.csv (+ category_id, is_amateur, underage_category_id). | Same. |
| Teams | teams.csv (+ participant_type_id, is_amateur, underage_category_id). | Same. |
| Entity feed mappings | entity_feed_mappings.csv (entity_type, entity_id, feed_provider_id, feed_id, domain_name). Sport mappings in sport_feed_mappings.csv. | Tables; sport mappings may be config. |
| Create entity | POST /api/entities (entity_type, name, sport, category, jurisdiction, feed_id, baseid, etc.). | Same API shape. |
| Update entity | POST /api/entities/name (entity_type, domain_id, name, jurisdiction, baseid, …). | Or PATCH per resource. |

---

## Out of scope for this spec (still part of module or platform)

- **Markets:** Market types tab, market type CRUD, market groups, templates, period/score/side types, market mapper (map domain market type to feed markets), Edit Market Type modal, Active/Inactive. All market-related behaviour is out of scope here.  
- **Remove Mappings:** Action is present in kebab; full behaviour (removing entity_feed_mappings for the entity) to be implemented later.  
- **Active/Inactive:** For non-market entities, not in scope; for markets, see Markets spec.

---

## Related specs

- **Feeder Events** — Uses entity_feed_mappings for green highlighting; Mapping Modal creates/links entities.  
- **Event Navigator** — Uses domain entities and mappings.  
- **Mapping Modal** — Create & Map flow; creates categories, competitions, teams and links feeds.  
- **Markets (separate spec)** — Market types, market groups, market mapper, feed market mapping.
