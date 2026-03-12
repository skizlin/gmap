# BetsAPI Postman Collection vs feed_json_examples — Analysis (Updated)

**File:** `docs/BetsAPI.postman_collection.json`  
**Status:** All request URLs and auth are present. Ready for implementation.

---

## 1. API endpoints (from Postman)

**Base host:** `https://api.b365api.com`  
**Auth:** API key sent as **query parameter** `token` (collection-level). Use env var in code; do not commit the real key.

| Feed        | Method | Path                     | Query params        | Full URL (token placeholder) |
|------------|--------|--------------------------|---------------------|------------------------------|
| **Bet365** | GET    | `/v1/bet365/upcoming`    | `sport_id=1`, `token` | `https://api.b365api.com/v1/bet365/upcoming?sport_id=1&token=YOUR-TOKEN` |
| **bwin**   | GET    | `/v1/bwin/prematch`      | `token`            | `https://api.b365api.com/v1/bwin/prematch?token=YOUR_TOKEN` |
| **Betfair (Sportsbook)** | GET | `/v1/betfair/sb/upcoming` | `sport_id=1`, `token` | `https://api.b365api.com/v1/betfair/sb/upcoming?sport_id=1&token=YOUR-TOKEN` |
| **1xBet**  | GET    | `/v1/1xbet/upcoming`     | `sport_id=1`, `token` | `https://api.b365api.com/v1/1xbet/upcoming?sport_id=1&token=YOUR-TOKEN` |

**Notes:**

- **Betfair SB:** Path `betfair/sb/upcoming` — **SB = Sportsbook**. Betfair has Sportsbook and Exchange; we use the Sportsbook endpoint.
- **sport_id=1:** Used for Bet365, Betfair (SB), 1xBet (typically Soccer). The JSON examples contain multiple sports; to match that we may need to call the API per sport (e.g. 1, 18, 13) or check if the API supports “all sports” (e.g. omit `sport_id` or use a special value). Implementation can start with `sport_id=1` and then extend.
- **bwin:** No `sport_id` in the request; response likely includes all sports (as in bwin.json).

---

## 2. Feed coverage: collection vs code vs examples

| Feed       | Postman request   | In `feeds.csv` | In `load_all_mock_data()` | JSON example  |
|-----------|-------------------|----------------|----------------------------|---------------|
| Bet365    | ✅ Events Bet365  | ✅ bet365      | ✅ unified                 | ✅ bet365.json |
| bwin      | ✅ Events bwin    | ✅ bwin        | ✅ bwin parser             | ✅ bwin.json   |
| Betfair (Sportsbook) | ✅ Events BetFairSB | ✅ betfair | ✅ unified | ✅ betfair.json |
| 1xBet     | ✅ Events 1xBet  | ✅ 1xbet       | ✅ unified                 | ✅ 1xbet.json  |
| b365racing| ❌               | ✅ b365racing  | ❌                         | ✅ b365racing.json |

We have URLs for all five feeds currently loaded by the app. b365racing has no Postman request; can be added later if the API exposes it (e.g. `/v1/bet365/racing/upcoming` or similar).

---

## 3. Response shape vs parsers (unchanged)

### 3.1 Unified format (Bet365, Betfair Sportsbook, 1xBet)

- **API response:** `success`, `pager` (page, per_page, total), `results[]` with `id`, `sport_id`, `time`, `time_status`, `league`, `home`, `away`, etc.
- **Parser:** `parse_unified()` expects this shape. **Match.** Pagination must be handled in the client (loop over pages or cap).

### 3.2 Bwin format

- **API response:** `results[]` with `Id`, `SportName`, `RegionName`, `LeagueName`, `Date`, `HomeTeam`, `AwayTeam`, `Markets`, `IsPreMatch`, etc.
- **Parser:** `parse_bwin()` matches for match events. For **outrights**, the parser expects `IsMainbook` and `Name` on markets; the bwin.json example uses `isMain` and `name` (object with `value`). **Adapter needed:** treat `isMain` as mainbook and use `name.value` (or `name`) as market name when building the unified event.

---

## 4. Implementation checklist (from this analysis)

| Item | Action |
|------|--------|
| Base URL | `https://api.b365api.com` (from collection) |
| Auth | Query param `token`; value from env (e.g. `BETSAPI_TOKEN`) |
| Per-feed path + query | Use table in §1; build URL per feed (and optionally per `sport_id` when we support multiple sports) |
| Pagination | Unified responses have `pager`; client should loop pages (or respect a max) |
| bwin market fields | In parser/adapter: support `isMain` and `name.value` for outright main market |
| Betfair SB endpoint | Map to provider code `betfair` (Sportsbook only; Exchange not used) |

---

## 5. Security

The exported collection still contains a literal API key in the `auth` section. For the repo:

- Prefer **not** committing the real key. Use a Postman environment variable (e.g. `{{token}}`) and re-export, or add the collection to `.gitignore` if it contains secrets.
- In the app, read the token from an environment variable (e.g. `BETSAPI_TOKEN`) and never hardcode it.

---

## 6. Summary

- **URLs:** All five feeds have full URLs in the Postman collection; base is `https://api.b365api.com`, paths and query params are clear.
- **Auth:** Query param `token`; ready to wire to env.
- **Parsers:** Unified feeds align with existing parsers; bwin match events align; bwin outright markets need a small adapter for `isMain` / `name.value`.
- **Next:** Implement config (env for base URL and token), HTTP client (one request per feed URL, with pagination for unified), and feed loader that uses the client and existing parsers (with bwin market adapter). Fallback to static JSON when token is missing or in offline mode.
