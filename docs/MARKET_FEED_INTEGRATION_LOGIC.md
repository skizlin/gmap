# Market feed integration – logic and infrastructure design

This document defines the **logic and infrastructure** for integrating markets from feeds (Bwin, Bet365, etc.) into our domain, **before** implementation. The goal is to identify which of our templates each feed market belongs to, match our fields to feed fields, and enable bulk integration once at least one market per template is mapped.

---

## 1. Our domain model (reference)

### 1.1 Market templates (blueprints)

**Source:** `backend/data/markets/market_templates.csv`

| code      | name           | Meaning |
|-----------|----------------|---------|
| WINNER2   | 2Way           | Two outcomes: side 1 vs side 2 (e.g. home/away). No line. |
| WINNER2D  | Match Betting  | Same as 2Way but 3-way variant (1 / X / 2) where applicable. |
| HANDICAP2 | Handicap       | Two outcomes + **line**. Each outcome is “side + line” (e.g. Home -3.5, Away +3.5). |
| OVERUNDER | Total          | Two outcomes (Over / Under) + **line**. Line is a number (e.g. 2.5 goals, 45.5 points). |

Templates are **categories** of markets. Many feed markets can map to the same template (e.g. “2Way - Who will win?” and “Which team will win the 1st set?” both → WINNER2).

### 1.2 Parameters shared across templates (not template-specific)

These are **additional dimensions** applied to a market; they come from reference data and are **shared** between templates.

| Dimension     | Source (our ref)        | Examples |
|---------------|-------------------------|----------|
| **period_type** | market_period_type.csv | FLGM (Full match), 1SET (1st set), 2HLF (2nd half), etc. |
| **score_type**  | market_score_type.csv  | GL (Goal), PT (Point), SET (Set), etc. |
| **side_type**   | (future / optional)    | e.g. home/away, team/player. |

So:

- “2Way - Who will win?” → template **WINNER2**, period **FLGM**, score **PT** (or by sport).
- “Which team will win the 1st set?” → template **WINNER2**, period **1SET**, score **PT**.
- “Who will win the first set? Handicap” → template **HANDICAP2**, period **1SET**, score **PT**, line e.g. **-3.5**.
- “Total Points Handicap” → template **HANDICAP2**, period **FLGM**, score **PT**, line e.g. **-14.5**.

Period, score, and side are **not** part of the template definition; they are **params** we attach when we create or map a domain market.

### 1.3 Domain market (one row in markets.csv)

A **domain market** is one concrete market we offer: it has a **template** (WINNER2, HANDICAP2, …) plus **period_type**, **score_type**, **side_type**, and for handicap/total the **line** (stored as needed, e.g. in name/code or a dedicated field). It may also have **market_group**, **abb**, etc.

---

## 2. Feed-side: what we need to recognise

From each feed market we need to derive:

1. **Our template** (WINNER2, HANDICAP2, OVERUNDER, etc.).
2. **Our period_type** (e.g. FLGM, 1SET).
3. **Our score_type** (e.g. PT, GL, SET).
4. **Line** (for HANDICAP2 and OVERUNDER only); feed may expose it in:
   - outcome name (e.g. “Maringa -3,5”),
   - market-level field (e.g. Bwin `attr`: "45,5"),
   - market name,
   - or a dedicated line/point field.
5. **Outcomes:**
   - **Fixed** (same structure for every event): e.g. 2-way → outcome keys 1/2 or home/away; handicap → two sides + line; over/under → Over/Under + line.
   - **Dynamic** (number and labels vary): e.g. Correct Score (Set 1), Set Bet (3-0, 3-1, …). For these we do not normalize to a fixed outcome schema; we keep feed outcome id/name and optionally a display label.

So the **minimal integration logic** is: for each feed market, (1) **classify** → our template + period + score (+ line if applicable), (2) **extract** line and outcomes in a feed-agnostic way where possible, (3) **map** to one domain market (or create one) using that classification.

---

## 3. Template recognition (feed market → our template)

### 3.1 By structure (preferred where possible)

We recognise our template from **how many outcomes** and **whether a line exists**:

| Our template | Outcome count | Line? | Outcome semantics |
|--------------|----------------|-------|--------------------|
| WINNER2 / WINNER2D | 2 (or 3 for WINNER2D) | No | Side 1, Side 2 (and optionally Draw). |
| HANDICAP2    | 2               | Yes  | Side 1 + line, Side 2 + line (e.g. -3.5 / +3.5). |
| OVERUNDER    | 2               | Yes  | Over line, Under line. |

