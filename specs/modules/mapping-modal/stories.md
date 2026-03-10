# Mapping Modal — User Stories

Stories use **As a Product Owner** and **Given/When/Then** in Acceptance Criteria. Small scope; minimal AC per story.

---

## Entry and header

**MM-1**  
As a Product Owner, I can open the Mapping Modal from a feed event so that I see the feed and event context.  
- **AC:** Given I am on Feeder Events with a feed selected, When I click Action → Map Event on a row, Then a modal opens showing the feed name (e.g. BET365), Feed ID (e.g. #189135832), and event label (Home vs Away or Outright).

**MM-2**  
As a Product Owner, I can close the modal without saving so that I cancel the mapping flow.  
- **AC:** Given the Mapping Modal is open, When I click the close (X) button or Cancel, Then the modal closes and no mapping is created or updated.

---

## Layout and sport

**MM-3**  
As a Product Owner, I see a 3-column grid (Source Feed, Field, Domain Event) so that I compare feed values to domain values.  
- **AC:** Given the modal is open, When I look at the content, Then I see columns for Source Feed (feed values), Field (labels), and Domain Event (resolved or editable domain values) for Sport, Category, Competition, Home Team, Away Team, Start Time.

**MM-4**  
As a Product Owner, I see sport resolved when it is already mapped for this feed so that I know I cannot change it in the modal.  
- **AC:** Given the feed event's sport is mapped (sport_feed_mappings / entity_feed_mappings), When the modal opens, Then the Domain Event column for Sport shows the domain sport name and "ID &lt;domain_id&gt;" (Name ID format) and a Matched badge; no editable control.

**MM-5**  
As a Product Owner, I see a message when sport is not mapped so that I know the event cannot be mapped until a developer maps sport.  
- **AC:** Given the feed event's sport is not mapped, When the modal opens, Then the Domain Event column for Sport shows a message that sport must be mapped by developer; Category/Competition/Teams are disabled or not usable until sport is mapped.

---

## Category

**MM-6**  
As a Product Owner, I see category resolved when it is already mapped for this feed so that I can still edit the category name/country if needed.  
- **AC:** Given the feed event's category is mapped for this feed, When the modal opens, Then the Domain Event column shows the domain category name and ID and Matched badge; the category textbox remains editable (e.g. for country/name).

**MM-7**  
As a Product Owner, I see category suggestions only when match is at least 55% so that I am not shown wrong domain categories.  
- **AC:** Given the feed has category "Barbados" and domain has "Argentina", When the modal opens, Then the domain side suggests Barbados (or Create), not Argentina at 100%. Domain category suggestions (Map) appear only when fuzzy match ≥ 55%.

**MM-8**  
As a Product Owner, I can select a jurisdiction (country) and type or search category so that I create or map a category.  
- **AC:** Given I am on the Category row and sport is resolved, When I select a country in the Jurisdiction dropdown and type in the category input, Then I can select an existing domain category (Map) or create a new one (Create). Dropdowns and labels use "Name ID 123" format.

---

## Competition and teams

**MM-9**  
As a Product Owner, I see competition resolved when it is already mapped for this feed so that I do not have to search again.  
- **AC:** Given the feed event's competition is mapped for this feed, When the modal opens, Then the Domain Event column for Competition shows the domain competition name and ID and Matched badge.

**MM-10**  
As a Product Owner, I can search or select a domain competition when not resolved so that I Map or Create.  
- **AC:** Given the competition is not resolved and sport (and category) are set, When I type in the competition field or select from the list, Then I can choose an existing competition (Map) or create a new one (Create). Competitions are filtered by sport and category.

**MM-11**  
As a Product Owner, I see home and away resolved when already mapped for this feed so that I do not have to search again.  
- **AC:** Given the feed event's home (or away) team is mapped for this feed, When the modal opens, Then the Domain Event column for that team shows the domain team name and ID and Matched badge.

**MM-12**  
As a Product Owner, I can search or select domain home and away teams when not resolved so that I Map or Create.  
- **AC:** Given home (or away) is not resolved and sport is set, When I type in the team field or select from the list, Then I can choose an existing team (Map) or create a new one (Create). Teams are filtered by sport.

---

## Find existing domain event and Confirm Mapping

**MM-13**  
As a Product Owner, I see suggested domain events (fuzzy match ≥ 50%) so that I can pick an existing domain event quickly.  
- **AC:** Given the modal is open, When there are domain events matching this feed event (normal or reversed home/away) with score ≥ 50%, Then I see them as cards with id, start time, category, competition, match %.

**MM-14**  
As a Product Owner, I can search for more domain events so that I find the correct one when not in suggestions.  
- **AC:** Given the modal is open, When I type in the search box for domain events, Then I see a list of matching domain events and can select one.

**MM-15**  
As a Product Owner, I can confirm mapping to a selected domain event so that the feed event is linked without creating a new domain event.  
- **AC:** Given I have selected a domain event (from suggestions or search), When I click Confirm Mapping, Then the system writes one row to event_mappings.csv and marks the feeder event MAPPED; I see a success message (e.g. "Feed Mapped!").

---

## Create & Map

**MM-16**  
As a Product Owner, I can create a new domain event and map the feed event so that I do not need to leave the flow.  
- **AC:** Given I have resolved Competition and both Home and Away (or outright path), When I click Create & Map, Then the system creates a new domain event (domain_events.csv), one event_mappings row, and marks the feeder event MAPPED; I see a success message with the new domain event id (e.g. G-XXXXXXXX).

**MM-17**  
As a Product Owner, the Create & Map button is available whenever competition and teams are resolved so that I can always create a new event if I choose.  
- **AC:** Given I have resolved Competition and both Home and Away, When I look at the footer, Then the Create & Map button is enabled and I can click it even when all entities are already matched (not disabled when "all matched").

**MM-18**  
As a Product Owner, I see a clear error when Create & Map request fails so that I know what went wrong.  
- **AC:** Given I click Create & Map and the server returns an error (e.g. 422 or 500), When the response is received, Then the modal content shows an error message (not raw JSON); I can correct and retry or close.

---

## Display and consistency

**MM-19**  
As a Product Owner, I see domain entities in "Name ID 123" format so that naming is consistent.  
- **AC:** Given the modal shows domain entities (sport, category, competition, teams) or dropdown options, When I look at labels and selections, Then they use the format "Name ID &lt;id&gt;" (name before ID), not "#&lt;id&gt; Name".

**MM-20**  
As a Product Owner, I see start time from the feed and can edit it for Create & Map so that the new domain event has the correct time.  
- **AC:** Given the modal is open, When I look at the Start Time row, Then I see the feed start time in the Domain Event column and can edit it; it is included in the Create & Map payload.

---

## Out of scope (explicit)

**Sport creation:** No story for creating sport in the modal; sports are mapped by developer.  
**Unmap:** No story for removing a mapping; define separately if required.  
**Market mapping, Margin, Feeder Configuration:** Other modules.  
**Reverse Home/Away checkbox:** Future enhancement; suggestion logic may already detect reversed matches.
