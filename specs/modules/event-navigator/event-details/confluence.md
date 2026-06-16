# Event Details — Confluence (module overview)

**Module:** Event Details (under Event Navigator)  
**Route:** `/event-navigator/event_details/{domain_id}`  
**Entry:** Event Navigator → Event column (new tab) or Action → View Event

---

## Purpose

Show **one domain event** in an operator workspace: which feeds are mapped, which **domain markets** apply to the event’s sport, and **odds comparison** (feed vs brand vs internal model) for the market and line the user selects. Used for pricing review and troubleshooting mapping/odds alignment—not for creating or editing the domain event mapping (that remains Feeder Events + Mapping Modal).

---

## Page and layout

- **Shell:** Standard backoffice layout; **no** standard page title row (`page_header` hidden) so the event header is the primary title area.
- **Event header card:** Event name (Home v Away), breadcrumb-style metadata (sport / category / competition / domain ID), status badge (e.g. Not Started), start time, placeholder prematch/live stats (Bets, Turnover, P/L).
- **Header actions (placeholders):** (S) Suspend, (D) Display, (L) Limits.
- **Pricing brand:** Dropdown (Global + configured brands); drives **Markets Overview** margined prices in the center column.
- **Three-column body (desktop):** Left ~2fr | Center ~6.4fr | Right ~3.6fr (responsive stack on small screens).

| Column | Panels |
|--------|--------|
| **Left** | **Markets** (grouped checkboxes), **Resulted Markets** (placeholder) |
| **Center** | **Markets Overview** (selected markets as rows; radio = active market for odds panels) |
| **Right** | **Incidents Overview** (placeholder), **Brand Overview**, **Feed Odds**, **Internal Model**, **Mapped Feeds** |

---

## Left column — Markets

- Markets loaded from configuration, **filtered by event sport** (`sport_id` on domain event).
- Grouped by **market group** (e.g. Main, Goals); each group has a **group checkbox** (select/deselect all markets in group).
- Each market: checkbox, name, optional abbreviation (`abb`).
- Market metadata on checkbox: `domain_id`, name, code, template, outcome type/count, has-line flag, outcome labels (JSON).
- **Resulted Markets:** Section present; “logic will be implemented later.”

---

## Center column — Markets Overview

- Empty state: “Select markets from the left to show them here.”
- When markets are checked on the left, each appears as a row in the overview with:
  - Market name and controls appropriate to template (e.g. line buttons for handicap/total).
  - **Radio** in row header: selects the **active market** for Brand Overview, Feed Odds, and Internal Model.
- Overview prices: loaded via API using **pricing brand** (Global or brand id) and optional **line**; shows margined outcome columns (S1–S6, L where applicable).
- Top bar (presentation): State/Status dropdown, Resulted dropdown, “Show only with bets” checkbox—not fully wired in initial version.

---

## Right column — Odds and feeds

### Brand Overview

- Requires **active market** (radio selected in center).
- Table: one row per brand; columns **L** (line), **S1–S6** (selections), **M** (implied margin % from displayed prices), **Liab.** (placeholder).
- Data: `GET /api/event-details/brand-overview-margined` — fair odds from pricing feed / IMLog → log2 margined per brand using PM% from margin templates.

### Feed Odds

- Requires **active market**.
- Table: one row per **mapped feed** that has cached event details; columns L, S1–S6, M.
- Data: `GET /api/event-details/feed-odds` — `all_lines` default true (multi-line markets list each line per feed); optional `line` for single line.
- Sources: `backend/data/feed_event_details/{feed_code}/{feed_valid_id}.json` (populated on create/map via BetsAPI background fetch).

### Internal Model

- Requires **active market**; sport/market-specific (e.g. Volleyball Correct Set Score).
- Data: `GET /api/event-details/internal-model` — de-vig/average across feeds where implemented.

### Mapped Feeds

- Static table from `event_mappings.csv`: feed provider code + feed event ID per row.
- No selection required.

### Incidents Overview

- Placeholder: “No match statuses available.”

---

