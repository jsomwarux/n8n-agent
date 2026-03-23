# Deploy a New Ranking Niche in 30 Minutes

## What You Need
- A niche topic with 4-8 measurable scoring dimensions (totaling 100 points)
- A callback endpoint (Replit app, or any HTTPS endpoint)
- A unique port number (8001=glow-index, use 8002+ for new niches)

## Steps

### 1. Copy the template
```bash
cp -r templates/ensemble-engine clients/[niche-name]-engine
cd clients/[niche-name]-engine
```

### 2. Configure
```bash
cp config_template.py config.py
```
Edit `config.py`:
- Set `NICHE_NAME = "your-niche-slug"`
- Set `PORT = 8002` (or next available)
- Optionally adjust models, timeouts, concurrency

### 3. Write your prompts
The most important step. See `prompt-guide.md` for the full format.

Edit `prompts/stage1_analysis.txt`:
- Replace the role description with your niche expert persona
- Define 4-8 scoring dimensions that total exactly 100 points
- Set scoring criteria for each dimension (high/mid/low ranges)
- Define tier thresholds and verdict values
- Keep the `{placeholder}` variables — they are filled at runtime

Edit `prompts/stage2_deliberation.txt`:
- Replace `[NICHE]` with your domain name
- Update verdict values to match Stage 1
- The deliberation logic is mostly generic — focus on the role description

### 4. Customize the collector
Edit `collectors/niche_collector.py`:
- Replace the 6 Brave Search queries with your niche-specific queries
- Update `_scrape_detail_page()` with your niche's authoritative data sources
- Update the import in `pipeline/stage1_collect.py` if you rename the file

### 5. Install dependencies
```bash
pip install -r requirements.txt
```

### 6. Create the LaunchAgent
Copy and edit the glow-index plist:
```bash
cp ~/Library/LaunchAgents/com.openclaw.glow-index-engine.plist \
   ~/Library/LaunchAgents/com.openclaw.[niche]-engine.plist
```
Edit the new plist:
- Change `Label` to `com.openclaw.[niche]-engine`
- Change `WorkingDirectory` to `/Users/jtsomwaru/projects/n8n-agent/clients/[niche-name]-engine`
- Change `--port` to your unique port
- Change `StandardOutPath` and `StandardErrorPath` to `/tmp/[niche]-engine.log`

### 7. Load and verify
```bash
launchctl load ~/Library/LaunchAgents/com.openclaw.[niche]-engine.plist
sleep 5
curl -s http://127.0.0.1:[PORT]/health
```

### 8. Create the n8n workflow
1. Duplicate the Glow Index workflow in n8n (workflow ID: LNae5xv5dmIi6nBP)
2. Change the webhook path to `/webhook/[niche]-analysis`
3. Update the HTTP Request node URL to `http://127.0.0.1:[PORT]/analyze`
4. Activate the workflow

### 9. Test end-to-end
```bash
curl -X POST http://localhost:5678/webhook/[niche]-analysis \
  -H "Content-Type: application/json" \
  -d '{"productId":"test-001","productName":"Test Item","brand":"Test Brand","category":"test","priceUsd":10,"callbackUrl":"https://your-app.replit.app/api/callback","callbackSecret":"your-secret"}'
```
Monitor: `tail -f /tmp/[niche]-engine.log`

Pipeline takes ~90-120 seconds. You should see Stages 1-4 complete, then callback sent.

## Active Niches

| Niche | Port | LaunchAgent | Status |
|-------|------|-------------|--------|
| glow-index | 8001 | com.openclaw.glow-index-engine | active |

Add a row above when you deploy a new niche.

## Troubleshooting

**Engine won't start**: Check `/tmp/[niche]-engine.log`. Common issues:
- Missing API keys in `~/.config/env/global.env`
- Port already in use (`lsof -i :[PORT]`)
- Python dependency missing (`pip install -r requirements.txt`)

**Pipeline fails at Stage 1**: Brave Search queries returning no results. Check your queries in the collector — make sure they match real web content for your niche.

**Pipeline fails at Stage 2**: LLM JSON parsing errors. Check your prompt output format — the JSON schema must match what `validators.py` expects (needs `base_score` field).

**Callback 404**: The callback endpoint doesn't exist or the secret doesn't match. Test with curl first.

**LaunchAgent not loading**: Check `launchctl list | grep openclaw`. If not listed, check plist XML syntax: `plutil -lint ~/Library/LaunchAgents/com.openclaw.[niche]-engine.plist`
