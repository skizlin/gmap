# Feeder Events — User Stories

Stories use **As a Product Owner** and **Given/When/Then** in Acceptance Criteria. Small scope; minimal AC per story.

---

## Page and navigation

**FE-1**  
As a Product Owner, I can open the Feeder Events page from the Betting Program menu so that I see the page title and short description.  
- **AC:** Given I am on the app, When I open Betting Program → Feeder Events, Then I see the heading "Feeder Events" and the description text for incoming events from feed providers.

**FE-2**  
As a Product Owner, I see a filter bar at the top so that I can narrow the list.  
- **AC:** Given I am on Feeder Events, When the page has loaded, Then I see a filter bar with at least Feed, Sport, Category, Competition, and a search area.

**FE-3**  
As a Product Owner, I see a table of events and a footer with “Showing X events” so that I know how many events match.  
- **AC:** Given I am on Feeder Events with a feed selected, When the table has loaded, Then I see a row count message (e.g. “Showing N events”) in the footer.

---

## Feed and date

**FE-4**  
As a Product Owner, I can select a single feed so that the table shows only that feed’s events.  
- **AC:** Given I am on Feeder Events, When I change the Feed dropdown, Then the table refreshes and shows only events for the selected feed.

**FE-5**  
As a Product Owner, I can set a date so that filtering by date is available for future use.  
- **AC:** Given I am on Feeder Events, When I look at the filter bar, Then I see a date control (e.g. date picker) that I can change.

---

## Sport / Category / Competition filters

**FE-6**  
As a Product Owner, I can select one or more sports so that the table shows only events for those sports.  
- **AC:** Given I am on Feeder Events with a feed selected, When I open the Sport dropdown and select one or more sports, Then the table shows only events whose sport is in my selection.

**FE-7**  
As a Product Owner, I see category options that depend on the selected sport(s) so that I filter correctly.  
- **AC:** Given I have selected at least one sport, When I open the Category dropdown, Then I see categories that exist for the selected feed and sports.

**FE-8**  
As a Product Owner, I can select one or more categories so that the table shows only events in those categories.  
- **AC:** Given I have selected sport(s) and opened Category, When I select one or more categories, Then the table shows only events in those categories.

**FE-9**  
As a Product Owner, I can select one or more competitions so that the table shows only events in those competitions.  
- **AC:** Given I am on Feeder Events with a feed selected, When I open the Competition dropdown and select one or more competitions, Then the table shows only events in those competitions.

**FE-10**  
As a Product Owner, I see filter chips for my dropdown selections so that I can remove a single filter easily.  
- **AC:** Given I have selected at least one sport, category, or competition, When I look at the filter area, Then I see a chip (or badge) for each selection that I can click to remove.

**FE-11**  
As a Product Owner, I can clear all active filters at once so that I quickly reset to “all”.  
- **AC:** Given I have applied one or more filters (e.g. sport, category, competition, status), When I click “Clear All”, Then all those filters are cleared and the table shows the full set for the current feed.

---

## Status and other filters

**FE-12**  
As a Product Owner, I can filter by event status (e.g. Open, Closed, Resulted) so that I see only events in those states.  
- **AC:** Given I am on Feeder Events, When I open the Status dropdown and select one or more statuses, Then the table shows only events whose status is in my selection.

**FE-13**  
As a Product Owner, I can toggle “Live match” so that I see only live events when the toggle is on.  
- **AC:** Given I am on Feeder Events, When I turn on the Live match toggle, Then the table shows only events that are live (time_status = live).

**FE-14**  
As a Product Owner, I can toggle “Notes” so that I see only events that have at least one note when the toggle is on.  
- **AC:** Given I am on Feeder Events, When I turn on the Notes filter toggle, Then the table shows only events that have notes.

**FE-15**  
As a Product Owner, I can filter by mapping status (Mapped / Unmapped) so that I focus on unmapped or mapped events.  
- **AC:** Given I am on Feeder Events, When I select a mapping status filter (e.g. Unmapped), Then the table shows only events with that mapping status.

**FE-16**  
As a Product Owner, I can filter by outright (Regular / Outright) so that I separate match and outright events.  
- **AC:** Given I am on Feeder Events, When I select Outright (or Regular), Then the table shows only outright events (or only non-outright events).

**FE-17**  
As a Product Owner, I can search by text so that I find events by name or competition.  
- **AC:** Given I am on Feeder Events, When I type in the search box and trigger search, Then the table shows only events whose sport, category, competition, or event label match the text.

---

## Table columns and display

**FE-18**  
As a Product Owner, I see Feed Source and Feed ID for each event so that I know the origin and can reference it.  
- **AC:** Given I am viewing the Feeder Events table, When I look at a row, Then I see the feed provider (Feed Source) and the feed event ID (Feed ID).

**FE-19**  
As a Product Owner, I see ID/Status as Mapped (domain ID), Unmapped, or Ignored so that I know the mapping state at a glance.  
- **AC:** Given I am viewing the table, When an event is mapped, Then ID/Status shows the domain event ID (e.g. green). When it is not mapped and not ignored, Then it shows “Unmapped” (e.g. red). When it is ignored, Then it shows “Ignored” (e.g. grey).

**FE-20**  
As a Product Owner, I see Start Time, Sport, Category, Competition, and Event (home vs away or outright) so that I identify the event.  
- **AC:** Given I am viewing the table, When I look at a row, Then I see start time, sport, category, competition, and event name (teams or outright label).

**FE-21**  
As a Product Owner, I see Status and #MKT columns so that I know feed status and market count (placeholder).  
- **AC:** Given I am viewing the table, When I look at a row, Then I see a Status value (e.g. Open, Closed) and a #MKT value (or placeholder).

