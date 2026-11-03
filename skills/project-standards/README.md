# Project Standards

A Claude skill that stops AI-generated code from drifting. It builds a **standards pack** for a codebase (locked decisions, layering rules, a definition of done and a progress log) and then makes Claude follow it on every change. A small rule checker catches the violations a regex can see.

## The problem

Over a long project, an AI coding assistant forgets last week's decisions. It reaches for a component library you rejected, writes a migration with the wrong tool, hard-codes a colour, or skips the role check in a server action because middleware "already did it". Each slip is small, and together they turn a codebase inconsistent.

## How it works

```
.claude/
├── skills/
│   ├── <project>-build/      master rules: locked decisions, layout, session routine
│   ├── <project>-frontend/   UI rules + definition of done
│   └── <project>-backend/    server and data rules + definition of done
└── standards-rules.json      rules a regex can check
PROGRESS.md                   build log read at the start of every session
```

1. **Create.** Claude reads the repo, asks only about decisions the code does not already answer (checklist in `references/decision-checklist.md`), and writes the pack from `templates/`.
2. **Build.** For each task Claude reads `PROGRESS.md` and the relevant skills, names the decisions that apply, writes the code, runs the checker, walks the definition of done and updates the progress log.
3. **Change.** When a decision changes, docs, skills and rules are updated together and the reason is logged.
4. **Review.** The checker runs on a branch's changed files and the diff is checked against the definition of done.

## Rule checker

`scripts/check_rules.py` is a dependency-free Python script. Rules are JSON: a glob, a regex, a message, and optional conditions such as "only in files marked `use client`".

```bash
python3 scripts/check_rules.py                        # whole repo
python3 scripts/check_rules.py --changed origin/main  # just this branch, good for CI
```

On the Suwa codebase (234 files) the six example rules run clean. A file planted with a raw hex colour, a hard-coded product name and a database import inside a client component is caught three times:

```
src/components/atoms/Bad.tsx:3  [error] no-raw-hex: Use a semantic Tailwind token from lib/design, never a raw hex colour.
src/components/atoms/Bad.tsx:2  [error] no-server-import-in-client: Client components must not import server-only modules.
src/components/atoms/Bad.tsx:3  [error] no-brand-literal: Read the product name from brand.* in lib/branding, never hard-code it.
```

## Worked example: Suwa

[`examples/suwa`](examples/suwa) is the real pack I use to build [Suwa](https://github.com/thusalapi/Suwa), a self-hosted clinic management system (Next.js, PostgreSQL, Drizzle, Liquibase, self-hosted auth). It covers tenant isolation, gap-free invoice numbering, frozen snapshots for reproducible reports, audit rows in the same transaction as every mutation, atomic design and i18n.

## Use it

**Claude Code**

```
/plugin marketplace add thusalapi/claude-skills
/plugin install project-standards@thusala-skills
```

Then ask: *"Set up a standards pack for this repo."*

**Claude app:** download this folder as a zip and upload it under Settings > Capabilities > Skills.
