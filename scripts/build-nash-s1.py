#!/usr/bin/env python3
"""Build the updated Nash Satoshi workflow with new Stage 1 nodes."""
import json
import copy

# Load existing workflow
with open('/Users/jtsomwaru/projects/n8n-agent/workflows/nash-satoshi-analysis.json', 'r') as f:
    wf = json.load(f)

# Nodes to REMOVE (old Stage 1)
remove_ids = {'bf1', 'bf2', 'wfm1', 'mf1', 'fs1', 'lcs1', 'brs1', 'wsm1', 'msoc1', 'ss1'}
remove_names = set()
for node in wf['nodes']:
    if node['id'] in remove_ids:
        remove_names.add(node['name'])

# Filter out old Stage 1 nodes
wf['nodes'] = [n for n in wf['nodes'] if n['id'] not in remove_ids]

# Remove old Stage 1 connections
for name in remove_names:
    wf['connections'].pop(name, None)

# Also clean references TO removed nodes from Parse CoinGecko and Parse DexScreener
for src in ['Parse CoinGecko', 'Parse DexScreener']:
    if src in wf['connections']:
        outputs = wf['connections'][src]['main']
        for i, output_list in enumerate(outputs):
            wf['connections'][src]['main'][i] = [
                conn for conn in output_list
                if conn['node'] not in remove_names
            ]

# Clean Fundamentals Synthesis and Social Synthesis refs from Merge Research connections
# (these nodes are being removed, Merge Research will get new inputs)
# Merge Research connections are set by SOURCE nodes connecting TO it, not FROM it
# So we just need to remove connection entries where source is a removed node

# ============================================================
# NEW STAGE 1A - FUNDAMENTALS (6 Brave + 1 Firecrawl)
# ============================================================

brave_base = {
    "type": "n8n-nodes-base.httpRequest",
    "typeVersion": 4.2,
    "parameters": {
        "method": "GET",
        "url": "https://api.search.brave.com/res/v1/web/search",
        "authentication": "none",
        "sendHeaders": True,
        "headerParameters": {
            "parameters": [
                {"name": "Accept", "value": "application/json"},
                {"name": "X-Subscription-Token", "value": "={{ $env.BRAVE_API_KEY }}"}
            ]
        },
        "sendQuery": True,
        "specifyQuery": "keypair",
        "queryParameters": {
            "parameters": []  # filled per node
        },
        "options": {"timeout": 15000}
    },
    "retryOnFail": True,
    "maxTries": 2,
    "waitBetweenTries": 3000,
    "onError": "continueRegularOutput"
}

brave_queries = [
    ("bfs1", "Brave Fund Overview",    [1100, -350], "={{ $json.ticker + ' ' + $json.name + ' project overview whitepaper' }}"),
    ("bfs2", "Brave Fund Tokenomics",  [1100, -200], "={{ $json.ticker + ' tokenomics supply vesting allocation holders' }}"),
    ("bfs3", "Brave Fund Team",        [1100, -50],  "={{ $json.ticker + ' ' + $json.name + ' team founder developer' }}"),
    ("bfs4", "Brave Fund Roadmap",     [1100, 100],  "={{ $json.ticker + ' roadmap milestones catalysts 2026' }}"),
    ("bfs5", "Brave Fund Competition", [1100, 250],  "={{ $json.ticker + ' competitive analysis narrative sector' }}"),
    ("bfs6", "Brave Fund OnChain",     [1100, 400],  "={{ $json.ticker + ' ' + $json.name + ' on-chain metrics volume trades' }}"),
]

brave_nodes = []
for node_id, name, pos, query_expr in brave_queries:
    node = copy.deepcopy(brave_base)
    node["id"] = node_id
    node["name"] = name
    node["position"] = pos
    node["parameters"]["queryParameters"]["parameters"] = [
        {"name": "q", "value": query_expr},
        {"name": "count", "value": "5"}
    ]
    brave_nodes.append(node)

