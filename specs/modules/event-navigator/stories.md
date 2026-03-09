# Event Navigator — User Stories

Stories use **As a Product Owner** and **Given/When/Then** in Acceptance Criteria. Small scope; minimal AC per story.

---

## Page and navigation

**EN-1**  
As a Product Owner, I can open the Event Navigator page from the Betting Program menu so that I see the page title and short description.  
- **AC:** Given I am on the app, When I open Betting Program → Event Navigator, Then I see the heading "Event Navigator" and the description text for canonical events built from mapped feed data.

**EN-2**  
As a Product Owner, I see a filter bar at the top so that I can narrow the list.  
- **AC:** Given I am on Event Navigator, When the page has loaded, Then I see a filter bar with Period, Sport, Category, Competition, Status, Live/Has Bets/Notes toggles, Outright tabs, Search, and Brand dropdown.

**EN-3**  
As a Product Owner, I see a table of domain events and a footer with "Showing X events" so that I know how many events match.  
- **AC:** Given I am on Event Navigator, When the table has loaded, Then I see a row count message (e.g. "Showing N events") in the footer.

---

## Period filter (Start Time)

**EN-4**  
As a Product Owner, I see a Period control showing a date range so that I can choose a time window (presentation only initially).  
- **AC:** Given I am on Event Navigator, When I look at the filter bar, Then I see a button showing a date range (e.g. "07/03/2026 - 07/03/2026") with a calendar icon and chevron; there is no "Period" label.

**EN-5**  
As a Product Owner, I can open the Period dropdown and select an option so that the displayed range updates.  
- **AC:** Given I am on Event Navigator, When I click the Period button, Then a dropdown opens with options: Today, Tomorrow, Next 7 Days, This Month, Next Month, Yesterday, Last 7 Days, Custom range. When I select an option, Then the displayed range updates and that option is highlighted.

---

## Sport / Category / Competition filters

**EN-6**  
As a Product Owner, I can select one or more sports so that the table shows only events for those sports.  
- **AC:** Given I am on Event Navigator, When I open the Sport dropdown and select one or more sports, Then the table shows only events whose sport is in my selection.

**EN-7**  
As a Product Owner, I see category options that depend on the selected sport(s) so that I filter correctly.  
- **AC:** Given I have selected at least one sport, When I open the Category dropdown, Then I see categories that exist for the selected sports; Category is disabled when no sport is selected.

**EN-8**  
As a Product Owner, I can select one or more categories so that the table shows only events in those categories.  
- **AC:** Given I have selected sport(s) and opened Category, When I select one or more categories, Then the table shows only events in those categories.

**EN-9**  
As a Product Owner, I can select one or more competitions so that the table shows only events in those competitions.  
- **AC:** Given I am on Event Navigator, When I open the Competition dropdown and select one or more competitions, Then the table shows only events in those competitions.

**EN-10**  
As a Product Owner, I see filter chips for my dropdown selections so that I can remove a single filter easily.  
- **AC:** Given I have selected at least one sport, category, or competition, When I look at the filter area, Then I see a chip (or badge) for each selection that I can click to remove.

**EN-11**  
As a Product Owner, I can clear all active filters at once so that I quickly reset to "all".  
- **AC:** Given I have applied one or more filters (e.g. sport, category, competition, status, period, brand), When I click "Clear All", Then all those filters are cleared and the table shows the full set; Brand resets to Global.

---

## Status and other filters

**EN-12**  
As a Product Owner, I can filter by event status (e.g. Open, Closed, Resulted) so that I see only events in those states.  
- **AC:** Given I am on Event Navigator, When I open the Status dropdown and select one or more statuses, Then the table shows only events whose status is in my selection.

**EN-13**  
As a Product Owner, I can toggle "Live match" so that I see only live events when the toggle is on.  
- **AC:** Given I am on Event Navigator, When I turn on the Live match toggle (icon), Then the table shows only events that are live; the icon colour changes when on (e.g. red).

**EN-14**  
As a Product Owner, I can toggle "Has Bets" so that I see only events that have bets when the toggle is on.  
- **AC:** Given I am on Event Navigator, When I turn on the Has Bets toggle ($ icon), Then the table shows only events that have bets; the icon colour changes when on (e.g. emerald).