**FE-22**  
As a Product Owner, I see a Notes indicator when an event has notes so that I know which events have operator notes.  
- **AC:** Given an event has at least one note, When I look at that row’s Notes column, Then I see a note icon (e.g. amber). When it has no notes, Then I see a neutral placeholder (e.g. “—”).

**FE-23**  
As a Product Owner, I see green highlighting for Sport/Category/Competition/Team when that value is mapped for this feed so that I know what is already linked.  
- **AC:** Given a feed event’s sport (or category, competition, team) is linked in entity_feed_mappings for the selected feed, When I look at that cell, Then it is shown in green (or equivalent highlight).

**FE-24**  
As a Product Owner, I see muted styling for ignored events in the data columns so that ignored rows are visually de-emphasised.  
- **AC:** Given an event is ignored, When I look at the row, Then columns from Feed ID through #MKT use muted (darker grey) styling; Feed Source, Notes, and Action stay normal.

---

## Action menu — Map Event

**FE-25**  
As a Product Owner, I can open the action menu (kebab) per row so that I can choose Map Event or other actions.  
- **AC:** Given I am viewing the table, When I click the action (kebab) button on a row, Then a menu opens with options such as Map Event, Copy Feed ID, Event Log, Ignore, Notes.

**FE-26**  
As a Product Owner, I can open Map Event from the action menu so that I map this feed event to a domain event.  
- **AC:** Given the event is not ignored, When I click “Map Event” in the kebab menu, Then the Mapping Modal opens for this feed event (see Mapping Modal spec).

**FE-27**  
As a Product Owner, I do not see Map Event for ignored events so that I cannot map events that are marked ignored.  
- **AC:** Given the event is ignored, When I open the action menu, Then “Map Event” is not shown (or is disabled and not clickable).

---

## Action menu — Copy Feed ID

**FE-28**  
As a Product Owner, I can copy the feed event ID to the clipboard from the action menu so that I can paste it elsewhere.  
- **AC:** Given I am on Feeder Events, When I click “Copy Feed ID” in the kebab menu, Then the feed event ID is copied to the clipboard.

**FE-29**  
As a Product Owner, I see a toast after copying the feed ID so that I get confirmation.  
- **AC:** Given I have clicked “Copy Feed ID”, When the copy succeeds, Then a toast appears (e.g. top-right, greenish) with a message like “Feed ID copied to clipboard”.

---

## Action menu — Event Log

**FE-30**  
As a Product Owner, I can open Event Log from the action menu so that I see the action history for that event.  
- **AC:** Given I am on Feeder Events, When I click “Event Log” in the kebab menu, Then a modal opens showing log entries (e.g. appeared, mapped, note_added, ignored, unignored) with timestamps.

**FE-31**  
As a Product Owner, I see Event Log entries in reverse chronological order so that the latest action is first.  
- **AC:** Given the Event Log modal is open, When I look at the list, Then entries are ordered newest first.

---

## Action menu — Ignore / Un-ignore

**FE-32**  
As a Product Owner, I can mark a feed event as Ignored from the action menu so that we do not map it without deleting data.  
- **AC:** Given the event is not ignored, When I click “Ignore Mapping” in the kebab menu, Then the event is marked ignored; ID/Status shows “Ignored” and the row uses muted styling for data columns.

**FE-33**  
As a Product Owner, I can clear the ignored state so that the event can be mapped again.  
- **AC:** Given the event is ignored, When I click “Un-ignore” in the kebab menu, Then the event is no longer ignored; ID/Status shows Mapped or Unmapped and styling returns to normal.

**FE-34**  
As a Product Owner, ignoring an event does not delete any stored data so that we can revert later.  
- **AC:** Given I ignore an event, When I later un-ignore it, Then any previous mapping or metadata is still available (no data removed by ignore).

---

## Action menu — Notes (out of scope for initial; still described)

**FE-35**  
As a Product Owner, I can open Notes from the action menu so that I can add or view notes for that event (future).  
- **AC:** Given I am on Feeder Events, When I click “Notes” in the kebab menu, Then a Notes modal opens (multi-note, platform notes; full behaviour out of scope for initial).

---

## Bulk select and Bulk Update

**FE-36**  
As a Product Owner, I can select individual rows via checkbox so that I can perform bulk actions later.  
- **AC:** Given I am on Feeder Events, When I check a row’s checkbox, Then that row is selected; I can select multiple rows.

**FE-37**  
As a Product Owner, I can select or clear all rows via the header checkbox so that I bulk-select quickly.  
- **AC:** Given I am on Feeder Events, When I check the header checkbox, Then all visible rows are selected. When I uncheck it, Then all are deselected.

**FE-38**  
As a Product Owner, I see a Bulk Update button in the footer so that bulk update is available in a later phase.  
- **AC:** Given I am on Feeder Events, When I look at the footer, Then I see a “Bulk Update” button (e.g. left of “Showing X events”); for initial version it may be disabled or placeholder with no behaviour.

---

## Data and consistency

**FE-39**  
As a Product Owner, the table reflects mapping status after I map an event so that I see up-to-date state without full reload.  
- **AC:** Given I have just mapped a feed event in the Mapping Modal, When I close the modal, Then the Feeder Events table (or refreshed fragment) shows that event as Mapped with the domain ID.

**FE-40**  
As a Product Owner, filter options (sport, category, competition) are scoped to the selected feed so that I only see relevant values.  
- **AC:** Given I select Feed A, When I open Sport (or Category, Competition), Then I see only values that exist in Feed A’s events.
