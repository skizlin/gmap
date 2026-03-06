# Margin Configuration – Behaviour Spec

## Scope: templates per brand × sport

- **Templates are scoped by (brand, sport).** Each brand has its own set of templates per sport; the same sport can have different templates for different brands.
- **Global level** = no brand selected (`brand_id` empty). It acts as the default configuration used when copying to a new brand (e.g. “Copy From” uses Global as source).
- **Copy From** = copy template(s) from a source (typically Global) into the current brand × sport.
- **Copy To** = copy the current template(s) to another brand × sport.

## Uncategorized template

- **Uncategorized** is a special template that is **always present** for every (brand, sport) scope.
- It is used to initially collect competitions and markets for new or unmapped competitions.
- Every new competition in the system is assigned to Uncategorized until it is moved to another template.
- There is exactly one Uncategorized per (brand_id, sport_id). The system ensures it exists when loading the Margin Configuration for that scope; if missing, it is created automatically.

## Template list and UI

- When the user selects **Brand** and **Sport** and clicks **Apply**, the table shows only templates for that (brand, sport).
- At **Global** (no brand), templates with `brand_id` empty are shown for the selected sport; these are the defaults used when adding a new brand.
- **Add Template** creates a new template in the current (brand, sport) scope. The name “Uncategorized” is reserved for the system-created default; user-created templates use other names (e.g. “Tier 1”, “Tier 2”).

## Data

- **margin_templates.csv** includes `brand_id` and `sport_id`. Empty = Global for brand; `sport_id` identifies the sport for that row.
- **margin_template_competitions.csv** maps `(template_id, competition_id)`. Competitions are domain-level; assignment to a template is per template (and thus per brand × sport when templates are scoped).

## Summary

| Concept              | Meaning                                                                 |
|----------------------|-------------------------------------------------------------------------|
| Templates per brand  | Each brand has its own templates; Global = no brand (defaults).       |
| Templates per sport  | Each sport has its own templates within a brand (or Global).            |
| Uncategorized        | Always present per (brand, sport); used for new/unmapped competitions.  |
| Copy From            | Copy from a source (e.g. Global) into current scope.                   |
| Copy To              | Copy from current scope to another brand × sport.                       |