**EN-15**  
As a Product Owner, I can toggle "Notes" so that I see only events that have at least one note when the toggle is on.  
- **AC:** Given I am on Event Navigator, When I turn on the Notes filter toggle, Then the table shows only events that have an Event Navigator note; the icon colour changes when on (e.g. amber).

**EN-16**  
As a Product Owner, I can filter by outright (All / Outright / Regular) so that I separate match and outright events.  
- **AC:** Given I am on Event Navigator, When I select Outright (or Regular) in the button group, Then the table shows only outright events (or only non-outright events). When I select All, Then no outright filter is applied.

**EN-17**  
As a Product Owner, I can search by text so that I find events by sport, category, competition, or event label.  
- **AC:** Given I am on Event Navigator, When I type in the search box and trigger search, Then the table shows only events whose sport, category, competition, or event label match the text.

---

## Brand filter

**EN-18**  
As a Product Owner, I see a Brand filter with label "Brand:" to the left of the dropdown so that I can filter by brand.  
- **AC:** Given I am on Event Navigator, When I look at the filter bar after the search box, Then I see the label "Brand:" and a dropdown showing the selected brand(s) (e.g. "Global" by default).

**EN-19**  
As a Product Owner, I can select Global or one or more specific brands so that the table is scoped accordingly.  
- **AC:** Given I am on Event Navigator, When I open the Brand dropdown, Then I see "Global" (first) and one option per brand. When I select Global, Then only Global is selected. When I select one or more non-Global brands, Then only those brands are selected.

**EN-20**  
As a Product Owner, Global cannot be combined with other brands so that the filter is mutually exclusive.  
- **AC:** Given Global is selected, When I select any other brand, Then Global is automatically deselected. Given one or more non-Global brands are selected, When I select Global, Then all other brands are deselected and only Global remains. If no brand is selected, Then selection reverts to Global.

---

## Table columns and display

**EN-21**  
As a Product Owner, I see Id, Start Time, Sport, Category, Competition, and Event for each domain event so that I identify the event.  
- **AC:** Given I am viewing the Event Navigator table, When I look at a row, Then I see domain event Id, Start Time, Sport, Category, Competition, and Event (e.g. "Home v Away").

**EN-22**  
As a Product Owner, I see Status, Class, CO (CashOut), T/O, In charge, Has Bets, Score, #FEED, and #mkt columns so that I have full context.  
- **AC:** Given I am viewing the table, When I look at a row, Then I see Status (e.g. Not Started), Class, CO, T/O, In charge, Has Bets, Score (placeholders "—" where not implemented), #FEED (number of mapped feeds), and #mkt (placeholder).

**EN-23**  
As a Product Owner, I see a Notes indicator when an event has an Event Navigator note so that I know which events have notes.  
- **AC:** Given an event has an Event Navigator note, When I look at that row's Notes column, Then I see a note icon (e.g. amber). When it has no note, Then I see "—".

**EN-24**  
As a Product Owner, I can click Sport, Category, or Competition in a row to apply that filter so that I quickly narrow the list.  
- **AC:** Given I am viewing the table, When I click the sport (or category, or competition) value in a row, Then that value is applied as a filter and the table refreshes with the new filter.

**EN-25**  
As a Product Owner, I see Start Time with a tooltip showing start time by feed when the event has multiple mapped feeds so that I can spot mismatches.  
- **AC:** Given a domain event has multiple feeds with start times, When I hover over the Start Time cell, Then a tooltip shows start time per feed. When there is a start_time_mismatch, Then the Start Time is shown in red (or equivalent).

---

## Event details and action menu

**EN-26**  
As a Product Owner, I can open the action menu (kebab) per row so that I can choose View Event, Notes, or other actions.  
- **AC:** Given I am viewing the table, When I click the action (kebab) button on a row, Then a menu opens with options such as View Event, Edit Event, Close Event, Abandon Event, Takeover Event, Release Event, Disable CO, Release CO, Copy Event ID, View Bets, Event Log, Dynamic Templates, Notes.

**EN-27**  
As a Product Owner, I can open Event Details from the Event cell so that I see full event information in a new tab.  
- **AC:** Given I am viewing the table, When I click the Event cell (e.g. "Home v Away"), Then Event Details opens in a new tab for that domain event.

