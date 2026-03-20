# DESIGN_TOKENS.md — iter/004 Visual System

**Role:** Frontend Architect (iter/004)
**Date:** 2026-03-20

---

## 1. Design principles

1. **Typography over ornament.** Use text hierarchy, not decorative borders.
2. **Surface hierarchy, not variety.** Fewer surface levels, more distinction between them.
3. **Quiet where it doesn't earn its noise.** Chips, pills, and badges only where they carry meaning.
4. **Dense where it helps.** Information density is a feature, not a problem.
5. **Light and editorial.** Not white-glove SaaS, not dark hacker terminal.

---

## 2. Color palette

### 2.1 Base palette (CSS custom properties)

```css
:root {
  /* Background layers */
  --color-bg:           #f4f6f9;   /* page background */
  --color-bg-subtle:    #edf0f5;   /* subtle inset areas */
  --color-surface:      #ffffff;   /* primary surface (panels, cards) */
  --color-surface-muted:#f8fafc;   /* muted surface (nested sections) */

  /* Border */
  --color-border:       #dde3ec;   /* default border */
  --color-border-strong:#b8c5d6;   /* emphasis border */

  /* Text */
  --color-text:         #0e1724;   /* primary text — slightly warmer than #0f172a */
  --color-text-secondary:#4a5568; /* secondary / descriptive text */
  --color-text-muted:   #718096;   /* metadata, labels, captions */
  --color-text-disabled: #a0aec0;  /* disabled controls */

  /* Accent — restrained indigo/slate */
  --color-accent:        #4338ca;  /* primary accent (links, active states) */
  --color-accent-light:  #eef2ff;  /* accent background tint */
  --color-accent-border: rgba(67, 56, 202, 0.22); /* accent-colored border */

  /* Semantic */
  --color-success:       #047857;
  --color-warning:       #92400e;
  --color-danger:        #991b1b;
  --color-danger-bg:     #fff5f5;

  /* Interactive states */
  --color-hover-bg:      rgba(14, 23, 36, 0.04);
  --color-selected-bg:   #f0f3ff;
  --color-selected-border: rgba(67, 56, 202, 0.3);
  --color-focus-ring:    rgba(67, 56, 202, 0.35);
}
```

### 2.2 Map / chart categorical palette

Used in Explorer color-by-source / color-by-cluster modes.
Chosen for: distinguishable at small point sizes, accessible contrast, editorial (not rainbow).

```js
// In MapPanel, keep existing color assignment logic but use these base hues
const CATEGORICAL_PALETTE = [
  '#4338ca',  // indigo
  '#0369a1',  // sky blue
  '#047857',  // emerald
  '#b45309',  // amber
  '#9d174d',  // rose
  '#6d28d9',  // violet
  '#0e7490',  // cyan
  '#15803d',  // green
  '#c2410c',  // orange
  '#475569',  // slate (for "other")
]
```

Outlier color: `#ef4444` (red) — retained from iter/003, it works.

### 2.3 Color use rules

- **Never** use accent color purely decoratively
- **Do not** use green/red to mean good/bad for editorial content (outlet bias is not a quality signal)
- Source color assignment should be consistent within a session (derived from source name hash)
- Cluster color assignment: consistent cluster_id → palette index mapping

---

## 3. Typography

### 3.1 Font stack

```css
:root {
  font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif;
}
```

Keep Inter. It is correct for this product. No changes.

### 3.2 Text scale

```css
:root {
  /* Body */
  --text-xs:    0.75rem;    /* 12px — labels, captions, eyebrows */
  --text-sm:    0.875rem;   /* 14px — secondary body, metadata */
  --text-base:  1rem;       /* 16px — primary body */
  --text-md:    1.0625rem;  /* 17px — article titles, card headlines */
  --text-lg:    1.25rem;    /* 20px — section headers, panel titles */
  --text-xl:    1.5rem;     /* 24px — route headers */
  --text-2xl:   1.875rem;   /* 30px — product wordmark */

  /* Line heights */
  --leading-tight:  1.2;
  --leading-snug:   1.35;
  --leading-normal: 1.5;
  --leading-relaxed:1.65;
}
```

### 3.3 Font weight usage

| Weight | Use |
|---|---|
| 400 | Body text, summaries, descriptions |
| 500 | Labels, field names, navigation |
| 600 | Card headlines, section names, active nav |
| 700 | Story card headline, route title, strong emphasis |

### 3.4 Eyebrow / label treatment

```css
.text-eyebrow {
  font-size: var(--text-xs);
  font-weight: 500;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: var(--color-text-muted);
}
```

Use sparingly — only where a category label genuinely helps orientation.
Do NOT use eyebrows as decorative styling above every panel.

