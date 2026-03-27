# Editorial Analysis v1

## Purpose

Classify each article by:
- article type
- political / ideological bias framing
- editorial tone dimensions
- framing devices
- evidence spans
- rationale
- confidence

This analysis must be:
- article-level, not outlet-level by default
- evidence-backed
- conservative when signal is weak
- structured for persistence, API exposure, filtering, and later recalculation

## Core principles

1. **Classify the article, not the outlet brand.**
   - Prior beliefs about the publication are weak context at most.
   - The output must be driven by the actual article text.

2. **Separate ideology from tone.**
   - An article can be center-right and calm.
   - An article can be left-leaning and inflammatory.
   - These are different dimensions.

3. **Require evidence spans.**
   - No label should exist without textual support.
   - If the model cannot point to evidence, confidence must drop or output should be `unclear`.

4. **Opinion and reporting are not the same thing.**
   - Opinion/editorial content can have stronger explicit framing than straight reporting.
   - Article type must be classified first and included in analysis.

5. **Prefer abstention over bullshit.**
   - If the signal is mixed, weak, ironic, or incomplete, return `unclear` where appropriate.

## Recommended persistence model

Recommended main table: `article_editorial_analysis`

Suggested fields:
- `id`
- `article_id`
- `article_type`
- `article_type_confidence`
- `bias_label`
- `bias_score`
- `bias_confidence`
- `tone_emotional`
- `tone_target`
- `opinionatedness`
- `sensationalism`
- `rhetorical_certainty`
- `framing_devices_json`
- `evidence_spans_json`
- `rationale`
- `analysis_status`
- `model_provider`
- `model_name`
- `model_version`
- `prompt_version`
- `schema_version`
- `content_hash`
- `analyzed_at`
- `updated_at`

## Metric definitions

### 1. `article_type`

Purpose: identify the editorial form before bias/tone analysis.

Allowed values:
- `news_report`
- `analysis`
- `opinion`
- `editorial`
- `interview`
- `feature`
- `explainer`
- `live_blog`
- `other`
- `unclear`

Guidance:
- `news_report`: primarily descriptive coverage of events.
- `analysis`: explanatory or interpretive piece with reporter synthesis.
- `opinion`: authored argument or column with explicit viewpoint.
- `editorial`: institutional stance of the publication.
- `interview`: structured Q&A or interview-led narrative.
- `feature`: long-form narrative or human-interest framing.
- `explainer`: educational breakdown of a topic/process.
- `live_blog`: rolling updates.
- `unclear`: genre cannot be determined confidently.

### 2. `bias_label`

Purpose: classify the ideological direction of the article's framing.

Allowed values:
- `far_left`
- `left`
- `center_left`
- `center`
- `center_right`
- `right`
- `far_right`
- `unclear`

Important:
- This does **not** judge factual accuracy.
- This does **not** simply inherit the outlet's reputation.
- It reflects the ideological direction expressed through framing, emphasis, legitimization, delegitimization, or evaluative language in the article.

Signals may include:
- what is foregrounded vs backgrounded
- which actors are legitimized or discredited
- language around markets/state/nation/identity/migration/security/redistribution
- framing of causes, blame, and moral stakes
- asymmetry in source selection or quote selection

### 3. `bias_score`

Purpose: numeric ideology scale for aggregation and comparison.

Range:
- `-1.0` = strongest left / far-left framing
- `0.0` = center or indeterminate
- `1.0` = strongest right / far-right framing

Recommended mapping:
- `far_left` -> around `-0.9`
- `left` -> around `-0.65`
- `center_left` -> around `-0.35`
- `center` -> around `0.0`
- `center_right` -> around `0.35`
- `right` -> around `0.65`
- `far_right` -> around `0.9`
- `unclear` -> near `0.0` with low confidence

### 4. `bias_confidence`

Purpose: express how strong and defensible the ideological classification is.

Range: `0.0` to `1.0`

Calibration:
- `0.00-0.30`: weak or ambiguous signal
- `0.31-0.60`: partial signal, debatable
- `0.61-0.80`: clear signal from wording/framing
- `0.81-1.00`: very explicit and well-supported ideological framing

### 5. `tone_emotional`

Purpose: capture emotional intensity of the article's language.

Allowed values:
- `calm`
- `loaded`
- `inflammatory`
- `unclear`

Guidance:
- `calm`: restrained, descriptive, minimal affective loading.
- `loaded`: noticeable emotionally charged wording or connotative adjectives.
- `inflammatory`: language designed to provoke outrage, fear, contempt, panic, or intense polarization.

### 6. `tone_target`

Purpose: capture stance toward the primary actor or target of the piece.

Allowed values:
- `supportive`
- `neutral`
- `critical`
- `hostile`
- `mixed`
- `unclear`

