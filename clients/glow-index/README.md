# Glow Index — Skincare Analysis Workflow

Client: Glow Index (skincare product ranking app)
App URL: https://9f38aa93-fe6f-48cd-a1ad-edfca444fe72-00-1k2fa9lt9onjl.worf.replit.dev

## What Was Built
- 4-LLM ensemble skincare analysis workflow (Stage 1 + Stage 2)
- Webhook trigger: POST /webhook/skincare-analysis
- Callback to Replit app at /api/analysis-callback
- Models: Claude Opus 4.5, GPT-5.2, Gemini 3 Pro, Grok 4

## Webhook Payload
```json
{
  "productId": "cuid_string",
  "productName": "Product Name",
  "brand": "Brand Name",
  "category": "moisturizer",
  "priceUsd": 45.00,
  "website": "https://example.com",
  "description": "Optional",
  "runId": "unique_run_id"
}
```
