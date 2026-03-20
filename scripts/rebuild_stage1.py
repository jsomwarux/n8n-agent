#!/usr/bin/env python3
"""Rebuild Nash Satoshi Stage 1: replace hallucinated research with real Brave + LunarCrush API calls."""
import json

WF_PATH = '/Users/jtsomwaru/projects/n8n-agent/workflows/nash-satoshi-analysis.json'

with open(WF_PATH) as f:
    wf = json.load(f)

# --- 1. Remove old Stage 1 nodes ---
remove_names = {'Build Fundamentals Prompt', 'Fundamentals Research', 'Build Social Prompt', 'Social Research'}
wf['nodes'] = [n for n in wf['nodes'] if n['name'] not in remove_names]

# --- 2. Shift all nodes from Merge Research onward +440px right ---
shift_names = {
    'Merge Research', 'Combine Research', 'Build Stage2 Bodies',
    'GPT Stage2', 'Gemini Stage2', 'Claude Stage2', 'Grok Stage2',
    'Merge Stage2', 'Build Stage3 Bodies',
    'GPT Stage3', 'Gemini Stage3', 'Claude Stage3', 'Grok Stage3',
    'Merge Stage3', 'Build Stage4 Body', 'Stage4 Aggregation',
    'Format Result', 'Send Result'
}
for node in wf['nodes']:
    if node['name'] in shift_names:
        node['position'][0] += 440

# --- 3. Define jsCode for Code nodes ---

MERGE_FUND_JS = r"""// Combine Brave search results and build fundamentals synthesis prompt
const items = $input.all();
let tokenData = null;
try { tokenData = $('Parse CoinGecko').first().json; } catch(e) {}
if (!tokenData || !tokenData.ticker) { try { tokenData = $('Parse DexScreener').first().json; } catch(e) {} }
if (!tokenData) { tokenData = $('Extract Input').item.json; }

// Extract Brave web results from both searches
let results1 = [], results2 = [];
try {
  const r1 = items[0].json;
  results1 = r1.web && r1.web.results ? r1.web.results : [];
} catch(e) {}
try {
  const r2 = items[1].json;
  results2 = r2.web && r2.web.results ? r2.web.results : [];
} catch(e) {}

const allResults = [...results1, ...results2];
const searchContext = allResults.map((r, i) => `[${i+1}] ${r.title}\n${r.description}\nURL: ${r.url}`).join('\n\n');

const d = tokenData;
const prompt = `You are a crypto research analyst. Analyze this token using the REAL search results provided below.

- Ticker: ${d.ticker}
- Name: ${d.name}
- Chain: ${d.chain}
- Contract: ${d.contract_address}
- Price: $${d.price}
- Market Cap: $${d.market_cap}
- FDV: $${d.fdv}
- 24h Volume: $${d.volume_24h}

REAL WEB SEARCH RESULTS:
${searchContext}

Using ONLY the search results above and the token data provided, cover:
1. Narrative Positioning
2. Project Fundamentals
3. Team & Backers
4. Value Capture
5. Traction & Usage
6. Tokenomics & Unlocks
7. Roadmap & Catalysts
8. Competitive Analysis

Be specific and data-driven. Cite sources from the search results. If information is not available in the search results, explicitly state "Not found in search results" rather than speculating.`;

return [{ json: { requestBody: { model: 'anthropic/claude-sonnet-4-6', messages: [{ role: 'user', content: prompt }], max_tokens: 4000 } } }];"""

MERGE_SOCIAL_JS = r"""// Combine LunarCrush metrics and Brave social search results, build synthesis prompt
const items = $input.all();
let tokenData = null;
try { tokenData = $('Parse CoinGecko').first().json; } catch(e) {}
if (!tokenData || !tokenData.ticker) { try { tokenData = $('Parse DexScreener').first().json; } catch(e) {} }
if (!tokenData) { tokenData = $('Extract Input').item.json; }

// LunarCrush data (input 0)
let lunarContext = 'LunarCrush data unavailable';
try {
  const lc = items[0].json;
  if (lc && !lc.error) {
    const metrics = [];
    if (lc.galaxy_score !== undefined) metrics.push('Galaxy Score: ' + lc.galaxy_score);
    if (lc.alt_rank !== undefined) metrics.push('Alt Rank: ' + lc.alt_rank);
    if (lc.social_dominance !== undefined) metrics.push('Social Dominance: ' + lc.social_dominance);
    if (lc.social_volume !== undefined) metrics.push('Social Volume: ' + lc.social_volume);
    if (lc.social_score !== undefined) metrics.push('Social Score: ' + lc.social_score);
    if (lc.sentiment !== undefined) metrics.push('Sentiment: ' + lc.sentiment);
    if (lc.interactions_24h !== undefined) metrics.push('Interactions 24h: ' + lc.interactions_24h);
    if (lc.social_contributors !== undefined) metrics.push('Social Contributors: ' + lc.social_contributors);
    if (metrics.length > 0) lunarContext = metrics.join('\n');
  }
} catch(e) { lunarContext = 'LunarCrush data unavailable: ' + e.message; }

// Brave social search results (input 1)
let braveResults = [];
try {
  const br = items[1].json;
  braveResults = br.web && br.web.results ? br.web.results : [];
} catch(e) {}
const searchContext = braveResults.map((r, i) => `[${i+1}] ${r.title}\n${r.description}\nURL: ${r.url}`).join('\n\n');

const d = tokenData;
const prompt = `You are a crypto social intelligence analyst. Analyze social signals for this token using the REAL data provided below.

- Ticker: ${d.ticker}
- Name: ${d.name}
- Chain: ${d.chain}
- Price: $${d.price}
- Market Cap: $${d.market_cap}

LUNARCRUSH METRICS:
${lunarContext}

SOCIAL WEB SEARCH RESULTS:
${searchContext}

Using ONLY the data above, cover:
1. Attention Metrics (social volume, dominance, galaxy score)
2. KOL Signals
3. Sentiment Analysis
4. Community Coordination
5. Narrative Heat

Be specific and data-driven. Cite sources. If information is not available, explicitly state so rather than speculating.`;

return [{ json: { requestBody: { model: 'anthropic/claude-sonnet-4-6', messages: [{ role: 'user', content: prompt }], max_tokens: 3000 } } }];"""

