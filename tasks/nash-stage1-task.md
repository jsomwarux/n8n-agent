Read tasks/lessons.md in full before starting. Apply all relevant lessons.

## Task: Rebuild Nash Satoshi Stage 1 — FINAL OPTIMAL SPEC

Workflow: `workflows/nash-satoshi-analysis.json`
Replace Stage 1 only. Do NOT touch Stage 2, 3, or 4.

Incoming data from "Parse Webhook" node:
ticker, name, chain, contract_address, price, market_cap, fdv, volume_24h, run_id, homepage_url (may be empty)

---

## STAGE 1A — FUNDAMENTALS

### Step 1: Build Scrape URLs (Code node: "Build Scrape URLs")
Runs once, outputs 4 items:
```js
const d = $("Parse Webhook").item.json;
const ticker = d.ticker;
const contract = d.contract_address;
const chain = (d.chain || "").toLowerCase();
const name = (d.name || "").toLowerCase().replace(/[^a-z0-9]/g, "");

const explorerUrl = (chain === "base" || chain === "ethereum" || chain === "eth")
  ? "https://etherscan.io/token/" + contract
  : "https://solscan.io/token/" + contract;

const homepage = d.homepage_url && d.homepage_url.length > 5
  ? d.homepage_url
  : "https://" + name + ".io";

return [
  { json: { url: "https://www.coingecko.com/en/coins/" + ticker.toLowerCase(), label: "coingecko" } },
  { json: { url: explorerUrl, label: "explorer" } },
  { json: { url: "https://dexscreener.com/search?q=" + contract, label: "dexscreener" } },
  { json: { url: homepage, label: "homepage" } }
];
```

### Step 2: Firecrawl Scrape (HTTP Request node: "Firecrawl Scrape")
Single node connected to Build Scrape URLs — runs 4 times.
POST https://api.firecrawl.dev/v1/scrape
Headers: Authorization: Bearer fc-0d0961fa920a466a869fdd4068b9fe7e | Content-Type: application/json
Body (JSON): { "url": "{{ $json.url }}", "formats": ["markdown"] }
After this node, add a Code node "Attach Label" that re-attaches the label from Build Scrape URLs:
```js
// Pair by index with Build Scrape URLs
const scraped = $input.all();
const urlItems = $("Build Scrape URLs").all();
return scraped.map((item, i) => ({
  json: {
    label: urlItems[i] ? urlItems[i].json.label : "unknown",
    markdown: item.json.data ? item.json.data.markdown : (item.json.markdown || "")
  }
}));
```

### Step 3: Brave Search (3 parallel HTTP Request nodes from Parse Webhook)

Node "Brave Team":
GET https://api.search.brave.com/res/v1/web/search
Params: q="{{ $("Parse Webhook").item.json.ticker }} {{ $("Parse Webhook").item.json.name }} team founder developer", count=5
Header: X-Subscription-Token: {{ $env.BRAVE_API_KEY }}

Node "Brave Fake":
GET https://api.search.brave.com/res/v1/web/search
Params: q="{{ $("Parse Webhook").item.json.ticker }} {{ $("Parse Webhook").item.json.name }} fake token scam imposter contract", count=5
Header: X-Subscription-Token: {{ $env.BRAVE_API_KEY }}

Node "Brave Catalysts":
GET https://api.search.brave.com/res/v1/web/search
Params: q="{{ $("Parse Webhook").item.json.ticker }} roadmap milestones catalysts 2026", count=5
Header: X-Subscription-Token: {{ $env.BRAVE_API_KEY }}

### Step 4: Merge Fundamentals (Code node)
Connect: Attach Label (4 items) + Brave Team + Brave Fake + Brave Catalysts
```js
const allItems = $input.all();
let ctx = "";

// Process firecrawl results (first 4 items have label field)
for (const item of allItems) {
  if (item.json.label) {
    const label = item.json.label.toUpperCase();
    const md = (item.json.markdown || "").substring(0, 2000);
    ctx += `\n=== ${label} ===\n${md}\n`;
  } else if (item.json.web) {
    // Brave result
    const results = (item.json.web.results || []).slice(0, 5);
    const section = results.map(r => r.title + ": " + r.description).join("\n");
    ctx += `\n=== BRAVE SEARCH ===\n${section}\n`;
  }
}

return [{ json: { fundamentals_context: ctx } }];
```

