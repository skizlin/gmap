# RBAC (Role & User Management) — CSV-based implementation plan (draft)

**Sources:** SBP-Global Mapper – Role & User Management (RBAC).pdf; Operational team requirements (user management, templates, email, client-side admin).  
**Status:** Draft — aligned with operational requirements and current product (Partners, Brands).  
**Constraint:** Demo site uses CSV only (no database).

**Implementation scope (first delivery):** Initial phase only. **Out of scope** for this implementation: 2FA, email-based password recovery, email verification before login, bulk onboarding/offboarding, and access logs. These remain in the plan as later phases.

---

## 1. Alignment with SBP and operational requirements

- **Personas:** Admin (full RBAC + audit), Power User, Standard User — access via assigned roles only. Operational ask: add **template-based** roles (e.g. Trading, Support, Brand Admin) for faster onboarding.
- **User scope:** Users are **not** globally agnostic. They can be:
  - **Platform-level** (our admins): no partner; full scope.
  - **Partner-scoped** (client admins): tied to a **Partner** (B2B client); may be restricted to that partner’s **Brands**. Partner admins manage only users within their assigned Partner (and optionally Brands). *Aligns with: “client-side user management within assigned TRS and Brands”.*
- **TRS:** Interpret “assigned TRS” as the partner’s scope (and optionally the set of brands assigned to that partner). No separate TRS entity in CSV; use existing Partners + Brands.
- **Permission matrix:** Entities (Sport, Category, Competition, Event, Markets, Market Types) with CRUD; Mapping (View, Create, Update, Unmap, Pause, Cascade); Customization (View, Create, Update, Delete). Operational ask: support **tab-level** view/edit semantics in UI (simplified mapping).
- **Audit:** Who did what, when; immutable and traceable. *Audit log* = RBAC actions (role/user/permission changes). *Access logs* (login/feature access) = later phase if required for compliance.
- **No hardcoded permissions** — all checks driven by CSV data.

**Current product:** Partners and Brands already exist (`partners.csv`, `brands.csv`; Configuration > Brands & Partners). RBAC must reference `partner_id` on users and optional brand scope; partner admins see only their partner’s users/brands.

---

## 2. Proposed CSV files

| File | Purpose |
|------|--------|
| `users.csv` | Users, **email** (mandatory), status, **partner_id** (optional), optional brand scope. No passwords in CSV; auth handled separately. |
| `roles.csv` | Role definitions (name, description, active). Optional: link to template. |
| `role_templates.csv` | (Optional) Named templates (e.g. Trading, Support, Brand Admin) = bundle of role_ids for “create user from template”. |
| `user_roles.csv` | Many-to-many: which user has which role(s). |
| `user_brands.csv` | (Optional) User–brand access when user is partner-scoped; empty = all brands of partner. |
| `role_permissions.csv` | Permissions per role (granular or tab-level codes). |
| `rbac_audit_log.csv` | Immutable log of role/permission/user changes. |

Optional: `permission_definitions.csv` for a single source of permission codes and labels.

---

## 3. Schema (suggested)

**users.csv**  
`user_id`, `login`, **`email`** (mandatory), `display_name`, `active`, **`partner_id`** (optional; null = platform user), `created_at`, `updated_at`

**roles.csv**  
`role_id`, `name`, `description`, `active`, `created_at`, `updated_at`  
Optional: `is_system`, `template_name` (e.g. for “Brand Admin” template).

**role_templates.csv** (optional, for template-based creation)  
`template_id`, `name`, `description`, `role_ids` (comma-separated or separate rows), `active`

**user_roles.csv**  
`user_id`, `role_id`, `assigned_at`, `assigned_by_user_id`  
Composite (user_id, role_id). One user can have multiple roles; permissions additive.

**user_brands.csv** (optional; when partner-scoped user has restricted brand access)  
`user_id`, `brand_id`  
If absent for a partner-scoped user, treat as “all brands of that partner”.

**role_permissions.csv**  
`role_id`, `permission_code`, (optional) `scope` / `cascade`  
One row per (role, permission).

**rbac_audit_log.csv**  
`id`, `created_at`, `actor_user_id`, `action`, `target_type`, `target_id`, `details`  
Append-only; no updates/deletes.

---

## 4. Permission codes (hierarchical)

- **Entities:** `entity.<resource>.<action>`  
  Resources: `sport`, `category`, `competition`, `event`, `markets`, `market_type`.  
  Actions: `view`, `create`, `update`, `delete`.  
  Examples: `entity.sport.view`, `entity.category.create`.

