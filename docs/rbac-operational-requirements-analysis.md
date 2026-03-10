# RBAC plan vs operational requirements — analysis report

**Date:** 2026  
**Purpose:** Compare operational team requirements with `plan-rbac-csv.md` and current product (Partners, Brands), and list changes needed in the plan.

---

## 1. Operational requirements (extracted)

| Category | Requirement | Phase |
|----------|-------------|--------|
| **Identity** | Mandatory email at account creation; email-anchored identity | Initial |
| **Identity** | 2FA; email-based password recovery | Later |
| **Identity** | Email verification before user can log in | Later |
| **Templates** | Template-based user creation (e.g. Trading, Support, Brand Admin) | Initial |
| **Templates** | Cloning of user templates for faster setup | Later |
| **Scope** | Client-side user management within assigned TRS and Brands | Initial |
| **Roles** | Simplify role structure to tab-level permissions (view/edit) | Initial |
| **UI** | Display user email and status clearly | Initial |
| **Audit** | Audit trail and access logs for compliance | Later (audit in plan already) |
| **Users** | Inactive users: allow deletion with proper controls (not only disable) | Later |
| **Operations** | Bulk onboarding/offboarding; brand access removal | Later |
| **Product** | Modular, phased delivery; reduce onboarding time and manual errors | — |

**Pain points addressed:** 3.5h onboarding per brand; clients cannot self-serve; no audit/visibility; no email/2FA.

---

## 2. Current plan (plan-rbac-csv.md) — what it already covers

- Personas (Admin, Power User, Standard User) and permission matrix (Entities, Mapping, Customization).
- CSV files: users, roles, user_roles, role_permissions, rbac_audit_log.
- **Users are brand-agnostic** (no partner/brand scope).
- Granular permission codes (entity.*, mapping.*, customization.*).
- Audit: append-only log (who did what, when).
- Guardrails: deactivate user (no delete); clone role.
- No email field; no templates; no partner/brand scope; no tab-level simplification; no 2FA/recovery/verification; no bulk ops; no “delete inactive” policy.

---

## 3. Current product structure (already built)

- **Partners** (B2B clients): `partners.csv` — id, name, code, active.
- **Brands**: `brands.csv` — id, name, code, **partner_id**, jurisdiction, languages, etc.  
  - `partner_id` empty = Global (platform); non-empty = brand belongs to that partner.
- **Configuration > Brands & Partners**: two tabs — Partners, Brands. Partners can have multiple brands.

So: any RBAC plan must align with **Partners** and **Brands** and support **client (partner) admins** managing users only within their partner and assigned brands.

---

## 4. Gap analysis: add / change / remove

### 4.1 Add to plan

| Item | Detail |
|------|--------|
| **Email (mandatory)** | Add `email` to users.csv; require at creation. Use for identity and (later) recovery. Clarify `login` vs email (e.g. login = email or separate). |
| **User/role templates** | Define named templates (e.g. “Trading”, “Support”, “Brand Admin”) as a bundle of roles (or one template role). Template-based user creation = “create user from template X” assigns that bundle. Option: `role_templates.csv` or template_id on roles. |
| **Partner and brand scope** | Users (and/or roles) scoped to Partner and optionally to Brand(s). Platform admins: no partner_id (or Global). Partner admins: `partner_id` set; can manage only users for their partner and (optionally) only for brands assigned to that partner. Add `partner_id` (and optionally brand scope) to users and to “who can manage whom” rules. |
| **TRS** | Clarify “assigned TRS” from ops (e.g. Trading / brand set / region). If TRS = trading or a tag, add to glossary; if TRS = set of brands, align with partner_id + brand_ids. |
| **Tab-level permissions (option)** | Ops want “tab-level view/edit”. Either: (a) add permission codes like `tab.entities.view`, `tab.entities.edit`, etc., or (b) document that existing granular permissions are presented as tab-level in UI (view = view-only, edit = create/update/delete). Plan should state support for tab-level semantics (for UI and simplification). |
| **UI requirements** | Show user email and status (active/inactive) clearly in user list and profile. |
| **Clone user (from template/user)** | Support “clone user” or “create from template” for faster onboarding (in addition to clone role). |
| **Later phases (explicit)** | 2FA; email-based password recovery; email verification before login; bulk onboarding/offboarding and brand access removal; access logs (who accessed what, when) in addition to audit log; deletion of inactive users with controls. |

### 4.2 Change in plan

| Item | Current | Change |
|------|---------|--------|
| **User scope** | “Users are brand-agnostic.” | **Replace with:** Users can be platform-level (no partner_id) or scoped to a Partner; optionally restrict to specific Brand(s). Partner admins manage only users in their scope. |
| **Deactivate vs delete** | “Deactivate user: set active=0; no delete.” | **Add policy:** Allow **deletion of inactive users** under controls (e.g. only by platform admin; only when user has been inactive for N days; and/or confirmation + audit log). Keep “no delete” for active users. |
| **Audit vs access logs** | Plan has “audit: who did what, when.” | **Clarify:** Audit log = actions on RBAC (role/user/permission changes). **Access logs** (login/access to features) = separate later-phase concern if needed for compliance. |

### 4.3 Remove / relax

| Item | Action |
|------|--------|
| **“Users are brand-agnostic”** | Remove; replaced by partner/brand-scoped model above. |
| **Strict “no delete” for users** | Relax to “no delete for active users; allow delete for inactive with controls”. |

---

## 5. Alignment with current product

- **Partners and Brands** are already in the product; plan must reference `partners.csv` and `brands.csv` and user scope (`partner_id`, optional brand list).
- **Global** = platform (our) admins; no partner_id or partner_id empty.
- **Partner admins** = users with a role that allows “manage users” restricted to their `partner_id` (and optionally their brands). Plan should describe this as “client-side user management within assigned TRS and Brands”.
- **Configuration > Brands & Partners** is the natural place to link from (or next to) user management when assigning partner/brand to a user.

---

## 6. Summary: plan updates to apply

1. **Schema:** Add `email` (mandatory) to users; add `partner_id` (optional) and optional brand scope (e.g. `brand_ids` or `user_brands.csv`).
2. **Templates:** Add role/user templates (e.g. Trading, Support, Brand Admin) for template-based creation and cloning.
3. **Scope:** Replace “brand-agnostic” with partner- and optionally brand-scoped users; document partner-admin scope rules.
4. **Permissions:** Add tab-level view/edit option or mapping from granular to tab-level in UI.
5. **UI:** Require display of user email and status.
6. **Guardrails:** Add “delete inactive user with controls”; add “clone user / create from template”.
7. **Phasing:** Add “Initial” vs “Later” (2FA, recovery, verification, bulk ops, access logs, delete inactive).
8. **Glossary:** Clarify TRS and its relation to Partners/Brands.
9. **References:** Reference existing `partners.csv` and `brands.csv` and Configuration > Brands & Partners.

These points have been applied in `plan-rbac-csv.md` in a consolidated way.
