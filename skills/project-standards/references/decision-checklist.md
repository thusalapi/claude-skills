# Decision checklist

Answer from the repo first. Ask the user only about what is still open. Every answer becomes a row in the locked-decisions table, phrased as a testable rule.

## Product and scope
- What is the product, who uses it, what are the core modules?
- Single tenant or multi-tenant? If multi, what is the tenant key and must every query filter by it?

## Frontend
- Framework and rendering model (server components, SPA, SSR)?
- Component library or hand-built? Anything explicitly banned?
- Component structure (atomic design, feature folders) and import direction?
- Styling source of truth (design tokens, Tailwind theme)? Are raw colours allowed in components?
- Forms and validation library? Shared schemas with the backend?
- i18n: languages now and later? Are literal strings allowed in components?
- Branding: where do the product name, colours and logo live?
- Accessibility baseline?

## Backend
- Runtime and hosting target (serverless, container, on-premise PC)?
- API style (REST, server actions, GraphQL, tRPC)?
- Database, query layer, and migration tool? Who owns migrations?
- Auth: self-hosted or provider? Roles? Where are role checks enforced?
- Validation at the boundary?
- Audit logging: which actions, same transaction or not?
- Deletion policy: hard delete or status changes?
- Money: integer minor units? Currency?
- Numbering or IDs that must be sequential or gap-free?
- Data that must be frozen at creation (prices on invoices, templates on reports)?

## Operations
- Secrets handling?
- Backups, restore testing, schedule?
- Logging rules (no personal data, no secrets)?
- What must stay provider-agnostic to allow a later migration?

## Process
- Where is progress tracked? (`PROGRESS.md` by default)
- Tests required per change? Which kinds?
- Branch and PR conventions?
