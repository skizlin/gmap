# Global Mapper Platform — dark theme design baseline

**Audience:** FE / backoffice UI (e.g. Angular implementation).  
**Source of truth for this document:** current HTML prototype (`backend/templates/layout.html` + shared Tailwind usage).  
**Light theme:** out of scope for this handoff; only **dark** is specified here.  
**Note:** Framework (Angular vs current Jinja + Tailwind CDN) does not change the **token values** below—map them to CSS variables or design tokens in Figma as you prefer.

This answers the checklist from **Design System UI_UX.pdf** where we already have stable choices in the prototype; other items (full Figma library, all breakpoints, every component state) remain for a later design pass.

---

## 1. Color palette (dark)

### Brand tokens (Tailwind `extend.colors` in prototype)

| Token     | Hex       | Usage |
|-----------|-----------|--------|
| `primary` | `#10b981` | Same hue as Tailwind **emerald-500**. Active nav/tabs, primary buttons, checkboxes, **mapped domain event ID** in grids, “success” counts where a single brand green is enough |
| `secondary` | `#3b82f6` | Tailwind **blue-500**. Logo gradient, text links (`text-secondary`), “add” / utility link accents with `hover:text-blue-300` |
| `darkbg`  | `#0f172a` | App background (page body) |
| `cardbg`  | `#1e293b` | Surfaces: cards, panels (slate-800 family) |

**Note:** The UI uses both the **custom `primary` token** and **named Tailwind `emerald-*` / `blue-*` / `red-*` steps**. They are intentionally layered: **`primary` ≈ emerald-500**, while **lighter/darker greens** come from **`emerald-300` … `emerald-600`** for hierarchy in tables and modals.

### Surfaces & structure (Tailwind `slate` scale — prototype defaults)

| Role | Typical classes | Notes |
|------|-----------------|--------|
| Top bar | `bg-slate-900` `border-slate-800` | Header strip |
| Page title band | `bg-slate-900/60` `border-slate-800` | Below header |
| Dropdown / popover shell | `bg-slate-900` or `bg-slate-800` `border-slate-700` | Nav menus, notifications |
| Elevated panel / modal | `bg-slate-800` `border-slate-700` | Modal content, some menus |
| Glassy panel | `bg-cardbg/80` `backdrop-blur-md` `border-slate-700/50` | Tables/cards on dashboard-style screens |
| Table header | `bg-slate-900/50` `text-slate-400` | Uppercase section headers |
| Table body | `text-slate-300` | Primary cell text |
| Muted / secondary text | `text-slate-500` `text-slate-400` | Descriptions, labels, inactive nav |
| Primary content text | `text-white` | Page titles, emphasis |
| Default body | `text-slate-200` | Set on `<body>` |

### Semantic / state (as used today — not a full DS yet)

| State | Pattern (examples) |
|-------|---------------------|
| Success / OK | `text-primary`, `text-emerald-300`–`emerald-400`, `bg-emerald-600` on primary button hover, toast `bg-emerald-950/95` `border-emerald-600/60` `text-emerald-100` |
| Warning | `text-amber-400` / `amber-500` (notes, notification badge on bell, dashboard “Unmapped” column, partial-create feedback) |
| Error / required | `text-red-400` `text-red-500` (validation, errors, **Unmapped** pill in feeder Status — see table below; live-only filter when active) |
| Info | `text-secondary` / `text-blue-400` / `hover:text-blue-300` (links, feed-side labels in mapping modal) |
| Disabled / subtle | `text-slate-500` `opacity-50` |

### Mapping & grid semantics (feeder events, domain lists)

| Meaning | Classes (typical) | Tailwind default hex (reference) |
|---------|-------------------|----------------------------------|
| **Mapped** domain event ID (numeric/domain id in Status column) | `text-primary` `font-mono` | `#10b981` (same as `primary`) |
| **Unmapped** pill | `text-red-400` `text-[11px]` `font-medium` `bg-red-400/10` `border-red-400/20` | red-400 ≈ `#f87171` |
| **Mapped** sport / category / competition / team / market text (entity aligned to feed) | `text-emerald-300` | ≈ `#6ee7b7` |
| **Mapped** flow in mapping modal (e.g. “Mapped” with check, status lines) | `text-emerald-400` | ≈ `#34d399` |
| **Matched** badge (modal) | `text-emerald-500/80` `border-emerald-700/50` | lighter + bordered chip |
| Resolved entity **names** in modal | `text-emerald-300` `font-medium` | distinct from IDs |
| **Domain ID** chips in modal (secondary label) | `font-mono` `text-slate-400` `bg-slate-800/80` | neutral, not blue |
| **Entities** table `domain_id` column | `font-mono` `text-slate-400` | neutral |

