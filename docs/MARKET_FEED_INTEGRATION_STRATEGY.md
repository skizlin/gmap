# Market feed integration – strategy (sport-agnostic)

Our **market templates** (WINNER2, HANDICAP2, OVERUNDER, etc.) are **the same for every sport**. A “2Way” or “Handicap” or “Total” market is identified by template + period + score (+ line); the sport only affects which **score_type** and **period_type** we use (e.g. Point/Set for volleyball, Goal for football). So we use **one integration strategy for the whole feed**: normalise each feed’s markets into a **canonical descriptor**, then match to our domain by (template, period_type, score_type, line). No separate “volleyball integration” vs “football integration”.

**Target UI:** The **Mapping [market type] market type** modal (Configuration → Entities → Markets → Map) is where integrated feed markets appear. When you select a feed (Bwin, Bet365, 1xbet) and the current sport (e.g. Volleyball) is set in the Markets tab filter, the "Available markets" list is populated from that feed's data (sport-specific JSON when present, e.g. `bwinvolleyball.json`, `bet365volleyball.json`, `1xbetvolleyball.json`). You map feed markets to domain market types there; the same flow will later apply to all sports.

**Scope:** We build for **volleyball first** (three feeds: Bwin, Bet365, 1xbet); the same logic then extends to all sports by adding more feed JSON and sport mappings.

This document defines that strategy and how **Bwin**, **Bet365**, and **1xbet** structures map into it, using the volleyball examples only as sample payloads.

---

## 1. Principle: one strategy for the whole feed

- **Templates** = WINNER2, HANDICAP2, OVERUNDER (and later WINNER2D, dynamic). Same list for all sports.
- **Period and score** = from our reference (market_period_type, market_score_type). Sport gives default score (e.g. PT for volleyball, GL for football); period comes from feed (match, 1st set, 1st half, etc.).
- **Integration steps** (same for every feed and every sport):
  1. **Extract** from feed: one “market” = one bet type with its outcomes and optional line.
  2. **Classify** → our template + period_type + score_type + line (if any).
  3. **Normalise outcomes** → canonical keys (1/2, over/under, side1/side2) for fixed templates; keep raw list for dynamic.
  4. **Match** to domain market by (template, period_type, score_type, line) or propose new domain market.
  5. **Map** feed market id + outcome id → domain market id + our outcome key (for odds/result sync).

So: **one normalisation path per feed**, then **one shared matching/mapping layer** that is sport-agnostic and template-based.

---

## 2. Canonical feed market descriptor (target of normalisation)

Every feed adapter should produce, for each “market” in the feed, a **canonical descriptor** like:

| Field | Type | Meaning |
|-------|------|--------|
| **feed_provider** | string | bwin, bet365, 1xbet |
| **feed_market_id** | string | Stable id for this market in the feed (event-scoped or global). |
| **feed_market_name** | string | Display name from feed (for logging/UI). |
| **our_template** | string | WINNER2, HANDICAP2, OVERUNDER, or DYNAMIC. |
| **period_type** | string | Our period code (FLGM, 1SET, 2HLF, …) or null if unknown. |
| **score_type** | string | Our score code (PT, GL, SET, …) or null; can default by sport. |
| **line** | string / number or null | For HANDICAP2 / OVERUNDER only; e.g. "-3.5", "45.5", "184.5". |
| **outcomes** | list | For fixed: [{ "our_key": "1"|"2"|"over"|"under"|"side1"|"side2", "feed_outcome_id": "...", "odds": decimal }]. For dynamic: list of { feed_outcome_id, name, odds }. |

**Our outcome keys (fixed templates):**

- **WINNER2:** `"1"` (home/side1), `"2"` (away/side2).
- **HANDICAP2:** `"side1"`, `"side2"` (with line; e.g. side1 = -3.5, side2 = +3.5).
- **OVERUNDER:** `"over"`, `"under"` (with line).

Once every feed produces this descriptor, the rest of the pipeline (matching to domain market, storing mapping, bulk integration) is **identical** and sport-agnostic.

