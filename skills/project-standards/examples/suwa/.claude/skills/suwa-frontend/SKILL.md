---
name: suwa-frontend
description: Frontend stack and standards for the Suwa clinic management system. Use when generating or modifying any client/UI code — React components, pages, layouts, forms, Tailwind styling, branding, translations, or client-side data fetching. Encodes the locked FE stack and the conventions every component must follow.
---

# Suwa — Frontend standards

Companion to `suwa-build` (the master conventions) and `docs/branding.md`. This skill is
the detail layer for the **frontend**. Docs win on any conflict; flag drift.

## Stack (locked)

| Concern | Choice |
|---------|--------|
| Framework | **Next.js (App Router)**, React Server Components by default |
| Language | **TypeScript** (strict) |
| Styling | **Tailwind CSS**, hand-built components — **no shadcn/ui, no component library** |
| Component model | **Atomic design**: `atoms → molecules → organisms → templates` |
| Forms | **react-hook-form + Zod** (shared schemas with the backend) |
| Data fetching | Server Components + **Server Actions**; client fetching only when interactivity demands it |
| Icons | One icon set (e.g. `lucide-react`), imported per-icon (no barrel) |
| Branding | `lib/branding/brand.ts` — never hard-code name/hex/logo |
| i18n | `lib/i18n` — every string via `t()`; **English-only at launch (`en`)**, multi-locale file pattern kept for later |
| PDF | `@react-pdf/renderer` components under `components/pdf/` |

## Component standards

### Atomic layering — what goes where
- **atoms/** — single-purpose primitives: `Button`, `Input`, `Field`, `Label`, `Badge`,
  `Spinner`, `Icon`. No business logic, no data fetching, no `t()` of feature copy
  (atoms take their labels as props).
- **molecules/** — small compositions of atoms: `FormRow`, `SearchBar`, `StatCard`,
  `Pagination`. May call `t()` for their own copy.
- **organisms/** — feature-aware sections: `PatientFinder`, `ReportView`, the report form
  renderer. May read data passed in via props from a Server Component.
- **templates/** — page-level layout/shell (dashboard shell, auth shell). No business
  data — slots/children only.
- **app/** pages compose templates + organisms and own data fetching.

Rule: a component may import **downward only** (organism → molecule → atom), never upward
or sideways into another feature's organism.

### Server vs Client components
- Default to **Server Components**. Add `"use client"` only for interactivity (state,
  effects, event handlers, browser APIs).
- Keep client components small and at the leaves; fetch data in Server Components and pass
  it down.
- Never import server-only modules (`lib/db`, `lib/auth`) into a client component.

### File & naming conventions
- One component per file; `PascalCase.tsx` matching the export name.
- Co-locate component-only types in the same file; shared types in `src/types`.
- Folder per component only when it has siblings (styles/tests/subparts); otherwise flat.
- Props interface named `<Component>Props`; prefer explicit props over spreading.

### Styling rules
- Tailwind utilities only; no inline `style` except for dynamic values that can't be
  expressed as classes.
- Colours come from the **design-token layer** (`lib/design`: primitive → semantic →
  theme) via Tailwind **semantic** utilities (`bg-primary`, `text-ink`, `border-border`,
  `bg-surface-raised`…) — **never a raw hex, never a primitive token, in a component**.
- New role needed? Add it to `tokens.semantic.ts`, map it in `theme.ts` (`cssVarName`) and
  `globals.css` (`@theme inline`), then use it. See `docs/design-system.md`.
- Keep the design-system slice (`lib/design`, `components/*`, `lib/i18n`) free of
  business/data deps so it stays extractable to a shared `packages/ui` at SaaS scale.
- Extract a repeated class string into a small atom or a `cn()`-composed variant, not
  copy-paste.
- Build mobile-first; the clinic PC is desktop but keep layouts fluid.

### Forms
- `react-hook-form` for state; **Zod** resolver using the schema shared with the backend
  (`lib/schema`). Never duplicate validation rules.
- Show field errors inline via the `Field` atom; map server validation errors back onto
  fields.
- Money inputs collect a display value but submit **integer minor units**; format via the
  i18n currency formatter.
- Patient forms: **phone is required** (the lookup key) and validated; **NIC is optional**.

### Branding & i18n (hard rules)
- No literal user-facing string in JSX — `t("namespace.key")`. Add keys to `en.ts` (the
  only locale at launch; the file pattern stays multi-locale-ready).
- No literal brand name / logo path / hex — read from `brand.*`.
- Numbers, currency (LKR), dates → locale-aware formatters from `lib/i18n`, never string
  concatenation or `toLocaleString` scattered inline.

### Accessibility (baseline, non-negotiable)
- Semantic elements first (`button`, `nav`, `table`, `label`+`for`).
- All interactive elements keyboard-reachable with visible focus styles.
- Inputs have associated labels; icons-only buttons have `aria-label` (via `t()`).
- Colour is never the only signal (pair flags/abnormal results with text/icon).

### State & data
- Local UI state in the component; cross-cutting state via React context sparingly.
- Mutations go through **Server Actions** that call backend helpers — components never
  embed SQL or hit the DB directly.
- Show optimistic/loading/empty/error states for every async surface.

### Performance
- Server Components + streaming for data-heavy pages; avoid shipping data-fetching libs to
  the client.
- `next/image` for raster assets; SVG logos inline from `brand`.
- Memoize only measured hot paths; don't pre-optimize.
- Keep client bundles lean — no heavy date/util libs where a small formatter suffices.

## Definition of done (any UI change)
- [ ] Built from existing atoms/molecules where possible; new primitives are generic.
- [ ] No hard-coded brand value (name/hex/logo) and no literal copy — `brand.*` + `t()`.
- [ ] New i18n keys added to `en` (the only locale at launch).
- [ ] Server/Client boundary correct; no server-only imports in client code.
- [ ] Accessible: labels, focus, keyboard, non-colour signals.
- [ ] Loading / empty / error states handled.
- [ ] Money as integer minor units; LKR/date via i18n formatters.
