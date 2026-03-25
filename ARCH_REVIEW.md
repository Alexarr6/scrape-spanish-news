# iter/007 final holistic architect review

## Bottom line
iter/007 fixed three real product problems, not fake ones:
- Stories → Explorer no longer lies about object identity
- same-story clustering is less willing to merge garbage through weak bridge articles
- ABC / La Vanguardia discovery now wastes fewer slots on obvious junk

That said, the repo is still a **good analytical prototype with one foot in product and one foot in lab gear**. The foundation is now credible. The experience is not yet fully sharp.

The biggest truth: **Stories is becoming the product. Explorer is still a powerful specialist tool.** That is fine, but the repo should stop acting like the semantic surface is already a mainstream comparative workflow. It isn’t.

---

## 1. Navigation / product ergonomics: Stories → Explorer cluster handoff

## What got fixed
Phase A was the right call and it landed the right thing.

The important improvement is architectural, not cosmetic:
- Stories now hands off `sem_story_cluster`
- Explorer backend resolves membership through `cluster_members`
- `sem_story_cluster` and semantic `cluster_id` are no longer pretending to be the same object
- selected article focus survives with `sem_article`
- the rail labels now distinguish **story cluster** vs **semantic cluster** instead of smearing them together

That is a real fix. Before this, the product was cheating with a title-search costume.

## What still feels mid
The flow is now correct, but not fully elegant.

Current Explorer behavior after the handoff is basically:
- you land inside the right subset
- you can inspect a selected article and its neighborhood
- you can still refine inside that subset

That is good enough technically, but still slightly under-explained product-wise.

The missing piece is not more routing. It is **better scope communication**:
- Explorer tells you you’re in a story cluster, but not strongly enough what that means operationally
- the no-selection state still reads like generic semantic-tool onboarding
- there is still no strong “compare this cluster semantically” framing once you enter from Stories

So the handoff is fixed, but the surrounding experience is still a little “you have been dropped into the engine room.”

## Verdict
**Pass.** The object-identity bug is gone. That matters more than any small UX polish.

---

## 2. Same-story clustering quality and remaining risks

## What improved
Phase B was solid and disciplined.

The scoring/persistence work in `src/analysis/pipeline.py` is a meaningful upgrade because it attacked the repo’s most dangerous failure mode: **connected-components merge bullshit**.

What is now materially better:
- follow-up drift gets penalized
- secondary-form pieces (`analysis`, `explainer`, `feature`, `interview`) need stronger lexical support
- entity-heavy / event-light pairs get tagged as risky instead of gluing clusters together for free
- guarded strongest-edge-first growth is better than the old naive transitive merge posture
- membership diagnostics now expose actual support evidence instead of making you spelunk raw rows like a cave goblin

That last point matters a lot. `membership_diagnostics` is one of the best iter/007 outcomes because it makes false merges/splits debuggable at the read side.

## What is still weak
The clustering is still a **heuristic scoring graph**, which means it is still vulnerable in two places:

### 1) recall on cross-outlet wording divergence
If two outlets describe the same event with very different lexical framing and only modest entity overlap, the current scorer can still miss the merge.

That is the price of the precision-first anti-bridge move. It was the right trade for this iteration, but it is still a trade.

### 2) cluster representation is still headline-led
Representative selection and summary generation are still pretty primitive:
- representative article is effectively the earliest ordered item
- summary text is joined article summaries
- cluster type is still blunt (`breaking_event`)

So while membership quality improved, **cluster explainability improved faster than cluster summarization quality**.

The matching core is now less dangerous than the cluster presentation layer.

## Verdict
**Better and more trustworthy, but still not “solved.”**

The repo is now less likely to tell a stupid false-merge story. That is a win. But same-story recall across divergent phrasing remains the next pressure point.

---

## 3. Scrape / source coverage quality and operational robustness

## What improved
Phase C attacked a real upstream defect instead of doing downstream spin.

The freshness-first ordering work for ABC and La Vanguardia is exactly the kind of bounded operational fix this repo needed:
- asset URLs get rejected earlier
- URL-date heuristics now help candidate ordering
- layered discovery can rank candidates before the extraction budget gets torched