- **Mapping:** `mapping.<action>`  
  Actions: `view`, `create`, `update`, `unmap`, `pause`, `cascade`.  
  Examples: `mapping.view`, `mapping.create`, `mapping.unmap`.

- **Customization:** `customization.<action>`  
  Actions: `view`, `create`, `update`, `delete`.

- **Tab-level (optional, for simplified UI):**  
  E.g. `tab.entities.view`, `tab.entities.edit`, `tab.mapping.view`, `tab.mapping.edit`, etc.  
  UI can map these to granular codes or use them directly for “view only” vs “can edit” per tab.

New features = new codes + new rows in `role_permissions.csv`; no default open access.

---

## 5. Runtime behaviour (concept)

- Load users, roles, user_roles, role_permissions (and optionally role_templates, user_brands) e.g. at startup or per request.
- Resolve current user → set of permission codes (from roles).
- **Scope check:** If user is partner-scoped (`partner_id` set), restrict all “manage users” (and optionally other) actions to that partner (and to allowed brands if `user_brands` is used).
- Every feature: check “user has permission X” (set lookup).
- UI: same codes drive visibility/disable (no hardcoded “if admin”).
- Admin flows: all changes write CSVs + one append to `rbac_audit_log.csv` per change.

---

## 6. Guardrails

- **Delete role:** Block if any user has that role (or force reassign first); or soft-delete (`active = 0`).
- **Deactivate user:** Set `active = 0`; permission check excludes inactive users.
- **Delete user:** **Allow deletion only when user is inactive**, with controls (e.g. only by platform admin; optional: only after N days inactive; confirmation + audit log entry). Do not allow delete of active users.
- **Clone role:** New role row + copy all `role_permissions` for that role; one audit entry.
- **Clone user / create from template:** Support “create user from template” (assigns template’s role bundle) or “clone user” (copy roles from existing user) for faster onboarding; one audit entry per created user.
- **Audit:** Append-only; never update/delete `rbac_audit_log.csv`.

---

## 7. Default roles and templates (suggestion)

| Role / Template | Permissions (examples) |
|-----------------|-------------------------|
| Admin | All entity/mapping/customization + `rbac.roles.manage`, `rbac.users.manage`, `rbac.audit.view` |
| Power User | Entity/Mapping/Customization: view, create, update (tuned); mapping unmap/pause/cascade as needed |
| Standard User | View only for entity, mapping, customization |
| **Templates (operational):** | |
| Trading | Role bundle for trading workflow (e.g. mapping + entities edit) |
| Support | Role bundle for support (e.g. view + limited edit) |
| Brand Admin | Role bundle for client-side admin: manage users only within own partner/brands |

---

## 8. UI requirements (operational)

- **User list / profile:** Display **user email** and **status** (active/inactive) clearly.
- **User creation:** Mandatory **email** at account creation; optional login (e.g. login = email).
- **Tab-level:** Present permissions as tab-level view/edit where appropriate to simplify UX.

---

## 9. Phasing

**Initial phase (CSV + current product)**  
- Template-based user creation (e.g. Trading, Support, Brand Admin).  
- Mandatory email in users; display email and status in UI.  
- Partner- and optional brand-scoped users; client-side user management within assigned partner and brands.  
- Tab-level permission semantics (view/edit) in UI.  
- Audit log for RBAC actions.

**Later phases (out of scope for first implementation)**  
- 2FA and email-based password recovery (auth layer / third-party).  
- Email verification before login.  
- Bulk onboarding/offboarding; bulk brand access removal.  
- Access logs (who accessed what, when) for compliance.  
- Deletion of inactive users with controls (policy already in guardrails).

---

## 10. File location

Example: `backend/data/rbac/` with `users.csv`, `roles.csv`, `user_roles.csv`, `role_permissions.csv`, `rbac_audit_log.csv`, and optionally `role_templates.csv`, `user_brands.csv`.  
Reference existing: `backend/data/partners.csv`, `backend/data/brands.csv`.

---

## 11. Extensibility

- New feature → new permission codes → new rows in `role_permissions` (and optional `permission_definitions`).
- New entity type → `entity.<new>.view/create/update/delete` and wire UI/API to these codes only.
- New template → new row in `role_templates` (or template_name on roles) and assign role bundle.

---

*For gap analysis vs operational requirements, see `rbac-operational-requirements-analysis.md`.*