Guidance:
- `supportive`: framing consistently favors the main target.
- `neutral`: descriptive with low evaluative direction.
- `critical`: clear negative evaluation without overt aggression.
- `hostile`: aggressive delegitimization, ridicule, or demonization.
- `mixed`: materially different targets are treated differently or tone shifts strongly within the piece.

### 7. `opinionatedness`

Purpose: measure how far the article moves from reporting into interpretation or advocacy.

Allowed values:
- `straight_reporting`
- `interpretive`
- `opinionated`
- `activist`
- `unclear`

Guidance:
- `straight_reporting`: mostly fact-forward and descriptive.
- `interpretive`: noticeable synthesis or implied thesis.
- `opinionated`: explicit evaluative viewpoint.
- `activist`: clear persuasive or mobilizing intent.

### 8. `sensationalism`

Purpose: measure exaggeration and drama amplification.

Allowed values:
- `low`
- `medium`
- `high`
- `unclear`

Signals:
- overdramatized headline language
- fear hooks
- catastrophe framing beyond evidence
- exaggerated urgency
- emotionally manipulative wording

### 9. `rhetorical_certainty`

Purpose: measure how cautiously or absolutely claims are presented.

Allowed values:
- `cautious`
- `assertive`
- `absolute`
- `unclear`

Guidance:
- `cautious`: hedging, uncertainty, attribution, nuance.
- `assertive`: direct declarative framing with moderate caution.
- `absolute`: overconfident or categorical claims with minimal room for ambiguity.

### 10. `framing_devices`

Purpose: capture dominant narrative frames used in the article.

Allowed values (0-5 items):
- `conflict`
- `economic_consequence`
- `moral_judgment`
- `public_order_security`
- `identity_culture`
- `governance_competence`
- `corruption_scandal`
- `humanitarian`
- `victimization`
- `progress_modernization`
- `institutional_stability`
- `strategic_geopolitics`

### 11. `evidence_spans`

Purpose: justify labels with direct textual support.

Guidance:
- Prefer 1-3 short spans.
- Spans may come from headline, standfirst/summary, or body.
- Include only text that materially supports the classification.
- Do not invent spans.

Suggested shape:
- `type`: `headline | summary | body`
- `text`: literal span from article text
- `note`: optional short explanation

### 12. `rationale`

Purpose: concise explanation of why the labels were assigned.

Constraints:
- 1 short paragraph or 2-4 sentences.
- Must reference framing/tone/evidence, not generic political stereotypes.

## Few-shot guidance examples

### Example A — center / calm / straight reporting
Headline:
- "El Congreso aprueba el paquete fiscal tras una votación ajustada"

Expected tendencies:
- `bias_label`: `center` or `unclear`
- `tone_emotional`: `calm`
- `opinionatedness`: `straight_reporting`
- `sensationalism`: `low`

Why:
- descriptive event framing, low emotional load, no obvious ideological push

### Example B — center-left / critical / interpretive
Headline:
- "El recorte de ayudas agrava la vulnerabilidad de miles de familias"

Expected tendencies:
- `bias_label`: `center_left`
- `tone_target`: `critical`
- `opinionatedness`: `interpretive`
- likely frames: `humanitarian`, `moral_judgment`

Why:
- foregrounds social harm and frames policy in distributive moral terms

### Example C — right / loaded / assertive
Headline:
- "El Gobierno cede ante el caos migratorio mientras las fronteras siguen desbordadas"

Expected tendencies:
- `bias_label`: `right`
- `tone_emotional`: `loaded`
- `tone_target`: `critical`
- `rhetorical_certainty`: `assertive`
- likely frames: `public_order_security`, `governance_competence`

Why:
- emotionally loaded security framing with blame attribution

### Example D — unclear because evidence is weak
Headline:
- "Claves para entender la reforma del mercado eléctrico"

Expected tendencies:
- `bias_label`: `unclear`
- `bias_confidence`: low
- `opinionatedness`: `explainer` + likely `straight_reporting` or `interpretive`

Why:
- educational framing may not contain enough ideological signal

## Abstention rules

Return `unclear` when:
- article text is too short or incomplete
- cues are mixed and contradictory
- classification depends mostly on outlet reputation rather than article wording
- the strongest evidence comes from quoted third parties, not the article's own framing

## Implementation notes

1. Create a dedicated ORM model, not extra columns on `articles`.
2. Keep JSON columns for `framing_devices` and `evidence_spans` in v1.
3. Persist `prompt_version`, `schema_version`, `model_provider`, and `model_name`.
4. Expose base CRUD via FastCRUD, but plan custom read endpoints for story/cluster comparisons.
5. Reuse OpenRouter client style already present in `src/analysis/llm_client.py`.
