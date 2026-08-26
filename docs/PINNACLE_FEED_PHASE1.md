# Pinnacle feed (Phase 1 + Phase 2 + multi-sport)

## What is supported

- Feed code: `pinnacle` (feeds.csv domain_id **7**)
- Sport + competition + event use real IDs (`sport_id`, `league_id`, `event_id`)
- Teams have **no** IDs: synthetic keys for `entity_feed_mappings`
- Prematch/inplay: when `parent_id` is set, `valid_id` = `parent_id` (canonical prematch)
- **All sports:** `feed_sports.csv` is seeded with known Pinnacle sport ids; ingest also **auto-adds** any new `sport_id` found in your dump
- Sport → domain mappings: `sport_feed_mappings.csv` (e.g. `29` → Football `S-1`, `33` → Tennis `S-2`, …)

## Team feed key

```
{normalized_runner}|u:{underage}|s:{sport_id}
```

Examples:

- Senior soccer: `parnu vaprus|u:0|s:29`
- U19: `parnu vaprus|u:19|s:29`

## How to load **real** data (all sports)

There is **no live Pinnacle HTTP pull yet**. Use a native JSON dump:

1. Export / save your real events as a JSON **array** (same fields as the sample: `sport_id`, `sport_name`, `league_id`, `league_name`, `event_id`, `starts`, `runner_home`, `runner_away`, `live_status`, `parent_id`, …).
2. Save the file as:
   ```
   backend/data/feed_data/pinnacle_raw.json
   ```
3. Restart the app (so sport mappings reload):
   ```powershell
   cd "c:\Users\SinisaKizlin\python_project\PTC Global Mapper - Cursor"
   python -m backend.main
   ```
4. Open http://127.0.0.1:8000/pull-feeds
5. Under **Pinnacle**:
   - Tick **Replace stored events** if you want to drop the old sample and load the full dump cleanly
   - Click **Ingest all sports**
6. Open http://127.0.0.1:8000/feeder-events → feed **pinnacle** → filter by sport as needed

Optional: use a per-sport **Ingest** button to load only one `sport_id` from the same file.

## Sample file

`designs/feed_json_examples/pinnacle_raw.json` — small Soccer-only sample for format checks.

## Phase 2 — Manual Map forever

1. Sport resolves from `sport_feed_mappings` (developer seed).
2. Competition / team **Map** persists feed ids immediately (`POST /api/entities`).
3. Team keys and underage (U19 vs senior) stay separate forever once mapped.

## Live API (not wired yet)

To pull from a live API instead of a file, send:

1. Base URL + path(s) (fixtures / events)
2. Auth (header or query param name)
3. How sports are listed (one call for all sports vs one call per `sport_id`)
4. Env var name for the key (do not paste the key into chat)

Then we can add a Pull button like Bet365/Bwin.
