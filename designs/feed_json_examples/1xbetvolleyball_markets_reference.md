# 1xbet Volleyball – markets reference (structure and identifiers)

**Source:** `1xbetvolleyball.json` (e.g. Suzano Esporte vs Minas, Brazil. SuperLiga — event id `710505432`).  
**Convention (current API shape):** Full event odds live under **`results[].Value.GE`**: a **flat array** of outcome groups. Each element is **`{ "G": <int>, "E": [ ... ] }`**. The feed’s **market id** is **`G`** (numeric). There is **no separate market name** in the payload; labels must be supplied by us (or inferred from **T** / **P** patterns and segment metadata).

**Also present:** `Value.SG[]` + `MEC[]` describe segments (1st set, 2nd set, …) and **market type categories** (Popular, Total, Handicap, …) with counts — useful for documentation, not a substitute for **`G`** as the stable mapping key when **`GE`** is present.

---

## 1. Top-level event and Value

| Field | Location | Meaning |
|-------|----------|---------|
| Event ID | `results[].id` | e.g. `"710505432"` |
| Home / Away | `results[].home`, `results[].away` | Team ids and names |
| Sport (feed) | `results[].Value.SI` | e.g. `6` = Volleyball (used for sport-scoped filtering) |
| Outcome groups | `results[].Value.GE[]` | **All** priced markets for this event (see §4) |
| Segments (meta) | `results[].Value.SG[]` | Period/theme + **MEC** (counts per market type) |
| Match-level MEC | `results[].Value.MEC[]` | Aggregate market-type breakdown for the match |

---

## 2. Segment (SG) structure

Each **SG** element describes one “segment” (period or theme) of markets:

| Field | Meaning | Example |
|-------|---------|---------|
| **I** | Segment id (numeric) | 702175341, 702175342, … |
| **PN** | Period name | "1st set", "2nd set", "3rd set", "" (match) |
| **TG** | Theme / sub-market | "Aces", "Blocks", "Serve faults", "" |
| **N** | Segment name (internal id) | 249108, 249109, … |
| **MEC** | Market type categories (see below) | Array of { MT, N, EC } |

**Example segments in volleyball:**

| PN (period) | TG (theme) | Typical markets |
|-------------|------------|------------------|
| (empty) | (empty) | Match – Winner, Total, Handicap |
| 1st set | (empty) | Set 1 – Winner, Total, Handicap |
| 2nd set | (empty) | Set 2 – same |
| 3rd set | (empty) | Set 3 – same |
| (varies) | Aces | Aces – Total, Handicap |
| (varies) | Blocks | Blocks – Total, Handicap |
| (varies) | Serve faults | Serve faults – Total, Handicap |

---

## 3. Market type categories (MEC)

Inside each **SG**, **MEC** lists market types and outcome counts:

| Field | Meaning | Example values |
|-------|---------|----------------|
| **MT** | Market type id | 1 = All markets, 2 = Popular (often Winner), 3 = Total, 4 = Handicap, 8 = Other, 10/15 = Points |
| **N** | Market type name | "Popular", "Total", "Handicap", "Other", "Points", "All markets" |
| **EC** | Event count (number of outcome groups?) | 40, 28, 12, 0, … |

**Mapping MT → our template (volleyball):**

| MT | N | Our template | Notes |
|----|---|--------------|-------|
| 2 | Popular | WINNER2 | Match/set winner (2 outcomes) |
| 3 | Total | OVERUNDER | Over/Under with line (2 outcomes) |
| 4 | Handicap | HANDICAP2 | Handicap with line (2 outcomes) |
| 8 | Other | DYNAMIC | Various specials |
| 1 | All markets | — | Container / all |

---

## 4. Outcome groups (`Value.GE`) — authoritative market list

**`Value.GE`** is an array of objects. In the sample match there are **17** distinct **`G`** values (17 markets).

| Field | Meaning |
|-------|---------|
| **G** | **Market id** for mapping (`feed_market_id` = string form, e.g. `"17"`, `"1"`). |
| **E** | List of **rows**. Each **row** is an array of **outcome cells** (same **G** repeated on each cell). |

### 4.1 Structure of **E** (rows and cells)

- One **row** = one “line” in UI terms when **P** varies (e.g. each total line 181.5, 184.5, …).
- Each **cell** inside a row is one selectable outcome with odds.

### 4.2 Fields on each cell (inside **E**`[][]`)

| Field | Meaning | Notes |
|-------|---------|------|
| **G** | Same market id as the parent **GE** item | Should match parent; redundant copy. |
| **T** | **Outcome / position code** | Meaning is **market-dependent**. Not globally 1X2. |
| **C** | Decimal odds (number) | **Use this** for integration. |
| **CV** | Odds as string | Duplicate of **C**; safe to ignore. |
| **P** | **Line** when present | Handicap level, total line, or other numeric parameter. |
| **CE** | Optional flag | e.g. `1` on some “main” lines in samples; semantics TBD. |

### 4.3 **T** codes — working hypotheses (to validate with you)

**Simple winner / 1X2-style (some sports):** In several feeds, **1 = home**, **2 = draw**, **3 = away**. **Volleyball** often has **no draw**: market **G=1** may only expose **T=1** and **T=3** (two cells across two rows in the sample).

**Other markets** use different **T** namespaces (e.g. **9 / 10** with **P** for Over/Under-style rows; large ids like **8771**, **5078** for multi-way or special markets). **Do not** assume 1/2/3 outside moneyline-style groups without checking the **G** block.

We will maintain a table **per market G** (or per template family) once names and semantics are confirmed.

---

## 5. Example: Match winner (**G = 1**)

- **GE** entry: `"G": 1`, `"E": [ [ {T:1, C:2.35, G:1} ], [ {T:3, C:1.53, G:1} ] ]`.
- Two rows, one outcome each: **T=1** (home), **T=3** (away); no **T=2** (no draw).

---

## 6. Example: Match total points (**G = 17**)

- Many rows; each row contains outcomes with the same **P** (the total line) and **T** distinguishing sides (e.g. **9** vs **10** in this file’s pattern).
- **Line** for each outcome = **P**; odds = **C**.

---

## 7. Summary: identifiers for integration (current parser)

| What we need | Where in 1xbet |
|--------------|----------------|
| **Market id (`feed_market_id`)** | **`Value.GE[].G`** (stringified). |
| **Market name (UI)** | Not in API; synthetic label from row count / **P** / distinct **T** until you supply a dictionary. |
| **Line** | **`GE.E[][].P`** when present. |
| **Outcomes** | Flatten **GE.E**: each cell with **C** is one outcome; label built from **T** and **P** until named. |
| **Odds** | **`C`** (prefer number; ignore **CV**). |
| **Legacy fallback** | If an old payload has **no** **`GE`**, synthetic id `{SG[].I}_{MEC.MT}` from segment + market type (no **G**). |

---

## 8. Segment list (from Brazil SuperLiga sample in this file)

| Segment **I** | PN | TG | MEC (MT → N) |
|---------------|-----|-----|----------------|
| 710505433 | 1st set | — | 2→Popular, 3→Total, 4→Handicap, 8→Other, 15/10→Points, 1→All markets |
| 710505434 | 2nd set | — | (same pattern) |
| 710505435 | 3rd set | — | (same pattern) |

**Note:** **`Value.GE`** already lists every priced **G** for the event. Correlating each **G** to a segment (**PN**) + **MEC** name would need extra API fields or heuristics; until then we map by **`G`** and enrich display names manually or from a config table you maintain.