# Firecrawl node
firecrawl_node = {
    "id": "fc1",
    "name": "Firecrawl Solscan",
    "type": "n8n-nodes-base.httpRequest",
    "typeVersion": 4.2,
    "position": [1100, 550],
    "parameters": {
        "method": "POST",
        "url": "https://api.firecrawl.dev/v1/scrape",
        "authentication": "none",
        "sendHeaders": True,
        "headerParameters": {
            "parameters": [
                {"name": "Authorization", "value": "Bearer fc-0d0961fa920a466a869fdd4068b9fe7e"},
                {"name": "Content-Type", "value": "application/json"}
            ]
        },
        "sendBody": True,
        "specifyBody": "json",
        "jsonBody": "={{ JSON.stringify({ url: 'https://solscan.io/token/' + $json.contract_address, formats: ['markdown'] }) }}",
        "options": {"timeout": 30000}
    },
    "retryOnFail": True,
    "maxTries": 2,
    "waitBetweenTries": 5000,
    "onError": "continueRegularOutput"
}

# Wait Fund Sources - Merge node with 7 inputs
wait_fund_sources = {
    "id": "wfs1",
    "name": "Wait Fund Sources",
    "type": "n8n-nodes-base.merge",
    "typeVersion": 3.2,
    "position": [1350, 100],
    "parameters": {
        "mode": "append",
        "numberInputs": 7
    }
}

# Merge Fundamentals - Code node
merge_fund_jscode = r"""// Combine 7 research sources into fundamentals context and build synthesis prompt
const items = $input.all();
let tokenData = null;
try { tokenData = $('Parse CoinGecko').first().json; } catch(e) {}
if (!tokenData || !tokenData.ticker) { try { tokenData = $('Parse DexScreener').first().json; } catch(e) {} }
if (!tokenData) { tokenData = $('Extract Input').item.json; }

const labels = ['PROJECT OVERVIEW', 'TOKENOMICS', 'TEAM & FOUNDERS', 'ROADMAP & CATALYSTS', 'COMPETITIVE LANDSCAPE', 'ON-CHAIN METRICS'];
const sections = [];

for (let i = 0; i < 6; i++) {
  try {
    const r = items[i].json;
    const results = (r.web && r.web.results) ? r.web.results : [];
    const snippets = results.map((s, j) => '[' + (j+1) + '] ' + s.title + '\n' + s.description + '\nURL: ' + s.url).join('\n\n');
    sections.push('--- ' + labels[i] + ' ---\n' + (snippets || 'No results found'));
  } catch(e) {
    sections.push('--- ' + labels[i] + ' ---\nSearch failed: ' + e.message);
  }
}

try {
  const fc = items[6].json;
  const md = (fc.data && fc.data.markdown) ? fc.data.markdown : (fc.markdown || JSON.stringify(fc).substring(0, 3000));
  sections.push('--- ON-CHAIN DATA (SOLSCAN) ---\n' + md.substring(0, 5000));
} catch(e) {
  sections.push('--- ON-CHAIN DATA (SOLSCAN) ---\nFirecrawl scrape failed: ' + e.message);
}

const fundamentals_context = sections.join('\n\n');
const d = tokenData;

const prompt = 'You are a crypto research analyst. Analyze this token using the REAL search results and on-chain data provided below.\n\n'
  + '- Ticker: ' + d.ticker + '\n- Name: ' + d.name + '\n- Chain: ' + d.chain + '\n- Contract: ' + d.contract_address
  + '\n- Price: $' + d.price + '\n- Market Cap: $' + d.market_cap + '\n- FDV: $' + d.fdv + '\n- 24h Volume: $' + d.volume_24h
  + '\n\nRESEARCH DATA:\n' + fundamentals_context
  + '\n\nUsing ONLY the data above, produce a structured analysis covering:\n'
  + '1. Narrative Positioning & Market Thesis\n'
  + '2. Project Fundamentals (product, tech, stage)\n'
  + '3. Team & Backers (names, credibility, exits)\n'
  + '4. Value Capture (token utility, staking, fees)\n'
  + '5. Traction & Usage (holders, volume, daily traders, TVL)\n'
  + '6. Tokenomics & Unlocks (supply, vesting, whale concentration)\n'
  + '7. Roadmap & Catalysts (upcoming milestones)\n'
  + '8. Competitive Analysis (comparable tokens, differentiation)\n'
  + '9. Key Links found\n\n'
  + 'Be specific and data-driven. Cite sources from the search results. If information is not available, explicitly state so rather than speculating.';

return [{ json: { requestBody: { model: 'anthropic/claude-sonnet-4-6', messages: [{ role: 'user', content: prompt }], max_tokens: 3000 } } }];"""

