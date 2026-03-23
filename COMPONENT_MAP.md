# COMPONENT_MAP.md — iter/005 Editorial Analysis Component Architecture

**Role:** Frontend architect  
**Date:** 2026-03-23

## 1. Goal

Map the exact frontend artifacts needed to integrate editorial analysis into the existing Stories and Explorer workflows.

This is a bounded addition to the current app, not a route rewrite.

---

## 2. Existing surfaces to extend

### Stories flow
- `frontend/src/routes/ClusterBrowserPage.tsx`
- `frontend/src/components/stories/StoryFocusPanel.tsx`
- `frontend/src/components/stories/CoverageBar.tsx`

### Explorer flow
- `frontend/src/routes/ExplorerPage.tsx`
- `frontend/src/components/explorer/ExplorerContextRail.tsx`

### Shared type/api layer
- `frontend/src/lib/types.ts`
- `frontend/src/lib/api.ts`

---

## 3. Proposed component additions

## 3.1 `components/editorial/EditorialStatusBadge.tsx`

### Role
Render normalized status/applicability/review badges.

### Inputs
```ts
type EditorialStatusBadgeProps = {
  kind:
    | 'completed'
    | 'pending'
    | 'failed'
    | 'limited'
    | 'out_of_domain'
    | 'low_confidence'
    | 'needs_review'
    | 'missing_evidence'
  compact?: boolean
}
```

### Used by
- `EditorialAnalysisCard`
- article list preview badges
- `EditorialLensSection`

---

## 3.2 `components/editorial/EditorialDimensionGrid.tsx`

### Role
Render article-level editorial dimensions in a compact grid.

### Inputs
```ts
type EditorialDimensionGridProps = {
  article_type: string
  article_type_confidence: number
  bias_label: string
  bias_confidence: number
  tone_emotional: string
  tone_target: string
  opinionatedness: string
  sensationalism: string
  rhetorical_certainty: string
  compact?: boolean
}
```

### Notes
- must support full and compact layouts
- confidence must show label + numeric value
- weak values should be muted, not removed

---

## 3.3 `components/editorial/EditorialEvidenceList.tsx`

### Role
Render the evidence spans in a consistent format.

### Inputs
```ts
type EditorialEvidenceListProps = {
  evidence: Array<{
    type: string
    text: string
    note: string
  }>
  compact?: boolean
}
```

### Notes
- clamp long evidence text
- preserve quotes/snippet feel
- empty evidence with completed analysis should allow a warning callout upstream

---

## 3.4 `components/editorial/EditorialAnalysisCard.tsx`

### Role
Primary article-level editorial artifact.

### Variants
- `full` → Stories article detail
- `compact` → ExplorerContextRail

### Inputs
```ts
type EditorialAnalysisCardProps = {
  editorial: ExplorerEditorialSummary | null
  variant: 'full' | 'compact'
  clusterId?: number | null
  storiesHref?: string | null
}
```

### Internal composition
- header row
- badge row
- dimension grid
- framing block
- evidence list
- rationale block
- limitations block
- optional CTA row

### State responsibilities
This component owns rendering for:
- null / absent
- pending
- failed
- limited
- out_of_domain
- completed strong
- completed weak

That keeps the ugly logic in one place instead of spread across Stories and Explorer.

---

## 3.5 `components/stories/EditorialSourceComparisonRow.tsx`

### Role
One source row inside cluster comparison.

### Inputs
```ts
type EditorialSourceComparisonRowProps = {
  sourceSummary: StoryClusterEditorialSourceSummary
  onSelectArticle?: (articleId: number) => void
}
```

### Rendered content
- source name
- analyzed / total count
- applicability indicators
- article type mix
- bias label mix
- opinionatedness mix
- framing highlight chips with example article hooks
- review-state counts

### Notes
This component should not try to narrate outlet ideology. It should narrate **cluster-scoped behavior**.

---

## 3.6 `components/stories/EditorialLensSection.tsx`

### Role
Cluster-level editorial comparison section for `StoryFocusPanel`.

### Inputs
```ts
type EditorialLensSectionProps = {
  editorialSummary: StoryClusterEditorialSummary | null
  onSelectArticle: (articleId: number) => void
}
```

### Internal blocks
1. analysis coverage summary
2. source comparison rows
3. cluster signals / pattern callouts
4. scope + confidence note

### Empty behavior
If no editorial summary exists:
- render a restrained empty state
- copy: `Editorial comparison is not yet available for this story.`

---

## 3.7 Optional `components/stories/EditorialMemberPreviewBadges.tsx`

### Role
Keep article-card badge logic isolated.

### Inputs
```ts
type EditorialMemberPreviewBadgesProps = {
  preview: StoryClusterMemberItem['editorial_preview'] | null | undefined
}
```

### Output
At most 2–3 badges.

### Notes
Worth adding if member preview data lands. Otherwise StoryFocusPanel can inline it, but a tiny component is cleaner.

---

## 4. Existing component changes

## 4.1 `StoryFocusPanel.tsx`

### New data dependencies
- `detail.editorial_summary`
- `article.editorial`
- optional `member.editorial_preview`

### Structural changes
Current:
- brief
- coverage
- article list OR article detail

Target:
- brief
- coverage
- editorial lens
- article list OR article detail

### Required edits
- insert `<EditorialLensSection />` after coverage
- insert `<EditorialAnalysisCard variant="full" />` inside `ArticleDetailSection`
- optionally render preview badges in `SourceGroupList`

### Why here
This file is the product center of gravity for the Stories workflow.

