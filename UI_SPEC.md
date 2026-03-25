# UI_SPEC.md — iter/005 Editorial Analysis Integration

**Role:** Frontend architect  
**Date:** 2026-03-23  
**Status:** Ready for implementer + frontend.react

## 1. Product stance

Editorial analysis belongs in the product, but only as an **evidence-backed comparison layer**.

This app should answer:
- how coverage of the same story differs across sources
- what signals are strong vs weak
- where interpretation is limited, unclear, or out-of-domain
- which article-level evidence supports the claim

This app should **not** become:
- a one-number bias toy
- an outlet ideology leaderboard
- an LLM confidence theater machine

**Core rule:**
- **story cluster** = best place to compare
- **article detail** = best place to inspect evidence
- **operator/debug views** = best place for raw diagnostics

---

## 2. Highest-value surfaces

### Primary surface
`frontend/src/components/stories/StoryFocusPanel.tsx`

This is the main editorial-analysis home because it already has:
- story brief
- cluster coverage
- grouped article lists by source
- article detail drill-in

### Secondary surface
`frontend/src/components/explorer/ExplorerContextRail.tsx`

This should expose a compact editorial read for the selected article so semantic exploration and editorial interpretation stay connected.

### Intentionally not primary in this slice
- story cards in the left stream
- dedicated editorial dashboard page
- source ideology summary pages

Those can come later. First land the comparison workflow where it already matters.

---

## 3. Surface architecture

## 3.1 StoryFocusPanel

### Current structure
1. Story brief
2. Coverage
3. Articles by source / article detail

### Required new structure
1. Story brief
2. Coverage
3. **Editorial lens** ← new first-class section
4. Articles by source / article detail

### Why this order
Coverage tells users **who covered it**. Editorial lens then tells them **how they covered it**. Article list/detail lets them inspect the evidence.

That sequencing is clean and credible.

---

## 3.2 Editorial lens section in StoryFocusPanel

### Purpose
Summarize editorial patterns inside one story cluster without pretending the aggregate is self-explanatory.

### Component to add
`EditorialLensSection`

Suggested path:
- `frontend/src/components/stories/EditorialLensSection.tsx`

### Inputs
`detail.editorial_summary`

### Layout
A sober stacked section with four blocks:

#### Block A — Analysis coverage
Shows whether the cluster has enough usable analysis to say anything.

Contents:
- analyzed article count
- pending / failed / no-analysis count
- applicability mix: `full`, `limited`, `out_of_domain`
- short coverage note

Example copy:
- `8 of 11 articles have usable editorial analysis`
- `2 articles are limited applicability; 1 is out of domain`

#### Block B — Source comparison rows
One row per source in the cluster.

Each source row should show:
- source name
- analyzed article count / total article count
- article type mix
- bias label mix
- opinionatedness mix
- tone / framing highlights only if supported
- review-state counts if materially present

This is the comparative core. If this section is weak, the whole integration is weak.

#### Block C — Cluster signals
Narrative callouts for patterns that clear a support threshold.

Allowed examples:
- `Opinion framing appears concentrated in 2 sources`
- `Coverage is mostly straight news reporting across the cluster`
- `Framing signal is mixed; no dominant pattern`

Every callout must be grounded by:
- count support
- supporting sources
- example article drilldown

#### Block D — Confidence / limits note
Always present, even when the signal is strong.

Examples:
- `Interpretation is based on 8 analyzed articles across 5 sources.`
- `Signal is weak: several articles are pending, limited, or low-confidence.`
- `This summary describes this cluster only, not each outlet overall.`

### What this section must not do
- show one cluster-wide ideology score
- color the whole cluster red/blue
- hide pending/limited/out_of_domain counts
- claim “Source X is left/right” as a universal fact

---

## 3.3 Stories article list badges

### Surface
`SourceGroupList` inside `StoryFocusPanel.tsx`

### Purpose
Help users spot which article cards are worth opening for editorial inspection.

### Badge rules
Keep them minimal. Show at most 2–3 compact badges per article card.

Priority order:
1. article type badge
2. applicability badge when not `full`
3. confidence state badge when materially weak

Suggested badge vocabulary:
- `news`
- `analysis`
- `opinion`
- `editorial`
- `limited`
- `out of domain`
- `low confidence`
- `needs review`

