# Specs — PTC Global Mapper

This folder contains **module specs** for the platform. Each spec defines scope, behaviour, and **Acceptance Criteria** so developers and agents can implement and fix features without conflicting or going in circles.

---

## How to use

- **Before changing a module:** Read its spec (e.g. `mapping-module.md`) and stay within **Scope**; satisfy the **Acceptance Criteria**.
- **When reporting bugs:** Refer to the spec and AC (e.g. "Mapping Module AC-03 is broken").
- **When adding features:** Update the spec and AC first, then implement.

---

## Spec template (for new modules)

Each spec should include:

| Section | Purpose |
|--------|--------|
| **Scope** | What this module owns. |
| **Out of scope** | What other modules own. |
| **User flows** | Main steps (1–2–3). |
| **Key behaviours** | Rules and edge cases. |
| **APIs / data** | Endpoints and CSVs used. |
| **Acceptance criteria** | Testable conditions (must all pass). |
| **References** | Links to related docs or code. |

---

## Module index

| Module | Spec | Owner |
|--------|------|--------|
| Mapping | [mapping-module.md](mapping-module.md) | Mapping agent |
| Feeder Events | *(to add)* | Feed agent |
| Domain Events | *(to add)* | Domain agent |
| Entities | *(to add)* | Entities agent |
