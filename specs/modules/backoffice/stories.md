# Backoffice — User Stories

Stories use **As a Product Owner** and **Given/When/Then** in Acceptance Criteria. Small scope; minimal AC per story.

---

## Layout and navigation

**BO-1**  
As a Product Owner, I see a fixed top navigation bar so that I can navigate from any page.  
- **AC:** Given I am on any page of the app, When I look at the top, Then I see a header bar with logo, navigation items, notifications, and profile avatar.

**BO-2**  
As a Product Owner, I can click the logo to go to the home page so that I return to the dashboard.  
- **AC:** Given I am on any page, When I click the logo (GMP), Then I navigate to the home page (dashboard).

**BO-3**  
As a Product Owner, I see Configuration as a dropdown so that I can access Entities, Localization, Brands, Feeder, Margin, Risk Rules.  
- **AC:** Given I am on the app, When I hover or focus Configuration, Then I see a dropdown with links: Entities, Localization, Brands, Feeder, Margin, Risk Rules.

**BO-4**  
As a Product Owner, I see Betting Program as a dropdown so that I can access Event Navigator, Feeder Events, Archived Events.  
- **AC:** Given I am on the app, When I hover or focus Betting Program, Then I see a dropdown with links: Event Navigator, Feeder Events, Archived Events.

**BO-5**  
As a Product Owner, I see the current section highlighted in the menu so that I know where I am.  
- **AC:** Given I am on Feeder Events, When I look at the Betting Program button and Feeder Events link, Then the active item is highlighted (e.g. text-primary or equivalent).

**BO-6**  
As a Product Owner, I see Admin, Risk, Bets/PTLs, Alerts, Reports as nav items so that I know they exist (placeholders).  
- **AC:** Given I am on the app, When I look at the nav bar, Then I see Admin, Risk, Bets/PTLs, Alerts, Reports (links or placeholders).

---

## Notifications

**BO-7**  
As a Product Owner, I see a notifications bell icon in the top-right so that I can open the notifications panel.  
- **AC:** Given I am on any page, When I look at the top-right area, Then I see a bell icon button (e.g. notifications).

**BO-8**  
As a Product Owner, I see a badge on the bell when there are unconfirmed notifications so that I know there are items to confirm.  
- **AC:** Given there is at least one unconfirmed notification, When I look at the bell icon, Then I see a badge with the count (e.g. amber background). When there are none, Then the badge is hidden.

**BO-9**  
As a Product Owner, I can open the notifications panel by clicking the bell so that I see the unconfirmed list.  
- **AC:** Given I am on the app, When I click the bell icon, Then a panel opens below it with the title "Confirm you read" and a list of unconfirmed notifications (or "No pending confirmations").

**BO-10**  
As a Product Owner, I see each unconfirmed notification with a message and a confirm button so that I can acknowledge I have read it.  
- **AC:** Given the notifications panel is open and there is at least one unconfirmed notification, When I look at the list, Then each item shows a message snippet, timestamp, and a button like "I've read and understood".

**BO-11**  
As a Product Owner, I can confirm a notification by clicking the confirm button so that it is removed from the list.  
- **AC:** Given I have opened the notifications panel and there is an unconfirmed notification, When I click "I've read and understood" on that item, Then the notification is confirmed and the list refreshes; the badge count updates or disappears if none remain.

**BO-12**  
As a Product Owner, I can close the notifications panel by clicking outside it so that it does not block the view.  
- **AC:** Given the notifications panel is open, When I click outside the panel (e.g. elsewhere on the page), Then the panel closes.

---

## Profile

**BO-13**  
As a Product Owner, I see a profile avatar in the top-right so that I know where the profile area is.  
- **AC:** Given I am on any page, When I look at the top-right (after the bell), Then I see a circular avatar (e.g. with initial "A" or user indicator).

**BO-14**  
As a Product Owner, the profile area is a placeholder for future profile menu/settings so that the layout is ready.  
- **AC:** Given I am on the app, When I look at the profile avatar, Then it is visible; full profile menu behaviour is out of scope for initial (placeholder).

---

## Dashboard

**BO-15**  
As a Product Owner, I land on the Dashboard when I open the app so that I see an overview first.  
- **AC:** Given I open the app (e.g. /), When the page loads, Then I see the Dashboard with page title "Dashboard" and a short description.

**BO-16**  
As a Product Owner, I see stat cards on the Dashboard so that I have a quick overview of events and mapping.  
- **AC:** Given I am on the Dashboard, When I look at the content, Then I see at least one stat card (e.g. Incoming Events, Mapped Successfully, Pending Action) with numbers and labels.

**BO-17**  
As a Product Owner, I see a link to the Feeder Events (or mapping tool) on the Dashboard so that I can start mapping quickly.  
- **AC:** Given I am on the Dashboard, When I look at the content, Then I see a link or button that navigates to Feeder Events (or the mapping tool).

**BO-18**  
As a Product Owner, I can use "Dump CSV data" on the Dashboard to clear backoffice-managed data so that I can reset for testing.  
- **AC:** Given I am on the Dashboard, When I click "Dump CSV data" and confirm, Then categories, competitions, teams, domain events, event mappings, entity feed mappings are cleared; feeds.csv, sports.csv, sport_feed_mappings.csv are not changed.

---

## Toast

**BO-19**  
As a Product Owner, I see a toast when a module triggers it (e.g. Copy Feed ID) so that I get short-lived feedback.  
- **AC:** Given a module calls showToast (e.g. after copying feed ID), When the action completes, Then a toast appears top-right with the message (e.g. greenish styling).

**BO-20**  
As a Product Owner, the toast disappears automatically after a few seconds so that it does not clutter the screen.  
- **AC:** Given a toast has appeared, When a few seconds pass (e.g. 3), Then the toast is removed from the view.

---

## Modal container

**BO-21**  
As a Product Owner, a modal opens when a module triggers it (e.g. Map Event, Notes) so that I can complete the action.  
- **AC:** Given a module opens a modal (e.g. Mapping Modal), When the modal opens, Then I see an overlay and a centered panel with the modal content.

**BO-22**  
As a Product Owner, I can close the modal by clicking the backdrop so that I can cancel or dismiss.  
- **AC:** Given a modal is open, When I click the backdrop (outside the panel), Then the modal closes.

**BO-23**  
As a Product Owner, the modal panel loads content via HTMX so that the shell does not need to know the modal content.  
- **AC:** Given a module opens a modal that loads content from an endpoint, When the modal opens, Then the content is loaded into the modal panel (e.g. HTMX swap).

---

## Page header

**BO-24**  
As a Product Owner, I see a page header (title + short description) on each module page so that I know what page I am on.  
- **AC:** Given I navigate to a module page (e.g. Feeder Events), When the page loads, Then I see a page header area with a title (e.g. "Feeder Events") and a short description.

**BO-25**  
As a Product Owner, a module can override or hide the page header (e.g. Event Details) so that it can use its own layout.  
- **AC:** Given a page (e.g. Event Details) overrides the page_header block, When the page loads, Then the default page header is not shown (or is replaced with custom content).