So:

- **2 outcomes, no line** (and names/sourceName indicate two sides) → **WINNER2** (or WINNER2D if 3-way).
- **2 outcomes, with line** (or line in outcome text like “-3,5” / “+3,5” or “Over 45,5” / “Under 45,5”) → **HANDICAP2** or **OVERUNDER** depending on Over/Under vs team handicap wording.
- **Many outcomes, no line** (e.g. correct score, set score) → **dynamic**; we do not force into WINNER2/HANDICAP2/OVERUNDER; we may have a “Dynamic” or “Correct score” template later, or treat as “unmapped template” for now.

### 3.2 By feed-specific identifiers (when structure is ambiguous)

Feeds often expose a **template id** or **category id** (e.g. Bwin `templateId`, `templateCategory.id`). We maintain a **per-feed mapping table**:

- **feed_provider** (e.g. bwin),
- **feed_template_id** (e.g. 1545, 1547, 1548, 9206, 13809, 6356, 9210),
- **our_template_code** (WINNER2, HANDICAP2, OVERUNDER),
- optional: **our_period_type_code**, **our_score_type_code** if derivable from feed category/name.

So:

- Bwin templateId **1545** (“2Way - Who will win?”) → WINNER2.
- Bwin templateId **1547** (“Which team will win the 1st set?”) → WINNER2.
- Bwin templateId **1548**, **9206**, **13809** (handicap names) → HANDICAP2.
- Bwin templateId **6356**, **9210** (point totals, Over/Under) → OVERUNDER.

Recognition **order**:

1. Try **feed_template_id** → our template (and optionally period/score) from mapping table.
2. If missing, fall back to **structure + outcome names** (2 outcomes + line → HANDICAP2/OVERUNDER; 2 outcomes, no line → WINNER2).

This gives a **template recogniser**: input = one feed market; output = our_template_code + optional period/score hints.

---

## 4. Line extraction (feed-specific)

The **line** is needed only for HANDICAP2 and OVERUNDER. Where it appears is **feed-specific**:

| Feed  | Where line can be | Example |
|-------|--------------------|---------|
| Bwin  | `attr` on market   | "45,5", "-3,5", "-14,5" |
| Bwin  | Inside outcome name| "Maringa -3,5", "Over 45,5" |
| Other | Market name        | "Total goals 2.5" |
| Other | Dedicated field    | `line`, `spread`, `total` |

So we need a **small per-feed “line extractor”**:

- **Bwin:** Prefer `attr`; if missing, parse from outcome `name.value` (e.g. “Over X” / “Under X” or “Team ±X”).
- **Others:** To be defined per feed (name regex, dedicated field, etc.).

Output: **line value** (string or number we can normalise, e.g. "-3.5", "45.5") and optionally **which side is minus/plus** for handicap.

Line is **not** part of template definition; it’s a **parameter of the market instance**. So the same template HANDICAP2 can have many lines (-3.5, -2.5, -14.5, etc.).

---

## 5. Period and score (shared reference)

- **period_type** and **score_type** are from our **reference CSVs** (market_period_type, market_score_type). They are not stored inside the template; they are chosen when we create or map a domain market.
- **Source of truth for the feed:**
  - Bwin: “Which team will win the **1st set**?” → period 1SET; “How many **points** …” → score PT; “Set Bet (best-of-five)” → score SET (or match-level). We can derive from:
    - market **name** / **description** (e.g. “Set 1”, “1st set”, “total”, “match”),
    - or from **feed category/description** if available.
  - Rule set per feed: e.g. “description contains ‘Set 1’ or name contains ‘1st set’” → period 1SET; “points” in name → score PT; “set” in name → score SET.

So we need:

- A **period matcher** and **score matcher** (by feed): input = feed market (name, description, category id, etc.); output = our **period_type code** and **score_type code** (or null if unknown).
- These can be:
  - **Rule-based** (keywords, regex, category id → our code),
  - Or **mapping table**: feed_category_id / feed_template_id + keyword → our period_type / score_type.

Implementation can start with a small table or config: feed_provider, feed_template_id (or name pattern), our_period_type_code, our_score_type_code.

---

## 6. Outcome mapping: fixed vs dynamic

### 6.1 Fixed-outcome templates (WINNER2, HANDICAP2, OVERUNDER)

For **bulk** integration we want a **canonical outcome representation** so that odds/result can be matched across feeds:

- **WINNER2:** Two outcomes. Canonical keys: e.g. **1** (home/side1) and **2** (away/side2). Feed may send:
  - Bwin: `sourceName.value` "1" / "2", or `name.value` "Maringa" / "Sorocaba".
  - Other feed: "Home" / "Away", or "1" / "2".
  - We **map** feed outcome to **1** or **2** (and store decimal odds under that key).
- **HANDICAP2:** Two outcomes + line. Canonical: e.g. **side1** (e.g. home -line) and **side2** (e.g. away +line). Feed may send:
  - Bwin: "Maringa -3,5" / "Sorocaba +3,5" → we parse line, assign side1/side2 by sign or by playerId.
  - We store: line + two outcome keys (side1, side2) + odds.
- **OVERUNDER:** Two outcomes + line. Canonical: **over** and **under**. Feed may send "Over 45,5" / "Under 45,5" → we parse line and map to over/under.

So for **fixed** templates we need:

- A **per-feed outcome normaliser**: feed outcome (id, name, sourceName, etc.) → **our outcome key** (1, 2, side1, side2, over, under) and optionally **line** if embedded in outcome.
- One **canonical schema per template** (e.g. WINNER2: { "1": odds1, "2": odds2 }; HANDICAP2: { "line": "-3.5", "side1": odds1, "side2": odds2 }; OVERUNDER: { "line": "45.5", "over": odds, "under": odds }).

### 6.2 Dynamic-outcome markets

Markets like **Correct Score (Set 1)** or **Set Bet (best-of-five)** have **variable outcome sets** (many possible scores or set results). We do **not** force them into WINNER2/HANDICAP2/OVERUNDER.

Options:

- **A)** Treat as “dynamic” template: we store **feed_market_id** + **feed_template_id** + list of (outcome_id or outcome_name, odds). No “our” outcome keys; integration is by feed outcome id/name.
- **B)** Introduce a **DYNAMIC** or **CORRECT_SCORE** template in our system later; for now we only **map** such markets to an existing domain market (if we have one with same name/semantics) or leave unmapped.

For the **first** version of the infrastructure we can:
- **Classify** them as “dynamic” (not WINNER2/HANDICAP2/OVERUNDER).
- **Store** raw outcome list (id, name, odds) for display and for later mapping.
- **Bulk integration** only for fixed-outcome templates; dynamic markets are mapped one-by-one or in a second phase.

---

## 7. One-market anchor and bulk integration

### 7.1 Anchor (first mapping per template per feed)

To “bulk integrate” we need **at least one** **domain market** per (our_template, feed) that we have **manually** (or semi-manually) mapped:

- **Domain market id** (our markets.csv) ↔ **Feed market id** (e.g. Bwin templateId + event scope or feed_market_id).
- For that market we know: **outcome mapping** (feed outcome → our outcome key) and **line extraction** (if any).

That pair is the **anchor**: it defines how “this feed’s WINNER2” (or HANDICAP2, etc.) looks and how we map its outcomes.

### 7.2 Bulk integration (same template, same feed)

Once we have an anchor for (e.g.) Bwin + WINNER2:

- For **any other** Bwin market that the **template recogniser** classifies as WINNER2, we know:
  - Outcome mapping is the same (e.g. sourceName 1→1, 2→2).
  - We only need **period_type** and **score_type** (from name/description/category).
- If we have a **domain market** with same template + period + score (and no line, or same line), we can **propose** or **auto-apply** the same mapping (feed_market_id → domain_market_id).
- If we don’t have such a domain market, we can **propose creating** one (template WINNER2, period 1SET, score PT, etc.) and then link the feed market to it.

So the flow is:

1. **Recognise** feed market → our_template + period + score + line.
2. **Find** anchor for (feed, our_template) to get outcome mapping.
3. **Find** domain market with same (template, period_type, score_type, line) if we want to map to existing.
4. **Propose** mapping: feed_market_id → domain_market_id, with outcome map and line; or propose new domain market creation.

Same idea for HANDICAP2 and OVERUNDER: anchor gives us line extraction and outcome semantics; then any feed market of same template + period + score can use the same outcome logic; **line** differentiates market instances (e.g. -3.5 vs -14.5 are two different domain markets or two different “lines” of the same logical market, depending on how we model lines).

---

## 8. Data and components (infrastructure)

### 8.1 Reference data (already exist)

- **market_templates.csv** – our template codes (WINNER2, HANDICAP2, OVERUNDER, …).
- **market_period_type.csv** – our period codes (FLGM, 1SET, …).
- **market_score_type.csv** – our score codes (GL, PT, SET, …).

