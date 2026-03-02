# Project structure (pre–initial commit)

## Layout

```
backend/
  main.py          # FastAPI app, all routes, load/save/migrations (still the main module)
  config.py        # Paths, DATA_DIR, entity/market schema constants
  schemas.py       # Pydantic request/response models for API
  domain.py        # Domain models (UnifiedEvent, FeederEventDraft, etc.)
  mock_data.py     # Loads feeder events from designs/feed_json_examples/
  data/            # CSV/JSON persistence (entities, events, mappings, feeds, brands, …)
  templates/       # Jinja2 HTML (layout, feeder/domain events, modal, entities, …)
  markets/         # Market-type mapping, feed adapters (Bet365, Bwin, SBObet, …)

designs/           # Feed JSON examples, prematch samples
docs/              # Notes, API collections, this file
specs/             # Feature specs (mapping, countries, entities)
tests/             # E2E tests (e.g. map modal)
```

## Refactoring done

- **config.py**: All path and schema constants moved out of `main.py` so they can be reused and so `main` is less cluttered.
- **schemas.py**: All Pydantic API models (CreateEntityRequest, UpdateEntityNameRequest, etc.) moved here so routes stay in `main` but models are in one place.
- **.gitignore**: `.pytest_cache/` added.

## Possible next steps (optional)

- **Data layer**: Move `_load_*`, `_save_*`, `_migrate_*` from `main.py` into a `backend/data_layer.py` (or `backend/repository.py`) and have `main` import and call them. Keeps persistence in one module.
- **Routers**: Split routes by area (e.g. `backend/routes/feeder_events.py`, `domain_events.py`, `entities.py`, `api.py`) and register them with `app.include_router(...)`. Requires passing or importing shared state (DOMAIN_ENTITIES, ENTITY_FEED_MAPPINGS, etc.).
- **Templates**: Current structure (partials with `_` prefix, one folder) is fine; optional subfolders like `templates/entities/`, `templates/events/` only if the number of templates grows a lot.

These can be done later; the current split (config + schemas) is enough for a clean initial commit.