# --- 4. Define new nodes ---

OPENROUTER_CRED = {"httpHeaderAuth": {"id": "eKuUbdByJmAQfvxu", "name": "OpenRouter Header Auth"}}

BRAVE_HEADERS = {
    "parameters": [
        {"name": "Accept", "value": "application/json"},
        {"name": "X-Subscription-Token", "value": "={{ $env.BRAVE_API_KEY }}"}
    ]
}

new_nodes = [
    # --- Fundamentals path ---
    {
        "id": "bf1", "name": "Brave Fundamentals 1",
        "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
        "position": [1100, -50],
        "parameters": {
            "method": "GET",
            "url": "={{ 'https://api.search.brave.com/res/v1/web/search?q=' + encodeURIComponent($json.ticker + ' ' + $json.name + ' tokenomics team backers') + '&count=5' }}",
            "authentication": "none",
            "sendHeaders": True,
            "headerParameters": BRAVE_HEADERS,
            "options": {"timeout": 15000}
        },
        "retryOnFail": True, "maxTries": 2, "waitBetweenTries": 3000,
        "onError": "continueRegularOutput"
    },
    {
        "id": "bf2", "name": "Brave Fundamentals 2",
        "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
        "position": [1100, 150],
        "parameters": {
            "method": "GET",
            "url": "={{ 'https://api.search.brave.com/res/v1/web/search?q=' + encodeURIComponent($json.ticker + ' crypto roadmap catalysts 2026') + '&count=5' }}",
            "authentication": "none",
            "sendHeaders": True,
            "headerParameters": BRAVE_HEADERS,
            "options": {"timeout": 15000}
        },
        "retryOnFail": True, "maxTries": 2, "waitBetweenTries": 3000,
        "onError": "continueRegularOutput"
    },
    {
        "id": "wfm1", "name": "Wait Fund Merge",
        "type": "n8n-nodes-base.merge", "typeVersion": 3.2,
        "position": [1320, 50],
        "parameters": {"mode": "append", "numberInputs": 2}
    },
    {
        "id": "mf1", "name": "Merge Fundamentals",
        "type": "n8n-nodes-base.code", "typeVersion": 2,
        "position": [1540, 50],
        "parameters": {"jsCode": MERGE_FUND_JS}
    },
    {
        "id": "fs1", "name": "Fundamentals Synthesis",
        "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
        "position": [1760, 50],
        "parameters": {
            "url": "https://openrouter.ai/api/v1/chat/completions",
            "method": "POST",
            "authentication": "predefinedCredentialType",
            "nodeCredentialType": "httpHeaderAuth",
            "sendBody": True, "specifyBody": "json",
            "jsonBody": "={{ $json.requestBody }}",
            "options": {"timeout": 120000}
        },
        "credentials": OPENROUTER_CRED,
        "retryOnFail": True, "maxTries": 2, "waitBetweenTries": 5000,
        "onError": "continueRegularOutput"
    },
    # --- Social path ---
    {
        "id": "lcs1", "name": "LunarCrush Social",
        "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
        "position": [1100, 450],
        "parameters": {
            "method": "GET",
            "url": "={{ 'https://lunarcrush.com/api4/public/coins/' + $json.ticker.toLowerCase() + '/v1' }}",
            "authentication": "none",
            "options": {"timeout": 15000}
        },
        "retryOnFail": True, "maxTries": 2, "waitBetweenTries": 3000,
        "onError": "continueRegularOutput"
    },
    {
        "id": "brs1", "name": "Brave Social",
        "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
        "position": [1100, 650],
        "parameters": {
            "method": "GET",
            "url": "={{ 'https://api.search.brave.com/res/v1/web/search?q=' + encodeURIComponent($json.ticker + ' crypto community sentiment 2026') + '&count=5' }}",
            "authentication": "none",
            "sendHeaders": True,
            "headerParameters": BRAVE_HEADERS,
            "options": {"timeout": 15000}
        },
        "retryOnFail": True, "maxTries": 2, "waitBetweenTries": 3000,
        "onError": "continueRegularOutput"
    },
    {
        "id": "wsm1", "name": "Wait Social Merge",
        "type": "n8n-nodes-base.merge", "typeVersion": 3.2,
        "position": [1320, 550],
        "parameters": {"mode": "append", "numberInputs": 2}
    },
    {
        "id": "msoc1", "name": "Merge Social",
        "type": "n8n-nodes-base.code", "typeVersion": 2,
        "position": [1540, 550],
        "parameters": {"jsCode": MERGE_SOCIAL_JS}
    },
    {
        "id": "ss1", "name": "Social Synthesis",
        "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
        "position": [1760, 550],
        "parameters": {
            "url": "https://openrouter.ai/api/v1/chat/completions",
            "method": "POST",
            "authentication": "predefinedCredentialType",
            "nodeCredentialType": "httpHeaderAuth",
            "sendBody": True, "specifyBody": "json",
            "jsonBody": "={{ $json.requestBody }}",
            "options": {"timeout": 120000}
        },
        "credentials": OPENROUTER_CRED,
        "retryOnFail": True, "maxTries": 2, "waitBetweenTries": 5000,
        "onError": "continueRegularOutput"
    },
]

