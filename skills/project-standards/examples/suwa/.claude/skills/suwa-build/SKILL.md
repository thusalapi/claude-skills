---
name: suwa-build
description: Build conventions for the Suwa clinic management system. Use whenever generating, scaffolding, or modifying application code for this project — components, auth, database, migrations, PDFs, branding, or translations. Encodes the locked stack and architecture decisions so generated code stays consistent.
---

# Building Suwa

**Suwa** (Sinhala සුව — "health/wellness") is a self-hosted clinic/lab management system
for small Sri Lankan medical centers. Two cores on a shared patient registry: **billing**
and a **schema-driven report engine**. First customer is a design-partner clinic.

Read alongside: `docs/architecture.md`, `docs/data-model.md`, `docs/report-engine.md`,
`docs/branding.md`, `docs/roadmap.md`. If those docs and this skill ever disagree, the
docs win — and flag the drift.

**Companion skills** (the detail layers — defer to them for specifics):
- `suwa-frontend` — UI/React/Tailwind/atomic-design/i18n standards.
- `suwa-backend` — server actions, DB/Drizzle, Liquibase, auth, audit, backups standards.
This skill is the shared source of truth; when FE/BE specifics are needed, use those.

## Session continuity — always track progress

`PROGRESS.md` (repo root) is the living build log and the **first thing to read when a
session starts**. It records what exists and what's next so work continues across
sessions. Keep it current as part of every build task:
- At the **start** of build work, read it to see where things stand.
- As you finish pieces, move items from "Next up" to "Done" and update "Last updated" /
  "Current stage".
- Record any new decision or gotcha there (and in the relevant `docs/*.md` if it's a
  lasting convention).

Updating `PROGRESS.md` is not optional — a build change without a progress update is
incomplete.

## Locked decisions — do not deviate without being asked

| Area | Rule |
|------|------|
| UI library | **No shadcn/ui, no component library.** Hand-build with Tailwind. |
| Component structure | **Atomic design**: `atoms/ → molecules/ → organisms/ → templates/`. |
| Auth | **Self-hosted credentials.** No Clerk / no external IdP. Hashed passwords (argon2/bcrypt), HTTP-only session cookies, server-side role checks. |
| DB migrations | **Liquibase** changelogs. Not Drizzle/Prisma migrate. |
| DB access | Drizzle for typed queries/schema only (migrations stay in Liquibase). |
| Hosting | **Self-hosted on the clinic's PC.** No Vercel, no serverless/edge assumptions. Next.js **standalone** output, run as a plain Node server. |
| Backups | Nightly `pg_dump` → encrypted → **Google Drive** upload (rclone/Drive API), Windows Task Scheduler. |
| Patient identity | **Phone number is the unique lookup key** (per clinic). **NIC is optional.** UUID stays the internal PK. |
| Branding | Centralized in `src/lib/branding/brand.ts`. Never hard-code the name "Suwa", a hex colour, or a logo path. |
| Translations | Centralized in `src/lib/i18n/`. **English-only at launch (`en`)**, kept on the multi-locale file pattern so `si`/`ta` drop in later (new `locales/*.ts` + extend the `Locale` union). **No literal user-facing strings in components** — use `t("namespace.key")`. |
| Money | Integers (smallest currency unit, LKR). No floats. |
| Numbering | `bill_number` / `report_number` sequential per clinic, gap-free, generated atomically. |
| Reproducibility | Reports freeze `template_snapshot`; bills snapshot price + description. Re-render reads only frozen data. |
| Audit | `recordAudit(...)` inside every create/edit/verify, in the same DB transaction. |

## Project layout (target)

```
src/
├── app/
│   ├── (auth)/          # login only — single-clinic, no public sign-up
│   ├── (dashboard)/     # session-gated: patients, billing, reports, templates, catalog, settings
│   └── api/             # route handlers (PDF gen, mutations)
├── components/          # atoms / molecules / organisms / templates  (+ pdf/)
├── lib/
│   ├── db/              # drizzle schema + client (queries/types)
│   ├── auth/            # hashing, sessions, role guards
│   ├── branding/        # brand.ts (single source of truth)
│   ├── i18n/            # t(), locales/en.ts (English-only at launch)
│   ├── schema/          # template JSON schema + Zod validators
│   ├── pdf/             # @react-pdf builders (report, invoice)
│   ├── flagging/        # reference-range -> flag logic
│   ├── backup/          # pg_dump + Google Drive job
│   └── audit/           # audit-log helpers
liquibase/               # changelogs (master + per-change)
scripts/                 # setup (seed owner), backup, restore
```

## When generating UI

1. Build from atoms up; reuse existing atoms/molecules before adding new ones.
2. No literal brand name / hex / logo path → read from `brand.*`.
3. No literal copy → `t("namespace.key")`; add the key to `en.ts` (the only locale at
   launch).
4. Money, dates, numbers → locale-aware formatters, never string concatenation.

## When generating server/data code

1. Every mutation re-checks role server-side; never trust the client.
2. Every domain table carries `clinic_id`; every query filters by it.
3. Schema changes = a new Liquibase changeset, never an ad-hoc ALTER or ORM migration.
4. Wrap create/edit/verify + its audit row in one transaction.
5. Patients: enforce `unique(clinic_id, phone)`; treat `nic` as optional.

## When deploying / scripting

- Assume the **clinic PC** (Windows): local Postgres, Next.js standalone Node server.
- No cloud/Vercel/Clerk calls. Secrets in a local `.env` (never committed).
- Keep everything cloud-agnostic so a later migration is config + data, not a rewrite.

## Editing these conventions

The user may revise any decision later. When they do: update the relevant `docs/*.md`
**and** this skill so they stay in sync, then proceed. Treat this file as the quick
reference; the docs are the detail.