---

## 4.2 `ExplorerContextRail.tsx`

### New data dependency
- `detail.editorial`

### Required edits
- insert compact editorial block after article section
- provide `storiesHref` / story comparison CTA when cluster exists
- keep cluster context and neighborhood below it

### Ordering
1. article identity / actions
2. editorial read
3. cluster context
4. semantic neighborhood

That order keeps the rail human-readable.

---

## 4.3 `ClusterBrowserPage.tsx`

No structural route change needed.

### Contract implication
Needs the same detail fetch call to return enriched `StoryClusterDetail` and enriched article detail payloads. Component wiring stays basically the same.

---

## 4.4 `ExplorerPage.tsx`

No route rewrite needed.

### Contract implication
The existing `detailState.data` becomes more useful once `detail.editorial` is present.

---

## 4.5 `frontend/src/lib/types.ts`

### Add
- `ExplorerEditorialSummary`
- `StoryClusterEditorialSummary`
- `StoryClusterEditorialSourceSummary`
- `StoryClusterEditorialSignal`
- optional member preview type

### Update
- `ExplorerArticleDetail`
- `StoryClusterDetail`
- optionally `StoryClusterMemberItem`

---

## 4.6 `frontend/src/lib/api.ts`

No new fetch function strictly required if backend enriches existing responses.

### Needed update
Adjust imported/consumed types to the enriched response contracts.

---

## 5. Component relationships

```txt
ClusterBrowserPage
├── StoryStream
└── StoryFocusPanel
    ├── CoverageBar
    ├── EditorialLensSection
    │   └── EditorialSourceComparisonRow*
    ├── SourceGroupList
    │   └── EditorialMemberPreviewBadges*
    └── ArticleDetailSection
        ├── EditorialAnalysisCard (full)
        │   ├── EditorialStatusBadge*
        │   ├── EditorialDimensionGrid*
        │   └── EditorialEvidenceList*
        └── semantic context block

ExplorerPage
├── ExplorerControlBar
├── MapPanel
└── ExplorerContextRail
    ├── article section
    ├── EditorialAnalysisCard (compact)
    │   ├── EditorialStatusBadge*
    │   ├── EditorialDimensionGrid*
    │   └── EditorialEvidenceList*
    ├── cluster context section
    └── semantic neighborhood section
```

`*` = new subcomponent

---

## 6. State ownership rules

## 6.1 Backend owns normalization
Frontend should not reverse-engineer editorial logic from raw diagnostics.

Backend/read-side should provide:
- shaped article editorial summary
- shaped cluster editorial summary
- optional member preview summary

## 6.2 Frontend owns presentation
Frontend decides:
- compact vs full layouts
- badge priority
- evidence truncation
- caution vs neutral visual emphasis

## 6.3 Don’t duplicate state logic everywhere
The nasty editorial state matrix should live mostly in:
- `EditorialAnalysisCard`
- `EditorialLensSection`
- maybe small helpers in `frontend/src/lib/editorialPresentation.ts`

That is better than sprinkling `if pending/failed/limited` branches through every page.

---

## 7. Thin helper module recommended

## `frontend/src/lib/editorialPresentation.ts`

### Role
Pure view helpers for consistent labels and ordering.

### Suggested helpers
```ts
export function confidenceBand(value: number): 'high' | 'moderate' | 'low'
export function formatConfidence(value: number): string
export function editorialApplicabilityLabel(value: string): string
export function shouldShowBiasLabel(editorial: ExplorerEditorialSummary): boolean
export function editorialStateSummary(editorial: ExplorerEditorialSummary): string[]
export function pickMemberPreviewBadges(preview: StoryClusterMemberPreview | null): string[]
```

This is optional but smart. The presentation rules are opinionated enough to deserve a shared helper.

---

## 8. CSS / visual-system impact

Small, not a redesign.

### New class groups likely needed
- `.editorial-card`
- `.editorial-card--compact`
- `.editorial-badges`
- `.editorial-grid`
- `.editorial-evidence-list`
- `.editorial-limitations`
- `.editorial-lens`
- `.editorial-source-row`
- `.editorial-signal-callout`
- `.editorial-preview-badges`

### Tone rules
- neutral analytical palette
- caution states use muted amber/slate, not tabloid red
- failed state can use stronger danger tone
- avoid partisan metaphors entirely

---

## 9. Build order recommendation

### Step 1
Backend lands enriched payloads first.

### Step 2
Frontend builds shared editorial components:
- `EditorialStatusBadge`
- `EditorialDimensionGrid`
- `EditorialEvidenceList`
- `EditorialAnalysisCard`

### Step 3
Frontend wires Stories:
- `EditorialLensSection`
- article detail card
- member preview badges

### Step 4
Frontend wires Explorer compact card.

This order avoids building pretty shells around fake or guessed contracts.

---

## 10. Crisp implementer handoff

The implementer must provide these exact UI-ready contracts next:

1. `ExplorerArticleDetail.editorial`
2. `StoryClusterDetail.editorial_summary`
3. optional `StoryClusterMemberItem.editorial_preview`

Once those exist, the frontend builder should create:

1. `components/editorial/EditorialAnalysisCard.tsx`
2. `components/stories/EditorialLensSection.tsx`
3. supporting editorial badge/evidence/grid subcomponents
4. StoryFocusPanel and ExplorerContextRail integration

If backend returns raw diagnostics blobs instead of shaped product summaries, it’s the wrong contract. The frontend should not be forced to become a forensic lab.