# Countries Reference & Entity Country Assignment

**Status:** Proposal  
**Scope:** Shared countries list (ISO-style) and optional `country_id` on Categories, Competitions, and Teams.

---

## 1. Goal

- **Categories** are often countries (e.g. Argentina, England) but sometimes not (e.g. Europe, International, UEFA).
- **Teams** should have a country (e.g. home country).
- **Competitions** should have a country where it makes sense; when category/competition is not country-based, it should be overridable.
- Use a **single shared countries list** (ISO-style) across the platform so every part (Entities, Mapping, Domain Events, etc.) uses the same reference.

---

## 2. Recommended Approach: Reference Table + Optional FK

### 2.1 Countries as reference data (not created from feeds)

- Add a **countries** reference that is **shared across the platform**.
- **Do not** create countries from feeds or from the mapping modal; they are **lookup/reference only**.
- Source: **ISO 3166-1** (or a subset). One canonical file, e.g. `backend/data/countries.csv` or a bundled JSON/list loaded at startup.
- Suggested schema for the reference:
  - `domain_id` (int, primary key)
  - `name` (e.g. "Argentina")
  - `code_2` (ISO 3166-1 alpha-2, e.g. "AR")
  - `code_3` (optional, alpha-3, e.g. "ARG")
- This file is **seeded once** (e.g. from ISO list) and can be extended manually if needed (e.g. "Kosovo", "England" as separate from "United Kingdom" for sport). No feed columns; no entity_feed_mappings for countries.

### 2.2 Categories: optional link to country

- **Keep** category creation as today: user creates a category by **name** under a **sport** (and we can link a feed to it via entity_feed_mappings).
- Add optional **`country_id`** (FK → countries) on categories.
  - When the category **is** a country (e.g. "Argentina"): set `country_id` to the corresponding country. Display name can stay "Argentina"; the link is for consistency and filtering.
  - When the category is **not** a country (e.g. "UEFA", "International", "Europe"): leave `country_id` **null**. No override needed — "not a country" is represented by null.
- **Do not** auto-create categories from the ISO list. We still create categories on demand (from mapping or Entities page); we only **optionally link** an existing category to a country from the shared list.
- UX: When creating/editing a category: optional dropdown **"Country (optional)"** with the full countries list; option "— None / Not a country —" for non-country categories.

### 2.3 Competitions: optional country, with sensible default

- Add optional **`country_id`** (FK → countries) on competitions.
- **Default behaviour:** When the category has a `country_id`, pre-fill the competition’s country with that (suggested default). User can **override**:
  - Keep it (same as category).
  - Change to another country (e.g. cross-border league).
  - Clear to "None" for international competitions (e.g. Champions League).
- So: competitions can have their own country, or inherit from category, or be null.

### 2.4 Teams: optional (or required) country

- Add optional **`country_id`** (FK → countries) on teams.
- Represents the team’s **home country**.
- Can be required later in UI/validation if desired; start as optional for backward compatibility.

---

## 3. Override semantics (summary)

| Entity       | Has country?        | Override / notes                                      |
|-------------|----------------------|--------------------------------------------------------|
| **Category**| Optional `country_id`| Null = "not a country" (e.g. Europe, International).   |
| **Competition** | Optional `country_id` | Pre-fill from category when category has country; user can change or clear. |
| **Team**    | Optional `country_id`| User picks country (team’s home country).              |

No separate "override" flag is needed: **null** means "no country" or "not applicable".

---

## 4. Implementation outline

1. **Countries reference**
   - Add `countries.csv` (or equivalent) with ISO-style list; add loader in `main.py` (e.g. `COUNTRIES` or `COUNTRIES_BY_ID`) and expose to templates/APIs.
   - Option: use a minimal list (e.g. FIFA countries) or full ISO 3166-1; can start minimal and expand.

2. **Schema changes**
   - **categories**: add `country_id` (optional int, FK to countries).
   - **competitions**: add `country_id` (optional int).
   - **teams**: add `country_id` (optional int).
   - Migration: existing rows get `country_id` null; new/edited rows can set it.

3. **Entities page (Configuration → Entities)**
   - Category form: optional "Country" dropdown (countries list); "— None —" for non-country.
   - Competition form: optional "Country" dropdown; optionally pre-fill from selected category’s country when category has one.
   - Team form: optional "Country" dropdown.
   - Tables: show country name (from countries reference) when `country_id` is set.

4. **Mapping modal**
   - When creating a category/competition/team from the modal, optional country can be added later on the Entities page, or we can add an optional country dropdown in the modal in a follow-up.

5. **Domain events / reporting**
   - Domain events store category and competition **names** (and team names). For "country" in reports or filters, resolve via category’s or competition’s or team’s `country_id` using the shared countries list.

---

## 5. Alternative considered: Categories = countries only

- **Idea:** Every category is a country; non-country groupings (Europe, International) are a different concept (e.g. "region" or "confederation").
- **Downside:** Bigger model and UI change; feeds often send "Argentina" or "Europe" in the same "category" field, so we’d still need a single category-like entity with optional link to country. So the recommended approach (optional `country_id` on categories) is simpler and fits "categories are sometimes countries, sometimes not."

---

## 6. File to use for the ISO list

- Common choice: **ISO 3166-1** (countries). You can maintain a single CSV, e.g. `backend/data/countries.csv`, with columns e.g. `domain_id,name,code_2,code_3`.
- Seed it once from an authoritative source (e.g. [ISO 3166-1](https://en.wikipedia.org/wiki/ISO_3166-1) or a JSON/CSV export). The platform then **reads** this file; creation/editing of the list itself can be admin-only or manual.
- If you need sport-specific variants (e.g. "England" vs "United Kingdom"), add those as extra rows in the same file with a note, or add an optional `sport_id` later; for now a single shared list is enough.

---

**Summary:** Use one **countries reference** (ISO-style list) and add optional **`country_id`** to categories, competitions, and teams. Categories and competitions can be "not a country" by leaving `country_id` null; competitions can override category’s country; teams get their own country. This keeps a single source of truth for countries and avoids creating categories from the ISO list.
