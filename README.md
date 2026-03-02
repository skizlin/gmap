# PTC Global Mapper

## 🚀 Quick Start

### Option 1: Double-Click (Windows)
1.  Go to the project folder.
2.  Double-click **`run_server.bat`**.
3.  Wait for "Application startup complete".
4.  Open [http://127.0.0.1:8000/feeder-events](http://127.0.0.1:8000/feeder-events).

### Option 2: Manual Terminal
If the batch file fails, open a terminal in this folder and run:
```bash
pip install -r backend/requirements.txt
python -m backend.main
```

---

## 🛠 Features Implemented
- **Feeder Events Dashboard**: View incoming events from multiple providers.
- **Manual Mapping Modal**: Split-view interface to link Feed Events to Domain Events.
- **Search API**: Smart lookup for domain events (try searching "Manchester").
- **Dark Mode UI**: Fully responsive, glassmorphism design.

## 📂 Project Structure
- `backend/main.py` – FastAPI app, routes, and data loading (single module for now).
- `backend/config.py` – Paths, data dirs, and CSV/entity schema constants.
- `backend/schemas.py` – API request/response models (Pydantic).
- `backend/domain.py` – Domain models (UnifiedEvent, FeederEventDraft, etc.).
- `backend/mock_data.py` – Loads feeder events from `designs/feed_json_examples/`.
- `backend/markets/` – Market-type mapping and feed adapters (Bet365, Bwin, etc.).
- `backend/templates/` – Jinja2 HTML templates.
- `backend/data/` – CSV/JSON data (entities, events, mappings, localization).
- `designs/` – Feed JSON examples and specs.
- `docs/` – Notes and API collections.
- `specs/` – Feature specs.
- `tests/` – E2E tests.
