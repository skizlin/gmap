# Figma handoff — Global Mapper prototype (developer request)

The interactive prototype in the repo is the **reference for layout and behaviour**. Please mirror it in Figma so developers can implement without guessing. **Do not add new navigation patterns or extra chrome** beyond what the prototype shows.

Add a link at the top of your Figma file to the running prototype or screenshots when available.

---

## Layout & structure

- **No sidebar** — no left navigation rail, no secondary side panels for primary navigation.
- **No collapsible / expandable side menus** — navigation stays as in the prototype (e.g. top-level only, no accordion sidebars).

## Priorities

- **UX over UI** — clarity of tasks, labels, and states matters more than decoration, illustration, or heavy branding.

## Density

- **Tight layout** — keep **horizontal and vertical spacing and padding minimal** (compact tables, filters, and content areas).
- **Small controls** — **dropdowns, buttons, and search fields** should use **small / compact** variants (height, font size, and padding aligned to a dense admin tool, not a marketing site).

## Colour

- **Restrained palette** — avoid a large set of accent colours; stick to a **small set** of neutrals plus **semantic** colours only where needed.
- **Green and red** must stay **obvious and accessible** for success / error / mapped / unmapped (or equivalent) on **both dark and light** themes — test contrast, not only aesthetics.

---

## Shared table system (all pages that show data tables)

Treat tables as **one reusable pattern** in Figma (components / variants), not one-off designs per screen.

| Area | Rule |
|------|------|
| **Look & feel** | Same typography, row height, borders/dividers, hover/focus, alignment, and empty/loading states on every table. |
| **Chrome** | Every table page uses the **same header and footer** regions (global chrome); only the **middle content** (filters + table) changes per page. |
| **Pagination** | **One shared pagination pattern** on every paginated table (placement, controls, labels, disabled states). |
| **Row count** | **Same placement and style** for the count under the table (e.g. “Showing X of Y”), consistent with the prototype. |
| **Bulk actions** | Reserve a **shared slot** for a **bulk update** (or similar) action aligned with the table footer / toolbar. It **may be hidden** on pages that do not need it, but **position and component style** stay the same so developers reuse one layout. |

### Sorting

- **All** data tables support **sorting by column** where the prototype implies it (same affordance: header interaction, sort indicator, default sort noted in Figma).

### Filtering

- **Same filtering UX** on every page: layout of the filter row, spacing, how dropdowns / toggles / search combine, how active filters read, clear/reset if applicable.
- **Only the set of filters changes per page** — document per screen *which* filters exist, not a different filter *design* per screen.

---

## Deliverable

- Figma frames that **match the prototype’s screens and flows**, not a redesign.
- **Components** for: table shell, header/footer, pagination, count line, filter row, bulk-action slot; **pages** only swap content and filter fields per route.
- If something is unclear, align with the prototype or ask product/engineering — **no invention** of new patterns without agreement.
