---
name: project-standards
description: Create and enforce a project's coding standards pack, so code Claude writes stays consistent with the locked stack, architecture and rules across sessions. Use when the user wants to set up conventions or guardrails for a codebase, asks Claude to follow "our stack" or "project rules", or when a repo already has a standards pack in .claude/skills and code is being written or reviewed.
---

# Project Standards

AI coding assistants drift. Across sessions they swap libraries, invent folder layouts, skip validation and forget decisions made last week. This skill fixes that with a **standards pack**: three small project skills plus a progress log, kept in the repo and read before any code is written.

```
.claude/
├── skills/
│   ├── <project>-build/SKILL.md      master: locked decisions, layout, session rules
│   ├── <project>-frontend/SKILL.md   UI detail layer + definition of done
│   └── <project>-backend/SKILL.md    server/data detail layer + definition of done
└── standards-rules.json              machine-checkable rules (optional)
PROGRESS.md                           living build log, read at the start of every session
```

The build skill is the shared source of truth. The frontend and backend skills add detail and never contradict it. Project docs (`docs/*.md`) win over all three. When they disagree, follow the docs and tell the user about the drift.

## Mode 1: create a pack

1. **Read the repo first.** `package.json` or equivalent, config files, folder layout, existing docs, README, and any existing `.claude/` or `CLAUDE.md`. Record what is already decided by the code itself.
2. **Interview for the gaps.** Ask only about decisions the repo does not answer. Group them so it takes one or two rounds. The checklist is in `references/decision-checklist.md`. Typical gaps: UI library or hand-built, auth provider, migration tool, hosting target, tenancy, money and date handling, i18n, audit and deletion policy.
3. **Write the pack** from `templates/`. Fill every placeholder. Rules must be specific and testable:
   - Weak: "Write secure code."
   - Strong: "Every mutation re-checks the user's role server-side, even when middleware already did."
4. **Write a definition of done** at the end of the frontend and backend skills. Each item must be checkable by reading a diff.
5. **Add machine rules** for anything a regex can catch (hard-coded colours, banned imports, literal brand names) in `.claude/standards-rules.json`. See `references/rules-format.md`.
6. **Create `PROGRESS.md`** from `templates/PROGRESS.md` with the current stage and the next 3 to 5 tasks.
7. Show the user the locked-decisions table for confirmation before saving.

## Mode 2: build with a pack

When the repo has a pack, follow this loop for every coding task:

1. Read `PROGRESS.md`, then the build skill, then the frontend or backend skill for the area being changed.
2. Before writing code, name the locked decisions that apply. If the request conflicts with one, stop and ask. Never quietly deviate.
3. Write the code.
4. Run `python3 <skill-dir>/scripts/check_rules.py` from the repo root if `standards-rules.json` exists, and fix every finding.
5. Walk the definition of done for each area touched, item by item.
6. Update `PROGRESS.md`: move finished items to Done, add new decisions or gotchas, update "Last updated". A change without a progress update is incomplete.

## Mode 3: change a decision

The user may revise any locked decision. When they do, update the relevant `docs/*.md`, the build skill, the detail skill and the rules file in the same change, and log the decision with its reason in `PROGRESS.md`.

## Mode 4: review

To review a branch or PR against the pack, run the rule checker on the changed files, then check the diff against each definition-of-done item and list findings as: rule broken, file and line, suggested fix.

## Worked example

`examples/suwa/` is the full pack from [Suwa](https://github.com/thusalapi/Suwa), a self-hosted clinic management system built with Next.js, PostgreSQL, Drizzle and Liquibase. Use it as a reference for the level of detail a good pack needs.