### Blue accents (feeds, links, IDs)

| Use | Classes | Hex reference |
|-----|---------|----------------|
| **Feed provider** title / feed-side section labels (mapping modal) | `text-blue-400` `font-bold` | ≈ `#60a5fa` |
| **Secondary** text links (Select All, Create Market Group, mapper add, etc.) | `text-secondary` `hover:text-blue-300` | `#3b82f6` → hover ≈ `#93c5fd` |
| **Domain / feed IDs in grids** | Mostly **`text-primary`** when mapped, **`text-slate-400`** for neutral mono columns — **not** blue. Blue is reserved for **feed-facing** emphasis and **hyperlink-style** actions. |

### Greens: `primary` vs `emerald-*` (tabs, buttons, tables)

| Pattern | Classes | Role |
|---------|---------|------|
| **Active tab** (e.g. Configuration sub-tabs, Archived Events) | `text-primary` `border-primary` | Same token as brand green; bottom border indicates selection |
| **Primary button** | `bg-primary` `hover:bg-emerald-600` `text-white` | Fill = `primary` (`#10b981`); hover darkens with **emerald-600** (`#059669`) — slightly **darker** than `primary` for press/hover feedback |
| **Outline / ghost primary** | `border-primary/50` `text-primary` `hover:bg-primary/20` | Map / score badges in modal |
| **Checkboxes / radios** | `text-primary` `focus:ring-primary` | Accent color |
| **M-Book / small success chips** (modal) | `text-emerald-400` `border-emerald-500/30` | Brighter mint than body text |

**Summary:** One **brand green** (`primary`). **Lighter greens** (`emerald-300`, `emerald-400`) signal *mapped / OK* in dense tables and modals. **Darker green** (`emerald-600`) is used for **primary button hover** only.

### Color usage guidelines (dark)

- **Primary** = “I am here” (current section) and **main positive action**; do not use for large fills except buttons/links.
- **White** = page titles and strong emphasis; **not** default for all nav text (keeps bar calmer and narrower visually).
- **Borders** stay **low contrast** (`slate-700` / `slate-800`) so dense tables remain readable.
- **Light theme:** deferred; when added, re-map tokens rather than hard-coding hex in components.

**Prototype reference (where these colors appear):** `backend/templates/feeder_events/_rows.html` (mapped ID / Unmapped pill / emerald entity text), `backend/templates/modal_mapping.html` (blues, emerald hierarchy, primary outlines).

---

## 2. Typography

### Family

- **UI font:** `font-sans` → Tailwind default stack (**system UI**: Segoe UI, Roboto, etc. on Windows).
- **No custom webfont** in the prototype today (contrast with legacy PTC Montserrat — intentional for density).

### Scale (from prototype patterns)

| Role | Typical classes |
|------|------------------|
| Logo mark | `text-lg font-black tracking-tight` + gradient `from-primary to-secondary` |
| Top navigation | `text-sm` weight default (~400), default `text-slate-400`, active `text-primary` |
| Page title (H1) | `text-lg font-bold text-white` |
| Page description | `text-sm text-slate-500` |
| Section / table title | `text-xs font-semibold uppercase tracking-wider text-slate-500` |
| Form label (dense) | `text-[10px] uppercase tracking-wider text-slate-500` |
| Table / dense UI | `text-xs` body; headers `text-[10px]`–`text-xs` uppercase where used |
| Helper / small print | `text-[11px]` `text-slate-500` |

### Headings

- Formal **H1–H6 ladder** is not fully codified; **page H1** = above. Inners sections rely on **uppercase tracked labels** + table titles.

### Line height / letter spacing

- **Uppercase labels:** `tracking-wider` is standard for form labels and table section headers.

---

## 3. Layout & spacing

### Shell