### Explicit no
Do **not** show full bias/tone/framing badges in the article list. That would turn the list into sticker hell.

---

## 3.4 Stories article detail editorial card

### Surface
`ArticleDetailSection` inside `StoryFocusPanel.tsx`

### Component to add
`EditorialAnalysisCard`

Suggested path:
- `frontend/src/components/editorial/EditorialAnalysisCard.tsx`

### Position
Inside article detail, after the article summary + actions and before semantic context.

### Purpose
Show the selected article’s editorial interpretation with evidence and uncertainty.

### Required sections inside the card

#### A. Header
- title: `Editorial read`
- analysis status badge
- applicability badge
- optional review badge if needed

#### B. Dimensional summary grid
Show compact labeled values, not giant pills.

Fields:
- article type
- bias label
- bias confidence
- tone emotional
- tone target
- opinionatedness
- sensationalism
- rhetorical certainty

Presentation rule:
- confidence should be shown as **qualitative + numeric assist**, not pure percent theater
- example: `Moderate confidence · 0.61`

#### C. Framing devices
Show only if meaningful.
- list up to 3 framing devices
- if none or unclear, say `No strong framing signal extracted`

#### D. Evidence
This is mandatory when analysis is completed and evidence exists.

Show:
- top 2–3 evidence spans
- each with type + text + note

If completed but evidence is missing:
- show a warning state, not silence

#### E. Rationale
One short rationale block.
- clamp to sensible length
- no raw JSON sludge

#### F. Limitations / uncertainty row
Summarize unclear reasons, low-confidence state, or limited applicability.

Possible labels:
- `Low confidence`
- `Limited applicability`
- `Out of domain`
- `Weak signal`
- `Needs review`

### EditorialAnalysisCard state model

#### completed / strong
- show all sections normally

#### completed / low confidence
- same card, but limitations row is prominent
- bias/tone/framing are visually muted, not hidden

#### pending
- show skeleton/placeholder card:
  - `Editorial analysis pending`
  - no fake badges

#### failed
- show explicit failure state:
  - `Editorial analysis unavailable`
  - include failure reason if safe and human-readable

#### out_of_domain
- show a specialized state:
  - `This article is outside the editorial-analysis domain for this workflow`
  - still allow article type if available, but mute the rest

#### limited applicability
- show limited state:
  - `Only partial editorial interpretation is appropriate for this article`
  - keep visible dimensions but annotate them as partial

### Operator/debug separation
The user card must never dump:
- diagnostics JSON
- provider path
- model metadata
- normalization warnings wall

If needed later, add a small operator-only disclosure or dedicated admin view. Not here.

---

## 3.5 ExplorerContextRail editorial block

### Surface
`frontend/src/components/explorer/ExplorerContextRail.tsx`

### Purpose
Keep editorial interpretation visible while the user explores semantic neighbors.

### Component usage
Reuse the same `EditorialAnalysisCard` family, but in a **compact rail variant**.

Suggested API:
- `variant="full"` for Stories article detail
- `variant="compact"` for ExplorerContextRail

### Placement
After article summary/actions and before cluster context.

### Compact variant contents
- status + applicability
- article type
- bias label + confidence
- opinionatedness
- tone emotional
- up to 2 evidence spans
- CTA to story comparison when cluster exists

### Compact variant omissions
Do not show the full dimensional grid if it makes the rail unreadable.
The rail is dense already.

### CTA
If `cluster_id` exists:
- button/link: `Open full story comparison →`

This turns Explorer into a bridge, not a dead-end.

---

## 4. Credibility rules

## 4.1 Confidence display

Confidence must never look like ground truth.

### Display model
Use three bands:
- `High` ≥ 0.75
- `Moderate` 0.45–0.74
- `Low` < 0.45

Display as:
- qualitative label first
- numeric value second

Example:
- `Low confidence · 0.38`

### UI behavior
- low-confidence values remain visible
- low-confidence values get muted visual treatment
- low-confidence values trigger a visible caution note

Do not hide the value just because it is messy.

---

## 4.2 Applicability display

Applicability is not a footnote. It is a primary trust signal.

### Required visible states
- `full`
- `limited`
- `out_of_domain`

### UX rule
Applicability appears in:
- card header badges
- cluster analysis coverage block
- source summary rows when relevant

### Reason handling
When available, show a plain-language reason under the badge or in the limitations row.

