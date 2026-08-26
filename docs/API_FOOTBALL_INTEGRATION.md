# API-Football integration

**Docs:** [API-Football v3](https://www.api-football.com/documentation-v3)  
**Base URL:** `https://v3.football.api-sports.io`  
**Auth:** header `x-apisports-key` (env `API_FOOTBALL_KEY`)

## Delivery order

| Phase | Scope | Status |
|-------|--------|--------|
| **1** | Fixtures only → Feeder Events + mapping | Shipped locally |
| **2** | Reference: `/odds/bets` + `/odds/bookmakers` catalogs | **Shipped locally** |
| **3** | Odds fetch under fixture → Feed Odds **one row per bookmaker** | **Shipped locally** |
| **4** | Outcome maps / richer market mapper | Planned |
| **5** | Bookmaker allowlist / pricing defaults | Planned |

## Phase 1 — Fixtures

### Feed identity

- Code: `api_football` (`feeds.csv` domain_id **8**)
- Sport: Football (`feed_sports` id `1` → domain `S-1`)
- Event `valid_id` = API-Football `fixture.id`
- Teams/leagues use real numeric IDs (`raw_home_id`, `raw_league_id`)
- Country → `category` (string from `league.country`)

### How to pull fixtures

1. Set `API_FOOTBALL_KEY` in `.env`
2. Restart the app, open **Pull Feeds** → **API-Football**
3. Click **Pull all upcoming** (default: **today → +365 days**)

The API has no single “all future forever” endpoint. We walk `/fixtures?from=&to=` in 14-day chunks from today through the horizon (about ~26 calls for a year). Optional league+season scopes to one competition.

### Stored data

- Normalized events: `backend/data/feed_data/api_football.json`

## Phase 2 — Odds catalogs (bets + bookmakers)

### Design rule

All bookmakers share the same **fixture id** and **bet (market) id**. Market mapping in Entities is **feed-scoped**, not per sportsbook:

- Map `api_football` + bet id `1` (“Match Winner”) → your domain market **once**
- Later (Phase 3+), `/odds?fixture=` returns prices nested under each bookmaker for that same bet id

Do **not** create one feed or one market mapping per bookmaker.

### Endpoints

| API | Stored file | Role |
|-----|-------------|------|
| `GET /odds/bets` | `feed_data/api_football_bets.json` | Feed markets for Entities mapper (`feed_market_id` = bet `id`) |
| `GET /odds/bookmakers` | `feed_data/api_football_bookmakers.json` | Bookmaker id → name (labels for nested odds later) |

Sample offline shapes: `designs/feed_json_examples/api_football_odds_bets.json`, `api_football_odds_bookmakers.json`.

### How to pull catalogs

1. Open **Pull Feeds** → **API-Football**
2. Click **Pull odds catalogs** (2 API calls)
3. Open **Entities** → Markets → Map → select feed **api_football** → Available list is the bets catalog

### Mapper wiring

- `api_football` is in the market mapper feed dropdown
- `/api/feed-markets` loads from the stored bets catalog (or designs sample if not pulled yet)
- Saved mappings use existing `market_type_mappings.csv` (`feed_provider_id` + `feed_market_id`)

## Phase 3 — Fixture odds (Feed Odds = one row per bookmaker)

When a domain event is mapped to `api_football`, opening **Feed Odds** (or mapping the event) fetches:

`GET /odds?fixture={fixture.id}` → cached as `feed_event_details/api_football/{fixture_id}.json`

**Feed Odds UI:** does **not** show a single “API-Football” row. It expands to **one row per bookmaker** (Bet365, Pinnacle, Bwin, …) using the mapped `bet.id` from Phase 2.

Sample: `designs/feed_json_examples/api_football_odds_fixture.json`.

## Open choices (later)

See **`docs/BACKLOG.md`** (API-Football section) for the full idea list. Highlights:

- **AF-PRICE-1:** Feeder Configuration tab — weighted blend vs bookmaker priority for fair odds
- Bookmaker allowlist for Feed Odds  
- In-play (`/odds/live`) timing  
- League allowlist for scheduled pulls  