---

## 3. Per-feed: where to get market id, name, period, line, outcomes

Below is how each feed exposes “market” and how we map to the canonical descriptor. Volleyball examples are for illustration; the **locations and rules** are the same for other sports.

### 3.1 Bwin (bwinvolleyball.json)

| Canonical field | Where in Bwin | Notes |
|-----------------|----------------|-------|
| **feed_market_id** | `Markets[].id` or `templateId` (event-scoped: same templateId can repeat per event). Prefer `id` for uniqueness. | Numeric id per market instance. |
| **feed_market_name** | `Markets[].name.value` | e.g. "2Way - Who will win?", "Total Points Handicap". |
| **our_template** | From `templateId` + mapping table; or from structure (2 outcomes, has line → HANDICAP2/OVERUNDER). | 1545, 1547 → WINNER2; 1548, 9206, 13809 → HANDICAP2; 6356, 9210 → OVERUNDER. |
| **period_type** | From `Markets[].description` or `name.value` ("1st set", "Set 1", "match") → our period code. | "Set 1" / "1st set" → 1SET; no description / "match" → FLGM. |
| **score_type** | From market name / templateCategory ("Points", "Set", "Totals") + sport. | Volleyball: Points → PT, Set → SET. |
| **line** | `Markets[].attr` (e.g. "45,5", "-3,5"); or parse from `results[].name.value` ("Over 45,5", "Maringa -3,5"). | Normalise comma to dot; keep sign for handicap. |
| **outcomes** | `Markets[].results[]`: `id`, `name.value`, `sourceName.value` (if 1/2), `odds`. | WINNER2: use sourceName "1"/"2" → our "1"/"2". HANDICAP2: parse "Team ±X" → side1/side2. OVERUNDER: "Over X"/"Under X" → over/under. |

**Bwin outcome mapping (fixed):**

- WINNER2: `sourceName.value` "1" → "1", "2" → "2"; else by playerId vs event HomeTeamId/AwayTeamId.
- HANDICAP2: two results; parse line from name or attr; assign side1/side2 by sign or order.
- OVERUNDER: "Over …" → over, "Under …" → under.

---

### 3.2 Bet365 (bet365volleyball.json)

| Canonical field | Where in Bet365 | Notes |
|-----------------|------------------|-------|
| **feed_market_id** | `main.sp.<market_key>.id` or `others[].sp.<market_key>.id` (e.g. "910000", "910204"). Combine with event + market key for uniqueness. | Same id can appear in main and others (different periods). Use e.g. `event_id + ":" + market_key + ":" + period_hint`. |
| **feed_market_name** | `main.sp.<market_key>.name` or `others[].sp.<market_key>.name` | e.g. "Game Lines", "Set 1 Lines", "Match Handicap (Points)". |
| **our_template** | From **market key** + **odds[].name** + **handicap**. game_lines + name "Winner" + empty handicap → WINNER2. name "Handicap" + handicap ± → HANDICAP2. name "Total" + handicap O/U → OVERUNDER. | game_lines → mix of Winner/Handicap/Total; set_1_lines → same. correct_set_score, score_after_2_sets → dynamic. |
| **period_type** | From **market key**: game_lines → FLGM; set_1_* → 1SET; set_2_* → 2SET; match_* → FLGM. | Map key prefix to our period code. |
| **score_type** | From market name + sport. "Points", "Set" → PT, SET. | Volleyball default PT for totals/handicap. |
| **line** | `odds[].handicap`: "+1.5", "-1.5" (handicap); "O 184.5", "U 184.5" (total). Parse to number; keep sign for handicap. | Normalise "O 184.5" → "184.5" for over, "U 184.5" → "184.5" for under. |
| **outcomes** | `odds[]`: `id`, `name`, `header` ("1"/"2"), `handicap`, `odds`. | Winner: header "1"/"2" → "1"/"2". Handicap: header + handicap → side1/side2 + line. Total: name "Total" + handicap O/U → over/under + line. |