No change to these for “logic”; they are the target taxonomy.

### 8.2 New or extended data (to implement)

| Asset | Purpose |
|-------|--------|
| **Feed template mapping** | feed_provider, feed_template_id (and optionally feed_category_id) → our_template_code, optional our_period_type_code, our_score_type_code. |
| **Period/score rules** | feed_provider, rule (e.g. name pattern, description pattern) → our_period_type_code, our_score_type_code. Used when feed_template_id is not enough. |
| **Line extractor config** | Per feed: where to read line (attr, outcome name, market name, field name). |
| **Anchor mappings** | For (feed, our_template): one chosen feed_market_id (or templateId) + its domain_market_id + outcome_map (feed outcome key → our outcome key). Used for bulk. |
| **market_type_mappings.csv** (existing) | Can extend to store feed_market_id → domain_market_id per feed_provider_id; and optionally store template + period + score + line so we can match new feed markets to existing domain markets. |

### 8.3 Components (logic, then implementation)

| Component | Responsibility |
|-----------|----------------|
| **Template recogniser** | Input: one feed market (raw). Output: our_template_code, optional period/score hints. Uses feed template mapping + structure (outcome count, line presence). |
| **Line extractor** | Input: feed market (raw), our_template (HANDICAP2 or OVERUNDER). Output: line value (normalised string/number). Feed-specific. |
| **Period/score matcher** | Input: feed market (name, description, category). Output: our period_type code, our score_type code. Rule-based or mapping. |
| **Outcome normaliser** | Input: feed market (raw), our_template. Output: list of (our_outcome_key, feed_outcome_id or name, odds). For fixed templates only; for dynamic, return “dynamic” + raw list. |
| **Anchor store** | Store and lookup: (feed, our_template) → domain_market_id, outcome_map, line extraction hint. |
| **Bulk matcher** | Input: feed market (raw). Run recogniser + line + period/score + outcome normaliser; then find domain market with same (template, period, score, line) or propose new; return proposed mapping or “create domain market” suggestion. |

---

## 9. Flow summary (end-to-end)

1. **Ingest** feed event → list of feed markets (already have this from Bwin adapter, etc.).
2. For **each** feed market:
   - **Recognise template** (template recogniser) → our_template + optional period/score.
   - **Extract line** (if HANDICAP2/OVERUNDER) via feed-specific line extractor.
   - **Resolve period/score** (period/score matcher) if not from recogniser.
   - **Normalise outcomes** (outcome normaliser) → fixed (our keys + odds) or dynamic (list of id/name + odds).
3. **Match to domain**:
   - Look up anchor for (feed, our_template) for outcome semantics.
   - Find domain market with (template, period_type, score_type, line) or propose new.
   - Attach mapping: feed_market_id → domain_market_id (and store outcome map for odds/result sync).
4. **Bulk**: For new feed markets, repeat step 2–3; use same outcome map as anchor for same template; use period/score/line to find or create domain market.

---

## 10. Implementation order (recommended)

1. **Define** feed template mapping table (and optionally period/score rules) for Bwin using Bwin volleyball (and football if needed) examples.
2. **Implement** template recogniser (by feed templateId first, then structure fallback).
3. **Implement** line extractor for Bwin (attr + outcome name parsing).
4. **Implement** period/score matcher for Bwin (name/description → FLGM, 1SET, PT, SET, etc.).
5. **Extend** NormalizedMarket (or add a “classified market” DTO) with: our_template_code, period_type, score_type, line, outcomes (fixed keys or dynamic list).
6. **Implement** outcome normaliser for WINNER2 and HANDICAP2 (and OVERUNDER) for Bwin.
7. **Anchor**: allow saving one mapping (feed templateId + example feed_market_id) → domain_market_id + outcome_map per (feed, our_template).
8. **Bulk matcher**: given a new feed market, run 2–6 and propose domain_market_id or “create domain market” with (template, period, score, line).
9. **Dynamic** markets: classify as “dynamic”, store raw outcomes; no bulk until we have a dynamic template or one-by-one mapping UI.

This keeps **period_type**, **score_type**, and **side_type** as shared reference dimensions and **templates** as the main “market type”; line and outcomes are template-specific in behaviour but parametrised per market instance. The infrastructure stays simple and feed-agnostic where possible, with feed-specific pieces (line extractor, period/score rules, template id mapping) isolated so adding another feed is mostly new mapping and small extractors.
