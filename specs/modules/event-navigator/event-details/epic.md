# Epic: Event Details (Event Navigator)

**Epic name:** Event Details — View and price a single domain event (markets, overview, feed odds, brands)

**Summary:**  
Operators need a dedicated page for one **canonical (domain) event** after mapping: event header, domain markets grouped by market group, a **Markets Overview** workspace to select markets and lines, and side panels for **Brand Overview**, **Feed Odds**, **Internal Model**, and **Mapped Feeds**. The page opens in a **new tab** from Event Navigator (Event cell link or View Event). Pricing uses configured brands, margin templates, and cached **feed event details** (fetched when the event is created or mapped).

**Goals:**
- Open Event Details for a valid domain event ID; show event label, sport/category/competition, start time, and mapped feed list.
- List domain markets (scoped to event sport) with group checkboxes; drive center **Markets Overview** from selected markets.
- For the **active** market (radio in overview): load **Feed Odds** per mapped feed, **Brand Overview** margined prices, **Internal Model** where supported, and **overview** margined prices for the selected pricing brand.
- Support line-based markets (handicap/total): line selector in overview; `all_lines` feed odds; main-line indicator where applicable (e.g. 1xbet).
- Respect **Pricing brand** (Global or specific brand) for center-column overview prices.

**Out of scope for initial / placeholder areas:** Full behaviour for Suspend/Display/Limits header actions; Incidents Overview data; Resulted Markets logic; center filters (State/Status, Resulted, “Show only with bets”) beyond presentation; liability columns with real data; Edit/Close/Abandon from this page (those remain Event Navigator placeholders unless linked later).

**Dependencies:** Event Navigator (entry), domain_events, event_mappings, Entities (markets, market groups, templates), brands, margin configuration (PM%), feed_event_details cache (BetsAPI / stored JSON), Market Type Mapping, Feeder Configuration (pricing feed order), internal pricing (IMLog, log2 margin).
