# Entities — User Stories

Stories use **As a Product Owner** and **Given/When/Then** in Acceptance Criteria. Small scope; minimal AC per story. **Markets are out of scope** — no stories for market types, market mapper, or market CRUD here.

---

## Page and navigation

**ENT-1**  
As a Product Owner, I can open the Entities page from the Configuration menu so that I see the page title and description.  
- **AC:** Given I am on the app, When I open Configuration → Entities, Then I see the heading "Entities" and the description for managing canonical domain entities (categories, competitions, teams; sports created outside backoffice).

**ENT-2**  
As a Product Owner, I see entity type tabs (Sports, Categories, Competitions, Teams) so that I can switch between entity lists.  
- **AC:** Given I am on Entities, When the page has loaded, Then I see tabs for Sports, Categories, Competitions, and Teams, each with a count badge (e.g. number of items).

**ENT-3**  
As a Product Owner, I can switch to the Categories, Competitions, or Teams tab so that I see the corresponding table and filters.  
- **AC:** Given I am on Entities, When I click the Categories (or Competitions, or Teams) tab, Then the active tab is highlighted and I see that entity type's table and filter bar.

---

## Sports tab

**ENT-4**  
As a Product Owner, I see the Sports tab by default so that I can view sports first.  
- **AC:** Given I open the Entities page, When the page loads, Then the Sports tab is active and I see the sports table.

**ENT-5**  
As a Product Owner, I see sports table columns (ID, Name, Base ID, Mapped feeds, Created, Last edited, Actions) so that I can identify and manage sports.  
- **AC:** Given I am on the Sports tab, When I look at the table, Then I see columns for ID, Name, Base ID, Mapped feeds, Created, Last edited, and Actions (kebab).

**ENT-6**  
As a Product Owner, I can search sports by name or other visible fields so that I find a sport quickly.  
- **AC:** Given I am on the Sports tab, When I type in the Search box, Then the table shows only rows whose name, base ID, or mapped feed info match the search text (client-side filter).

**ENT-7**  
As a Product Owner, I can edit a sport's name and base ID from the action menu so that I correct or complete sport data.  
- **AC:** Given I am on the Sports tab, When I click the kebab on a row and choose Edit, Then an Edit modal opens with Name and Base ID (optional); I can save and the table reflects the change (e.g. after reload). Sports are not created from this page.

---

## Categories tab

**ENT-8**  
As a Product Owner, I see a Categories table with columns (ID, Name, Base ID, Sport, Jurisdiction, Mapped feeds, Created, Last edited, Actions) so that I can manage categories.  
- **AC:** Given I am on the Categories tab, When I look at the table, Then I see the listed columns and a "New Category" button.

**ENT-9**  
As a Product Owner, I can filter categories by sport so that I see only categories for that sport.  
- **AC:** Given I am on the Categories tab, When I select a sport in the Sport dropdown, Then the table shows only categories for that sport. I can clear the filter with Clear.

**ENT-10**  
As a Product Owner, I can search categories so that I find one by name or related data.  
- **AC:** Given I am on the Categories tab, When I type in the Search box, Then the table filters to rows matching the search text (e.g. name, sport, feed refs).

**ENT-11**  
As a Product Owner, I can create a new category via the quick-add form so that I add categories without leaving the page.  
- **AC:** Given I am on the Categories tab, When I click "New Category", Then a form appears with Type (Category), Sport (required), optional Jurisdiction, Base ID, Name, Feed ID. When I fill Name and Sport and click Create, Then the category is created and I see feedback (e.g. "Created #id" or "Already exists #id"); form hides or page reloads.

**ENT-12**  
As a Product Owner, I can edit a category's name, country, and base ID from the action menu so that I keep data correct.  
- **AC:** Given I am on the Categories tab, When I click the kebab on a category row and choose Edit, Then the Edit modal opens with Name, Jurisdiction, and Base ID. When I save, Then the category is updated and the modal closes.

**ENT-13**  
As a Product Owner, I see which feeds are mapped to each category in the Mapped feeds column so that I know linkage to feeds.  
- **AC:** Given I am on the Categories tab, When I look at a row, Then the Mapped feeds column shows badges per (feed, feed_id) or "No feeds mapped" when none.

---

## Competitions tab

**ENT-14**  
As a Product Owner, I see a Competitions table with columns (ID, Name, Base ID, Sport, Category, Amateur, Age category, Jurisdiction, Mapped feeds, Created, Last edited, Actions) so that I can manage competitions.  
- **AC:** Given I am on the Competitions tab, When I look at the table, Then I see the listed columns and a "New Competition" button.

