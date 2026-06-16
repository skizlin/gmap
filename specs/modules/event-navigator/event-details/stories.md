# Event Details — User Stories

Stories use **As a Product Owner** and **Given/When/Then** in Acceptance Criteria. Prefix **ED-** (Event Details). Parent module: Event Navigator.

---

## Entry and page shell

**ED-1**  
As a Product Owner, I can open Event Details from Event Navigator so that I work on one domain event in a dedicated view.  
- **AC:** Given I am on Event Navigator, When I click the Event cell (e.g. "Home v Away") or Action → View Event, Then Event Details opens in a **new tab** at `/event-navigator/event_details/{domain_id}`.

**ED-2**  
As a Product Owner, I see the event identity in the header so that I know which event I am viewing.  
- **AC:** Given Event Details has loaded, When I look at the header, Then I see the event label (Home v Away or event id), sport / category / competition / domain ID, start time, and a status badge (e.g. Not Started).

**ED-3**  
As a Product Owner, I get a clear error when the domain event does not exist so that I am not shown a broken page.  
- **AC:** Given an invalid or unknown domain_id in the URL, When I open Event Details, Then I receive a not-found response (e.g. 404).

---

## Mapped feeds

**ED-4**  
As a Product Owner, I see which feeds are mapped to this domain event so that I know the feed coverage.  
- **AC:** Given the event has rows in event_mappings, When I look at the Mapped Feeds panel, Then I see each feed provider and feed event ID. When none are mapped, Then I see a message that no feeds are mapped.

---

## Left column — Markets

**ED-5**  
As a Product Owner, I see domain markets grouped by market group so that I can navigate many market types.  
- **AC:** Given markets exist for this event’s sport, When I look at the Markets panel, Then markets are listed under group headings with a group-level checkbox and per-market checkboxes.

**ED-6**  
As a Product Owner, I can select or clear all markets in a group so that I bulk-select a category of markets.  
- **AC:** Given a market group is shown, When I check the group checkbox, Then all markets in that group are selected; When I uncheck it, Then all in that group are deselected.

**ED-7**  
As a Product Owner, I only see markets for this event’s sport so that irrelevant market types are hidden.  
- **AC:** Given the domain event has a sport, When the Markets panel loads, Then only markets configured for that sport (or sport_id) appear.

**ED-8**  
As a Product Owner, I see a Resulted Markets section reserved for future use so that the layout matches the target design.  
- **AC:** Given I am on Event Details, When I scroll the left column, Then I see a Resulted Markets block with placeholder text that logic will be implemented later.

---

## Center column — Markets Overview

**ED-9**  
As a Product Owner, I see an empty overview until I select markets so that the flow is clear.  
- **AC:** Given no market checkboxes are checked, When I look at Markets Overview, Then I see a message to select markets from the left.

**ED-10**  
As a Product Owner, I see a row in Markets Overview for each selected market so that I can work with those markets.  
- **AC:** Given I check one or more markets on the left, When the overview updates, Then each selected market appears as a row in the center column.

**ED-11**  
As a Product Owner, I choose one active market via radio in the overview so that Brand Overview and Feed Odds apply to that market.  
- **AC:** Given multiple markets are shown in the overview, When I select the radio on one row, Then that market is the active market for the right-column odds panels.

**ED-12**  
As a Product Owner, I can choose a pricing brand so that overview prices use the correct margin scope.  
- **AC:** Given I am on Event Details, When I change the Pricing brand dropdown (Global or a brand), Then the Markets Overview prices for the active market refresh using that brand scope.

**ED-13**  
As a Product Owner, I can select a line for line-based markets so that odds and overview align on the same handicap/total.  
- **AC:** Given the active market supports lines (e.g. handicap/total), When I click a line button in the overview row, Then Feed Odds, Brand Overview, and overview prices use that line (where supported).

---

## Right column — Brand Overview and Feed Odds

**ED-14**  
As a Product Owner, I see Brand Overview only when a market is active so that I am not confused by empty tables.  
- **AC:** Given no market radio is selected, When I look at Brand Overview, Then I see a message to select a market from the center. When a market is active, Then the table loads with one row per brand and outcome columns (L, S1–S6, M, Liab.).

**ED-15**  
As a Product Owner, I see Feed Odds from each mapped feed for the active market so that I compare source prices.  
- **AC:** Given a market is active and feeds have cached event details, When Feed Odds loads, Then I see one row per feed with odds columns; multi-line markets may show multiple lines per feed when all_lines is enabled.

**ED-16**  
As a Product Owner, I see margin (M) on feed and brand tables so that I understand book overround on displayed prices.  
- **AC:** Given odds are displayed, When I look at the M column, Then it reflects implied margin from the shown decimal odds (consistent formula across panels).

**ED-17**  
As a Product Owner, I see Internal Model data when the sport/market supports it so that I can compare model vs feeds.  
- **AC:** Given the active market is supported (e.g. specific volleyball markets), When Internal Model loads, Then I see model rows; otherwise I see empty or not-applicable state.

---

## Header actions (placeholders)

**ED-18**  
As a Product Owner, I see Suspend, Display, and Limits actions in the header so that trading controls can be added later.  
- **AC:** Given I am on Event Details, When I look at the header action row, Then I see (S) Suspend, (D) Display, and (L) Limits buttons; behaviour may be placeholder until trading integration.

---

## Data and integration

**ED-19**  
As a Product Owner, feed odds reflect cached event details fetched when the event was mapped so that I do not expect live API on every click.  
- **AC:** Given the event was mapped and background fetch succeeded, When I open Feed Odds for a market, Then odds come from stored feed_event_details. When cache is missing, Then the feed row may show no odds or dashes.

**ED-20**  
As a Product Owner, Brand Overview uses configured margin templates so that displayed prices match pricing policy.  
- **AC:** Given margin templates and PM% are configured for brands, When Brand Overview loads, Then margined prices use log2 (or configured conversion) from fair/true odds and the brand’s prematch margin.

---

## Permissions and navigation

**ED-21**  
As a Product Owner, I can open Event Details only when I have Event Navigator access so that permissions stay consistent.  
- **AC:** Given my role lacks `menu.betting_program.event_navigator.view`, When I try to open Event Details, Then I am denied per platform RBAC rules.

---

## Related Event Navigator stories

Entry stories **EN-27** and **EN-28** in [../stories.md](../stories.md) cover opening Event Details from the list page; this document specifies behaviour **on** the Event Details page.
