# E2E tests

## Map modal (Map → Cancel → Map)

Tests in `test_map_modal_reopen.py` check that the Map Event modal works after closing and reopening:

- **test_map_modal_first_open_has_sport_control** – First open has sport control.
- **test_map_modal_after_cancel_reopen_is_usable** – Map → Cancel → Map: modal is usable the second time (sport control and scripts run again).
- **test_map_modal_console_no_errors** – No JS errors during the flow.

## Run

1. Start the app: `python -m backend.main` (or `run_server.bat`). Wait for "Application startup complete".
2. Install deps: `pip install -r tests/requirements-e2e.txt` and `python -m playwright install chromium`.
3. Run: `pytest tests/e2e/ -v` (or `python -m pytest tests/e2e/ -v`).

Optional: `HEADLESS=1` for headless; omit for a visible browser. Use `-s` to see print output.
