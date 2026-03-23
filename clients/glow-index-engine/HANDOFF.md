## What Was Done
- LaunchAgent: ~/Library/LaunchAgents/com.openclaw.glow-index-engine.plist (loaded, engine persists across reboots)
- End-to-end test: PASS — consensus score for The Ordinary Niacinamide 10% + Zinc 1%: 84.75/100 (S tier, BUY_IT)
- Pipeline completed in 108.3 seconds (Stage 1: 3s, Stage 2: 53s, Stage 3: 52s, Stage 4: instant)
- All 4 models scored successfully in Stage 2 (Grok: 85, Claude: 87, Gemini: 85, o3: 84)
- 3/4 models completed Stage 3 deliberation (Gemini had a JSON parse error — non-fatal, 3/4 is above minimum)
- Callback to Replit: returned HTTP 404 (expected — test productId "test-001" not in Replit database)

## How to Use Glow Index
POST to http://localhost:5678/webhook/skincare-analysis
Fields: productId, productName, brand, category, priceUsd, callbackUrl, callbackSecret
Result arrives at callbackUrl ~90-120 seconds later
Logs: tail -f /tmp/glow-engine.log
Status: curl http://127.0.0.1:8001/status

## How to Add a New Niche
Template: ~/projects/n8n-agent/templates/ensemble-engine/
Follow: templates/ensemble-engine/SETUP.md

## Known Issues
- Gemini 3.1 Pro occasionally returns malformed JSON in Stage 3 deliberation (raw response starts with text instead of JSON). Non-fatal — pipeline degrades gracefully to 3/4 models. The JSON extraction regex catches most cases but Gemini's verbosity before the JSON block sometimes defeats it.
- Callback endpoint returned 404 for test product — this is expected behavior (Replit app validates productId against its database). Real products queued via the Replit app will succeed.
- LaunchAgent plist is stored both in ~/Library/LaunchAgents/ (active) and in clients/glow-index-engine/ (version-controlled backup). Keep both in sync.
