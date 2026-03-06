# Template & route refactoring plan

## Phase 1 – Rename to match UI (done)

- **Event Navigator** (ex Domain Events): templates `domain_events*` → `event_navigator*`, routes `/domain-events` → `/event-navigator`.
- **Margin** (ex Margin Configuration): template `margin_config.html` → `margin.html`, route `/margin-config` → `/margin`.
- All references in layout, main.py and templates updated. API routes (`/api/domain-events`, `/api/search-domain-events`) unchanged (they refer to the domain model, not the page).

## Phase 2 – Group templates by feature (done)

Templates are grouped into feature folders. Final structure:

```
backend/templates/
  layout.html
  modal_mapping.html
  index.html
  event_details.html
  event_navigator/
    event_navigator.html
    _rows.html
    _category_checkboxes.html
    _competition_checkboxes.html
  feeder_events/
    feeder_events.html
    _rows.html
    _sport_checkboxes.html
    _category_checkboxes.html
    _competition_checkboxes.html
  margin/
    margin.html
  archived_events/
    archived_events.html
  configuration/
    entities.html
    brands.html
    feeders.html
    localization.html
    risk_rules.html
```

- In `main.py`, template paths use the folder prefix (e.g. `"event_navigator/event_navigator.html"`, `"configuration/entities.html"`).
- In templates, `{% extends "layout.html" %}` unchanged (layout stays at root). Partials use paths like `{% include 'event_navigator/_rows.html' %}`.
