# Anthropic Claude API — n8n HTTP Request Pattern

## Headers (same for all calls)
- x-api-key: [ANTHROPIC_API_KEY]
- anthropic-version: 2023-06-01
- Content-Type: application/json

## Claude Haiku (classification, routing, categorization)
POST https://api.anthropic.com/v1/messages
{
  "model": "claude-haiku-4-5-20251001",
  "max_tokens": 300,
  "messages": [{"role": "user", "content": "[PROMPT]"}]
}

## Claude Sonnet (parsing, analysis, answer generation)
POST https://api.anthropic.com/v1/messages
{
  "model": "claude-sonnet-4-6",
  "max_tokens": 2000,
  "messages": [{"role": "user", "content": "[PROMPT]"}]
}

## Sending a PDF to Claude
{
  "model": "claude-sonnet-4-6",
  "max_tokens": 4000,
  "messages": [{
    "role": "user",
    "content": [
      {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": "{{BASE64_DATA}}"}},
      {"type": "text", "text": "[PROMPT]"}
    ]
  }]
}
n8n stores binary data as base64 already. Access via: items[0].binary.data.data

## Response Parsing
Extract answer text: response.content[0].text

## Error Handling
After every Claude HTTP Request node, add IF node:
- If status !== 200 or node errors → log error, use fallback response
- 429 = rate limit → retry after delay
- 500 = server error → retry once
