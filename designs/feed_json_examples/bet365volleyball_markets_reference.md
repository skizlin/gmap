# Bet365 Volleyball – markets reference (one event)

**Source:** `bet365volleyball.json` (CHKS Chelm vs Kedzierzyn Kozle).  
**Convention:** Market ID = `main.sp.<key>.id` or `others[].sp.<key>.id`. Game Lines (910000) is split into three virtual markets: **910000_1** Winner, **910000_2** Handicap, **910000_3** Total. Outcome = `header` ("1"/"2" for home/away) or `name`; line in `handicap`. Odds = decimal (string in JSON).

---

## 1. Game Lines – Winner (910000_1)

| Market Name | Market ID | Outcome (header) | Odds (decimal) |
|-------------|-----------|------------------|----------------|
| Game Lines - Winner | 910000_1 | 1 (home) | 2.50 |
| Game Lines - Winner | 910000_1 | 2 (away) | 1.50 |

---

## 2. Game Lines – Handicap (910000_2)

| Market Name | Market ID | Outcome (header) | Line (handicap) | Odds (decimal) |
|-------------|-----------|------------------|-----------------|----------------|
| Game Lines - Handicap | 910000_2 | 1 | +1.5 | 1.72 |
| Game Lines - Handicap | 910000_2 | 2 | -1.5 | 2.00 |

---

## 3. Game Lines – Total (910000_3)

| Market Name | Market ID | Outcome (header) | Line (handicap) | Odds (decimal) |
|-------------|-----------|------------------|-----------------|----------------|
| Game Lines - Total | 910000_3 | 1 | O 184.5 | 1.83 |
| Game Lines - Total | 910000_3 | 2 | U 184.5 | 1.83 |

---

## 4. Correct Set Score (910201)

| Market Name | Market ID | Outcome (name) | Odds (decimal) |
|-------------|-----------|----------------|----------------|
| Correct Set Score | 910201 | 3-0 (header 1) | 8.00 |
| Correct Set Score | 910201 | 3-1 (header 1) | 6.50 |
| Correct Set Score | 910201 | 3-2 (header 1) | 6.00 |
| Correct Set Score | 910201 | 3-0 (header 2) | 3.75 |
| Correct Set Score | 910201 | 3-1 (header 2) | 4.00 |
| Correct Set Score | 910201 | 3-2 (header 2) | 4.75 |

---

## 5. Double Result (910210)

| Market Name | Market ID | Outcome (name) | Odds (decimal) |
|-------------|-----------|----------------|----------------|
| Double Result | 910210 | CHKS Chelm to WIN First set and WIN Match | 3.50 |
| Double Result | 910210 | CHKS Chelm to WIN First set and LOSE Match | 5.00 |
| Double Result | 910210 | Kedzierzyn Kozle to WIN First set and WIN Match | 2.00 |
| Double Result | 910210 | Kedzierzyn Kozle to WIN First set and LOSE Match | 7.50 |

---

## 6. Score After 2 Sets (910211)

| Market Name | Market ID | Outcome (name) | Header | Odds (decimal) |
|-------------|-----------|----------------|--------|----------------|
| Score After 2 Sets | 910211 | 2-0 | 1 | 4.75 |
| Score After 2 Sets | 910211 | 2-0 | 2 | 2.60 |
| Score After 2 Sets | 910211 | 1-1 | — | 2.00 |

---

## 7. Score After 3 Sets (910212)

| Market Name | Market ID | Outcome (name) | Header | Odds (decimal) |
|-------------|-----------|----------------|--------|----------------|
| Score After 3 Sets | 910212 | 3-0 | 1 | 8.00 |
| Score After 3 Sets | 910212 | 2-1 | 1 | 3.10 |
| Score After 3 Sets | 910212 | 3-0 | 2 | 3.75 |
| Score After 3 Sets | 910212 | 2-1 | 2 | 2.37 |

---

## 8. Set 1 Lines – Winner (910204_1)

*Same structure as Game Lines: one feed block (910204) is split into three virtual markets: 910204_1 Winner, 910204_2 Handicap, 910204_3 Total.*

| Market Name | Market ID | Outcome (header) | Odds (decimal) |
|-------------|-----------|------------------|----------------|
| Set 1 Lines - Winner | 910204_1 | 1 | 2.20 |
| Set 1 Lines - Winner | 910204_1 | 2 | 1.61 |

---

## 8b. Set 1 Lines – Handicap (910204_2)

| Market Name | Market ID | Outcome (header) | Line (handicap) | Odds (decimal) |
|-------------|-----------|------------------|-----------------|----------------|
| Set 1 Lines - Handicap | 910204_2 | 1 | +2.5 | 1.61 |
| Set 1 Lines - Handicap | 910204_2 | 2 | -2.5 | 2.20 |

---

## 8c. Set 1 Lines – Total (910204_3)

| Market Name | Market ID | Outcome (header) | Line (handicap) | Odds (decimal) |
|-------------|-----------|------------------|-----------------|----------------|
| Set 1 Lines - Total | 910204_3 | 1 | O 46.5 | 2.00 |
| Set 1 Lines - Total | 910204_3 | 2 | U 46.5 | 1.72 |

---

## 9. Set 1 Winning Margin (910207)

