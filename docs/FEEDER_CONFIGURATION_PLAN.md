# Feeder Configuration — Analysis & Implementation Plan

**Source document:** `docs/QNX Admin Manual - Feeder Configuration.pdf`  
**Status:** PDF present in repo; content not machine-readable here. Plan below is based on repo context and the same pattern used for Market Types.

---

## 1. Document analysis (limitation)

- The file **QNX Admin Manual - Feeder Configuration.pdf** is in `docs/` (~942 KB).
- **I cannot read PDF content** from the tooling (no PDF library in the project). So I have not seen the exact screens, filters, table columns, or forms described in the manual.
- For **Market Types**, the approach was to create a **markdown spec** (`docs/MARKET_TYPES_QNX.md`) that describes the PDF (filters, table, create form, actions). Implementation then followed that spec.

**Recommendation:** Create **`docs/FEEDER_CONFIGURATION_QNX.md`** by extracting the structure from the PDF (same style as `MARKET_TYPES_QNX.md`): sections for top filters/actions, table columns, create/edit form fields, and any modals (e.g. mapping, credentials). Once that exists, implementation can match the manual and we can refine this plan if needed.

---

## 2. Agreed scope (from your message)

- Add **Feeder** (or **Feeders**) to the **Configuration** menu, at the **bottom** of the dropdown.
- Current Configuration menu: **Entities** → **Localization** → **Brands**. After change: **Entities** → **Localization** → **Brands** → **Feeder** (or **Feeders**).
- No implementation to start until we agree on this plan.

---

## 3. Current state in the app

- **Feeds** are stored in `backend/data/feeds.csv`: columns `domain_id`, `code`, `name` (e.g. Betfair, Bwin, Bet365, 1xBet, SBOBET).
- **Loaded at startup** in `main.py` via `_load_feeds()` into `FEEDS`; used everywhere we need feed list (mapping modal, entity_feed_mappings, market type mappings, etc.).
- **No UI** today to manage feeders: the list is effectively static/config-driven.
- **FEED_INTEGRATION_PLAN.md** mentions future per-feed config: base URL, API keys (env), auth type, etc. A Feeder Configuration page could later hold that.

---

## 4. Tentative implementation plan (to be aligned with the PDF spec)

Until we have `FEEDER_CONFIGURATION_QNX.md`, the following is a **draft** and will be adjusted to match the manual.

### 4.1 Menu

- In **`backend/templates/layout.html`**, inside the Configuration dropdown, add a new link after **Brands**:
  - Label: **Feeder** (or **Feeders**, per your preference).
  - Link: **`/feeders`** (or `/configuration/feeders` if you prefer a path under configuration).
  - Icon: e.g. `fa-satellite-dish` (consistent with “Feeder Events”) or another from the manual.
- Set `section == 'feeders'` (or similar) so the nav highlights when on that page.

### 4.2 New route and page

- **Route:** e.g. `GET /feeders` (or `GET /configuration/feeders`) rendering a Feeder Configuration page.
- **Template:** e.g. `feeders.html` (or `configuration/feeders.html`), extending the same layout as Entities/Localization/Brands (breadcrumb: Configuration → Feeder).
- **Data:** Pass current list of feeders (from `feeds.csv` / `FEEDS`) to the template so the page can show at least a read-only list. If the PDF specifies filters (e.g. by source, status), we add them when the spec is known.

### 4.3 Page content (to be confirmed from PDF)

- **If the manual is mainly a table of feeders:**  
  Table with columns as per the manual (e.g. Code, Name, Source type, Status, Order, Actions).  
  - **Read-only first step:** Show rows from `feeds.csv` with columns we already have (`domain_id`, `code`, `name`) plus placeholders for any extra columns from the spec.  
  - **Later:** Add/create/edit/delete when the spec and data model are agreed (e.g. new columns in `feeds.csv` or a separate config store).

- **If the manual includes a “Create / Edit Feeder” form:**  
  - Add a “+ Create Feeder” (or “Add Feeder”) button and a form (modal or inline) with fields from the spec.  
  - Backend: `POST /api/feeders` (create) and `PUT /api/feeders/{id}` (update), persisting to `feeds.csv` or to the structure defined in the spec.  
  - Validation and uniqueness (e.g. on `code`) as in the manual.

- **If the manual includes extra concepts** (e.g. “Feeder sources”, “Feeder types”, mapping to market types, credentials):  
  - Represent them in the spec (`FEEDER_CONFIGURATION_QNX.md`) and we add the corresponding UI and data in a follow-up phase.

### 4.4 Data model (to be confirmed)

- **Current:** `feeds.csv` = `domain_id`, `code`, `name`.
- **Possible extensions** (only if in the manual): e.g. `source`, `is_active`, `sort_order`, `base_url`, `auth_type`, etc. Any new columns would be added in a backward-compatible way (migration/defaults) and documented in the spec.

### 4.5 Implementation order (once we agree)

1. **Spec (recommended first):** Create `docs/FEEDER_CONFIGURATION_QNX.md` from the PDF (filters, table, form, actions).
2. **Menu:** Add “Feeder” at the bottom of the Configuration dropdown in `layout.html`.
3. **Route + stub page:** Register `GET /feeders` and a minimal `feeders.html` that shows “Feeder Configuration” and the current feeders table (columns from spec or minimal: ID, Code, Name).
4. **Refine from spec:** Add filters, buttons, create/edit form, and API endpoints to match `FEEDER_CONFIGURATION_QNX.md`.

---

## 5. Summary

| Item | Proposal |
|------|----------|
| **Menu** | Add **Feeder** at the bottom of **Configuration** (after Brands). |
| **URL** | `/feeders` (or `/configuration/feeders`). |
| **Spec** | Create **`docs/FEEDER_CONFIGURATION_QNX.md`** from the PDF so implementation matches the manual (as with Market Types). |
| **First deliverable** | Menu entry + route + page that lists feeders from `feeds.csv`; then extend with filters/form/actions per spec. |
| **Next step** | You confirm this plan and, if possible, add the markdown spec from the PDF. Then implementation can start. |

No code changes will be made until you confirm.