merge_fund_node = {
    "id": "mfund1",
    "name": "Merge Fundamentals",
    "type": "n8n-nodes-base.code",
    "typeVersion": 2,
    "position": [1570, 100],
    "parameters": {
        "jsCode": merge_fund_jscode
    }
}

# Fundamentals Synthesis - OpenRouter HTTP Request
fund_synth_node = {
    "id": "fsyn1",
    "name": "Fundamentals Synthesis",
    "type": "n8n-nodes-base.httpRequest",
    "typeVersion": 4.2,
    "position": [1790, 100],
    "parameters": {
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "method": "POST",
        "authentication": "predefinedCredentialType",
        "nodeCredentialType": "httpHeaderAuth",
        "sendBody": True,
        "specifyBody": "json",
        "jsonBody": "={{ $json.requestBody }}",
        "options": {"timeout": 120000}
    },
    "credentials": {
        "httpHeaderAuth": {
            "id": "eKuUbdByJmAQfvxu",
            "name": "OpenRouter Header Auth"
        }
    },
    "retryOnFail": True,
    "maxTries": 2,
    "waitBetweenTries": 5000,
    "onError": "continueRegularOutput"
}

# ============================================================
# NEW STAGE 1B - SOCIAL (5 Brave social searches + LunarCrush)
# ============================================================

social_queries = [
    ("bss1", "Brave Social General",   [1100, 750],  "={{ $json.ticker + ' crypto twitter community discussion' }}"),
    ("bss2", "Brave Social Project",   [1100, 900],  "={{ $json.ticker + ' ' + $json.name + ' token social media' }}"),
    ("bss3", "Brave Social Sentiment", [1100, 1050], "={{ $json.ticker + ' bullish bearish whale sentiment crypto' }}"),
    ("bss4", "Brave Social KOL",       [1100, 1200], "={{ $json.ticker + ' KOL thread alpha influencer crypto analysis' }}"),
    ("bss5", "Brave Social News",      [1100, 1350], "={{ $json.ticker + ' ' + $json.name + ' news announcement partnership 2026' }}"),
]

social_brave_nodes = []
for node_id, name, pos, query_expr in social_queries:
    node = copy.deepcopy(brave_base)
    node["id"] = node_id
    node["name"] = name
    node["position"] = pos
    node["parameters"]["queryParameters"]["parameters"] = [
        {"name": "q", "value": query_expr},
        {"name": "count", "value": "5"}
    ]
    social_brave_nodes.append(node)

# LunarCrush node (lesson #73 - public API, no auth needed)
lunarcrush_node = {
    "id": "lc1",
    "name": "LunarCrush Social",
    "type": "n8n-nodes-base.httpRequest",
    "typeVersion": 4.2,
    "position": [1100, 1500],
    "parameters": {
        "method": "GET",
        "url": "={{ 'https://lunarcrush.com/api4/public/coins/' + $json.ticker.toLowerCase() + '/v1' }}",
        "authentication": "none",
        "options": {"timeout": 15000}
    },
    "retryOnFail": True,
    "maxTries": 2,
    "waitBetweenTries": 3000,
    "onError": "continueRegularOutput"
}

# Wait Social Sources - Merge node with 6 inputs (5 Brave + 1 LunarCrush)
wait_social_sources = {
    "id": "wss1",
    "name": "Wait Social Sources",
    "type": "n8n-nodes-base.merge",
    "typeVersion": 3.2,
    "position": [1350, 1050],
    "parameters": {
        "mode": "append",
        "numberInputs": 6
    }
}