### Step 5: Fundamentals Synthesis (HTTP Request: "Fundamentals Synthesis")
POST https://api.anthropic.com/v1/messages
Headers:
  x-api-key: {{ $env.ANTHROPIC_API_KEY }}
  anthropic-version: 2023-06-01
  content-type: application/json
Body (build as JSON in n8n, use "Raw" body type):
{
  "model": "claude-sonnet-4-6",
  "max_tokens": 3000,
  "messages": [{
    "role": "user",
    "content": "You are analyzing a crypto token for investment scoring. Use ONLY the research data provided. Do not hallucinate.\n\nTOKEN: {{ $('Parse Webhook').item.json.ticker }} / {{ $('Parse Webhook').item.json.name }}\nCHAIN: {{ $('Parse Webhook').item.json.chain }}\nCONTRACT: {{ $('Parse Webhook').item.json.contract_address }}\nPRICE: {{ $('Parse Webhook').item.json.price }}\nMARKET CAP: {{ $('Parse Webhook').item.json.market_cap }}\nFDV: {{ $('Parse Webhook').item.json.fdv }}\n\nRESEARCH DATA:\n{{ $json.fundamentals_context }}\n\nProduce structured analysis:\n- Narrative Positioning & Market Thesis\n- Project Fundamentals (product, tech stack, stage)\n- Team & Backers (names, credibility)\n- Value Capture (token utility, fees, revenue model)\n- Traction & Usage (holders, volume, TVL)\n- Tokenomics & Unlocks (supply, vesting, whales)\n- Roadmap & Catalysts (upcoming milestones)\n- Competitive Analysis (comparable tokens)\n- WARNING: Fake Token Alert (flag any imposter contracts found)\n- Key Links\nInclude Confidence (High/Medium/Low) per section."
  }]
}
Extract output from: $json.content[0].text

---

## STAGE 1B — SOCIAL

### Step 1: Build X Queries (Code node)
```js
const d = $("Parse Webhook").item.json;
const ticker = d.ticker.replace(/[^a-zA-Z0-9]/g, "");
const name = d.name.replace(/[^a-zA-Z0-9 ]/g, "").trim();
return [
  { json: { query: ticker + " crypto", label: "general" } },
  { json: { query: "$" + ticker, label: "dollar" } },
  { json: { query: name + " token", label: "project" } },
  { json: { query: ticker + " bullish bearish aping sold", label: "sentiment" } },
  { json: { query: ticker + " " + name + " fake scam imposter", label: "fake" } }
];
```

### Step 2: X Search (Execute Command node: "X Search")
Single node, runs 5 times.
Command:
cd /Users/jtsomwaru/.openclaw/workspace/skills/x-research && source /Users/jtsomwaru/.config/env/global.env && bun run x-search.ts search "{{ $json.query }}" --quick --limit 10 2>&1

### Step 3: Merge Social (Code node)
```js
const items = $input.all();
const queryItems = $("Build X Queries").all();
const allTweets = [];
const sections = {};

for (let i = 0; i < items.length; i++) {
  const stdout = items[i].json.stdout || items[i].json.output || "";
  const label = queryItems[i] ? queryItems[i].json.label : "unknown";
  let tweets = [];
  try {
    tweets = JSON.parse(stdout);
  } catch(e) {
    const match = stdout.match(/\[[\s\S]*\]/);
    if (match) { try { tweets = JSON.parse(match[0]); } catch(e2) {} }
  }
  if (!Array.isArray(tweets)) tweets = [];
  sections[label] = tweets;
  tweets.forEach(t => allTweets.push(Object.assign({}, t, { _label: label })));
}

// Sort all tweets by engagement descending
allTweets.sort((a, b) => {
  const mA = a.public_metrics || {};
  const mB = b.public_metrics || {};
  const engA = (mA.like_count||0) + (mA.retweet_count||0) + (mA.reply_count||0);
  const engB = (mB.like_count||0) + (mB.retweet_count||0) + (mB.reply_count||0);
  return engB - engA;
});

let ctx = "TOP TWEETS BY ENGAGEMENT (KOL signal — sorted high to low):\n\n";
allTweets.slice(0, 20).forEach(t => {
  const m = t.public_metrics || {};
  const author = t.author_username || (t.author && t.author.username) || "unknown";
  ctx += "@" + author + " | Likes:" + (m.like_count||0) + " RT:" + (m.retweet_count||0) + " Replies:" + (m.reply_count||0) + "\n";
  ctx += '"' + (t.text||"").substring(0, 280) + '"\n\n';
});

const labels = ["general","dollar","project","sentiment","fake"];
for (const lbl of labels) {
  const tweets = sections[lbl] || [];
  ctx += "\n--- " + lbl.toUpperCase() + " (" + tweets.length + " tweets) ---\n";
  tweets.forEach(t => {
    const author = t.author_username || (t.author && t.author.username) || "unknown";
    ctx += "@" + author + ": " + (t.text||"").substring(0, 200) + "\n";
  });
}

return [{ json: { social_context: ctx } }];
```

