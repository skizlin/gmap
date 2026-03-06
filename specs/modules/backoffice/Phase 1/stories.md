# Backoffice Phase 1 — User Stories

Stories use **As a Product Owner** and **Given/When/Then**. Phase 1 scope: Feeder Events, Event Navigator, Entities, Mapping Modal only.

---

## Layout and navigation (Phase 1)

**BO1-1**  
As a Product Owner, I see a fixed top bar so that I can navigate from any Phase 1 page.  
- **AC:** Given I am on Dashboard, Feeder Events, Event Navigator, or Entities, When I look at the top, Then I see a header with logo, nav menu, notifications bell, and profile avatar.

**BO1-2**  
As a Product Owner, I can go to Dashboard from the logo so that I land on the home page.  
- **AC:** Given I am on any page, When I click the logo (GMP), Then I navigate to the Dashboard (/).

**BO1-3**  
As a Product Owner, I can open Configuration and go to Entities so that I manage domain entities.  
- **AC:** Given I am on the app, When I hover/focus Configuration and click Entities, Then I navigate to the Entities page; the Configuration / Entities item is highlighted.

**BO1-4**  
As a Product Owner, I can open Betting Program and go to Feeder Events so that I map feed events.  
- **AC:** Given I am on the app, When I hover/focus Betting Program and click Feeder Events, Then I navigate to the Feeder Events page; the Betting Program / Feeder Events item is highlighted.

**BO1-5**  
As a Product Owner, I can open Betting Program and go to Event Navigator so that I view domain events.  
- **AC:** Given I am on the app, When I hover/focus Betting Program and click Event Navigator, Then I navigate to the Event Navigator page; the Betting Program / Event Navigator item is highlighted.

**BO1-6**  
As a Product Owner, I see the current section highlighted so that I know where I am.  
- **AC:** Given I am on Feeder Events, When I look at the nav, Then the Betting Program button and Feeder Events link are highlighted (e.g. text-primary).

---

## Notifications (from Feeder Events)

**BO1-7**  
As a Product Owner, I see a notifications bell in the top-right so that I can open the panel.  
- **AC:** Given I am on any Phase 1 page, When I look at the top-right, Then I see a bell icon button.

**BO1-8**  
As a Product Owner, I see a badge on the bell when there are unconfirmed notifications so that I know there are items to confirm.  
- **AC:** Given at least one unconfirmed notification (e.g. from a Feeder Events note with "confirm read"), When I look at the bell, Then I see a badge with the count. When there are none, Then the badge is hidden.

**BO1-9**  
As a Product Owner, I can open the notifications panel and see the unconfirmed list so that I can confirm I have read them.  
- **AC:** Given I click the bell, When the panel opens, Then I see the "Confirm you read" section and a list of unconfirmed notifications (or "No pending confirmations").

**BO1-10**  
As a Product Owner, I can confirm a notification by clicking "I've read and understood" so that it is removed from the list.  
- **AC:** Given the panel is open and there is an unconfirmed notification, When I click "I've read and understood", Then the notification is confirmed and the list refreshes; the badge updates.

---

## Profile

**BO1-11**  
As a Product Owner, I see a profile avatar in the top-right so that the layout is ready for future profile features.  
- **AC:** Given I am on any page, When I look at the top-right (after the bell), Then I see a circular avatar (e.g. "A"). Phase 1: placeholder only.

---

## Dashboard (Phase 1)

**BO1-12**  
As a Product Owner, I land on the Dashboard when I open the app so that I see an overview first.  
- **AC:** Given I open the app (e.g. /), When the page loads, Then I see the Dashboard with title "Dashboard" and a short description.

**BO1-13**  
As a Product Owner, I see stat cards and a link to Feeder Events on the Dashboard so that I can start mapping quickly.  
- **AC:** Given I am on the Dashboard, When I look at the content, Then I see stat cards (e.g. Incoming Events, Mapped Successfully, Pending Action) and a "Go to Mapping Tool" (or similar) link to Feeder Events.

**BO1-14**  
As a Product Owner, I can use "Dump CSV data" on the Dashboard to clear backoffice-managed data so that I can reset for testing.  
- **AC:** Given I am on the Dashboard, When I click "Dump CSV data" and confirm, Then categories, competitions, teams, domain events, event mappings, entity feed mappings are cleared; feeds.csv, sports.csv, sport_feed_mappings.csv are unchanged.

---

## Toast (from Feeder Events)

**BO1-15**  
As a Product Owner, I see a toast when Feeder Events triggers it (e.g. Copy Feed ID) so that I get short-lived feedback.  
- **AC:** Given I am on Feeder Events and copy a feed ID, When the copy succeeds, Then a toast appears top-right with "Feed ID copied to clipboard" (greenish).

**BO1-16**  
As a Product Owner, the toast disappears automatically so that it does not clutter the screen.  
- **AC:** Given a toast has appeared, When a few seconds pass, Then the toast is removed.

---

## Modal container (Mapping Modal, Notes, Event Log)

**BO1-17**  
As a Product Owner, the Mapping Modal opens when I click Map Event on Feeder Events so that I can map a feed event to a domain event.  
- **AC:** Given I am on Feeder Events and click Action → Map Event on an unmapped event, When the modal opens, Then I see the Mapping Modal with feed event info and options to Confirm Mapping or Create & Map.

**BO1-18**  
As a Product Owner, I can close the modal by clicking the backdrop so that I can cancel or dismiss.  
- **AC:** Given a modal (Mapping, Notes, or Event Log) is open, When I click the backdrop, Then the modal closes.

**BO1-19**  
As a Product Owner, the modal content is loaded via HTMX so that the shell does not need to know the content.  
- **AC:** Given Feeder Events opens a modal (e.g. Map Event), When the modal opens, Then the content is loaded into the modal panel (e.g. HTMX swap).

**BO1-20**  
As a Product Owner, after I complete Mapping Modal (Confirm Mapping or Create & Map), the Feeder Events table refreshes so that I see the updated MAPPED status.  
- **AC:** Given I have completed Mapping Modal (Confirm Mapping or Create & Map), When the modal closes, Then the Feeder Events table (or relevant fragment) refreshes and shows the event as MAPPED with domain ID.

---

## Page header (Phase 1)

**BO1-21**  
As a Product Owner, I see a page header (title + description) on Feeder Events, Event Navigator, and Entities so that I know what page I am on.  
- **AC:** Given I navigate to Feeder Events, Event Navigator, or Entities, When the page loads, Then I see a page header with a title and short description.

**BO1-22**  
As a Product Owner, the Event Details page can override the page header so that it can use its own layout.  
- **AC:** Given I navigate to Event Details (from Event Navigator), When the page loads, Then the default page header is not shown (or is replaced); Event Details uses its own header as per domain-events spec.
