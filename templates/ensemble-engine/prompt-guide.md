# Ensemble Engine Prompt Guide

How to write prompts for the 4-stage ensemble pipeline.

## Architecture Overview

The engine runs 4 stages:

1. **Stage 1 — Independent Analysis**: Each of 4 LLM models scores the item independently using the same prompt. Results: 4 independent scores + reasoning.

2. **Stage 2 — Cross-Model Deliberation**: Each model sees all 4 Stage 1 results and refines its own score. Models can adjust if another model cited evidence they missed. Results: 4 refined scores.

3. **Stage 3 — (Internal)**: Not a separate prompt. The deliberation in Stage 2 IS the cross-review step.

4. **Stage 4 — Consensus Aggregation**: Pure math — weighted average of scores, outlier dampening, majority vote on verdict. No LLM calls.

You write **two prompts**:
- `prompts/stage1_analysis.txt` — the independent analysis prompt
- `prompts/stage2_deliberation.txt` — the deliberation prompt

## Stage 1 Prompt: Independent Analysis

This is the most critical file. It defines what gets scored and how.

### Required Sections

1. **Role definition**: Who is this analyst? Be specific about expertise.
2. **Item data block**: Uses `{placeholders}` filled at runtime.
3. **Research data injection**: `{research_section}` inserts Brave Search results.
4. **Analysis framework**: The core question being evaluated.
5. **Scoring dimensions**: 4-8 dimensions totaling exactly 100 points.
6. **Tier thresholds**: S+ (90-100), S (80-89), A (65-79), B (50-64), C (below 50).
7. **Consumer verdict**: 3 values (positive / neutral / negative).
8. **Output JSON schema**: Must include `base_score`, `scores`, `tier`, `reasoning`.

### Scoring Dimension Design Tips

- **Use 4-8 dimensions** — too few loses nuance, too many dilutes each dimension
- **Weights must total exactly 100** — the validators check this
- **The highest-weighted dimension should be the most differentiating** — if ingredient quality is what separates good from bad products, weight it highest
- **Each dimension needs clear scoring bands** — "26-30: excellent, 20-25: good, 13-19: fair, 7-12: poor, 0-6: terrible"
- **Reference concrete thresholds** — "Vitamin C at 10-20% is clinically effective" not "good amount of Vitamin C"
- **Include a value/price dimension** — consumers always care about value vs. alternatives

### Required JSON Output Fields

The validators and Stage 4 aggregator require these fields:

```json
{
  "llm": "{llmName}",           // filled by placeholder
  "stage": 1,                    // always 1 for Stage 1
  "product": "{productName}",    // filled by placeholder
  "brand": "{brand}",            // filled by placeholder
  "scores": {                    // dimension scores — keys must match your dimensions
    "dimension_1": 25,
    "dimension_2": 18
  },
  "base_score": 85,              // REQUIRED — exact sum of all dimension scores
  "tier": "S",                   // REQUIRED — must match base_score thresholds
  "consumer_verdict": "BUY_IT",  // REQUIRED — one of your 3 verdict values
  "reasoning": "...",            // REQUIRED — minimum 200 words, cite evidence
  "key_findings": ["...", "..."],
  "red_flags": ["..."],          // empty array if none
  "top_competitors": ["..."],
  "best_dupe": "...",            // or null
  "verdict": "..."               // one sentence
}
```

### Placeholder Variables

These are available in `stage1_analysis.txt`:

| Placeholder | Value |
|-------------|-------|
| `{productName}` | The item being analyzed |
| `{brand}` | The brand/company |
| `{category}` | The item category |
| `{priceUsd}` | The price in USD |
| `{date}` | Today's date (ISO format) |
| `{research_section}` | Full Brave Search + Firecrawl data |
| `{llmName}` | Display name of the model (e.g. "Claude Sonnet 4.6") |

Use double braces `{{` for literal braces in the JSON output example.

## Stage 2 Prompt: Deliberation

This prompt is mostly generic across niches. Each model receives:
- Its own Stage 1 analysis (`{own_analysis}`)
- All other models' Stage 1 analyses (`{other_analyses}`)

The deliberation steps are universal:
1. Compare scores across models
2. Identify agreements (3+ models within 3 points)
3. Investigate disagreements (>5 point spread)
4. Update only if concrete evidence was missed
5. Hallucination check
6. Final verdict

### Customization Points
- Update the role description to match your niche
- Update verdict values to match Stage 1
- The rest is generic — the deliberation logic works for any domain

### Required JSON Output Fields (Stage 2)

Same as Stage 1, plus:
- `consensus_notes`: what models agreed/disagreed on
- `dimension_rulings`: per-dimension range and ruling
- `hallucinations_flagged`: any unverifiable claims
- `confidence`: high/medium/low
- `confidence_reason`: why

## Anti-Patterns

**Don't**: Assign different roles to different models (that's a pipeline, not an ensemble)
**Do**: Give all 4 models the SAME prompt — consensus comes from independent agreement

**Don't**: Make scoring dimensions subjective ("how good does it feel?")
**Do**: Make them measurable ("0-30 based on active ingredient concentrations vs clinical thresholds")

**Don't**: Forget the hallucination check in Stage 2
**Do**: Explicitly instruct models to flag unverifiable claims from other models

**Don't**: Use scores that don't total 100
**Do**: Validate that your dimension weights add up to exactly 100

**Don't**: Inline prompts in Python code
**Do**: Keep prompts in `.txt` files — version-controllable, editable, verifiable

## Cost

Per analysis run (13 LLM calls):
- Stage 1: 4 parallel calls (one per model)
- Stage 2: 4 parallel calls (deliberation)
- Total: ~8 LLM calls + 5 unused slots for retries
- Cost: ~$0.75-0.80 with the default model config
- Latency: ~90-120 seconds end-to-end
