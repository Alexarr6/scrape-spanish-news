# Explorer article-type control correction — bounded UX architecture (2026-03-24)

## Verdict

The current **article-type editorial lens** is in the right zone but the wrong shape.

Do **not** move it out of the main Explorer control bar.
Do **not** redesign the whole bar.
Do **replace the current labeled form field** with a compact control that belongs to the same visual family as the surrounding controls.

## Diagnosis

The user is right. The current control feels off because it breaks the control-bar grammar in three ways at once.

### 1. It is the only vertically stacked form field in a horizontal bar of compact analysis toggles
The rest of the bar is built from short, inline, high-density controls:
- segmented `2D | 3D`
- segmented `Highlight | Filter`
- segmented `Color by`
- ghost utility actions like `Fit all`

Then the article-type lens arrives as:
- uppercase micro-label (`Editorial lens`)
- stacked label + select
- separate `Clear lens` button

That makes it read like a sidebar form fragment jammed into a toolbar.

### 2. Its height/baseline rhythm does not match the neighboring controls
The bar itself is fixed-height (`3rem`).
The segmented controls are visually centered and compact.
The article-type field is a two-line block with a `2rem` select and a tiny header floating above it.

So even if it technically fits, it does not feel aligned. It has different vertical logic, different density, and different eye weight.

### 3. The control splits one concept across too many pieces
Right now the user has to parse:
- `Visual mode` segmented control
- `Editorial lens` label
- article-type dropdown
- `Clear lens` button
- a separate generic `Article type lens` badge on the right

That is too many fragments for one bounded action.
The badge is especially weak: it repeats that a lens exists, but not **which** article type is active.

## Recommended control pattern

## Replace the current stacked field with a compact inline popover/dropdown trigger

**Recommendation:** keep the **dropdown interaction**, but **reframe it as a compact toolbar control**, not a labeled mini-form.

That means:
- keep it in the same control family/zone
- keep article type as the only dimension
- keep the underlying URL/query model
- replace the current vertical field with a single compact trigger button

### Proposed interaction
A single toolbar button in the main left control cluster:
- default label: `Article type`
- active label: `Type: Opinion` / `Type: News` / etc.
- affordance: chevron/down indicator
- active state: accent-tinted like other active analysis controls
- clear action: inside the menu/popover, not as a separate persistent button

When opened, the control shows a compact menu/popover with:
- `All article types` / `Clear lens`
- article-type options with counts
- current selection checkmark

### Why this pattern is the right one
Because the current issue is not that article type needs a radically different interaction. The issue is that it currently looks like it escaped from a settings form.

A compact trigger fixes the actual problem:
- matches toolbar density
- keeps the control in the same area the user already likes
- removes the stacked-label misalignment
- collapses label + select + clear into one coherent unit
- preserves scalability if a second bounded lens ever appears later

## Explicit recommendation: keep dropdown, reframe it better

Not chips.
Not a full segmented control.
Not a redesign of the whole bar.

### Why not chips
Article-type values are too many and too uneven for a clean inline chip row in this toolbar.
A chip row would either:
- sprawl horizontally and bully the rest of the bar, or
- collapse badly on narrower widths

### Why not segmented control
Segmented controls work for tiny fixed sets like `2D | 3D` and `Highlight | Filter`.
Article type has too many categories for that to stay clean.

### Why not move it into Refine only
That would hide a visual-analysis lens inside a filtering drawer, which is the wrong product signal. This belongs in the visible Explorer analysis controls.

## Proposed layout behavior

### Current desired neighborhood stays intact
Keep the article-type control in the same general family as:
- visual mode
- color mode
- nearby analysis controls

### Recommended order
Keep this order on the left side:
1. `2D | 3D`
2. `Highlight | Filter`
3. `Color by`
4. `Article type` trigger
5. `Fit all`
6. `Focus selected` when relevant

That keeps the lens near the visual controls it modifies, which is exactly where it belongs.

## Exact scope for the correction pass

This pass should be **frontend-only** unless implementer finds a tiny accessibility-only helper is needed.

### In scope
- replace the current `label + select + Clear lens button` composition in `ExplorerControlBar.tsx`
- introduce a compact inline trigger/button for article type
- show active value directly on the trigger label
- move clear/reset into the opened menu/popover
- remove the redundant right-side `Article type lens` badge, or replace it with nothing
- align styling so the new control matches segmented controls / ghost buttons in height and baseline rhythm
- keep the same editorial target behavior and URL semantics
- keep existing backend contract and article-type options/counts usage

### Out of scope
- no bias lens
- no tone lens
- no generalized multi-editorial-lens picker
- no Explorer control-bar redesign
- no change to rail legend semantics beyond tiny copy if needed for the active label
- no backend query/contract changes

## Implementation notes for frontend

### `ExplorerControlBar.tsx`
Refactor the editorial control into a single compact trigger component.

Target behavior:
- no stacked uppercase field label
- no always-visible secondary `Clear lens` button
- active value visible inline on the trigger
- menu contains options + clear/reset row

### Styling
Create a toolbar-specific style for the article-type trigger so it visually belongs beside segmented controls and ghost buttons.

The key requirement:
- one-line control
- toolbar-aligned height
- no mini-form look

### Badge cleanup
Remove the generic `Article type lens` badge from the right side.
It adds noise and repeats information poorly.
If the trigger already says `Type: Opinion`, the badge is dead weight.

## Handoff recommendation

### Next agent
**frontend implementer**

### Implementer brief
Apply a bounded Explorer toolbar UX correction pass for the landed article-type editorial lens. Keep the control in the current bar/zone, but replace the current stacked labeled select with a compact inline dropdown/popover trigger that matches the surrounding control family. Show the active article-type value directly on the trigger, move clear/reset into the opened menu, and remove the redundant `Article type lens` badge on the right. Do not redesign the full bar. Do not touch bias/tone or backend contracts.

## Bottom line

The control feels off because it is visually speaking a different language from the rest of the toolbar.

The fix is simple and bounded:
**keep the dropdown, but make it look like a toolbar control instead of a tiny settings form.**