Example:
- `Limited applicability — mixed-format service coverage with minimal editorial framing`

---

## 4.3 Unclear / weak signal / needs review

These states should be legible and boring. Boring is good here.

### UI treatment
Use neutral warning styling, not alarmist danger red unless the system actually failed.

#### unclear / weak signal
- label in limitations row
- muted dimensional values
- confidence note visible

#### needs review
- visible pill or small status line
- should not dominate the card unless multiple issues stack

#### failed analysis
- use stronger warning/error treatment

---

## 4.4 Evidence rules

If the product surfaces a claim, it needs evidence or an explicit explanation for why evidence is missing.

### Article-level
Always prefer direct evidence spans over aggregate labels.

### Cluster-level
Every meaningful cluster-level pattern should support drilldown to representative article ids.

### No-evidence rule
If an aggregate/source row has no evidenceable examples, keep the statement weak:
- `signal mixed`
- `pattern tentative`
- `insufficient support`

Not:
- `Source X frames this story as…` with no receipts

---

## 5. Data shape the implementer should provide

## 5.1 Explorer article detail payload extension

Extend `ExplorerArticleDetail` with a compact editorial payload.

### Frontend type
```ts
export type EditorialStatus = 'completed' | 'pending' | 'failed'

export type EditorialSummaryBadgeTone = 'neutral' | 'caution' | 'warning'

export type ExplorerEditorialEvidence = {
  type: string
  text: string
  note: string
}

export type ExplorerEditorialSummary = {
  article_id: number
  analysis_status: EditorialStatus
  editorial_applicability: 'full' | 'limited' | 'out_of_domain'
  editorial_applicability_reason: string
  article_type: string
  article_type_confidence: number
  bias_label: string
  bias_score: number
  bias_confidence: number
  tone_emotional: string
  tone_target: string
  opinionatedness: string
  sensationalism: string
  rhetorical_certainty: string
  framing_devices: string[]
  evidence_spans: ExplorerEditorialEvidence[]
  rationale: string
  unclear_reasons: string[]
  review_flags: {
    missing_evidence: boolean
    low_confidence: boolean
    failed_analysis: boolean
    unclear_bias: boolean
    out_of_domain: boolean
    pending_analysis: boolean
    needs_review: boolean
  }
  diagnostics_summary: {
    dimension_status: Record<string, string>
  } | null
}
```

### API contract change
Add to `ExplorerArticleDetail`:
```ts
editorial: ExplorerEditorialSummary | null
```

### Reason for compact shape
The full editorial API already exists for operator/audit use. The product card needs a shaped summary, not the whole machine room.

---

## 5.2 Story cluster detail payload extension

Extend `StoryClusterDetail` with cluster-scoped editorial comparison data.

### Frontend type
```ts
export type StoryClusterEditorialSourceSummary = {
  source: string
  article_count: number
  analyzed_article_count: number
  applicability_breakdown: Record<string, number>
  article_type_breakdown: Record<string, number>
  bias_label_breakdown: Record<string, number>
  opinionatedness_breakdown: Record<string, number>
  tone_emotional_breakdown: Record<string, number>
  top_framing_devices: Array<{
    framing_device: string
    count: number
    example_article_ids: number[]
  }>
  review_flag_counts: {
    low_confidence: number
    needs_review: number
    out_of_domain: number
    limited: number
  }
}

export type StoryClusterEditorialSignal = {
  label: string
  strength: 'strong' | 'moderate' | 'weak'
  supporting_sources: string[]
  example_article_ids: number[]
  note: string
}

export type StoryClusterEditorialSummary = {
  analyzed_article_count: number
  pending_article_count: number
  failed_article_count: number
  applicability_breakdown: Record<string, number>
  article_type_breakdown: Record<string, number>
  source_summaries: StoryClusterEditorialSourceSummary[]
  cluster_signals: StoryClusterEditorialSignal[]
  confidence_note: string
  scope_note: string
}
```

### API contract change
Add to `StoryClusterDetail`:
```ts
editorial_summary: StoryClusterEditorialSummary | null
```

### Required aggregation rules
- cluster summary is **cluster-scoped only**
- pending and failed rows remain visible as counts
- limited and out-of-domain remain visible as counts
- top framing devices require support threshold
- example article ids are mandatory for any strong cluster signal

