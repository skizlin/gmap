# Future Improvements

This file tracks planned improvements to be implemented later.

---

## Map-to-existing domain event: score only on unmapped entities

**Context:** When mapping a feed event to an existing domain event, the suggestion list shows a match percentage (e.g. 50%). Currently that percentage is based on all dimensions (sport, category, competition, home team, away team). If sport, category, and competition are already mapped but teams are not, a domain event in the same league but with different teams can still show as 50% match, which is misleading.

**Improvement:** When computing the match % for “map to existing domain event”, **only take into account entities that are not already mapped** for this feed event.

- If sport is already mapped → do **not** include sport in the score.
- If category is already mapped → do **not** include category.
- If competition is already mapped → do **not** include competition.
- If home team is not mapped (only suggested) → **do** include home team in the score.
- If away team is not mapped → **do** include away team.

**Result:** The match percentage would reflect how well the candidate domain event matches on the **remaining** unmapped dimensions (e.g. teams). A “same league, different teams” domain event would score low instead of 50%, and strong suggestions would be those that actually match on the unmapped entities.

**Status:** Not implemented — to be picked up later.