**ENT-15**  
As a Product Owner, I can filter competitions by sport, amateur, and age category so that I narrow the list.  
- **AC:** Given I am on the Competitions tab, When I select Sport and/or Amateur and/or Age category, Then the table shows only matching competitions. I can clear with Clear.

**ENT-16**  
As a Product Owner, I can create a new competition via the quick-add form so that I add competitions with sport and category.  
- **AC:** Given I am on the Competitions tab, When I click "New Competition", Then a form appears with Type Competition, Sport, Category (required), optional Jurisdiction, Base ID, Name, Feed ID. When I fill required fields and click Create, Then the competition is created and I see feedback.

**ENT-17**  
As a Product Owner, I can edit a competition's name, country, base ID, amateur, and age category from the action menu so that I keep competition data correct.  
- **AC:** Given I am on the Competitions tab, When I click the kebab and choose Edit, Then the Edit modal shows Name, Jurisdiction, Base ID, Amateur (checkbox), Age category. When I save, Then the competition is updated.

---

## Teams tab

**ENT-18**  
As a Product Owner, I see a Teams table with columns (ID, Name, Base ID, Sport, Type, Amateur, Age category, Jurisdiction, Mapped feeds, Created, Last edited, Actions) so that I can manage teams.  
- **AC:** Given I am on the Teams tab, When I look at the table, Then I see the listed columns and a "New Team" button.

**ENT-19**  
As a Product Owner, I can filter teams by sport, type (participant type), amateur, and age category so that I narrow the list.  
- **AC:** Given I am on the Teams tab, When I select Sport and/or Type and/or Amateur and/or Age category, Then the table shows only matching teams. I can clear with Clear.

**ENT-20**  
As a Product Owner, I can create a new team via the quick-add form so that I add teams with sport.  
- **AC:** Given I am on the Teams tab, When I click "New Team", Then a form appears with Type Team, Sport (required), optional Jurisdiction, Base ID, Name, Feed ID. When I fill Name and Sport and click Create, Then the team is created and I see feedback.

**ENT-21**  
As a Product Owner, I can edit a team's name, country, base ID, type (participant type), amateur, and age category from the action menu so that I keep team data correct.  
- **AC:** Given I am on the Teams tab, When I click the kebab and choose Edit, Then the Edit modal shows Name, Jurisdiction, Base ID, Type (participant type), Amateur, Age category. When I save, Then the team is updated.

---

## Quick-add form (shared)

**ENT-22**  
As a Product Owner, the quick-add form shows only fields relevant to the selected entity type so that I am not confused by market or sport-only fields.  
- **AC:** Given the quick-add form is open, When I select Type Category, Then I see Sport, Jurisdiction, Base ID, Name, Feed ID (no Category dropdown). When I select Type Competition, Then I also see Category. When I select Type Team, Then I see Sport, Jurisdiction, Base ID, Name, Feed ID (no Category). Market-specific fields are not in scope.

**ENT-23**  
As a Product Owner, I can cancel the quick-add form so that I close it without creating an entity.  
- **AC:** Given the quick-add form is visible, When I click Cancel, Then the form hides and no entity is created.

---

## Action menu and Edit modal

**ENT-24**  
As a Product Owner, I can open the row action menu (kebab) so that I can Edit or Remove Mappings.  
- **AC:** Given I am viewing any entity table (Sports, Categories, Competitions, Teams), When I click the kebab on a row, Then a menu opens with at least Edit; for non-sports, Remove Mappings may be present (placeholder allowed).

**ENT-25**  
As a Product Owner, the Edit modal validates that name is required so that I cannot save an empty name.  
- **AC:** Given the Edit modal is open, When I clear the Name field and click Save, Then I see a validation message (e.g. "Name is required") and the entity is not updated.

**ENT-26**  
As a Product Owner, I can close the Edit modal without saving so that I discard changes.  
- **AC:** Given the Edit modal is open, When I click Cancel (or close), Then the modal closes and no changes are saved.

---

## Data and consistency

**ENT-27**  
As a Product Owner, after I create or edit an entity the list reflects the change so that I see up-to-date data.  
- **AC:** Given I have just created or edited an entity, When the form or modal completes (e.g. page reload or partial refresh), Then the table shows the new or updated entity (name, country, etc.).

**ENT-28**  
As a Product Owner, category options in the quick-add form depend on the selected sport when creating a competition so that I pick a valid category.  
- **AC:** Given the quick-add form is open with Type = Competition, When I select a Sport, Then the Category dropdown shows only categories for that sport.

---

## Out of scope (explicit)

**Markets:** No user stories in this document cover Market types, Market tab behaviour, market type CRUD, market groups, market mapper (mapping domain market type to feed markets), or Edit Market Type. Those will be specified in a separate Markets module/epic.
