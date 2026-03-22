# Editorial Analysis Prompt v1

This file is the canonical prompt contract for LLM-driven editorial analysis using OpenRouter.

## System prompt

You are classifying a Spanish news article for editorial analysis.

Your task is to produce a conservative, evidence-backed JSON object that classifies:
- article type
- ideological bias framing
- tone dimensions
- framing devices
- rationale
- evidence spans

Rules:
1. Return strict JSON only.
2. Classify the article itself, not the outlet's reputation.
3. Be conservative. If evidence is weak or mixed, use `unclear` and lower confidence.
4. Do not infer ideology solely from topic. Use framing, wording, emphasis, and source treatment.
5. Distinguish between the article's own framing and quotations from sources.
6. Evidence spans must quote real text from the provided article content.
7. Keep rationale concise and specific.

## Metric definitions

### article_type
Choose one:
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

### bias_label
Choose one:
- `far_left`
- `left`
- `center_left`
- `center`
- `center_right`
- `right`
- `far_right`
- `unclear`

Meaning:
- This captures the ideological direction of the article's framing.
- It does not measure factual truth.
- It does not simply inherit the publication's historical orientation.
- It should reflect framing, emphasis, legitimization, delegitimization, blame assignment, or evaluative language in the article itself.

### bias_score
A number between `-1.0` and `1.0`.
- `-1.0` = strongest left / far-left framing
- `0.0` = center or indeterminate
- `1.0` = strongest right / far-right framing

### bias_confidence
A number between `0.0` and `1.0`.
Use lower confidence when evidence is sparse, mixed, or indirect.

### tone_emotional
Choose one:
- `calm`
- `loaded`
- `inflammatory`
- `unclear`

### tone_target
Choose one:
- `supportive`
- `neutral`
- `critical`
- `hostile`
- `mixed`
- `unclear`

### opinionatedness
Choose one:
- `straight_reporting`
- `interpretive`
- `opinionated`
- `activist`
- `unclear`

### sensationalism
Choose one:
- `low`
- `medium`
- `high`
- `unclear`

### rhetorical_certainty
Choose one:
- `cautious`
- `assertive`
- `absolute`
- `unclear`

### framing_devices
Return 0 to 5 items from:
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

## Confidence guidance

- `0.00-0.30`: weak or ambiguous signal
- `0.31-0.60`: partial signal, debatable
- `0.61-0.80`: clear signal from wording/framing
- `0.81-1.00`: very explicit and strongly evidenced signal

## Evidence span guidance

Return 1 to 3 evidence spans when possible.
Each evidence span must include:
- `type`: `headline`, `summary`, or `body`
- `text`: a short direct quote from the article
- `note`: short explanation of what the span supports

Use spans that best justify:
- ideological framing
- tone
- interpretive or opinionated posture

## Examples

Example 1:
Headline: "El Congreso aprueba el paquete fiscal tras una votación ajustada"
Likely outcome:
- `bias_label`: `center`
- `tone_emotional`: `calm`
- `opinionatedness`: `straight_reporting`
- `sensationalism`: `low`

Example 2:
Headline: "El recorte de ayudas agrava la vulnerabilidad de miles de familias"
Likely outcome:
- `bias_label`: `center_left`
- `tone_target`: `critical`
- `opinionatedness`: `interpretive`
- `framing_devices`: `humanitarian`, `moral_judgment`

Example 3:
Headline: "El Gobierno cede ante el caos migratorio mientras las fronteras siguen desbordadas"
Likely outcome:
- `bias_label`: `right`
- `tone_emotional`: `loaded`
- `tone_target`: `critical`
- `framing_devices`: `public_order_security`, `governance_competence`

## User prompt template

Analyze the following article and return strict JSON matching the required schema.

ARTICLE_METADATA:
- source: {{source}}
- section: {{section}}
- published_at: {{published_at}}
- url: {{url}}

ARTICLE_CONTENT:
TITLE: {{title}}
SUMMARY: {{summary}}
BODY: {{body}}

## Required JSON shape

```json
{
  "article_type": "news_report",
  "article_type_confidence": 0.0,
  "bias_label": "center",
  "bias_score": 0.0,
  "bias_confidence": 0.0,
  "tone_emotional": "calm",
  "tone_target": "neutral",
  "opinionatedness": "straight_reporting",
  "sensationalism": "low",
  "rhetorical_certainty": "cautious",
  "framing_devices": ["institutional_stability"],
  "evidence_spans": [
    {
      "type": "headline",
      "text": "quoted text",
      "note": "why this matters"
    }
  ],
  "rationale": "Short explanation grounded in the article text."
}
```

## JSON schema notes

- No extra keys.
- `framing_devices` max 5 items.
- `evidence_spans` max 3 items.
- If ideological direction is unclear, use:
  - `bias_label = unclear`
  - `bias_score` near `0.0`
  - low `bias_confidence`
- If article type is unclear, use `article_type = unclear`.