# Merge Social - Code node
merge_social_jscode = r"""// Combine 5 Brave social searches + LunarCrush into social context and build synthesis prompt
const items = $input.all();
let tokenData = null;
try { tokenData = $('Parse CoinGecko').first().json; } catch(e) {}
if (!tokenData || !tokenData.ticker) { try { tokenData = $('Parse DexScreener').first().json; } catch(e) {} }
if (!tokenData) { tokenData = $('Extract Input').item.json; }

const labels = ['GENERAL SOCIAL', 'PROJECT SOCIAL', 'SENTIMENT SIGNALS', 'KOL/ANALYST COVERAGE', 'NEWS & ANNOUNCEMENTS'];
const sections = [];

// Process 5 Brave social search results
for (let i = 0; i < 5; i++) {
  try {
    const r = items[i].json;
    const results = (r.web && r.web.results) ? r.web.results : [];
    const snippets = results.map((s, j) => '[' + (j+1) + '] ' + s.title + '\n' + s.description + '\nURL: ' + s.url).join('\n\n');
    sections.push('--- ' + labels[i] + ' ---\n' + (snippets || 'No results found'));
  } catch(e) {
    sections.push('--- ' + labels[i] + ' ---\nSearch failed: ' + e.message);
  }
}

// Process LunarCrush data (item index 5)
let lunarContext = 'LunarCrush data unavailable';
try {
  const lc = items[5].json;
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
} catch(e) { lunarContext = 'LunarCrush error: ' + e.message; }
sections.push('--- LUNARCRUSH METRICS ---\n' + lunarContext);

const social_context = sections.join('\n\n');
const d = tokenData;

const prompt = 'You are a crypto social intelligence analyst. Analyze social signals for this token using the REAL data provided below.\n\n'
  + '- Ticker: ' + d.ticker + '\n- Name: ' + d.name + '\n- Chain: ' + d.chain
  + '\n- Price: $' + d.price + '\n- Market Cap: $' + d.market_cap
  + '\n\nSOCIAL DATA:\n' + social_context
  + '\n\nUsing ONLY the data above, produce a structured analysis covering:\n'
  + '1. Discussion Quality (organic vs shills/bots ratio)\n'
  + '2. Signal-to-Noise Ratio estimate\n'
  + '3. Key Influencers/KOLs identified (with follower context if available)\n'
  + '4. Social Volume assessment (LunarCrush metrics + search result density)\n'
  + '5. Sentiment Analysis (bullish/bearish/neutral based on actual content)\n'
  + '6. Community Activity patterns\n'
  + '7. Narrative & Messaging themes found\n'
  + '8. Notable KOL Coverage (specific threads/posts)\n'
  + '9. Overall Social Health assessment\n\n'
  + 'Be specific and data-driven. Cite sources. If information is limited, explicitly state so rather than speculating.';

return [{ json: { requestBody: { model: 'anthropic/claude-sonnet-4-6', messages: [{ role: 'user', content: prompt }], max_tokens: 3000 } } }];"""

merge_social_node = {
    "id": "msoc2",
    "name": "Merge Social",
    "type": "n8n-nodes-base.code",
    "typeVersion": 2,
    "position": [1570, 1050],
    "parameters": {
        "jsCode": merge_social_jscode
    }
}

# Social Synthesis - OpenRouter HTTP Request
social_synth_node = {
    "id": "ssyn1",
    "name": "Social Synthesis",
    "type": "n8n-nodes-base.httpRequest",
    "typeVersion": 4.2,
    "position": [1790, 1050],
    "parameters": {
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "method": "POST",
        "authentication": "predefinedCredentialType",
        "nodeCredentialType": "httpHeaderAuth",
        "sendBody": True,
        "specifyBody": "json",
        "jsonBody": "={{ $json.requestBody }}",
        "options": {"timeout": 120000}
    },
    "credentials": {
        "httpHeaderAuth": {
            "id": "eKuUbdByJmAQfvxu",
            "name": "OpenRouter Header Auth"
        }
    },
    "retryOnFail": True,
    "maxTries": 2,
    "waitBetweenTries": 5000,
    "onError": "continueRegularOutput"
}