**EN-28**  
As a Product Owner, I can open View Event from the action menu so that I see Event Details.  
- **AC:** Given I am on Event Navigator, When I click "View Event" in the kebab menu, Then Event Details opens (e.g. in a new tab) for that domain event.

---

## Event Navigator Notes (screen-only)

**EN-29**  
As a Product Owner, I can open the Notes modal from the Notes column or from the action menu so that I add or edit a note for that domain event.  
- **AC:** Given I am on Event Navigator, When I click the Notes column (icon or "—") or Action → Notes, Then a Notes modal opens titled e.g. "Notes (Event Navigator)" with a textarea for the note and an IMPORTANT checkbox.

**EN-30**  
As a Product Owner, the Notes modal states that notes are for this screen only so that I understand they are not shared with Feeder Events.  
- **AC:** Given the Event Navigator Notes modal is open, When I read the modal, Then I see text that notes are for this screen only (Event Navigator).

**EN-31**  
As a Product Owner, I can enter or edit note text and save so that the note is stored for this domain event.  
- **AC:** Given the Notes modal is open, When I type in the Note textarea and click Save, Then the note is saved; the modal closes and the table refreshes; the Notes column shows the note icon if a note exists.

**EN-32**  
As a Product Owner, I can check "IMPORTANT! Please confirm you read and understood!" so that a platform notification is created for all users until they confirm.  
- **AC:** Given the Notes modal is open, When I check the IMPORTANT checkbox and click Save, Then the note is saved and a platform notification is created; all users see the notification (e.g. top-right) until they confirm "I've read and understood". The note text is still stored only in Event Navigator notes.

**EN-33**  
As a Product Owner, I see help text for the IMPORTANT checkbox so that I understand the behaviour.  
- **AC:** Given the Notes modal is open, When I look at the IMPORTANT checkbox, Then I see help text such as: "If checked, all users will see a notification (top right) until they confirm they have read it."

**EN-34**  
As a Product Owner, I can cancel the Notes modal without saving so that no changes are applied.  
- **AC:** Given the Notes modal is open, When I click Cancel, Then the modal closes and no note is saved or updated.

---

## Bulk select

**EN-35**  
As a Product Owner, I can select individual rows via checkbox so that I can perform bulk actions later.  
- **AC:** Given I am on Event Navigator, When I check a row's checkbox, Then that row is selected; I can select multiple rows.

**EN-36**  
As a Product Owner, I can select or clear all rows via the header checkbox so that I bulk-select quickly.  
- **AC:** Given I am on Event Navigator, When I check the header checkbox, Then all visible rows are selected. When I uncheck it, Then all are deselected.

**EN-39**  
As a Product Owner, I see a Bulk Update button in the footer so that bulk update is available in a later phase.  
- **AC:** Given I am on Event Navigator, When I look at the footer below the table, Then I see a "Bulk Update" button on the left (e.g. disabled with tooltip "Bulk update – coming soon"); for initial version it has no behaviour.

---

## Pagination (placeholders)

**EN-40**  
As a Product Owner, I see Previous and Next buttons in the footer so that pagination can be used when implemented.  
- **AC:** Given I am on Event Navigator, When I look at the footer, Then I see "Previous" and "Next" buttons on the right; for initial version they are disabled (e.g. tooltip "Pagination – coming soon").

**EN-41**  
As a Product Owner, the table is intended to show a limited number of events per page (e.g. 20) when pagination is implemented so that the list is manageable.  
- **AC:** (Future) When pagination is implemented, Then the table shows at most the configured page size (e.g. 20 events per page) and the footer count reflects the current page (e.g. "Showing 1–20 of 45 events"). For initial version, all matching events are shown; no page limit.

---

## Data and consistency

**EN-42**  
As a Product Owner, the table reflects the note state after I save a note so that I see the note icon without full reload.  
- **AC:** Given I have just saved (or cleared) a note in the Notes modal, When the modal closes, Then the Event Navigator table (or refreshed fragment) shows the updated Notes column (icon or "—").

**EN-43**  
As a Product Owner, filter options (sport, category, competition) are scoped to domain events so that I only see relevant values.  
- **AC:** Given I am on Event Navigator, When I open Sport (or Category, Competition), Then I see only values that exist in the domain events data.