That is good engineering. It fixes stupid waste at the point where it happens.

## What is still structurally wrong
The scraping system is still **source-blind downstream**.

The repo still has these amplification stages:
- `ENRICH_LIMIT`
- `CLUSTER_LIMIT`
- `SEMANTIC_LIMIT`
- `SEMANTIC_BUILD_LIMIT`

Those are global recent-row caps. So even after cleaner intake, the product remains vulnerable to whichever sources dominate recent insert volume.

This especially affects Explorer, which is supposed to feel like a comparative map of the ecosystem but is still partly a map of **who won the last recency knife fight**.

### The biggest remaining scrape-side weakness
Not ABC. Not La Vanguardia.

It is **elDiario’s skip logic plus downstream cap policy**.

The remaining issue is more subtle now:
- elDiario can still stop layered discovery too early based on raw candidate count
- downstream global caps can still overrepresent louder sources in semantic/export outputs

That means operational robustness has improved, but **coverage fairness has not actually been solved**.

## Verdict
**Upstream quality got better; downstream fairness still lags.**

---

## 4. Editorial / comparative UX fit in the current product

## What is good
The repo’s strongest product instinct is now clear:
- Stories is the primary comparative surface
- editorial analysis is cluster-scoped and mostly honest about support
- Explorer is additive semantic context, not the main place for cross-source narrative claims

That is the right hierarchy.

The cluster editorial lens is restrained in the right way:
- comparative metrics only appear when support exists
- divergence signals are gated instead of sprayed everywhere
- limited / out-of-domain cases are surfaced instead of buried

That restraint gives the product credibility.

## What is not fully working
The product still has a mild identity split.

Right now it is trying to be all three of these at once:
- a same-story comparison tool
- a semantic map explorer
- an editorial framing analysis product

It can do all three, but it still lacks one dominant user workflow that stitches them together cleanly.

Today the most coherent flow is:
1. find a cluster in Stories
2. compare source/editorial framing there
3. hop to Explorer if you want semantic neighborhood/context

That is a good workflow. The repo should embrace it more explicitly.

What it should **not** do is pretend most users want to begin from the semantic map. They don’t.

## Verdict
**Editorial/comparative UX fits best in Stories, not Explorer.** That should now be treated as a product principle, not an accident.

---

## 5. Data/model/readside contract quality and debuggability

## What is strong
This iteration improved contract quality a lot.

Best examples:
- explicit `sem_story_cluster` separation from semantic `cluster_id`
- `membership_diagnostics` exposed in cluster detail payloads
- product-facing editorial payloads kept separate from raw operator/audit diagnostics
- shaped cluster comparative payloads with honest null/suppression behavior

That is good contract discipline. The APIs are getting more intentional.

## What is still rough
The repo still exposes a conceptual split between:
- story clusters
- semantic clusters
- editorial summaries
- article-level semantic detail

Those are all legitimate objects, but the read side does not yet give enough **cross-object traceability**.

What is missing most:
- a cleaner explanation path from story cluster member → why exactly this article belongs here
- a more explicit story-cluster-level debug surface for false split / false merge review
- source-level operational diagnostics surfaced in a stable report, not just inferred from logs/artifacts/scripts

The data model is no longer confusing in a dangerous way. But the debugging story is still too dependent on code familiarity.

## Verdict
**Much better than before, still not operator-friendly enough.**

---

## 6. Biggest remaining product or architecture weaknesses

## Weakness 1 — Explorer still overstates its maturity as a comparative surface
Explorer is good, but it is still a specialist interface. The product should stop leaning on it as if it already carries the comparative experience.

## Weakness 2 — downstream source fairness is unresolved
The scrape fixes improved intake quality, but the repo still uses global caps that distort later stages. This is now the biggest architecture-level credibility issue.

## Weakness 3 — cluster summarization is behind cluster membership quality
The system got better at deciding what belongs together than at summarizing what the cluster actually is. That mismatch will start to matter more as cluster quality improves.

## Weakness 4 — false-split debugging is still weaker than false-merge debugging
`membership_diagnostics` helps explain why an article is inside a cluster. The repo still lacks an equally strong read on why two near-same-event articles ended up separated.