---

## 4. Spacing scale

```css
:root {
  --space-1:  0.25rem;   /*  4px */
  --space-2:  0.5rem;    /*  8px */
  --space-3:  0.75rem;   /* 12px */
  --space-4:  1rem;      /* 16px */
  --space-5:  1.25rem;   /* 20px */
  --space-6:  1.5rem;    /* 24px */
  --space-8:  2rem;      /* 32px */
  --space-10: 2.5rem;    /* 40px */
  --space-12: 3rem;      /* 48px */
}
```

### Spacing use rules

- Panel inner padding: `--space-5` (20px) default, `--space-4` (16px) for compact sections
- Gap between stream cards: `--space-3` (12px)
- Gap between major sections: `--space-6` (24px)
- Top bar height: `--space-12` (48px)

---

## 5. Border and radius

```css
:root {
  /* Radius */
  --radius-sm:   0.375rem;  /*  6px — chips, tags, small buttons */
  --radius-md:   0.625rem;  /* 10px — cards, panels, inputs */
  --radius-lg:   0.875rem;  /* 14px — drawers, dialogs */
  --radius-full: 9999px;    /* pills */

  /* Border */
  --border-width: 1px;
}
```

### Radius use rules

The current design uses `--radius-md: 1rem` and `--radius-lg: 1.25rem` everywhere — this creates a soft, rounded look that undercuts the analytical character. Reduce across the board.

- Story cards: `--radius-md` (10px)
- Filter drawer: `--radius-lg` (14px) on the panel edge
- Inputs: `--radius-sm` (6px) — inputs should feel precise, not bubbly
- Segmented controls: `--radius-full` only for the pill container, `--radius-sm` for buttons inside
- Chips/tags: `--radius-sm` (not `--radius-full` — pill chips look too casual for analytical UI)

---

## 6. Elevation / shadow

```css
:root {
  --shadow-none: none;
  --shadow-xs:   0 1px 3px rgba(14, 23, 36, 0.06);
  --shadow-sm:   0 2px 8px rgba(14, 23, 36, 0.08);
  --shadow-md:   0 4px 16px rgba(14, 23, 36, 0.10);
  --shadow-lg:   0 8px 32px rgba(14, 23, 36, 0.14);
  --shadow-overlay: 0 16px 48px rgba(14, 23, 36, 0.18);
}
```

### Elevation use rules

| Element | Shadow |
|---|---|
| Page background | none |
| Panel / card (default) | `--shadow-xs` |
| Hovered card | `--shadow-sm` |
| Focus panel / context rail | `--shadow-sm` |
| Top bar (sticky) | `--shadow-xs` on scroll |
| Filter drawer (overlay) | `--shadow-overlay` |
| Tooltip | `--shadow-md` with dark background |

Current styles use `--shadow-sm: 0 8px 20px` on nearly everything, which makes all surfaces feel equally elevated — kills hierarchy. Scale this down.

---

## 7. Surface hierarchy rules

The current UI applies borders + background + shadow to almost every element at the same intensity. This makes everything look equally important.

New rule: **only three surface levels**.

| Level | Background | Border | Shadow | Use |
|---|---|---|---|---|
| 0 — Page | `--color-bg` | none | none | Page background |
| 1 — Panel | `--color-surface` | `--color-border` | `--shadow-xs` | Main panels, focus panel, context rail |
| 2 — Inset | `--color-surface-muted` | `--color-border` | none | Nested sections within Level 1 (source groups, article detail) |
| Overlay | `--color-surface` | `--color-border-strong` | `--shadow-overlay` | Filter drawer, tooltips |

Cards (story cards, article rows) are elements within Level 1 panels — they should not have their own full border+shadow stack. Use subtle border or hover state only.

---

## 8. Interactive states

```css
/* Focus ring — keyboard navigation */
:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
  border-radius: var(--radius-sm);
}

/* Selected story card */
.story-card.selected {
  border-left: 3px solid var(--color-accent);
  background: var(--color-selected-bg);
  /* No box-shadow ring */
}

/* Hovered card */
.story-card:hover {
  background: var(--color-hover-bg);
  border-color: var(--color-border-strong);
}

/* Selected article row */
.article-row.selected {
  background: var(--color-accent-light);
  border-left: 2px solid var(--color-accent);
}

/* Active nav item */
.nav-item.active {
  color: var(--color-text);
  font-weight: 600;
  border-bottom: 2px solid var(--color-accent);
  /* No background, no box shadow */
}
```

### Transition rules

- Button/card hover: `120ms ease` — quick, not sluggish
- Drawer open/close: `220ms ease-out` — smooth slide
- Filter changes: no transition on data (let data swap immediately)
- No bounce, spring, or elaborate animation

