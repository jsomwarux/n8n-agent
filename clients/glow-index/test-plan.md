# Glow Index Skincare Analysis - Test Plan

## Workflow Details
- **Workflow ID**: LNae5xv5dmIi6nBP
- **Workflow Name**: Glow Index Skincare Analysis
- **n8n URL**: http://localhost:5678
- **Webhook Path**: POST /webhook/skincare-analysis
- **Public URL (ngrok)**: https://unwearing-sniffingly-rudolph.ngrok-free.dev/webhook/skincare-analysis
- **Callback URL**: https://9f38aa93-fe6f-48cd-a1ad-edfca444fe72-00-1k2fa9lt9onjl.worf.replit.dev/api/analysis-callback

## Test 1: Basic Product Analysis (The Ordinary Niacinamide)

```bash
curl -X POST https://unwearing-sniffingly-rudolph.ngrok-free.dev/webhook/skincare-analysis \
  -H "Content-Type: application/json" \
  -d '{
    "productId": "test-001",
    "productName": "Niacinamide 10% + Zinc 1%",
    "brand": "The Ordinary",
    "category": "serum",
    "priceUsd": 6
  }'
```

**Expected**: HTTP 202 with `{"status":"accepted","message":"Analysis queued"}`

## Test 2: Luxury Product (La Mer Moisturizing Cream)

```bash
curl -X POST https://unwearing-sniffingly-rudolph.ngrok-free.dev/webhook/skincare-analysis \
  -H "Content-Type: application/json" \
  -d '{
    "productId": "test-002",
    "productName": "Moisturizing Cream",
    "brand": "La Mer",
    "category": "moisturizer",
    "priceUsd": 190
  }'
```

## Test 3: Mid-Range Product (SkinCeuticals C E Ferulic)

```bash
curl -X POST https://unwearing-sniffingly-rudolph.ngrok-free.dev/webhook/skincare-analysis \
  -H "Content-Type: application/json" \
  -d '{
    "productId": "test-003",
    "productName": "C E Ferulic",
    "brand": "SkinCeuticals",
    "category": "serum",
    "priceUsd": 182
  }'
```

## Test 4: Validation Error (Missing Fields)

```bash
curl -X POST https://unwearing-sniffingly-rudolph.ngrok-free.dev/webhook/skincare-analysis \
  -H "Content-Type: application/json" \
  -d '{
    "productId": "test-004"
  }'
```

**Expected**: HTTP 202 (webhook responds immediately), workflow fails at Validate Input, Error Trigger sends error to callback

## Test 5: Local n8n Direct (bypass ngrok)

```bash
curl -X POST http://localhost:5678/webhook/skincare-analysis \
  -H "Content-Type: application/json" \
  -d '{
    "productId": "test-005",
    "productName": "Skin Perfecting 2% BHA Liquid Exfoliant",
    "brand": "Paula'\''s Choice",
    "category": "exfoliant",
    "priceUsd": 35
  }'
```

## Callback Payload Structure

The workflow POSTs to the callback URL with this structure:
```json
{
  "productId": "test-001",
  "productName": "Niacinamide 10% + Zinc 1%",
  "brand": "The Ordinary",
  "category": "serum",
  "priceUsd": 6,
  "consensusScore": 82.5,
  "tier": "S",
  "consumerVerdict": "CONSUMER WINS",
  "stage1Results": {
    "claude": { "llm": "Claude Opus 4.5", "stage": 1, "total": 84, ... },
    "gpt": { "llm": "GPT-5.2", "stage": 1, "total": 81, ... },
    "gemini": { "llm": "Gemini 3 Pro", "stage": 1, "total": 83, ... },
    "grok": { "llm": "Grok 4", "stage": 1, "total": 80, ... }
  },
  "stage2Results": [
    { "llm": "Claude Opus 4.5", "stage": 2, "total": 83.25, ... },
    { "llm": "GPT-5.2", "stage": 2, "total": 82.10, ... },
    { "llm": "Gemini 3 Pro", "stage": 2, "total": 82.75, ... },
    { "llm": "Grok 4", "stage": 2, "total": 81.90, ... }
  ],
  "modelScores": { "claude": 83.25, "gpt": 82.10, "gemini": 82.75, "grok": 81.90 },
  "analysisTimestamp": "2026-02-23T18:00:00.000Z"
}
```

## Architecture

```
Webhook (202) -> Validate Input -> Build S1 Prompts
  -> [S1 Claude | S1 GPT | S1 Gemini | S1 Grok] (parallel)
  -> Merge Stage 1 -> Build S2 Prompts
  -> [S2 Claude | S2 GPT | S2 Gemini | S2 Grok] (parallel)
  -> Merge Stage 2 -> Calculate Consensus -> Send Callback -> Log Status
```

Error Trigger -> Error Notifier (POSTs error to callback URL)

## LLM Configuration
| Model | API | Credential | Display Name |
|-------|-----|------------|--------------|
| claude-opus-4-5-20250514 | Anthropic | Anthropic API | Claude Opus 4.5 |
| gpt-4o | OpenAI | OpenAI API | GPT-5.2 |
| gemini-1.5-pro | Google | Gemini API | Gemini 3 Pro |
| grok-2 | xAI | xAI API | Grok 4 |

## Tier Mapping
| Score | Tier |
|-------|------|
| 85+ | S+ |
| 75-84 | S |
| 65-74 | A |
| 50-64 | B |
| <50 | C |

## Consensus Algorithm
1. Collect all 4 Stage 2 total scores
2. Calculate median of the 4 scores
3. For any score deviating >15 points from median, apply 50% weight
4. Weighted average = consensus score
