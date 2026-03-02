# Market Types — design spec (from QNX Admin Manual)

**Source:** `docs/QNX Admin Manual - Market Types.pdf`  
**Goal:** Copy this design into the app — same filters, table columns, buttons, and create form. Build the UI first; add data and behaviour slowly (we don’t have all feed data yet, and there are other things to add before creating markets).

---

## Top filters and actions

| Element | Description |
|--------|-------------|
| **Sport** | Dropdown — select sport for which market types are shown below. |
| **Name** | Search field — search market type by name (sport must be selected for search to return results). |
| **Active only** | Checkbox — load only active market types. |
| **Clear "X"** | Button — clear sport selection and name input. |
| **Sort Market Types** | Button — open sort UI; order here is the order used on site. |
| **+ create Market Type** | Button — open form to create a new market type. |

---

## Create / Edit Market Type form

(All of these are used for “+ create Market Type” and for **Edit** on a row.)

| Field / control | Description |
|-----------------|-------------|
| **Name** | New market type name. |
| **Short Name** | Short name; if set, shown in Event Details instead of full name. |
| **Category** | Dropdown — market category (list dynamic). **Add Category** button to create new category from here. |
| **Group** | Dropdown — market group (list dynamic). **Add group** button to create new market group. |
| **Type** | Dropdown: **Both** (prematch + live), **PreMatch** (prematch only), **Live** (live only). |
| **General Type** | Dropdown — e.g. Money Line (2-Way), Money Line/Full Time Result (3-way), Spread, Total. List dynamic (devs can add). |
| **Side** | Dropdown: **Undefined**, **Home**, **Away**, **Player**, **Team**. |
| **Period** | Field (number, e.g. 1 or 2 for Half) + Dropdown: **Full Time**, **Half**, **Quarter**, **Period**, **Set**, **Game**, **Inning**, **Map**, **Round**, **Frame**, **End**, **Overtime**, **HalfTime**, **Shootout**, **Shootout Ten**, **Match**, **Plate Appearance**, **Leg**. |
| **Category Type** | Dropdown — more detailed category for incidents. |
| **Params** | Parameter fields (e.g. Dismissal, Over, Over2, Delivery, Day, Session, Game, Point, Milestone, Variant, Ups, Balls, Runs, Goals, From, To). |
| **Score** | Checkbox to enable score + dropdown for score type. |
| **Preview** | Checkbox — Preview Market Type (shown in preview section when Asian View is selected). |
| **BetRadar** | Checkbox — allow BetRadar feeder to control markets for this type. |
| **Settle** | Checkbox — allow mapped feeder to settle this market type’s outcome. |
| **Save** | Button — save (create or update). |
| **Cancel** | Button — close without saving. |

---

## Table: Market Types list (columns)

Data shown below the filters:

| Column | Description |
|--------|-------------|
| **Name** | Market type name. |
| **Short Name** | Short name (if set, used in Event Details). |
| **Category** | Market category. |
| **Group** | Market group. |
| **Type** | Both / PreMatch / Live. |
| **General Type** | General type. |
| **Side** | Undefined / Home / Away / Player / Team. |
| **Period** | Period (e.g. Full Time, Half, Set). |
| **Category Type** | Category type. |
| **Params** | Set parameters (e.g. Over, Goals). |
| **Score** | Score setting. |
| **Preview** | Is Preview Market Type. |
| **BetRadar** | BetRadar enabled. |
| **Settle** | Settlement enabled. |
| **Mappings** | Number of mapped feeders. |
| **Action** | **Activate/Deactivate** (switch), **Edit**, **Map** (feeder mapping), **LineType** (lines/outcomes). |

---

## Map (feeder mapping) modal / panel

When **Map** is used for a market type:

| Element | Description |
|--------|-------------|
| **Prematch** | Which feeder sources are mapped for prematch; order with Up/Down arrows (order defines odds priority). |
| **Live** | Which feeder sources are mapped for live; order with Up/Down. |
| **Source** | Dropdown — filter feeder list by source. |
| **Bet type** | Dropdown — filter by **Both** / **PreMatch** / **Live**. |
| **Name** | Text field — filter feeder source by name. |
| **Feeder Source List** | List of available feeders; map with **←** / unmap with **→**. |
| **Save** | Save mapping changes. |
| **Cancel** | Discard. |

---

## LineType (lines and outcomes)

| Element | Description |
|--------|-------------|
| **Create** | Create new line: **Name** + **Outcome Type** dropdown (e.g. Home, Draw, Away). |
| **Sort** | Sort lines. |
| **Activate/Deactivate** | Switch per line. |
| **Edit** | Edit line (same as Create). |
| **Cancel** | Cancel creating. |

---

## Implementation notes

- **Data:** Start with static/empty or minimal data; we don’t have all feeds yet and there are other prerequisites before creating markets.
- **Placement:** This can be a dedicated **Market Types** page (e.g. Configuration → Market Types) or a tab; ensure it matches the PDF layout (filters on top, table below, create form as modal or inline).
- **Entities vs Market Types:** Current **Entities** → Markets tab is a simple entity list (domain_id, code, name). The **Market Types** screen from this spec is the full QNX-style admin (filters, table, create form, Map, LineType). Align later whether Market Types reuse `markets.csv` or extend the schema.
