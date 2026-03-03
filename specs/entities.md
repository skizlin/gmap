# Entities — Spec

---

## Feature

**Entities** is the configuration area for **domain reference data**: Sports, Categories, Competitions, Teams, Markets. Users create, edit, and view these entities and their **feed links** (which feed IDs map to which domain entity). Used by Mapping Modal and Domain Events for resolution and display.

**Related:** Mapping Modal Tool (creates entities + feed links), Domain Events (displays entity names), Feeder Events (green highlighting uses entity_feed_mappings), Margin Configuration (templates ↔ competitions).

---

## Problem Statement

- Domain model requires canonical sports, categories, competitions, teams, and markets.
- Multiple feeds use different IDs and names for the same real-world entity; a single domain entity can be linked to several feed IDs (multi-feed).
- Without a central place to manage entities and feed links, mapping and reporting are inconsistent.

---

## Proposed Solution

- **Entities page** (e.g. Configuration → Entities): tabbed UI (Sports, Categories, Competitions, Teams, Markets). Each tab: list/table of entities with search and relevant filters (e.g. Sport for Categories/Competitions, Sport for Competitions, Category for Competitions). Add/Edit (and optional Delete) per entity type. Display **feed references** per entity (from `entity_feed_mappings.csv`).
- **Persistence:** Entity records in CSVs (e.g. `sports.csv`, `categories.csv`, `competitions.csv`, `teams.csv`, `markets.csv`). Feed links in `entity_feed_mappings.csv` (entity_type, domain_id, feed_provider_id, feed_id). No feed columns on entity CSVs; all feed linkage via entity_feed_mappings.
- **Optional country/jurisdiction:** Categories, Competitions, Teams may have optional `country_id` (or jurisdiction) from a shared **countries** reference; see platform reference docs if present.

---

## Milestones

| # | Milestone | Notes |
|---|-----------|--------|
| M1 | Sports CRUD + list | Create, edit, list; no feed columns; feed links in entity_feed_mappings |
| M2 | Categories CRUD + list | Parent: Sport; optional filters (e.g. by sport); feed refs display |
| M3 | Competitions CRUD + list | Parent: Sport, Category; filters; feed refs; optional country |
| M4 | Teams CRUD + list | Optional sport/category/competition context; feed refs; optional country |
| M5 | Markets CRUD + list | Market group, template, period/score types as per domain model |
| M6 | Feed refs per entity | Show which feeds (feed_provider_id + feed_id) link to each entity |

---

## User Journey / Process Flow

```
[User] → Configuration → Entities
  → Select tab (Sports | Categories | Competitions | Teams | Markets)
  → (Optional) Apply filters (e.g. Sport for Categories/Competitions)
  → Search / scroll to find entity
  → Add new entity (form) or Edit existing
  → Save → entity CSV + optional entity_feed_mappings rows (if created from modal or linked here)
  → View feed references per entity (read-only or manage links depending on product)
```

---

## Business Rules

- **Hierarchy:** Categories belong to a Sport; Competitions belong to Sport and Category; Teams are standalone but can be filtered by sport/competition; Markets have market group and template.
- **Uniqueness:** Per-entity-type uniqueness rules (e.g. sport name; category name per sport; competition name per category; team name; market code/name as defined).
- **Feed links:** One domain entity can have many (feed_provider_id, feed_id) pairs. Stored only in `entity_feed_mappings.csv`. Creating an entity from the Mapping Modal adds one feed link; Entities page may show and optionally manage additional links.
- **New competitions:** When a new **competition** is created in the domain, it is auto-assigned to the default margin template (e.g. “Uncategorized”) for the current product behavior. Markets are not auto-assigned.

---

## Assumptions / Constraints

- Countries (or jurisdictions) are reference data; not created from feeds. Optional FK from categories/competitions/teams to countries.
- Entity IDs (domain_id) are stable; feed_id in entity_feed_mappings is string (can be numeric or string from feed).
- Margin Configuration may consume competition list and template–competition assignments; Entities does not own margin logic, only entity data.

---

## NFRs

- **Consistency:** Entity list and feed refs must reflect current CSVs; reload from disk when needed so manual CSV edits or API writes are visible.
- **Performance:** List and search should remain responsive with thousands of entities (pagination or virtual scroll if needed).
- **Integrity:** Deleting an entity should consider references (e.g. domain events, margin_template_competitions); soft-delete or guardrails as per product.

---

## Reporting / Compliance

- No specific reporting in scope. Entity lists may be exported or audited via CSVs. Compliance (e.g. jurisdiction) can be derived from optional country/jurisdiction on entities if implemented.

---

## Out of Scope

- **Mapping Modal:** Creates entities and feed links; does not replace Entities page for bulk or structured editing. See **mapping-modal-tool** spec.
- **Feeder Events / Domain Events:** Only consume entity data and entity_feed_mappings for display and resolution. See **feeder-events**, **domain-events** specs.
- **Margin Configuration:** Uses competitions and template–competition assignments; margin rules and templates are a separate module.
- **Feeder Configuration, Localization, Market Type Sets:** Other platform areas; referenced only where relevant.
