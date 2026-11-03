---
name: {{project}}-frontend
description: Frontend stack and standards for {{Project}}. Use when generating or modifying any client or UI code, including components, pages, layouts, forms, styling, branding, translations and client-side data fetching.
---

# {{Project}}: frontend standards

Companion to `{{project}}-build`. Docs win on any conflict. Flag drift.

## Stack (locked)

| Concern | Choice |
|---------|--------|
| Framework | {{}} |
| Language | {{}} |
| Styling | {{}} |
| Component model | {{}} |
| Forms and validation | {{}} |
| Data fetching | {{}} |
| i18n | {{}} |

## Component standards

### Layering: what goes where
- {{layer}}: {{what it may contain, what it may import}}

Rule: {{import direction rule}}

### File and naming conventions
- {{}}

### Styling rules
- {{where colours and spacing come from, what is banned in components}}

### Forms
- {{validation source, error display, special field rules}}

### Branding and i18n
- {{}}

### Accessibility (baseline)
- Semantic elements first.
- Every interactive element is keyboard-reachable with a visible focus style.
- Inputs have labels. Icon-only buttons have an `aria-label`.
- Colour is never the only signal.

### State, data and performance
- {{}}

## Definition of done (any UI change)
- [ ] {{checkable item}}
- [ ] Loading, empty and error states handled.
- [ ] Accessible: labels, focus, keyboard, non-colour signals.