## Weakness 5 — too much product logic still lives as implied knowledge
A smart reviewer can infer the intended product flow. A normal user cannot. Some of the repo’s best ideas are still buried in implementation rather than surfaced in the UX.

---

## 7. Highest-value next iteration(s)

## Best next iteration: bounded fairness + explainability pass
Not a rewrite. Not embeddings religion. Not a fancy new clustering framework.

The best next move is a **bounded fairness + explainability iteration** with three concrete slices.

### Slice A — source-aware downstream windowing for Explorer and maybe enrichment
Goal: stop recent-row global caps from turning source volume into product visibility bias.

Smallest useful version:
- add per-source ceilings or source-aware round-robin candidate selection in semantic sync/build
- keep total limits intact
- measure before/after source distribution in semantic outputs

Why this is next:
- the repo has already improved intake quality
- downstream skew is now the most obvious remaining credibility problem
- this is operationally bounded and measurable

### Slice B — elDiario usable-candidate discovery fix
Goal: stop layered discovery from skipping too early based on raw candidate count.

Smallest useful version:
- refine skip thresholds to consider freshness/usable-candidate heuristics instead of only `len(urls)`
- keep it source-bounded to elDiario first

Why this matters:
- it addresses the remaining obvious undercoverage defect without broad crawler churn

### Slice C — cluster explainability / debug panel improvements in Stories
Goal: make cluster quality review easier without opening the codebase.

Smallest useful version:
- expose bounded membership diagnostics in Stories detail for selected articles
- show why an article belongs to the cluster in human terms: support edges, best score, bridge-risk flags, penalties
- keep it behind restrained UI, not as a giant forensic dashboard

Why this matters:
- the backend now has the data
- the product does not yet use it
- this closes the loop between clustering quality and user trust

---

## Concrete implementer handoff — what is worth building next right now

If I were assigning the next bounded pass today, I would do this in order:

### 1. Add source-aware semantic candidate selection
Touch likely areas:
- `scripts/semantic_sync.py`
- `src/semantic/dbstore.py` (`select_embedding_candidates` and/or related build selection logic)
- relevant semantic build tests if present

Target behavior:
- do not simply take the latest N rows globally
- instead, pull recent rows with a per-source cap or round-robin selection strategy
- preserve date-window semantics and total limit
- emit source-count diagnostics for the selected/exported set

Success looks like:
- Explorer semantic outputs are less distorted by one loud source
- no claim of perfect fairness, just less stupid skew

### 2. Refine elDiario layered discovery skip logic
Touch likely areas:
- `src/adapters/eldiario.py`
- maybe shared helper logic if needed, but keep it bounded
- `tests/test_eldiario_adapter.py`
- maybe `tests/test_layered_discovery.py`

Target behavior:
- skip deeper layers based on likely usable/fresh candidates, not raw accepted URL count alone

Success looks like:
- better kept/processed ratio or at least healthier same-day discovery on thin days

### 3. Surface cluster membership diagnostics in Stories article detail
Touch likely areas:
- `src/api/contracts/clusters.py` if extra shaping is needed
- `frontend/src/components/stories/*`
- possibly `src/analysis/readside.py` only if you need a more product-friendly shaped diagnostics object

Target behavior:
- when viewing a cluster member, show concise “why this belongs here” evidence
- support edge count
- best / mean support score
- risky bridge support flag
- penalties if present

Success looks like:
- cluster quality can be inspected without reading raw JSON or backend code

---

## What should not be done next
- do **not** rewrite clustering around embeddings end-to-end just because embeddings sound cooler
- do **not** add source quotas in the UI as a cosmetic bandage while backend selection stays skewed
- do **not** bloat Explorer into the main editorial comparison surface
- do **not** start a giant summarization rewrite before fixing downstream fairness and cluster explainability

---

## Final verdict
iter/007 was a good iteration.

Not because it made the app pretty. Because it removed three kinds of bullshit:
- fake cluster handoff
- cheap bridge merges
- obviously wasteful scrape candidate ordering

That is real progress.

The repo is now **substantially more honest** than it was at the start of the iteration. In this product, honesty is half the battle.

Next, fix downstream fairness and make cluster reasoning visible. That’s the move.