**Bet365 market keys → our template + period (examples):**

- `game_lines`: contains Winner (WINNER2), Handicap (HANDICAP2), Total (OVERUNDER); period FLGM.
- `set_1_lines`: same three types; period 1SET.
- `match_handicap_(points)`: HANDICAP2, FLGM, line from outcome name ("+5.5", "-5.5").
- `correct_set_score`, `score_after_2_sets`, `score_after_3_sets`, `set_1_correct_score`, etc.: DYNAMIC (many outcomes).
- `match_total_odd_even`, `set_1_total_odd_even`: two outcomes (Odd/Even); could be a small fixed template later or DYNAMIC.
- `double_result`: DYNAMIC (combo outcomes).

**Bet365 outcome mapping (fixed):**

- WINNER2: `header` "1" → "1", "2" → "2"; odds from `odds`.
- HANDICAP2: two rows with same `handicap` (e.g. "+1.5" / "-1.5"); header "1" → side1, "2" → side2; line from handicap.
- OVERUNDER: two rows with "O X" / "U X"; map to over/under; line = X.

---

### 3.3 1xbet (1xbetvolleyball.json)

| Canonical field | Where in 1xbet | Notes |
|-----------------|----------------|-------|
| **feed_market_id** | `Value.SG[].I` (market group id) combined with `Value.GE[].G` (outcome group). Each GE.G + E row = one “market” (e.g. one line). Or use CI (category id) + TI (type id). | Structure is nested: event → SG (period/segment) → MEC (market type: Popular, Total, Handicap) → GE (outcome groups) → E (rows of outcomes). Need to interpret G and T to get “one market”. |
| **feed_market_name** | Derived from SG[].PN (e.g. "1st set"), SG[].TG (e.g. "Aces"), MEC[].N (Popular, Total, Handicap). | e.g. "1st set – Total", "Match – Handicap". |
| **our_template** | From **MEC.MT** (market type): MT 2 → Popular (often WINNER2); MT 3 → Total (OVERUNDER); MT 4 → Handicap (HANDICAP2). And from **GE.E** structure: 2 outcomes + line → HANDICAP2/OVERUNDER; 2 outcomes no line → WINNER2. | MT = 2 → WINNER2; MT = 3 → OVERUNDER; MT = 4 → HANDICAP2. |
| **period_type** | From **SG[].PN**: "1st set" → 1SET, "2nd set" → 2SET, "3rd set" → 3SET; empty or "Match" → FLGM. | Map PN to our period code. |
| **score_type** | From **SG[].TG** (e.g. "Aces", "Blocks", "Set") + sport. Empty TG = main market (e.g. Set/Point by sport). | Volleyball: Set → SET; Points → PT; Aces → optional sub type. |
| **line** | **GE.E[][].P** (e.g. 130.5, -20.5, 46.5). P = line value; sign for handicap. | Normalise to string "-3.5", "184.5", etc. |
| **outcomes** | **GE.E**: each inner array = one “market” (one line); elements have T (outcome type?), C/CV (odds), P (line). T can indicate Over/Under (9/10), Handicap side (7/8), Winner (e.g. 13/14?). | Need feed-specific T mapping: e.g. T 9 → over, T 10 → under; T 7 → side1, T 8 → side2; or by position in E row. |

**1xbet specifics:**

- One event has **Value.SG** = list of segments (1st set, 2nd set, Aces, …). Each segment has **MEC** (market type counts) and **GE** (outcome groups).
- **GE** is a flat list of groups; each **G** + **E** (array of rows) defines outcomes. Often two rows in E = two outcomes (e.g. Over/Under, or side1/side2). **P** in each outcome = line.
- To get “one market”: take one segment (SG item) + one market type (MT from MEC) + one line value (P) → one canonical market. Iterate over GE where G matches the segment/type, then over E rows that share the same P to get the two outcomes (or one row for WINNER2).
- **Outcome mapping**: Document T codes per feed (e.g. 9=Over, 10=Under, 7=Handicap home, 8=Handicap away) in a small config so we map to our "1"/"2", "over"/"under", "side1"/"side2".