## APIs (Event Details)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/event-navigator/event_details/{domain_id}` | Full page HTML |
| GET | `/api/event-details/feed-odds` | Feed odds rows for domain event + market (+ line, all_lines) |
| GET | `/api/event-details/brand-overview-margined` | Margined prices per brand |
| GET | `/api/event-details/overview-margined-prices` | Center overview margined prices (pricing brand scope) |
| GET | `/api/event-details/internal-model` | Internal model rows when supported |

Query params: `domain_event_id`, `domain_market_id`, optional `line`, `pricing_brand_id`, `all_lines`, `market_name` (internal model).

---

## Business rules

- **404:** Unknown `domain_id` → HTTP 404.
- **Markets scope:** Only markets for the event’s sport appear on the left.
- **Active market:** Exactly one overview row should be “active” via radio for right-column odds; changing radio refreshes Feed Odds, Brand Overview, Internal Model.
- **Mapped feeds only:** Feed Odds shows feeds linked in `event_mappings` for this domain event; odds come from cached details, not live pull on every click (background fetch on map/create).
- **Pricing brand:** Empty / Global uses global margin scope; numeric brand id uses that brand’s PM% for overview margined prices.
- **Green/red elsewhere:** Not applicable on this page; mapping highlight rules apply on Feeder Events only.

---

## User journey / process flow

1. User is on **Event Navigator** → clicks **Event** cell or **View Event** → Event Details opens in **new tab**.
2. Page loads event header, market list (by group), Mapped Feeds table, empty overview and odds panels.
3. User checks one or more markets on the left → rows appear in **Markets Overview**.
4. User selects **radio** on one overview row (and line if applicable) → **Brand Overview**, **Feed Odds**, **Internal Model** load for that market.
5. User changes **Pricing brand** → center overview prices refresh for active market.
6. User toggles group/market checkboxes → overview rows add/remove; active market logic follows last selection rules in UI.

---

## Assumptions / constraints

- **Cached event details:** Requires prior map/create (or manual files under `feed_event_details/`); token from `.env` (`BETSAPI_TOKEN`) for fetch.
- **Bwin L2 / prematch:** Special handling for bwin_l2 and stored snapshots (see `docs/BWIN_L2_STORAGE_AND_LIVE_ODDS_FUTURE.md`).
- **IMLog:** Internal pricing may write/read `feed_event_details/imlog/{domain_event_id}.json`.
- **Not a list page:** No shared table footer/pagination; different layout from Event Navigator list (documented under Backoffice table system for list pages only).

---

## NFRs

- **Performance:** Odds APIs should respond within acceptable time for one event; large `all_lines` responses may be heavy—use line filter when needed.
- **New tab:** Event link uses `target="_blank"` so operators can keep Event Navigator open.
- **Consistency:** Outcome column headers (S1–S6, L) align across Brand Overview, Feed Odds, Internal Model, and Overview where the same market template applies.

---

## Data and tech (demo site)

| Area | Demo implementation | Production note |
|------|---------------------|-----------------|
| Domain event | `domain_events` in memory + CSV | DB |
| Mappings | `event_mappings.csv` | DB |
| Markets / groups | `markets.csv`, groups config | DB |
| Feed details cache | `data/feed_event_details/{feed}/{id}.json` | Object store or DB |
| Brands | `brands.csv` | DB |
| Margins | Margin templates / PM% resolution in code | Config service |
| Page template | `event_details.html` + client JS | Same pattern |

---

## Out of scope (this page)

- Creating or editing domain event mapping (Feeder Events + Mapping Modal).
- Event Navigator notes (separate modal on list page).
- Full incident/match state integration.
- Resulted markets settlement UI.
- Header Suspend/Display/Limits implementation (placeholders).

---

## Related specs

- **Event Navigator** — List, filters, entry to Event Details.
- **Feeder Events** — Mapping; triggers event-details fetch on map/create.
- **Mapping Modal** — Create & Map / Confirm Mapping.
- **Entities / Markets** — Domain market definitions and groups.
- **Margin Configuration** — PM% for brand overview.
- **Market Type Mapping** — Feed market ↔ domain market.
- **Backoffice** — Shell, nav, permissions (`menu.betting_program.event_navigator.view`).
