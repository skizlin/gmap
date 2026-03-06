# Backoffice — Module specs

The backoffice is the **shell** that hosts all platform modules. Specs are organized by **phase**.

---

## Phases

| Phase | Scope | Documents |
|-------|-------|-----------|
| **Phase 1** | Shell for the 4 modules with specs: Feeder Events, Event Navigator (Domain Events), Entities, Mapping Modal Tool. Everything those modules require from the backoffice is covered. | [Phase 1/](Phase%201/) — confluence, epic, stories |

---

## Phase 1 coverage

Phase 1 documents cover only what the backoffice provides for:

- **Feeder Events** — Nav (Betting Program → Feeder Events), toast, modal container, notifications, page header
- **Event Navigator** — Nav (Betting Program → Event Navigator), page header; Event Details can override header
- **Entities** — Nav (Configuration → Entities), page header
- **Mapping Modal Tool** — Modal container (opened from Feeder Events → Map Event)

---

## Root-level docs

The root `confluence.md`, `epic.md`, `stories.md` describe the **full** backoffice shell (all nav items, placeholders). Use Phase 1 docs when implementing or verifying the initial release scope.
