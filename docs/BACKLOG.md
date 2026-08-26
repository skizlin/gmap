# Product backlog

Ideas and enhancements **not yet scheduled**. When work starts, move the item to a phase doc or implementation plan and link it here.

**Status key:** `idea` → `planned` → `in progress` → done (remove or mark complete)

---

## API-Football

### AF-PRICE-1 — Feeder Configuration: API-Football pricing tab

**Status:** idea  
**Context:** Feed Odds shows every bookmaker; Brand Overview / center **Price** uses **one** row today (first bookmaker for feed id 8 after Pricing Feed selection). See `docs/API_FOOTBALL_INTEGRATION.md` Phase 3.

**Proposal:** New tab/section under **Feeder Configuration** (or API-Football–specific config):

| Mode | Behaviour |
|------|-----------|
| **Weighted blend** | List bookmakers from `/odds/bookmakers` catalog; each row has **Weight** (e.g. 0–100). De-vig each book’s line, then combine fair odds (weighted average of implied probs or true odds — TBD). |
| **Priority** | Rank bookmakers 1, 2, 3…; use **first ranked book with a complete price set** for that market (similar to global Pricing Feed, but per bookmaker inside api_football). |

**Also consider:**

- Bookmaker allowlist (hide from Feed Odds UI)
- Default mode: weighted vs priority
- Persist in feeder config CSV (scope: global / sport / competition — TBD)
- Fallback when top priority has no odds for mapped bet

**Related today:** Global **Pricing Feed** row treats `api_football` as one feed; does not distinguish Bet365 vs Pinnacle.

---

### AF-ODDS-1 — Live odds (`/odds/live`)

**Status:** idea  
Fetch and cache in-play odds; timing/refresh rules TBD.

---

### AF-PULL-1 — League allowlist for scheduled fixture pulls

**Status:** idea  
Optional filter for automated or bulk fixture pulls.

---

## Pricing & Event Details

### PRICE-1 — Per-market fallback in Pricing Feed order

**Status:** idea  
**Context:** Feeder Configuration UI notes that missing lines do **not** yet fall through to the next feed in priority order. Extend pricing walk so incomplete lines try feed #2, #3, etc.

---

## Pinnacle

### PIN-API-1 — Live HTTP pull (all sports)

**Status:** idea  
Phase 1+2 use file ingest; live Pinnacle API pull not implemented. See `docs/PINNACLE_FEED_PHASE1.md`.

---

## How to add items

1. Append a section with id `AREA-SHORT-#`, **Status:** `idea`, short context, and bullet proposal.
2. Link to any existing design doc.
3. When implementing, change status and add a link to the PR or phase doc.