| Market Name | Market ID | Outcome (name) | Header | Odds (decimal) |
|-------------|-----------|----------------|--------|----------------|
| Set 1 Winning Margin | 910207 | 2 | 1 | 5.50 |
| Set 1 Winning Margin | 910207 | 3-4 | 1 | 6.50 |
| Set 1 Winning Margin | 910207 | 5-7 | 1 | 7.50 |
| Set 1 Winning Margin | 910207 | 8-11 | 1 | 17.00 |
| Set 1 Winning Margin | 910207 | 12+ | 1 | 67.00 |
| Set 1 Winning Margin | 910207 | 2 | 2 | 5.00 |
| Set 1 Winning Margin | 910207 | 3-4 | 2 | 5.50 |
| Set 1 Winning Margin | 910207 | 5-7 | 2 | 5.00 |
| Set 1 Winning Margin | 910207 | 8-11 | 2 | 9.50 |
| Set 1 Winning Margin | 910207 | 12+ | 2 | 41.00 |

---

## 10. Set 1 Correct Score (910208)

| Market Name | Market ID | Outcome (name) | Header | Odds (decimal) |
|-------------|-----------|----------------|--------|----------------|
| Set 1 Correct Score | 910208 | After extra points | 1 | 11.00 |
| Set 1 Correct Score | 910208 | 25-23 | 1 | 11.00 |
| Set 1 Correct Score | 910208 | 25-22 | 1 | 12.00 |
| Set 1 Correct Score | 910208 | 25-21 | 1 | 15.00 |
| Set 1 Correct Score | 910208 | 25-20 | 1 | 17.00 |
| Set 1 Correct Score | 910208 | 25-19 | 1 | 21.00 |
| Set 1 Correct Score | 910208 | 25-18 | 1 | 26.00 |
| Set 1 Correct Score | 910208 | 25-17 | 1 | 34.00 |
| Set 1 Correct Score | 910208 | 25-16 | 1 | 41.00 |
| Set 1 Correct Score | 910208 | 25-15 or better | 1 | 34.00 |
| Set 1 Correct Score | 910208 | After extra points | 2 | 9.50 |
| Set 1 Correct Score | 910208 | 25-23 | 2 | 10.00 |
| … (further scores for header 2) | 910208 | … | 2 | … |

---

## 11. Set 1 To Go To Extra Points (910209)

| Market Name | Market ID | Outcome (name) | Odds (decimal) |
|-------------|-----------|----------------|----------------|
| Set 1 To Go To Extra Points | 910209 | Yes | 5.00 |
| Set 1 To Go To Extra Points | 910209 | No | 1.14 |

---

## 12. Match Handicap (Points) (910216)

| Market Name | Market ID | Outcome (name) | Header | Odds (decimal) |
|-------------|-----------|----------------|--------|----------------|
| Match Handicap (Points) | 910216 | +5.5 | 1 | 1.83 |
| Match Handicap (Points) | 910216 | -5.5 | 2 | 1.83 |

---

## 13. Match Total Odd/Even (910217)

| Market Name | Market ID | Outcome (name) | Odds (decimal) |
|-------------|-----------|----------------|----------------|
| Match Total Odd/Even | 910217 | Odd | 1.83 |
| Match Total Odd/Even | 910217 | Even | 1.83 |

---

## 14. Set 1 Total Odd/Even (910218)

| Market Name | Market ID | Outcome (name) | Odds (decimal) |
|-------------|-----------|----------------|----------------|
| Set 1 Total Odd/Even | 910218 | Odd | 2.37 |
| Set 1 Total Odd/Even | 910218 | Even | 1.53 |

---

## 15. Team Totals (910214)

| Market Name | Market ID | Header | Line (handicap) | Odds (decimal) |
|-------------|-----------|--------|-----------------|----------------|
| Team Totals | 910214 | 2 | Over 95.5 | 1.83 |
| Team Totals | 910214 | 2 | Under 95.5 | 1.83 |

*Note: More lines/teams may appear in other events; structure uses `header`, `handicap`, `team`, `odds`.*

---

## Summary: market IDs and names

| Market ID | Market Name |
|-----------|-------------|
| 910000_1 | Game Lines - Winner |
| 910000_2 | Game Lines - Handicap |
| 910000_3 | Game Lines - Total |
| 910201 | Correct Set Score |
| 910204 | Set 1 Lines |
| 910207 | Set 1 Winning Margin |
| 910208 | Set 1 Correct Score |
| 910209 | Set 1 To Go To Extra Points |
| 910210 | Double Result |
| 910211 | Score After 2 Sets |
| 910212 | Score After 3 Sets |
| 910214 | Team Totals |
| 910216 | Match Handicap (Points) |
| 910217 | Match Total Odd/Even |
| 910218 | Set 1 Total Odd/Even |

**Notes:**

- **game_lines** block has `id` "910000"; we split it into three virtual markets (910000_1 Winner, 910000_2 Handicap, 910000_3 Total) using `odds[].name` (Winner / Handicap / Total).
- **Line** for handicap/total: from `odds[].handicap` (e.g. "+1.5", "O 184.5", "U 184.5").
- Some blocks (e.g. Match Handicap, Set 1 Lines) can appear in `main.sp` with empty `odds` and in `others[].sp` with populated `odds` (period-specific).