- **App:** `h-screen flex flex-col overflow-hidden` — header fixed height, main scrolls internally.
- **Header height:** `h-12` (48px), horizontal padding `px-4`.
- **Page header block:** `px-6 py-4` (when shown).
- **Main content:** `flex-1 overflow-auto p-6`.

### Spacing scale

- Prototype follows **Tailwind default spacing** (4px base: `1` = 4px, `2` = 8px, …). No custom scale file.

### Grid / max-width

- **No rigid 12-column grid** in prototype; layouts are **flex** + **full-width tables** (operations backoffice).

### Breakpoints

- Tailwind defaults: `sm` 640px, `md` 768px, `lg` 1024px, `xl` 1280px, `2xl` 1536px.
- **Internal product baseline** is **desktop Full HD**; responsive polish is incremental.

---

## 4. Components (prototype behavior — for Figma parity)

Document **patterns**, not every screen:

| Component | Dark theme pattern |
|-----------|-------------------|
| **Primary button** | `bg-primary hover:bg-emerald-600 text-white text-xs font-medium px-3 py-1.5 rounded` |
| **Ghost / secondary** | `border border-slate-600` + slate or colored text (purple/blue used for placeholder actions in some pages) |
| **Text input / select** | `bg-slate-900 border-slate-700 text-sm text-white rounded px-2.5 py-1.5 focus:border-primary outline-none` |
| **Card / panel** | `bg-cardbg/80 backdrop-blur-md border border-slate-700/50 rounded-lg` |
| **Modal** | Backdrop `bg-slate-900/90`; panel `bg-slate-800 border-slate-700 rounded-lg shadow-xl max-w-6xl` |
| **Table** | Header row slate-900/50; rows `border-slate-700/40` hover `bg-white/3`; sticky cells use `bg-cardbg/95` or `bg-slate-900/50` |
| **Tabs** | Border-bottom tab strip, active `text-primary border-primary` (varies slightly per page) |
| **Dropdown / kebab** | `bg-slate-800 border-slate-600 rounded-lg shadow-xl`; items `text-xs` hover `bg-white/10` |
| **Notifications** | Bell `bg-slate-800`; badge `bg-amber-500 text-slate-900`; panel `bg-slate-800 border-slate-600` |
| **Icons** | Font Awesome **6.0** (CDN); menu icons often `text-slate-500` |

**Tooltips, loaders, pagination, full validation states:** partially present; extend in Figma as needed.

---

## 5. Navigation & layout

- **Top horizontal bar only** in the prototype (no persistent sidebar) — product direction for trader-facing density.
- **Nav item:** default `text-slate-400`; hover `text-white` + `bg-white/5`; **active section** `text-primary`.
- **Dropdown:** `absolute` under item, `w-52`–`w-56`, same header background family.
- **Footer:** none in prototype.

---

## 6. Responsive & theme

- **Dark:** `html` carries `class="dark"`; Tailwind `darkMode: 'class'`.
- **Light theme:** not defined — skip until requested.
- **Mobile / tablet:** not fully designed; future hamburger / overflow behavior TBD.

---

## 7. Interaction (summary)

- **Hover:** nav `bg-white/5`; rows `hover:bg-white/3`; buttons lighten/darken per above.
- **Focus:** `focus:border-primary` on inputs; `focus-visible:ring` on some icon buttons.
- **Modal:** backdrop click closes (prototype).

---

## 8. Icons & assets

- **Font Awesome 6.0** all.min.css from cdnjs.
- **Logo:** text “GMP” with gradient (no SVG logo file in repo).

---

## 9. Developer handoff

| Name | Value |
|------|--------|
| `--color-primary` | `#10b981` |
| `--color-secondary` | `#3b82f6` |
| `--color-darkbg` | `#0f172a` |
| `--color-cardbg` | `#1e293b` |

**Implementation reference:** `backend/templates/layout.html` (Tailwind CDN `tailwind.config` block + body/header/main structure).

**Angular:** bind these tokens in `styles` / design tokens / Material theme overrides as appropriate; behavior should match the semantics above, not the specific CDN setup.

---

## 10. Gap vs Design System PDF request

The PDF also asks for: full **Figma** library, **light** theme, **all** breakpoints, **sidebar** variants, **every** flow hi-fi. This document **does not** replace that—it gives **dark theme + typography + layout + color** grounded in the **current GMP prototype** so FE can start tokens and components without waiting for full Figma coverage.
