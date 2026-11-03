---
name: {{project}}-backend
description: Backend stack and standards for {{Project}}. Use when generating or modifying server-side code, including handlers, database schema and queries, migrations, auth, validation, audit logging, background jobs and deployment scripts.
---

# {{Project}}: backend standards

Companion to `{{project}}-build`. Docs win on any conflict. Flag drift.

## Stack (locked)

| Concern | Choice |
|---------|--------|
| Runtime | {{}} |
| API surface | {{}} |
| Database | {{}} |
| Queries and types | {{}} |
| Migrations | {{}} |
| Auth | {{}} |
| Validation | {{}} |

## Layering

```
Handler            validate input, resolve session, check role
   |
Service            business logic, one transaction per mutation
   |
Data access        typed queries, tenant filter on every query
```

- Handlers are thin: parse, authorise, call a service, shape the response.
- No SQL or business rules in handlers or UI code.

## Database standards
- {{migration rule: tool, immutability of applied changesets}}
- {{tenancy rule}}
- {{money, dates, deletion policy, JSON vs columns}}

## Mutations: the standard shape
1. Validate input with the shared schema.
2. Resolve the session and check the role server-side.
3. Run the change {{and its audit row}} in one transaction.
4. Return a typed result. Map domain errors to safe messages.

## Auth and authorisation
- {{}}

## Validation and errors
- {{}}

## Operations
- {{backups, restore test, secrets, scheduling}}

## Definition of done (any server change)
- [ ] Input validated with a shared schema.
- [ ] Role checked server-side in the mutation itself.
- [ ] {{checkable item}}
- [ ] Schema change is a new migration, never an edit to an applied one.
- [ ] No secrets or personal data in logs. Errors mapped to safe messages.