### Step 4: Social Synthesis (HTTP Request: "Social Synthesis")
POST https://api.anthropic.com/v1/messages
Headers: x-api-key: {{ $env.ANTHROPIC_API_KEY }} | anthropic-version: 2023-06-01 | content-type: application/json
Body (raw JSON):
{
  "model": "claude-sonnet-4-6",
  "max_tokens": 3000,
  "messages": [{
    "role": "user",
    "content": "Analyze social signals for this crypto token. Use ONLY the tweet data provided. Identify KOLs from engagement metrics (high likes/retweets = high reach), NOT from keywords.\n\nTOKEN: {{ $('Parse Webhook').item.json.ticker }} / {{ $('Parse Webhook').item.json.name }}\n\nTWEET DATA:\n{{ $json.social_context }}\n\nProduce:\n- Discussion Quality (organic vs shills/bots ratio, signal-to-noise %)\n- Top Accounts by Reach (ranked by engagement as influence proxy, include counts)\n- Social Volume (total tweets, dominant direction)\n- Sentiment Breakdown (bullish/bearish/neutral % with evidence)\n- Community Activity & Tone\n- Key Opinion Leaders (high-engagement accounts, stance, specific claims)\n- Narrative & Ecosystem Fit\n- WARNING: Fake Token Alerts (flag tweets mentioning different contracts or scam warnings)\n- Overall Social Health\nInclude Confidence (High/Medium/Low) per section."
  }]
}
Extract: $json.content[0].text

---

## Stage 2/3/4 Claude node migration to Anthropic direct:
Find every HTTP Request node in Stage 2, 3, 4 that calls OpenRouter with a model starting with "anthropic/".
For each one:
1. Change URL to: https://api.anthropic.com/v1/messages
2. Remove OpenRouter Authorization header
3. Add headers: x-api-key: {{ $env.ANTHROPIC_API_KEY }} and anthropic-version: 2023-06-01
4. In the body, change model from "anthropic/claude-sonnet-4-6" to "claude-sonnet-4-6" and from "anthropic/claude-opus-4.6" to "claude-opus-4-6"
5. Change response extraction from $json.choices[0].message.content to $json.content[0].text
Keep GPT-5, Gemini, Grok nodes on OpenRouter unchanged.

---

## Import steps:
1. Get API key: sqlite3 ~/.n8n/database.sqlite "SELECT apiKey FROM user WHERE email='jsomwarux@yahoo.com'"
2. List workflows and find Nash Satoshi ID: curl -s http://localhost:5678/api/v1/workflows -H "X-N8N-API-KEY: KEY" | python3 -c "import sys,json; [print(w['id'],w['name']) for w in json.load(sys.stdin)['data']]"
3. Delete it: curl -s -X DELETE http://localhost:5678/api/v1/workflows/ID -H "X-N8N-API-KEY: KEY"
4. Import: curl -s -X POST http://localhost:5678/api/v1/workflows -H "X-N8N-API-KEY: KEY" -H "Content-Type: application/json" -d @workflows/nash-satoshi-analysis.json
5. Activate: curl -s -X PATCH http://localhost:5678/api/v1/workflows/NEWID/activate -H "X-N8N-API-KEY: KEY"
6. git add workflows/nash-satoshi-analysis.json && git commit -m "Stage 1 final: Firecrawl 4-page scrape + 3 Brave + 5 X searches engagement-sorted, Anthropic direct all Claude nodes" && git push origin main
7. Add lessons to tasks/lessons.md and commit

When completely done, output the summary: DONE - Nash Satoshi Stage 1 final build complete. New workflow ID: [id]. Commit: [hash].
