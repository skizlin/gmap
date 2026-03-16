# Markets data folder

Market-related CSV files live here. They are **not** cleared by "Dump CSV data" (that only clears entity/relation files under `data/` root). All use 3 columns unless noted: `domain_id`, `code`, `name`.

## market_templates.csv

**Purpose:** Blueprints for market types. Each template defines a reusable pattern (e.g. 2-Way, 3-Way, Spread, Total) and can have a set of params.

**Columns:** `domain_id`, `code`, `name`, `params` (params = optional comma-separated param names, for future use).

**Who maintains it:** Developers. Not creatable from the Create Market Type UI. The form only **selects** a template from the dropdown.

**Used by:** Template dropdown and Template column in the Market Types table (display: name (code)).

---

## market_period_type.csv

**Purpose:** Period types for market types (e.g. Full Time, Half, Set).

**Columns:** `domain_id`, `code`, `name`.

**Who maintains it:** Developers. Not creatable from the Create Market Type UI.

**Used by:** Period Type dropdown and Period Type column in the Market Types table (display: name (code)).

---

## market_score_type.csv

**Purpose:** Score types for market types (e.g. None, Goals, Points, Runs).

**Columns:** `domain_id`, `code`, `name`.

**Who maintains it:** Developers. Not creatable from the Create Market Type UI.

**Used by:** Score Type dropdown and Score Type column in the Market Types table (display: name (code)).

---

## market_groups.csv

**Purpose:** Market groups for grouping market types. Populated from the **Create Market Group** modal (link next to the Market Group dropdown when creating a market type).

**Columns:** `domain_id`, `code`, `name`.

**Who maintains it:** Users can create groups via the modal; developers can also edit the CSV.

**Used by:** Market Group dropdown in Create Market Type form; Market Group column in the Market Types table (display: name (code)).

---

## market_type_mappings.csv

**Purpose:** Stores which feed market (feed_provider_id + feed_market_id) maps to which domain market (domain_market_id), per phase (prematch/live). Used to hide already-mapped feed markets from the “Available markets” list in the Market Mapper.

**Per-environment:** This file is **not** in the repo (see `.gitignore`). Each instance (local, server) has its own. Mapping on the server does not use data from your local machine.

**Columns:** `domain_market_id`, `feed_provider_id`, `feed_market_id`, `feed_market_name`, `phase`.

**Who maintains it:** Users via the Market Mapper UI (Entities → Markets tab → Map on a market).