wf['nodes'].extend(new_nodes)

# --- 5. Update connections ---

# Remove old connection entries
for name in remove_names:
    wf['connections'].pop(name, None)

# Parse CoinGecko now fans out to all 4 search nodes
wf['connections']['Parse CoinGecko'] = {"main": [[
    {"node": "Brave Fundamentals 1", "type": "main", "index": 0},
    {"node": "Brave Fundamentals 2", "type": "main", "index": 0},
    {"node": "LunarCrush Social", "type": "main", "index": 0},
    {"node": "Brave Social", "type": "main", "index": 0}
]]}

# Parse DexScreener fans out to same 4 search nodes
wf['connections']['Parse DexScreener'] = {"main": [[
    {"node": "Brave Fundamentals 1", "type": "main", "index": 0},
    {"node": "Brave Fundamentals 2", "type": "main", "index": 0},
    {"node": "LunarCrush Social", "type": "main", "index": 0},
    {"node": "Brave Social", "type": "main", "index": 0}
]]}

# Fundamentals path connections
wf['connections']['Brave Fundamentals 1'] = {"main": [[
    {"node": "Wait Fund Merge", "type": "main", "index": 0}
]]}
wf['connections']['Brave Fundamentals 2'] = {"main": [[
    {"node": "Wait Fund Merge", "type": "main", "index": 1}
]]}
wf['connections']['Wait Fund Merge'] = {"main": [[
    {"node": "Merge Fundamentals", "type": "main", "index": 0}
]]}
wf['connections']['Merge Fundamentals'] = {"main": [[
    {"node": "Fundamentals Synthesis", "type": "main", "index": 0}
]]}
wf['connections']['Fundamentals Synthesis'] = {"main": [[
    {"node": "Merge Research", "type": "main", "index": 0}
]]}

# Social path connections
wf['connections']['LunarCrush Social'] = {"main": [[
    {"node": "Wait Social Merge", "type": "main", "index": 0}
]]}
wf['connections']['Brave Social'] = {"main": [[
    {"node": "Wait Social Merge", "type": "main", "index": 1}
]]}
wf['connections']['Wait Social Merge'] = {"main": [[
    {"node": "Merge Social", "type": "main", "index": 0}
]]}
wf['connections']['Merge Social'] = {"main": [[
    {"node": "Social Synthesis", "type": "main", "index": 0}
]]}
wf['connections']['Social Synthesis'] = {"main": [[
    {"node": "Merge Research", "type": "main", "index": 1}
]]}

# --- 6. Remove the workflow ID so n8n assigns a new one on import ---
wf.pop('id', None)

# --- 7. Write output ---
with open(WF_PATH, 'w') as f:
    json.dump(wf, f, indent=2)

# Quick sanity check
node_names = [n['name'] for n in wf['nodes']]
conn_sources = list(wf['connections'].keys())
print(f"Nodes: {len(wf['nodes'])}")
print(f"Connections: {len(conn_sources)} source nodes")

# Verify removed nodes are gone
for name in remove_names:
    assert name not in node_names, f"FAIL: {name} still in nodes"
    assert name not in conn_sources, f"FAIL: {name} still in connections"

# Verify new nodes exist
new_names = {'Brave Fundamentals 1', 'Brave Fundamentals 2', 'Wait Fund Merge',
             'Merge Fundamentals', 'Fundamentals Synthesis',
             'LunarCrush Social', 'Brave Social', 'Wait Social Merge',
             'Merge Social', 'Social Synthesis'}
for name in new_names:
    assert name in node_names, f"FAIL: {name} missing from nodes"
    assert name in conn_sources, f"FAIL: {name} missing from connections"

print("All checks passed!")
