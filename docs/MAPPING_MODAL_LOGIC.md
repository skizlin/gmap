# Mapping Modal — Logic and Priority

This document describes how the **Mapping Modal** (map feed event → domain event) works so the team and the code stay aligned.

---

## 1. Purpose

- Map a **feed event** (e.g. bet365 #190228030 “St Andrew Lions vs Ellerton FC”) to the **domain** (golden copy).
- Either **link to an existing domain event** (Confirm Mapping) or **create a new domain event** (Create & Map).
- All domain-side fields (Sport, Category, Competition, Home Team, Away Team) are **search boxes**: user can pick an existing entity or type a name and use **Create** to add it.

---

## 2. Order of Priority (When Entities Are Not Mapped)

Resolution order is fixed so parent entities exist before children:

1. **Sport** (required first)  
   - Resolved by: sport alias (feed sport name → domain sport) or user selecting from the **sport search dropdown**.  
   - Until sport is set, **Category**, **Competition**, and **Teams** stay disabled (no dropdown, no Create).  
   - Locked when: feed has a sport alias (e.g. “Soccer” → Football) → shows “Auto-matched”.

2. **Category** (after Sport)  
   - User **focuses/types** in the category field → **dropdown** shows domain categories for the selected sport.  
   - User can **select** from the list or **type a new name** and click **Create** to create and link the category.  
   - If there is **no domain match** for the feed category (e.g. “Barbados”), the field is **pre-filled with the raw feed value** and a yellow **“Suggested”** label.

3. **Competition** (after Sport; optionally after Category)  
   - Same behaviour as Category: **search/dropdown** + **Create**.  
   - Dropdown options are filtered by **sport** and optionally **category**.  
   - If there is **no domain match** (e.g. “Barbados Premier League”), the field shows the **raw feed value** with yellow **“Suggested”**.

4. **Home Team / Away Team** (after Sport)  
   - Same pattern: **search/dropdown** (existing domain teams for the sport) + **Create**.  
   - If there is **no domain match**, the field shows the **raw feed name** (e.g. “St Andrew Lions”) with yellow **“Suggested”**.  
   - **Create** requires the **domain sport name** to be known (from locked sport or from the sport search field). The modal sends it via the hidden field `domain-sport-name` when sport is locked.

---

## 3. Suggestion Rules (What Gets Pre-filled)

- **Suggested = raw feed value, no domain match**  
  When we have nothing to match in the domain (or match score is 0), we pre-fill with the **feed value** and show the yellow **“Suggested”** label. The user can keep it and click **Create** or change it (search/select another entity).

- **Do not use another event’s entities for Category/Competition**  
  A “suggested domain event” (e.g. fuzzy match to “Argentina / Liga Profesional”) is used for Category and Competition **only** when the event match score is **≥ 70%** (likely same match). Otherwise we must **not** overwrite with that event’s category/competition (e.g. we must not show “Argentina” / “Liga Profesional” for a **Barbados** feed). For low-scoring or different events we use only:
  - fuzzy match from the **current feed’s** category/competition names, or  
  - the **raw feed values** with **“Suggested”**.

- **Teams**  
  - If there is a high-scoring suggested domain event (score ≥ 70%), we may pre-fill Home/Away from that event (same match from another feed).  
  - Otherwise we pre-fill with **raw feed team names** and show **“Suggested”**.

---

## 4. UI Behaviour (Unified)

- **Sport, Category, Competition, Home Team, Away Team** all behave the same way:
  - **Search box** + **custom dropdown** on focus/type (no browser autocomplete / “black box”).
  - **Placeholder**: “Search existing &lt;entity&gt; or type name to create…”
  - **Create** button next to each: creates (or links) the entity for the current feed and enables “Create & Map” when all required fields are resolved.

- **Labels**  
  - **“Suggested”** (yellow): value is from the feed and has no domain match; user can Create or change.  
  - **Match %** (e.g. 35%): value comes from a domain match (or from a suggested domain event when score ≥ 70%).  
  - **“Auto-matched” / “Matched”** (lock): value was resolved by feed→domain mapping (e.g. sport alias, or existing entity_feed_mapping).

---

## 5. Why “Create” Might Fail (and Fixes)

- **Teams: “Cannot Create”**  
  Creating a team requires the **domain sport name** (e.g. “Football”). When sport is **locked** (Auto-matched), the modal must send that name. The frontend now reads it from the hidden field **`domain-sport-name`** (set when sport is locked) so the Create request always includes the correct sport name.

- **Category/Competition wrong values**  
  If the modal showed “Argentina” / “Liga Profesional” for a **Barbados** event, it was because a **different** suggested domain event was used for category/competition. The backend now uses that event’s category/competition **only when suggested event match score ≥ 70%**. Otherwise it uses feed-based suggestions or raw feed values with **“Suggested”**.

---

## 6. Summary Table

| Step | Field        | Priority | When not mapped | UI                          |
|------|--------------|----------|------------------|-----------------------------|
| 1    | Sport        | Must be first | Search/dropdown or alias | Search box + dropdown; “Suggested” if raw only |
| 2    | Category     | After Sport   | Raw name + “Suggested” or match | Search box + dropdown + Create |
| 3    | Competition  | After Sport (and Category for filter) | Same as Category | Search box + dropdown + Create |
| 4    | Home / Away  | After Sport   | Raw names + “Suggested” or from same event (≥70%) | Search box + dropdown + Create |

All domain-side fields use the same pattern: **search box + custom dropdown + Create**, and **“Suggested”** only when the value is the raw feed value with no domain match.