# ============================================================
# ADD ALL NEW NODES
# ============================================================
new_nodes = brave_nodes + [
    firecrawl_node,
    wait_fund_sources,
    merge_fund_node,
    fund_synth_node,
] + social_brave_nodes + [
    lunarcrush_node,
    wait_social_sources,
    merge_social_node,
    social_synth_node,
]

wf['nodes'].extend(new_nodes)

# ============================================================
# REBUILD CONNECTIONS
# ============================================================

# Update Parse CoinGecko connections - connect to all new upstream nodes
all_fund_names = [n["name"] for n in brave_nodes] + ["Firecrawl Solscan"]
all_social_names = [n["name"] for n in social_brave_nodes] + ["LunarCrush Social"]
all_targets = all_fund_names + all_social_names
wf['connections']['Parse CoinGecko'] = {
    "main": [
        [{"node": name, "type": "main", "index": 0} for name in all_targets]
    ]
}

# Update Parse DexScreener connections - same targets
wf['connections']['Parse DexScreener'] = {
    "main": [
        [{"node": name, "type": "main", "index": 0} for name in all_targets]
    ]
}

# Stage 1A: Brave nodes → Wait Fund Sources (each to different input index)
for i, node in enumerate(brave_nodes):
    wf['connections'][node["name"]] = {
        "main": [[{"node": "Wait Fund Sources", "type": "main", "index": i}]]
    }

# Firecrawl → Wait Fund Sources input 6
wf['connections']['Firecrawl Solscan'] = {
    "main": [[{"node": "Wait Fund Sources", "type": "main", "index": 6}]]
}

# Wait Fund Sources → Merge Fundamentals
wf['connections']['Wait Fund Sources'] = {
    "main": [[{"node": "Merge Fundamentals", "type": "main", "index": 0}]]
}

# Merge Fundamentals → Fundamentals Synthesis
wf['connections']['Merge Fundamentals'] = {
    "main": [[{"node": "Fundamentals Synthesis", "type": "main", "index": 0}]]
}

# Fundamentals Synthesis → Merge Research input 0
wf['connections']['Fundamentals Synthesis'] = {
    "main": [[{"node": "Merge Research", "type": "main", "index": 0}]]
}

# Stage 1B: 5 Brave Social nodes → Wait Social Sources (each to different input index)
for i, node in enumerate(social_brave_nodes):
    wf['connections'][node["name"]] = {
        "main": [[{"node": "Wait Social Sources", "type": "main", "index": i}]]
    }

# LunarCrush → Wait Social Sources input 5
wf['connections']['LunarCrush Social'] = {
    "main": [[{"node": "Wait Social Sources", "type": "main", "index": 5}]]
}

# Wait Social Sources → Merge Social
wf['connections']['Wait Social Sources'] = {
    "main": [[{"node": "Merge Social", "type": "main", "index": 0}]]
}

# Merge Social → Social Synthesis
wf['connections']['Merge Social'] = {
    "main": [[{"node": "Social Synthesis", "type": "main", "index": 0}]]
}

# Social Synthesis → Merge Research input 1
wf['connections']['Social Synthesis'] = {
    "main": [[{"node": "Merge Research", "type": "main", "index": 1}]]
}

# Remove old connection entries that reference removed nodes
# BUT skip names that are reused by new nodes
new_node_names = {n["name"] for n in new_nodes}
old_conn_keys_to_remove = []
for key in list(wf['connections'].keys()):
    if key in remove_names and key not in new_node_names:
        old_conn_keys_to_remove.append(key)
for key in old_conn_keys_to_remove:
    del wf['connections'][key]

# ============================================================
# WRITE OUTPUT
# ============================================================
output_path = '/Users/jtsomwaru/projects/n8n-agent/workflows/nash-satoshi-analysis.json'
with open(output_path, 'w') as f:
    json.dump(wf, f, indent=2)

print(f"Written {len(wf['nodes'])} nodes to {output_path}")
print(f"Removed nodes: {remove_names}")
print(f"Added {len(new_nodes)} new nodes")
print(f"Connection keys: {list(wf['connections'].keys())}")
