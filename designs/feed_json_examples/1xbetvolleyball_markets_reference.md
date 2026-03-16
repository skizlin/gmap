# 1xbet Volleyball – markets reference (structure and identifiers)

**Source:** `1xbetvolleyball.json` (Lokomotiv Novosibirsk vs Yaroslavich, Russia. Superleague).  
**Convention:** 1xbet uses a **nested structure**: event → **Value.SG** (segments) → **MEC** (market categories) → **Value.GE** (outcome groups). There is no single “market ID” per row like Bwin/Bet365; market identity is by **segment (SG)** + **market type (MEC.MT)** + **outcome group (GE.G)**. Outcomes and odds live in **GE.E** with **C**/CV = decimal odds, **P** = line, **T** = outcome type.

---

## 1. Top-level event and segments

| Field | Location | Meaning |
|-------|----------|---------|
| Event ID | `results[].id` | e.g. "702175340" |
| Home / Away | `results[].home.name`, `results[].away.name` | Team names |
| Segments | `results[].Value.SG[]` | List of market segments (Match, 1st set, 2nd set, Aces, etc.) |

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

## 4. Outcome groups (GE) and odds

**Value.GE** is an array of outcome groups. Each group has:

| Field | Meaning |
|-------|---------|
| **G** | Group id (links to segment/category; e.g. 17, 2, 15, 62, 136, 2663) |
| **E** | Array of “rows”; each row is an array of outcomes (typically 2 for fixed markets). |

**Each outcome in E[][]:**

| Field | Meaning | Example |
|-------|---------|---------|
| **C** / **CV** | Decimal odds | 1.42, 2.53, 1.83 |
| **P** | Line (handicap/total value) | 130.5, -20.5, 46.5, 75.5 |
| **T** | Outcome type id | 9 = Over, 10 = Under; 7 = side1, 8 = side2; 11/12 = Total pair; 13/14 = another pair; 731 = 3-way; etc. |
| **CE** | (optional) | e.g. 1 for “main” or tie |

**Outcome type (T) mapping (from sample):**

| T | Likely meaning | Used in |
|---|----------------|--------|
| 9 | Over | Total (Over X) |
| 10 | Under | Total (Under X) |
| 7 | Handicap side 1 | Handicap (e.g. +X) |
| 8 | Handicap side 2 | Handicap (e.g. -X) |
| 11 | Total outcome 1 | One line total |
| 12 | Total outcome 2 | Same line total |
| 13 / 14 | Total (another group) | Other totals |
| 731 | 3-way (e.g. 1 / X / 2) | Double result / correct score style |
| 196 / 197, 206 / 207 | Pair of outcomes | Handicap or total by group |

*Exact T values may vary by sport/segment; need to infer from context (pair of outcomes + P = line).*

---

## 5. Example: Match Total (one segment)

- **Segment:** SG with empty **PN** (match), **MEC** with **MT** 3, **N** "Total".
- **GE:** Find group **G** that belongs to this segment (e.g. **G: 17**).
- **E:** e.g. two rows (two lines); each row has two outcomes (Over/Under):
  - Row 1: P=130.5 → T=9 (Over 130.5) odds 1.42, T=10 (Under 130.5) odds 2.53.
  - Row 2: P=132.5 → Over 2.14, Under 1.94.
- So **line** = **P**, **outcomes** = two elements per row with **C** = odds, **T** = over/under.

---

## 6. Example: Handicap (one segment)

- **Segment:** e.g. Set 1; **MEC** with **MT** 4, **N** "Handicap".
- **GE:** e.g. **G: 2**.
- **E:** rows with **P** = handicap line (e.g. -20.5, -19.5, … and +20.5, +19.5, …). Each row: two outcomes (T=7 and T=8 or similar) with **C** = odds.
- **Line** = **P** (can be negative/positive); **outcomes** = two sides.

---

## 7. Summary: identifiers for integration

| What we need | Where in 1xbet |
|--------------|----------------|
| **Market “id”** | Composite: `SG[].I` + `MEC[].MT` (e.g. segment id + market type), or `GE[].G` per outcome group. Parser currently uses `{segmentI}_{MT}`. |
| **Market name** | Derived: `SG[].PN` + " – " + `MEC[].N` (e.g. "1st set – Total", "Match – Handicap"). |
| **Line** | **GE.E[][].P** (numeric; e.g. 130.5, -20.5). |
| **Outcomes** | **GE.E**; each inner array = one line; elements have **C** (odds), **P** (line), **T** (outcome type). Map T to Over/Under or Side1/Side2. |
| **Odds** | **C** or **CV** (decimal). |

---

## 8. Segment list (from sample event)

| Segment I | PN | TG | MEC (MT → N) |
|-----------|-----|-----|----------------|
| 702175341 | 1st set | — | 2→Popular, 3→Total, 4→Handicap, 8→Other, 15/10→Points, 1→All markets |
| 702175342 | 2nd set | — | (same structure) |
| 702175343 | 3rd set | — | (same structure) |
| … | … | Aces | 2→Popular, 3→Total, 4→Handicap, … |
| … | … | Serve faults | (same) |
| … | … | Blocks | (same) |

**Note:** Full extraction of every market name and outcome list (like Bwin/Bet365 tables) would require walking all **SG** and **GE** and resolving **G** to segment + **MT**, then building a flat list. This document defines the **structure and identifiers** so that 1xbet parsing and mapping can match the same canonical descriptor (template, period, line, outcomes) as the other feeds.