---

## 5.3 Optional member-level badge payload

To avoid extra frontend inference hacks, the implementer may also attach a compact member-level editorial preview.

### Optional extension
```ts
editorial_preview?: {
  analysis_status: 'completed' | 'pending' | 'failed'
  article_type: string
  bias_label: string
  bias_confidence: number
  editorial_applicability: 'full' | 'limited' | 'out_of_domain'
  review_flags: {
    low_confidence: boolean
    needs_review: boolean
  }
} | null
```

This is worth doing. It keeps the article list badge logic honest and cheap.

---

## 6. Component architecture

## 6.1 New components

### `components/editorial/EditorialStatusBadge.tsx`
Small reusable badge for:
- completed
- pending
- failed
- limited
- out_of_domain
- low confidence
- needs review

### `components/editorial/EditorialDimensionGrid.tsx`
Renders article-level dimensions in a sober two-column or stacked grid.

### `components/editorial/EditorialEvidenceList.tsx`
Renders evidence spans with type, quote, and note.

### `components/editorial/EditorialAnalysisCard.tsx`
Main article-level card.
Variants:
- `full`
- `compact`

### `components/stories/EditorialLensSection.tsx`
Cluster-level comparison section for StoryFocusPanel.

### `components/stories/EditorialSourceComparisonRow.tsx`
Subcomponent for one source row inside the cluster editorial lens.

---

## 6.2 Existing components to touch

### `StoryFocusPanel.tsx`
Add:
- `Editorial lens` section
- article-level `EditorialAnalysisCard`
- compact article list badges

### `ExplorerContextRail.tsx`
Add:
- compact `EditorialAnalysisCard`
- story-comparison CTA

### `frontend/src/lib/types.ts`
Add editorial summary types.

### `frontend/src/lib/api.ts`
No new endpoint necessarily required for frontend routing, but update types to consume enriched detail payloads.

---

## 7. State behavior matrix

| Surface | No editorial data | Pending | Failed | Limited | Out of domain | Completed strong | Completed weak |
|---|---|---|---|---|---|---|---|
| Stories article detail | hide card entirely only if truly null | placeholder card | error/unavailable card | limited card | out-of-domain card | full card | full card + caution |
| Explorer rail | compact absent state | compact pending | compact unavailable | compact limited | compact OOD | compact populated | compact populated + caution |
| Story editorial lens | show "analysis not available for this cluster" | coverage note includes pending | coverage note includes failed | applicability mix visible | applicability mix visible | source rows + signals | source rows + weak-signal note |
| Story article list badges | no badges | `pending` optional | `unavailable` optional | `limited` | `out of domain` | article type | article type + low confidence |

---

## 8. Visual/tone guidance

The product should feel:
- analytical
- credible
- restrained
- audit-friendly

### Avoid
- partisan color coding
- giant red/blue metaphors
- “bias meter” gauges
- celebratory confidence visuals

### Prefer
- compact neutral badges
- explicit scope notes
- evidence excerpts
- muted caution styling
- language like `signal`, `coverage`, `applicability`, `support`

---

## 9. Implementer handoff

## What the implementer must build next

### Backend / contract work first
1. extend `src/api/contracts/semantic.py` and semantic article detail response with `editorial`
2. extend `src/api/contracts/clusters.py` and cluster detail response with `editorial_summary`
3. add read-side helpers for:
   - article editorial summary shaping
   - cluster editorial aggregation
   - optional member preview shaping
4. preserve pending / failed / limited / out_of_domain states in those read models
5. expose example article ids in cluster/source signals

### Then frontend
1. create `EditorialAnalysisCard` and supporting editorial subcomponents
2. create `EditorialLensSection`
3. wire `StoryFocusPanel` to render:
   - editorial lens section
   - article editorial card
   - article list preview badges
4. wire `ExplorerContextRail` to render compact editorial summary + story CTA
5. verify that weak/limited/out_of_domain states remain visible and boring

### Minimum acceptance for this iter/005 slice
- StoryFocusPanel shows a cluster-level editorial comparison block
- Story article detail shows evidence-backed editorial analysis
- ExplorerContextRail shows compact editorial analysis for selected article
- no surface collapses editorial analysis into a single score
- uncertainty and applicability remain visible

If the next pass ships only badges without evidence and limits, it failed.