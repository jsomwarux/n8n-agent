---
name: ensemble-architect
description: >
  Use when building multi-LLM ensemble workflows in n8n. Activates for:
  4-LLM consensus, multi-model validation, ensemble patterns, cross-checking,
  model agreement scoring, audit trails, LLM orchestration, parallel LLM calls.
---

# 4-LLM Ensemble Pattern for n8n Workflows

## When to Use This Skill

Use the 4-LLM ensemble when:
- Accuracy matters more than speed (scoring, risk assessment, compliance)
- An audit trail is needed (insurance, financial, legal contexts)
- Extracting data from messy/unstructured inputs (quotes, claims, RFIs)
- Classification with real consequences (triage, routing, risk flags)

Do NOT use ensemble when:
- Speed is critical (real-time chat, sub-2-second responses)
- The task is simple (formatting, lookups, simple routing)
- Cost is a concern and accuracy is not critical
- A single LLM with RAG gives good-enough answers

## Core Principle: Same Task, Same Schema, Independent Analysis

Every model receives the EXACT SAME prompt and must return the EXACT SAME JSON schema.
This is a consensus pattern, NOT a pipeline. Each model works independently.

- CORRECT: All 4 models extract line items from a quote → consensus engine compares
- CORRECT: All 4 models assess claim severity → consensus engine averages
- WRONG: Model A extracts, Model B scores, Model C validates, Model D routes
  (that's a pipeline — use sequential nodes instead, not an ensemble)

## The Pattern
[Input arrives] | [Preprocess: clean and structure the input] | [Split into 4 parallel branches] | | | | [Claude] [ChatGPT] [Gemini] [Grok] | | | | [Wait for all 4 to respond] | [Consensus Engine: compare, score, merge] | [Output: result + confidence + audit trail]

## Required Output Schema

Every model MUST return this exact JSON format. Include this requirement in every prompt:
```json
{
  "analysis": "detailed analysis text",
  "score": 0-100,
  "confidence": 0-100,
  "flags": ["concern1", "concern2"],
  "recommendation": "what to do",
  "reasoning": ["step 1", "step 2", "step 3"]
}
```

If a model doesn't return valid JSON, the consensus engine handles it as a failure and continues with the remaining models.

## How to Build Each Branch in n8n

Each LLM branch is an HTTP Request node calling that model's API directly.
Do NOT use n8n's built-in AI nodes — use HTTP Request for full control.

### Branch A — Claude (Anthropic)
- Node type: HTTP Request
- Method: POST
- URL: `https://api.anthropic.com/v1/messages`
- Authentication: Use n8n credential named **"Anthropic API"** (Header Auth)
- Additional headers: `anthropic-version` = `2023-06-01`
- Body (JSON):
```json
{
  "model": "claude-sonnet-4-20250514",
  "max_tokens": 4096,
  "system": "{{$json.systemPrompt}}",
  "messages": [{"role": "user", "content": "{{$json.processedInput}}"}]
}
```
- Parse response: `$json.content[0].text`
- Role in ensemble: Primary analyst. Deep reasoning.

### Branch B — GPT-4 (OpenAI)
- Node type: HTTP Request
- Method: POST
- URL: `https://api.openai.com/v1/chat/completions`
- Authentication: Use n8n credential named **"OpenAI API"** (Header Auth)
- Body (JSON):
```json
{
  "model": "gpt-4o",
  "messages": [
    {"role": "system", "content": "{{$json.systemPrompt}}"},
    {"role": "user", "content": "{{$json.processedInput}}"}
  ],
  "response_format": {"type": "json_object"}
}
```
- Parse response: `$json.choices[0].message.content`
- Role in ensemble: Cross-validator. Different training data catches blind spots.

### Branch C — Gemini (Google)
- Node type: HTTP Request
- Method: POST
- URL: `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent`
- Authentication: Use n8n credential named **"Gemini API"** (Header Auth)
- Body (JSON):
```json
{
  "contents": [{"parts": [{"text": "{{$json.systemPrompt}}\n\n{{$json.processedInput}}"}]}],
  "generationConfig": {"responseMimeType": "application/json"}
}
```
- Parse response: `$json.candidates[0].content.parts[0].text`
- Role in ensemble: Alternative perspective.

### Branch D — Grok (xAI)
- Node type: HTTP Request
- Method: POST
- URL: `https://api.x.ai/v1/chat/completions`
- Authentication: Use n8n credential named **"xAI API"** (Header Auth)
- Body (JSON):
```json
{
  "model": "grok-3",
  "messages": [
    {"role": "system", "content": "{{$json.systemPrompt}}"},
    {"role": "user", "content": "{{$json.processedInput}}"}
  ]
}
```
- Parse response: `$json.choices[0].message.content`
- Role in ensemble: Contrarian check.

## Consensus Engine (Code Node after Merge)

Place a Code node after the Merge node (set to "Wait for All"). This JavaScript calculates agreement across all 4 models:
```javascript
// Parse each model's response
const models = ['claude', 'gpt4', 'gemini', 'grok'];
const items = $input.all();
const responses = {};

for (let i = 0; i < items.length; i++) {
  try {
    let text;
    const data = items[i].json;
    if (data.content) text = data.content[0].text; // Claude
    else if (data.choices) text = data.choices[0].message.content; // OpenAI/Grok
    else if (data.candidates) text = data.candidates[0].content.parts[0].text; // Gemini
    responses[models[i]] = JSON.parse(text);
  } catch (e) {
    responses[models[i]] = null; // Model failed — ensemble continues with others
  }
}

// Filter to successful responses only
const valid = Object.entries(responses).filter(([k, v]) => v !== null);
const validCount = valid.length;

if (validCount === 0) {
  return [{ json: { error: 'All models failed', responses } }];
}

// Defensive field access — handle missing or invalid fields
const safeNum = (val, fallback = 0) => (typeof val === 'number' && !isNaN(val)) ? val : fallback;
const scores = valid.map(([k, v]) => safeNum(v.score, 50));
const confidences = valid.map(([k, v]) => safeNum(v.confidence, 50));
const avgScore = scores.reduce((a, b) => a + b, 0) / scores.length;
const spread = Math.max(...scores) - Math.min(...scores);
const avgConfidence = confidences.reduce((a, b) => a + b, 0) / confidences.length;

// Weighted score (higher confidence = more weight)
const totalConf = confidences.reduce((a, b) => a + b, 0);
const weightedScore = totalConf > 0
  ? valid.reduce((sum, [k, v], i) => sum + (scores[i] * (confidences[i] / totalConf)), 0)
  : avgScore;

// Agreement level
let consensus;
if (spread <= 10) consensus = 'STRONG';
else if (spread <= 25) consensus = 'MODERATE';
else if (spread <= 40) consensus = 'WEAK';
else consensus = 'DISAGREEMENT';

// Combine all flags (deduplicated)
const allFlags = [...new Set(valid.flatMap(([k, v]) => Array.isArray(v.flags) ? v.flags : []))];

// Estimate token costs (approximate)
const estimatedCost = {
  claude: 0.003,   // per 1K tokens, rough average
  gpt4: 0.005,
  gemini: 0.001,
  grok: 0.003,
  note: 'These are rough estimates. Check provider dashboards for actual costs.'
};

return [{
  json: {
    consensus: {
      level: consensus,
      weightedScore: Math.round(weightedScore * 10) / 10,
      averageScore: Math.round(avgScore * 10) / 10,
      spread: spread,
      confidence: Math.round(avgConfidence * 10) / 10,
      modelsUsed: validCount,
      modelsFailed: 4 - validCount,
      degraded: validCount < 4
    },
    flags: allFlags,
    auditTrail: valid.map(([model, resp]) => ({
      model,
      score: safeNum(resp.score),
      confidence: safeNum(resp.confidence),
      flags: Array.isArray(resp.flags) ? resp.flags : [],
      reasoning: Array.isArray(resp.reasoning) ? resp.reasoning : [resp.reasoning || 'No reasoning provided'],
      recommendation: resp.recommendation || 'No recommendation provided'
    })),
    failedModels: Object.entries(responses)
      .filter(([k, v]) => v === null)
      .map(([k]) => k),
    estimatedCost,
    timestamp: new Date().toISOString()
  }
}];
```

## Error Handling Rules

1. Each LLM branch gets its own error handler (use n8n Error Trigger)
2. Set timeout on each HTTP Request: 30 seconds
3. Set retry: 1 retry with 5 second wait
4. If a model fails: ensemble continues with remaining models (degraded mode)
5. If score spread > 40: flag as DISAGREEMENT, include all reasoning for human review
6. NEVER fail silently — always log which model failed and why to a Set node
7. If ALL models fail: return an error object, do NOT return empty results

## Credential Rules

- NEVER put API keys directly in the workflow JSON
- ALWAYS use n8n credential references by the exact names defined in Part 4:
  - "Anthropic API"
  - "OpenAI API"
  - "Gemini API"
  - "xAI API"
- If a credential is missing, the workflow should still deploy but that branch will fail gracefully

## Cost Tracking Rule

Every ensemble workflow MUST include a final Set node that logs:
- Which models were called
- Whether each succeeded or failed
- Timestamp
- The consensus level achieved

This enables cost monitoring and debugging across all client workflows.
