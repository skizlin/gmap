# Specs — PTC Global Mapper Platform

This folder contains **specifications** for platform modules. Each spec is written so other teams can build their platform following the same logic. Use them before changing a module and when adding features or reporting bugs.

---

## Spec structure

Each spec includes (precise, minimal description):

| Section | Purpose |
|--------|--------|
| **Feature** | What the module is; relation to other modules. |
| **Problem Statement** | Why this exists. |
| **Proposed Solution** | Main behaviour and deliverables. |
| **Milestones** | Ordered delivery steps. |
| **User Journey / Process Flow** | Steps and flow (text or diagram). |
| **Business Rules** | Rules and edge cases. |
| **Assumptions / Constraints** | Dependencies and limits. |
| **NFRs** | Non-functional requirements. |
| **Reporting / Compliance** | If any. |
| **Out of Scope** | Other modules / areas. |

---

## Module index (specs in scope)

| Module | Spec | Description |
|--------|------|-------------|
| **Backoffice** | [modules/backoffice/](modules/backoffice/) | Shell: top menu, layout, notifications (confirm read), profile, dashboard, toast, modal container, page header. Hosts all modules. |
| Feeder Events | [feeder-events.md](feeder-events.md) / [modules/feeder-events/](modules/feeder-events/) | Feed events view, filters, mapping status, green highlighting; entry to Mapping Modal. |
| Entities | [entities.md](entities.md) | Domain reference data: Sports, Categories, Competitions, Teams, Markets; feed links (entity_feed_mappings). |
| Domain Events | [domain-events.md](domain-events.md) | Golden copy of events; mapped feeds; start-time mismatch (red). |
| Mapping Modal Tool | [mapping-modal-tool.md](mapping-modal-tool.md) / [modules/mapping-modal/](modules/mapping-modal/) | Map feed event → domain (Confirm Mapping / Create & Map); suggestions, per-entity match %, entity resolution. |

---

## Other platform areas (specs to be added later)

- **Feeder Configuration** — System actions, incidents per feed/sport.
- **Margin Configuration** — Templates, market type sets, competitions per template, margins.
- **Localization / Translation** — Brand/sport/locale, copy.
- **Market Type Mapping** — Domain markets ↔ feed markets (prematch/live).
- **Countries / Jurisdiction** — Reference data; optional link from categories, competitions, teams.
- **Admin / Audit** — Logging, audit trail (if required).

When adding a new spec, use the same structure and reference the modules above where they interact.
