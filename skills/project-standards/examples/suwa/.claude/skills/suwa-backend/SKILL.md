---
name: suwa-backend
description: Backend stack and standards for the Suwa clinic management system. Use when generating or modifying any server-side code — route handlers, server actions, database schema/queries, Liquibase migrations, auth, sessions, validation, audit logging, PDF generation, backups, or deployment scripts. Encodes the locked BE stack and the rules every mutation must follow.
---

# Suwa — Backend standards

Companion to `suwa-build` (master conventions), `docs/architecture.md`, and
`docs/data-model.md`. This skill is the detail layer for the **backend**. Docs win on any
conflict; flag drift.

## Stack (locked)

| Concern | Choice |
|---------|--------|
| Runtime | **Next.js standalone Node server** on the clinic PC — no serverless/edge |
| API surface | **Server Actions** for mutations; **Route Handlers** for PDFs/files/webhooks |
| Database | **PostgreSQL**, installed locally |
| Queries/types | **Drizzle** (schema + typed queries) |
| Migrations | **Liquibase** changelogs — never Drizzle/Prisma migrate |
| Auth | **Self-hosted credentials** — argon2/bcrypt, HTTP-only session cookies |
| Validation | **Zod** (schemas shared with the frontend) |
| PDF | **@react-pdf/renderer** server-side |
| Backups | nightly `pg_dump` → encrypted → **Google Drive** |

## Layering

```
Server Action / Route Handler   ← validate input, resolve session, check role
        │
        ▼
Service/helper in lib/*          ← business logic, one transaction per mutation
        │
        ▼
lib/db (Drizzle)                 ← typed queries; every query filters by clinic_id
```

- Route handlers / actions are thin: parse → authorize → call a service → shape response.
- No SQL or business rules in components or actions; put them in `lib/*` services.

## Database standards

- **Schema lives in Liquibase.** Every change = a new changeset in `liquibase/` (master
  changelog includes per-change files). Changesets are immutable once applied — never edit
  a shipped changeset; add a new one. Drizzle's schema mirrors the DB for types/queries but
  does **not** own migrations.
- **Tenant isolation:** every domain table carries `clinic_id`; **every query filters by
  it.** No exceptions. Consider Postgres RLS later for defense in depth.
- **Money is integers** (smallest currency unit, LKR). No floats, no decimals in money
  columns.
- **Status, never hard-delete** for financial/clinical rows; cancellations are a state.
- **JSONB** for flexible structure (template schema, report data); real columns for
  queryable facts (money, status, dates, FKs).
- **Patients:** `unique(clinic_id, phone)` — phone is the lookup key (required); `nic` is
  optional. Search/dedupe by phone.

### Sequential numbering (gap-free)
- `bill_number` / `report_number` are sequential **per clinic** and gap-free.
- Generate atomically inside the same transaction as the row insert (DB sequence scoped
  per clinic, or `SELECT ... FOR UPDATE` on a per-clinic counter). Never compute from
  `COUNT(*)` or in app code outside a transaction.

### Reproducibility (most important rule)
- **Reports** freeze `template_snapshot` (full schema JSON at creation).
- **Bills** snapshot `unit_price` + `description` onto each `bill_item`.
- Re-rendering a PDF reads only frozen data — never the live catalog/template.

## Mutations — the standard shape

Every create/edit/verify mutation must:
1. **Validate** input with the shared Zod schema (reject early, typed errors).
2. **Resolve session** and **check role server-side** (never trust the client).
3. Run the change **and its audit row in one DB transaction**:
   ```ts
   await db.transaction(async (tx) => {
     const row = await writeChange(tx, input);
     await recordAudit(tx, { action, entityType, entityId: row.id, metadata });
     return row;
   });
   ```
4. Return a typed result; map domain errors to safe messages (no stack/SQL leakage).

If the audit write can't happen, the change must not commit — they live or die together.

## Auth & authorization

- Passwords hashed with **argon2** (or bcrypt); never store or log plaintext.
- Login verifies the hash, then issues a **signed, HTTP-only, SameSite** session cookie;
  sessions resolved in middleware → user + role on every request.
- **No public sign-up.** First **owner** seeded by a one-time `scripts/` setup script;
  owner invites staff/doctor; invited users set their password on first login
  (`must_reset`).
- Roles: `owner | staff | doctor`. Enforce per-action with a server-side guard helper;
  the middleware gate is necessary but not sufficient — re-check in each mutation.
- Rate-limit / lock out repeated failed logins; constant-time hash comparison.

## Validation & errors

- Zod schemas in `lib/schema`, shared with the FE so rules aren't duplicated.
- Validate at the boundary (action/handler entry). Treat all client input as hostile.
- Distinguish: validation errors (400-ish, field-mapped), auth errors (401/403), and
  unexpected errors (500, logged with context, generic message to client).

## PDF generation

- `@react-pdf/renderer` in a route handler / server action — pure Node, no headless
  browser.
- Documents read **frozen** data (snapshot), plus **clinic identity** from the `clinics`
  row and **product brand** from `lib/branding`.
- Stream or buffer the PDF; set correct content-type and filename.

## Backups & operations

- Nightly job (`lib/backup/` + a `scripts/` entry): `pg_dump` → encrypt → upload to
  **Google Drive** (rclone/Drive API), scheduled via Windows Task Scheduler.
- Keep a tested **restore** script — a backup that can't restore isn't a backup.
- Secrets in a local `.env` on the clinic PC (never committed). No cloud/Vercel/Clerk
  calls.

## Cloud-migration readiness

Keep everything provider-agnostic: connection via env, schema via Liquibase, server as
standalone Node. Migration later = restore a dump into managed Postgres, replay Liquibase,
repoint the connection string, run the same server. Don't introduce Vercel/Clerk lock-in.

## Definition of done (any server change)
- [ ] Input validated with a shared Zod schema.
- [ ] Session resolved; role checked server-side in the mutation, not just middleware.
- [ ] Change + audit row in one transaction.
- [ ] Query filters by `clinic_id`.
- [ ] Money as integers; numbering generated atomically and gap-free.
- [ ] Snapshots frozen for reports/bills.
- [ ] Schema change is a new Liquibase changeset (not an ad-hoc ALTER or ORM migrate).
- [ ] No secrets/PII in logs; errors mapped to safe messages.
