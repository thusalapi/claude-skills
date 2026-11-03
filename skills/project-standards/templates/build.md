---
name: {{project}}-build
description: Build conventions for {{Project}}. Use whenever generating, scaffolding or modifying application code for this project. Encodes the locked stack and architecture decisions so generated code stays consistent.
---

# Building {{Project}}

{{One paragraph: what the product is, who uses it, the main modules.}}

Read alongside: {{list of docs/*.md}}. If those docs and this skill disagree, the docs win. Flag the drift.

**Companion skills** (detail layers, defer to them for specifics):
- `{{project}}-frontend`: UI standards.
- `{{project}}-backend`: server, data, auth and operations standards.

## Session continuity

`PROGRESS.md` is the living build log and the first thing to read in every session.
- At the start of build work, read it to see where things stand.
- As pieces finish, move them from "Next up" to "Done" and update "Last updated" and "Current stage".
- Record any new decision or gotcha there, and in the relevant `docs/*.md` if it is lasting.

A build change without a progress update is incomplete.

## Locked decisions (do not deviate without being asked)

| Area | Rule |
|------|------|
| {{Area}} | {{Specific, testable rule. Name what is banned as well as what is chosen.}} |

## Project layout

```
{{tree with one-line purpose per folder}}
```

## When generating UI

1. {{rule}}

## When generating server or data code

1. {{rule}}

## When deploying or scripting

- {{target environment, secrets handling, what must stay provider-agnostic}}

## Editing these conventions

The user may revise any decision. When they do, update the relevant `docs/*.md` and this skill together, then proceed.