---

## 4. Single integration flow (all feeds, all sports)

1. **Per feed, per event:**
   - Parse event and list of “markets” (Bwin: Markets[]; Bet365: main.sp + others[].sp; 1xbet: SG + GE).
   - For each market, run **feed-specific extractor** that fills the **canonical descriptor** (feed_market_id, feed_market_name, our_template, period_type, score_type, line, outcomes).
   - Default **score_type** from sport if not derivable from feed (e.g. volleyball → PT for “points” totals).

2. **Matching (same for all feeds):**
   - Find domain market where (template, period_type, score_type, line) match.
   - If none: propose “create domain market” with that (template, period, score, line).

3. **Mapping storage:**
   - Store (feed_provider, feed_market_id, domain_market_id, outcome_map: feed_outcome_id → our_key).
   - Use for odds/result sync and for bulk: same template + period + score + line → same outcome_map.

4. **Bulk:**
   - After one “anchor” mapping per (feed, our_template), any new feed market with same template reuses outcome semantics; only (period, score, line) need to resolve to domain market.

No sport-specific branches: sport only influences default score_type and which period/score combinations exist. The **strategy** is: normalise to one descriptor, match by (template, period, score, line), store one mapping format.

---

## 5. Implementation checklist (simplified)

| Step | What | Sport-agnostic? |
|------|------|------------------|
| 1 | **Canonical descriptor** (DTO): feed_market_id, name, our_template, period_type, score_type, line, outcomes. | Yes |
| 2 | **Bwin adapter** to descriptor: templateId → our_template; attr/outcome name → line; results → outcomes with our keys. | Yes (same for all Bwin sports) |
| 3 | **Bet365 adapter** to descriptor: market key + odds[].name/handicap → our_template, period from key; handicap → line; header/handicap → outcomes. | Yes |
| 4 | **1xbet adapter** to descriptor: MEC.MT → our_template; SG.PN → period; GE.E, P, T → line + outcomes; T mapping table. | Yes |
| 5 | **Period/score mapping** (per feed): feed period name/code → our period_type; feed score/category → our score_type. Optional default by sport_id. | Yes (sport only for defaults) |
| 6 | **Match** descriptor to domain market by (template, period_type, score_type, line). | Yes |
| 7 | **Store** feed_market_id → domain_market_id + outcome_map. | Yes |

Templates and (period_type, score_type, line) are shared across sports; only the **default score_type** and the **set of period/score combinations** that appear in the feed are sport-dependent. The integration code stays **one strategy for the whole feed**.

---

## 6. Quick reference: feed → our template

| Feed | Feed “market” identifier | Our template | Period from | Line from |
|------|--------------------------|--------------|-------------|-----------|
| **Bwin** | Markets[].id, templateId | Mapping table or structure (2 outcomes ± line) | description / name ("1st set", "Set 1") | attr, or outcome name |
| **Bet365** | main.sp / others[].sp key (e.g. game_lines, set_1_lines) + odds[].name | "Winner" → WINNER2; "Handicap" → HANDICAP2; "Total" → OVERUNDER | market key (game_lines=FLGM, set_1_*=1SET) | odds[].handicap |
| **1xbet** | SG[].I + GE[].G (segment + outcome group) | MEC.MT: 2→WINNER2, 3→OVERUNDER, 4→HANDICAP2 | SG[].PN ("1st set", "2nd set") | GE.E[][].P |

**Outcome keys:**

- **Bet365:** header "1"/"2" → "1"/"2"; Total O/U from handicap string.
- **1xbet:** T codes (e.g. 9=over, 10=under, 7=side1, 8=side2) from feed docs or discovery; map to our over/under, side1/side2, 1/2.

For detailed template recognition, line extraction, and outcome mapping, see **MARKET_FEED_INTEGRATION_LOGIC.md**.