---

## 9. Component visual rules

### 9.1 Chips / badges

Remove the two-tier chip system (`status-chip`, `summary-pill`) — they're interchangeable in the current CSS and both overused.

New unified rules:

```css
/* Use for: source names, counts, quick metadata */
.badge {
  display: inline-flex;
  align-items: center;
  padding: 0.2rem 0.5rem;
  font-size: var(--text-xs);
  font-weight: 500;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  background: var(--color-surface-muted);
  color: var(--color-text-secondary);
}

/* Accent variant — current workspace or emphasis */
.badge.accent {
  background: var(--color-accent-light);
  border-color: var(--color-accent-border);
  color: var(--color-accent);
}

/* Muted variant — secondary metadata */
.badge.muted {
  border-color: transparent;
  background: var(--color-bg-subtle);
  color: var(--color-text-muted);
}
```

Usage discipline:
- Max 3 source chips visible on a story card
- No entity chips on stream cards
- Tag chips: 1 primary tag maximum on stream cards
- Source chips: should show source name only, not count (count is in the meta row)

### 9.2 Buttons

```css
/* Ghost button — primary action in context */
.btn-ghost {
  padding: 0.45rem 0.85rem;
  font-size: var(--text-sm);
  font-weight: 500;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text);
  cursor: pointer;
}

.btn-ghost:hover {
  border-color: var(--color-border-strong);
  background: var(--color-hover-bg);
}

/* Accent button — for primary CTAs like "Refine", "Clear all" */
.btn-accent {
  padding: 0.45rem 0.85rem;
  font-size: var(--text-sm);
  font-weight: 600;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-accent-border);
  background: var(--color-accent-light);
  color: var(--color-accent);
}

/* Text link button — for back navigation, secondary actions */
.btn-text {
  padding: 0;
  font-size: var(--text-sm);
  font-weight: 500;
  border: none;
  background: none;
  color: var(--color-accent);
  text-decoration: underline;
  text-underline-offset: 3px;
}
```

### 9.3 Inputs and selects

```css
input, select {
  height: 2.25rem;
  padding: 0 0.75rem;
  font-size: var(--text-sm);
  border-radius: var(--radius-sm);    /* reduced from current 0.85rem */
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text);
}

input:focus, select:focus {
  outline: 2px solid var(--color-accent);
  outline-offset: -1px;
  border-color: transparent;
}
```

### 9.4 Section dividers

```css
/* SectionDivider — between named sections within a panel */
.section-divider {
  border: none;
  border-top: 1px solid var(--color-border);
  margin: var(--space-5) 0;
}
```

Used in Story focus panel and Explorer context rail between named sections.
Do not use between every element — only between semantically distinct sections.

---

## 10. Layout-level tokens

```css
:root {
  /* Top bar */
  --topbar-height: 3rem;       /* 48px */

  /* Stories layout */
  --stories-stream-width: minmax(0, 1fr);
  --stories-focus-width:  min(480px, 37vw);

  /* Explorer layout */
  --explorer-context-width: 320px;

  /* Filter drawer */
  --filter-drawer-width: 340px;

  /* Content max width (stories header, etc.) */
  --content-max: 72rem;        /* 1152px — prevents ultra-wide stretch */
}
```

---

## 11. CSS architecture notes for builder

### What to keep from `styles.css`
- Color variable names (can rename to match above tokens if cleaner)
- Map canvas and DeckGL-related styles (`.map-frame`, `.map-canvas`, `.tooltip-card`)
- Segmented control pattern
- `color-scheme: light` declaration

### What to rewrite in `styles.css`
- The giant `.brand-block, .sidebar-note, .status-strip, .workspace-panel ...` border/shadow rule (applies the same look to ~25 elements — kills hierarchy)
- All sidebar-related styles (`.app-sidebar`, `.brand-block`, `.sidebar-note`)
- `.workspace-grid` and `.workspace-panel` as generic three-column layout
- All `.status-chip` and `.summary-pill` — replace with `.badge` system
- Border radius values — reduce across the board

### Stylesheet structure recommendation

Consider splitting styles:
```
frontend/src/
  styles/
    tokens.css     ← custom properties only
    base.css       ← reset, html/body/root
    layout.css     ← shell, top bar, route-level layouts
    components.css ← reusable component styles
    stories.css    ← stories-specific styles
    explorer.css   ← explorer-specific styles
```

Or keep single `styles.css` if the builder prefers — but at minimum, the token block must come first and all component styles must reference tokens, not hardcoded values.

---

*Design tokens complete. See UI_SPEC.md for layout and component specs.*
