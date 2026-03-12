# Feed Integration Plan — PTC Global Mapper

**Role:** Feed Integration Developer  
**Goal:** Replace static JSON files with live API integration using your API keys, links, and provider documentation.

---

## 1. Current State (Summary)

### 1.1 Data flow today
- **Feeds** are defined in `backend/data/feeds.csv` (betfair, bwin, bet365, 1xbet, b365racing).
- **Static JSON** lives in `designs/feed_json_examples/` (e.g. `bet365.json`, `bwin.json`).
- **`backend/mock_data.py`**:
  - `load_all_mock_data()` reads those files and returns a list of events.
  - **Two parsers:**
    - **Unified format** (bet365, betfair, 1xbet): `results[]` with `id`, `sport_id`, `time`, `league`, `home`, `away`, etc.
    - **Bwin-specific**: `results[]` with `Id`, `SportName`, `RegionName`, `LeagueName`, `HomeTeam`, `AwayTeam`, `Date`, `Markets`, `IsOutright`, etc.
- **`backend/main.py`**:
  - At startup: `DUMMY_EVENTS = load_all_mock_data()` (in-memory).
  - All feeder views and the mapping modal use `DUMMY_EVENTS`; mapping status is synced from `event_mappings.csv`.

### 1.2 Unified event shape (after parsing)
Every parsed event has: `feed_provider`, `valid_id`, `domain_id`, `raw_home_name`, `raw_away_name`, `raw_home_id`, `raw_away_id`, `raw_league_name`, `raw_league_id`, `category`, `category_id`, `start_time`, `time_status`, `sport`, `sport_id`, `betradar_id`, `is_outright`, `market_name`, `is_mainbook`, `updated_at`, `mapping_status`.

### 1.3 Dependencies
- `httpx` is already in `requirements.txt` — suitable for async HTTP to feed APIs.

---

## 2. What I Need From You

Before implementing, please provide **per feed** (or per API family):

1. **API base URL(s)** — e.g. `https://api.provider.com/v1`
2. **Authentication** — e.g. API key header name and value, or Bearer token, or other (per provider).
3. **Documentation** — link to API docs (or a short description of endpoints for “events” / “fixtures” and any pagination).
4. **API key(s)** — we will **not** hardcode these; they will go in environment variables or a secure config (see below).

If multiple feeds use the **same API** (e.g. one vendor supplying bet365, betfair, 1xbet), one set of URL + auth + docs is enough and we can distinguish by a parameter or path.

---

## 3. Recommended Implementation Plan

### Phase 1 — Configuration and security
- **1.1** Add a **config module** (e.g. `backend/config.py`) that reads:
  - Feed API base URLs (e.g. `FEED_BET365_BASE_URL`, or a single `FEED_API_BASE_URL` if shared).
  - API keys (e.g. `FEED_API_KEY`, or per-provider keys).
  - Values from **environment variables** (and optional `.env` via `python-dotenv`), so keys are never committed.
- **1.2** Optionally extend `feeds.csv` or add a small **feed_config** (e.g. JSON/CSV) to store per-feed: `code`, `base_url`, `auth_type`, `env_key_name` — so adding a new feed is a config change, not code.

### Phase 2 — HTTP client and fetch layer
- **2.1** Introduce a **feed client** (e.g. `backend/feed_client.py` or `backend/feeds/client.py`):
  - Use `httpx.AsyncClient` for async GET requests.
  - One function per API shape, e.g. `fetch_unified_events(provider_code, base_url, api_key)` and `fetch_bwin_events(base_url, api_key)`.
  - Apply auth (header or query param) from config.
  - Parse **pagination** from provider docs (e.g. `page`, `per_page` in bet365) and either:
    - Fetch all pages in a loop, or
    - Expose a “max_pages” or “max_events” limit for safety.
- **2.2** Map provider-specific responses into the **existing unified event shape** so the rest of the app stays unchanged. Reuse current parsers where possible:
  - For “unified” APIs: keep `parse_unified` logic but accept a **dict** (from `response.json()`) instead of reading from a file path.
  - For bwin: keep `parse_bwin` logic but accept a dict instead of a file path.

### Phase 3 — Replace file load with API fetch
- **3.1** Change **`mock_data.py`** (or rename to something like `feed_loader.py`):
  - Add functions that **call the feed client** and get JSON (e.g. `fetch_events_bet365()`, `fetch_events_bwin()`).
  - Pass the response body into the existing parsers (so they take `data: dict` instead of `file_path`).
  - Keep **fallback to static files** when:
    - No API key/URL is configured for that feed, or
    - A “use_mock” or “offline” flag is set (e.g. for dev/demos).
- **3.2** In **`main.py`**:
  - Replace the one-off `DUMMY_EVENTS = load_all_mock_data()` with a **single place** that:
    - Calls the new “load from API (or fallback to file)” loader, and
    - Still produces the same list-of-dicts format and assigns it to the same in-memory variable (e.g. still `DUMMY_EVENTS` for minimal change), **or**
  - Introduce a small **cache** (e.g. in-memory with TTL, or a background task that refreshes every N minutes) so we don’t hit the API on every request. Recommendation: start with “load once at startup + optional manual refresh endpoint,” then add TTL/background refresh if needed.

### Phase 4 — Error handling and resilience
- **4.1** In the feed client:
  - Timeouts (e.g. 30s per request).
  - Retries (e.g. 2–3 retries with backoff) for 5xx or network errors.
  - If a feed fails, **log and return partial data** (e.g. other feeds still populate the list) or an empty list for that provider so the UI doesn’t break.
- **4.2** Optional: **health endpoint** (e.g. `/health/feeds`) that reports per-feed status (OK / failed / no config).

### Phase 5 — Optional improvements
- **5.1** **Refresh endpoint**: e.g. `POST /api/feeds/refresh` to re-fetch all feeds and update in-memory (or cache), so you can refresh without restarting the server.
- **5.2** **Per-feed enable/disable** in config so you can turn off a provider without removing code.
- **5.3** If the provider uses **webhooks** or **delta updates**, we can add a separate small handler later; the plan above assumes “pull” (we call their API).

---

## 4. Suggested file layout (after implementation)

```
backend/
  config.py              # Env-based config (URLs, API keys)
  feed_client.py         # Async HTTP fetch per API type (unified vs bwin)
  feed_loader.py         # Replaces mock_data for “load”: calls client, then parsers
  mock_data.py           # Kept for fallback: file-based load + existing parsers
  main.py                # Uses feed_loader (with fallback to mock_data when no config)
  data/
    feeds.csv            # Unchanged
  ...
designs/
  feed_json_examples/    # Kept for tests and fallback
  ...
docs/
  FEED_INTEGRATION_PLAN.md  # This file
```

Parsers can stay in `mock_data.py` (and be called with a dict) or be moved to `feed_loader.py` / a small `feed_parsers.py` — your choice; the plan only requires that the **output** remains the same list of dicts with the unified event shape.

---

## 5. Next steps

1. **You:** Send API base URL(s), auth method (and header/param names), docs links, and how you want to provide API key(s) (e.g. env var names).
2. **Me:** Implement Phase 1 (config) and Phase 2 (feed client + pagination), then Phase 3 (wire to load and optional fallback). We can do Phase 4 in the same pass or right after.
3. **You:** Add the API key(s) to your environment (or `.env`) and run the app; we verify one feed first (e.g. bet365 or bwin), then repeat for the rest.

If you already have docs or a Postman collection, sharing the exact “events” endpoint path and a sample response (with secrets redacted) will speed up the client implementation.
