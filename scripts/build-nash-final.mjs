#!/usr/bin/env node
/**
 * Build Nash Satoshi Token Analysis workflow — FINAL OPTIMAL SPEC
 * Stage 1A: 4 Firecrawl scrapes (batch) + 3 Brave searches → Anthropic synthesis
 * Stage 1B: 5 X searches → Anthropic synthesis
 * Stage 2-4: Claude nodes on Anthropic direct, GPT/Gemini/Grok on OpenRouter
 */
import { writeFileSync } from 'fs';

const OUT = '/Users/jtsomwaru/projects/n8n-agent/workflows/nash-satoshi-analysis.json';

// ============= HELPERS =============

const conn = (node, index = 0) => ({ node, type: 'main', index });

function codeNode(id, name, position, jsCode) {
  return { id, name, type: 'n8n-nodes-base.code', typeVersion: 2, position, parameters: { jsCode } };
}

function anthropicHttp(id, name, position, jsonBodyExpr) {
  return {
    id, name, type: 'n8n-nodes-base.httpRequest', typeVersion: 4.2, position,
    parameters: {
      url: 'https://api.anthropic.com/v1/messages', method: 'POST', authentication: 'none',
      sendHeaders: true,
      headerParameters: { parameters: [
        { name: 'x-api-key', value: '={{ $env.ANTHROPIC_API_KEY }}' },
        { name: 'anthropic-version', value: '2023-06-01' },
        { name: 'content-type', value: 'application/json' }
      ] },
      sendBody: true, specifyBody: 'json', jsonBody: jsonBodyExpr,
      options: { timeout: 120000 }
    },
    retryOnFail: true, maxTries: 2, waitBetweenTries: 5000, onError: 'continueRegularOutput'
  };
}

function openRouterHttp(id, name, position, jsonBodyExpr) {
  return {
    id, name, type: 'n8n-nodes-base.httpRequest', typeVersion: 4.2, position,
    parameters: {
      url: 'https://openrouter.ai/api/v1/chat/completions', method: 'POST',
      authentication: 'predefinedCredentialType', nodeCredentialType: 'httpHeaderAuth',
      sendBody: true, specifyBody: 'json', jsonBody: jsonBodyExpr,
      options: { timeout: 120000 }
    },
    credentials: { httpHeaderAuth: { id: 'eKuUbdByJmAQfvxu', name: 'OpenRouter Header Auth' } },
    retryOnFail: true, maxTries: 2, waitBetweenTries: 5000, onError: 'continueRegularOutput'
  };
}

function braveSearch(id, name, position, queryExpr) {
  return {
    id, name, type: 'n8n-nodes-base.httpRequest', typeVersion: 4.2, position,
    parameters: {
      method: 'GET', url: 'https://api.search.brave.com/res/v1/web/search',
      authentication: 'none',
      sendHeaders: true,
      headerParameters: { parameters: [
        { name: 'Accept', value: 'application/json' },
        { name: 'X-Subscription-Token', value: '={{ $env.BRAVE_API_KEY }}' }
      ] },
      sendQuery: true, specifyQuery: 'keypair',
      queryParameters: { parameters: [
        { name: 'q', value: queryExpr },
        { name: 'count', value: '5' }
      ] },
      options: { timeout: 15000 }
    },
    retryOnFail: true, maxTries: 2, waitBetweenTries: 3000, onError: 'continueRegularOutput'
  };
}

function mergeAppend(id, name, position, numInputs) {
  return {
    id, name, type: 'n8n-nodes-base.merge', typeVersion: 3.2, position,
    parameters: { mode: 'append', numberInputs: numInputs }
  };
}

// ============= CODE STRINGS =============

const parseWebhookCode = [
  '// Extract and validate webhook input',
  'const items = $input.all();',
  'const body = items[0].json.body || items[0].json;',
  'const contract_address = (body.contract_address || "").trim();',
  'if (!contract_address) { throw new Error("Missing required field: contract_address"); }',
  'return [{ json: {',
  '  ticker: (body.ticker || "").trim(),',
  '  name: (body.name || "").trim(),',
  '  chain: (body.chain || "ethereum").toLowerCase().trim(),',
  '  contract_address: contract_address,',
  '  price: body.price || 0,',
  '  market_cap: body.market_cap || 0,',
  '  fdv: body.fdv || 0,',
  '  volume_24h: body.volume_24h || 0,',
  '  run_id: (body.run_id || "").trim(),',
  '  homepage_url: (body.homepage_url || "").trim(),',
  '  analysis_date: new Date().toISOString()',
  '} }];'
].join('\n');

const buildScrapeUrlsCode = [
  '// Build 4 scrape URLs for Firecrawl',
  'const d = $("Parse Webhook").item.json;',
  'const ticker = d.ticker;',
  'const contract = d.contract_address;',
  'const chain = (d.chain || "").toLowerCase();',
  'const name = (d.name || "").toLowerCase().replace(/[^a-z0-9]/g, "");',
  'const explorerUrl = (chain === "base" || chain === "ethereum" || chain === "eth")',
  '  ? "https://etherscan.io/token/" + contract',
  '  : "https://solscan.io/token/" + contract;',
  'const homepage = d.homepage_url && d.homepage_url.length > 5',
  '  ? d.homepage_url',
  '  : "https://" + name + ".io";',
  'return [',
  '  { json: { url: "https://www.coingecko.com/en/coins/" + ticker.toLowerCase(), label: "coingecko" } },',
  '  { json: { url: explorerUrl, label: "explorer" } },',
  '  { json: { url: "https://dexscreener.com/search?q=" + contract, label: "dexscreener" } },',
  '  { json: { url: homepage, label: "homepage" } }',
  '];'
].join('\n');

const attachLabelCode = [
  '// Pair Firecrawl results back with their labels by index',
  'const scraped = $input.all();',
  'const urlItems = $("Build Scrape URLs").all();',
  'return scraped.map((item, i) => ({',
  '  json: {',
  '    label: urlItems[i] ? urlItems[i].json.label : "unknown",',
  '    markdown: item.json.data ? item.json.data.markdown : (item.json.markdown || "")',
  '  }',
  '}));'
].join('\n');

const mergeFundamentalsCode = [
  '// Combine 4 Firecrawl + 3 Brave results and build Anthropic synthesis request',
  'const allItems = $input.all();',
  'const d = $("Parse Webhook").first().json;',
  'let ctx = "";',
  '// Items arrive: 4 firecrawl (with label field), then 3 brave (with web field)',
  'for (const item of allItems) {',
  '  if (item.json.label) {',
  '    const label = item.json.label.toUpperCase();',
  '    const md = (item.json.markdown || "").substring(0, 2000);',
  '    ctx += "\\n=== " + label + " ===\\n" + md + "\\n";',
  '  } else if (item.json.web) {',
  '    const results = (item.json.web.results || []).slice(0, 5);',
  '    const section = results.map(r => r.title + ": " + r.description).join("\\n");',
  '    ctx += "\\n=== BRAVE SEARCH ===\\n" + section + "\\n";',
  '  }',
  '}',
  'const prompt = "You are analyzing a crypto token for investment scoring. Use ONLY the research data provided. Do not hallucinate.\\n\\n"',
  '  + "TOKEN: " + d.ticker + " / " + d.name + "\\n"',
  '  + "CHAIN: " + d.chain + "\\n"',
  '  + "CONTRACT: " + d.contract_address + "\\n"',
  '  + "PRICE: " + d.price + "\\n"',
  '  + "MARKET CAP: " + d.market_cap + "\\n"',
  '  + "FDV: " + d.fdv + "\\n\\n"',
  '  + "RESEARCH DATA:\\n" + ctx + "\\n\\n"',
  '  + "Produce structured analysis:\\n"',
  '  + "- Narrative Positioning & Market Thesis\\n"',
  '  + "- Project Fundamentals (product, tech stack, stage)\\n"',
  '  + "- Team & Backers (names, credibility)\\n"',
  '  + "- Value Capture (token utility, fees, revenue model)\\n"',
  '  + "- Traction & Usage (holders, volume, TVL)\\n"',
  '  + "- Tokenomics & Unlocks (supply, vesting, whales)\\n"',
  '  + "- Roadmap & Catalysts (upcoming milestones)\\n"',
  '  + "- Competitive Analysis (comparable tokens)\\n"',
  '  + "- WARNING: Fake Token Alert (flag any imposter contracts found)\\n"',
  '  + "- Key Links\\n"',
  '  + "Include Confidence (High/Medium/Low) per section.";',
  'return [{ json: { requestBody: { model: "claude-sonnet-4-6", messages: [{ role: "user", content: prompt }], max_tokens: 3000 } } }];'
].join('\n');

const buildXQueriesCode = [
  '// Build 5 X search queries from token data',
  'const d = $("Parse Webhook").item.json;',
  'const ticker = d.ticker.replace(/[^a-zA-Z0-9]/g, "");',
  'const name = d.name.replace(/[^a-zA-Z0-9 ]/g, "").trim();',
  'return [',
  '  { json: { query: ticker + " crypto", label: "general" } },',
  '  { json: { query: "$" + ticker, label: "dollar" } },',
  '  { json: { query: name + " token", label: "project" } },',
  '  { json: { query: ticker + " bullish bearish aping sold", label: "sentiment" } },',
  '  { json: { query: ticker + " " + name + " fake scam imposter", label: "fake" } }',
  '];'
].join('\n');

const mergeSocialCode = [
  '// Combine 5 X search results with engagement sorting and build synthesis request',
  'const items = $input.all();',
  'const queryItems = $("Build X Queries").all();',
  'const d = $("Parse Webhook").first().json;',
  'const allTweets = [];',
  'const sections = {};',
  'for (let i = 0; i < items.length; i++) {',
  '  const stdout = items[i].json.stdout || items[i].json.output || "";',
  '  const label = queryItems[i] ? queryItems[i].json.label : "unknown";',
  '  let tweets = [];',
  '  try {',
  '    tweets = JSON.parse(stdout);',
  '  } catch(e) {',
  '    try {',
  '      const match = stdout.match(/\\[[\\s\\S]*\\]/);',
  '      if (match) { tweets = JSON.parse(match[0]); }',
  '    } catch(e2) {}',
  '  }',
  '  if (!Array.isArray(tweets)) tweets = [];',
  '  sections[label] = tweets;',
  '  tweets.forEach(t => allTweets.push(Object.assign({}, t, { _label: label })));',
  '}',
  '// Sort all tweets by engagement descending',
  'allTweets.sort((a, b) => {',
  '  const mA = a.public_metrics || {};',
  '  const mB = b.public_metrics || {};',
  '  const engA = (mA.like_count||0) + (mA.retweet_count||0) + (mA.reply_count||0);',
  '  const engB = (mB.like_count||0) + (mB.retweet_count||0) + (mB.reply_count||0);',
  '  return engB - engA;',
  '});',
  'let ctx = "TOP TWEETS BY ENGAGEMENT (KOL signal sorted high to low):\\n\\n";',
  'allTweets.slice(0, 20).forEach(t => {',
  '  const m = t.public_metrics || {};',
  '  const author = t.author_username || (t.author && t.author.username) || "unknown";',
  '  ctx += "@" + author + " | Likes:" + (m.like_count||0) + " RT:" + (m.retweet_count||0) + " Replies:" + (m.reply_count||0) + "\\n";',
  '  ctx += "\\"" + (t.text||"").substring(0, 280) + "\\"\\n\\n";',
  '});',
  'const labels = ["general","dollar","project","sentiment","fake"];',
  'for (const lbl of labels) {',
  '  const tweets = sections[lbl] || [];',
  '  ctx += "\\n--- " + lbl.toUpperCase() + " (" + tweets.length + " tweets) ---\\n";',
  '  tweets.forEach(t => {',
  '    const author = t.author_username || (t.author && t.author.username) || "unknown";',
  '    ctx += "@" + author + ": " + (t.text||"").substring(0, 200) + "\\n";',
  '  });',
  '}',
  'const prompt = "Analyze social signals for this crypto token. Use ONLY the tweet data provided. Identify KOLs from engagement metrics (high likes/retweets = high reach), NOT from keywords.\\n\\n"',
  '  + "TOKEN: " + d.ticker + " / " + d.name + "\\n\\n"',
  '  + "TWEET DATA:\\n" + ctx + "\\n\\n"',
  '  + "Produce:\\n"',
  '  + "- Discussion Quality (organic vs shills/bots ratio, signal-to-noise %)\\n"',
  '  + "- Top Accounts by Reach (ranked by engagement as influence proxy, include counts)\\n"',
  '  + "- Social Volume (total tweets, dominant direction)\\n"',
  '  + "- Sentiment Breakdown (bullish/bearish/neutral % with evidence)\\n"',
  '  + "- Community Activity & Tone\\n"',
  '  + "- Key Opinion Leaders (high-engagement accounts, stance, specific claims)\\n"',
  '  + "- Narrative & Ecosystem Fit\\n"',
  '  + "- WARNING: Fake Token Alerts (flag tweets mentioning different contracts or scam warnings)\\n"',
  '  + "- Overall Social Health\\n"',
  '  + "Include Confidence (High/Medium/Low) per section.";',
  'return [{ json: { requestBody: { model: "claude-sonnet-4-6", messages: [{ role: "user", content: prompt }], max_tokens: 3000 } } }];'
].join('\n');

// extractLLM helper used in multiple Stage 2/3/4 code nodes
const extractLLMHelper = [
  'function extractLLM(item) {',
  '  try { if (item.json.content && Array.isArray(item.json.content)) return item.json.content[0].text; } catch(e) {}',
  '  try { return item.json.choices[0].message.content; } catch(e) {}',
  '  return "Unavailable";',
  '}'
].join('\n');

const combineResearchCode = [
  '// Combine fundamentals + social synthesis outputs',
  extractLLMHelper,
  'const items = $input.all();',
  'const tokenData = $("Parse Webhook").first().json;',
  'let fund = "Unavailable", social = "Unavailable";',
  'try { fund = extractLLM(items[0]); } catch(e) {}',
  'try { social = extractLLM(items[1]); } catch(e) {}',
  'return [{ json: Object.assign({}, tokenData, { fundamentals_research: fund, social_research: social }) }];'
].join('\n');

const buildStage2BodiesCode = [
  '// Stage 2: 4-LLM analysis prompt (Apex Game Theorist)',
  'const d = $input.all()[0].json;',
  'const prompt = "You are the Apex Crypto Game Theorist...\\n\\n"',
  '  + "TOKEN: " + d.ticker + " (" + d.name + ")\\n"',
  '  + "Chain: " + d.chain + ", Price: $" + d.price + ", MCap: $" + d.market_cap + ", FDV: $" + d.fdv + "\\n"',
  '  + "Volume 24h: $" + d.volume_24h + "\\n\\n"',
  '  + "FUNDAMENTALS:\\n" + d.fundamentals_research + "\\n\\n"',
  '  + "SOCIAL:\\n" + d.social_research + "\\n\\n"',
  '  + "Output ALL fields in key: value format (one per line, no markdown).";',
  'const mk = (m) => ({ model: m, messages: [{ role: "user", content: prompt }], max_tokens: 4000 });',
  'return [{ json: {',
  '  gptBody: mk("openai/gpt-5"),',
  '  geminiBody: mk("google/gemini-3.1-pro-preview"),',
  '  claudeBody: mk("claude-sonnet-4-6"),',
  '  grokBody: mk("x-ai/grok-4")',
  '} }];'
].join('\n');

const buildStage3BodiesCode = [
  '// Stage 3: Deliberation - each model reviews own + 3 others',
  extractLLMHelper,
  'const items = $input.all();',
  'const names = ["GPT", "Gemini", "Claude", "Grok"];',
  'const ids = ["openai/gpt-5", "google/gemini-3.1-pro-preview", "claude-sonnet-4-6", "x-ai/grok-4"];',
  'const s2 = [];',
  'for (let i = 0; i < 4; i++) {',
  '  try { s2.push(extractLLM(items[i])); } catch(e) { s2.push("Unavailable"); }',
  '}',
  'const ticker = $("Parse Webhook").first().json.ticker || "";',
  'const bp = (mi) => {',
  '  const others = [0,1,2,3].filter(i => i !== mi).map(i => "--- " + names[i] + " ---\\n" + s2[i]).join("\\n");',
  '  return "Review your " + ticker + " analysis vs 3 others.\\nYOURS:\\n" + s2[mi] + "\\nOTHERS:\\n" + others + "\\nRevise if evidence warrants. Output key: value format.";',
  '};',
  'return [{ json: {',
  '  gptBody: { model: ids[0], messages: [{ role: "user", content: bp(0) }], max_tokens: 4000 },',
  '  geminiBody: { model: ids[1], messages: [{ role: "user", content: bp(1) }], max_tokens: 4000 },',
  '  claudeBody: { model: ids[2], messages: [{ role: "user", content: bp(2) }], max_tokens: 4000 },',
  '  grokBody: { model: ids[3], messages: [{ role: "user", content: bp(3) }], max_tokens: 4000 }',
  '} }];'
].join('\n');

const buildStage4BodyCode = [
  '// Stage 4: Consensus aggregation via Opus',
  extractLLMHelper,
  'const items = $input.all();',
  'const s3 = [];',
  'for (let i = 0; i < 4; i++) {',
  '  try { s3.push(extractLLM(items[i])); } catch(e) { s3.push("Unavailable"); }',
  '}',
  'const td = $("Parse Webhook").first().json;',
  'const prompt = "Final Consensus Aggregator for " + (td.ticker || "token") + ".\\n"',
  '  + "Price: $" + td.price + ", MCap: $" + td.market_cap + ", FDV: $" + td.fdv + "\\n\\n"',
  '  + "--- GPT ---\\n" + s3[0] + "\\n"',
  '  + "--- Gemini ---\\n" + s3[1] + "\\n"',
  '  + "--- Claude ---\\n" + s3[2] + "\\n"',
  '  + "--- Grok ---\\n" + s3[3] + "\\n\\n"',
  '  + "Aggregate: median scores, majority vote categories, synthesize thesis/catalysts/risks.\\n"',
  '  + "Consensus spread: <=10 HIGH, <=25 MIXED, <=40 LOW, >40 CONFLICTED.\\n"',
  '  + "Output key: value format. Include gpt_score, gemini_score, claude_score, grok_score.";',
  'return [{ json: { requestBody: { model: "claude-opus-4-6", messages: [{ role: "user", content: prompt }], max_tokens: 4000 } } }];'
].join('\n');

const formatResultCode = [
  '// Format result for Nash Satoshi webhook callback',
  'const run_id = $("Parse Webhook").item.json.run_id || "";',
  'const resp = $input.all()[0].json;',
  'let result = "";',
  'try {',
  '  if (resp.content && Array.isArray(resp.content)) { result = resp.content[0].text || ""; }',
  '  else if (resp.choices) { result = resp.choices[0].message.content || ""; }',
  '  else { result = JSON.stringify(resp); }',
  '} catch(e) { result = JSON.stringify(resp); }',
  'return [{ json: { webhookBody: { run_id: run_id, state: "DONE", outputs: { analysis_result: result } } } }];'
].join('\n');

const errorFormatCode = [
  '// Build failure webhook body',
  'let run_id = "";',
  'try { run_id = $("Parse Webhook").item.json.run_id || ""; } catch(e) { run_id = "unknown"; }',
  'return [{ json: { webhookBody: { run_id: run_id, state: "FAILED", outputs: {} } } }];'
].join('\n');

// ============= BUILD NODES =============

const pw = '$("Parse Webhook").item.json';

const nodes = [
  // --- Trigger + Input ---
  {
    id: 'wh1', name: 'Webhook Trigger', type: 'n8n-nodes-base.webhook', typeVersion: 2.1,
    position: [0, 300], webhookId: 'nash-satoshi-webhook',
    parameters: {
      httpMethod: 'POST', path: 'nash-satoshi-analysis', responseMode: 'onReceived',
      options: {
        responseCode: { values: { responseCode: 'customCode', customCode: 202 } },
        responseData: '{"status":"accepted","message":"Analysis queued"}'
      }
    }
  },

  codeNode('pw1', 'Parse Webhook', [250, 300], parseWebhookCode),

  // --- Stage 1A: Fundamentals ---
  codeNode('bsu1', 'Build Scrape URLs', [500, 200], buildScrapeUrlsCode),

  // Firecrawl Scrape — runs 4 times (one per Build Scrape URLs item)
  {
    id: 'fcs1', name: 'Firecrawl Scrape', type: 'n8n-nodes-base.httpRequest', typeVersion: 4.2,
    position: [750, 200],
    parameters: {
      method: 'POST', url: 'https://api.firecrawl.dev/v1/scrape', authentication: 'none',
      sendHeaders: true,
      headerParameters: { parameters: [
        { name: 'Authorization', value: 'Bearer fc-0d0961fa920a466a869fdd4068b9fe7e' },
        { name: 'Content-Type', value: 'application/json' }
      ] },
      sendBody: true, specifyBody: 'json',
      jsonBody: '={{ JSON.stringify({ url: $json.url, formats: ["markdown"] }) }}',
      options: { timeout: 30000 }
    },
    retryOnFail: true, maxTries: 2, waitBetweenTries: 5000, onError: 'continueRegularOutput'
  },

  codeNode('al1', 'Attach Label', [1000, 200], attachLabelCode),

  // 3 Brave searches — parallel from Parse Webhook
  braveSearch('bt1', 'Brave Team', [500, -200],
    `={{ ${pw}.ticker + " " + ${pw}.name + " team founder developer" }}`),

  braveSearch('bfk1', 'Brave Fake', [500, -400],
    `={{ ${pw}.ticker + " " + ${pw}.name + " fake token scam imposter contract" }}`),

  braveSearch('bct1', 'Brave Catalysts', [500, 0],
    `={{ ${pw}.ticker + " roadmap milestones catalysts 2026" }}`),

  // Wait for all 4 sources: Attach Label(0), Brave Team(1), Brave Fake(2), Brave Catalysts(3)
  mergeAppend('wfs1', 'Wait Fund Sources', [1250, 0], 4),

  codeNode('mf1', 'Merge Fundamentals', [1500, 0], mergeFundamentalsCode),

  anthropicHttp('fs1', 'Fundamentals Synthesis', [1750, 0], '={{ $json.requestBody }}'),

  // --- Stage 1B: Social ---
  codeNode('bxq1', 'Build X Queries', [500, 700], buildXQueriesCode),

  {
    id: 'xs1', name: 'X Search', type: 'n8n-nodes-base.executeCommand', typeVersion: 1,
    position: [750, 700],
    parameters: {
      command: '=cd /Users/jtsomwaru/.openclaw/workspace/skills/x-research && source /Users/jtsomwaru/.config/env/global.env && bun run x-search.ts search "{{ $json.query }}" --quick --limit 10 2>&1'
    },
    onError: 'continueRegularOutput'
  },

  codeNode('ms1', 'Merge Social', [1000, 700], mergeSocialCode),

  anthropicHttp('ss1', 'Social Synthesis', [1250, 700], '={{ $json.requestBody }}'),

  // --- Merge Research (bridge to Stage 2) ---
  mergeAppend('mr1', 'Merge Research', [2000, 300], 2),

  codeNode('cr1', 'Combine Research', [2250, 300], combineResearchCode),

  // --- Stage 2: 4-LLM Analysis ---
  codeNode('bs2', 'Build Stage2 Bodies', [2500, 300], buildStage2BodiesCode),

  openRouterHttp('gs2', 'GPT Stage2', [2750, -50], "={{ $('Build Stage2 Bodies').item.json.gptBody }}"),
  openRouterHttp('ges2', 'Gemini Stage2', [2750, 200], "={{ $('Build Stage2 Bodies').item.json.geminiBody }}"),
  anthropicHttp('cs2', 'Claude Stage2', [2750, 450], "={{ $('Build Stage2 Bodies').item.json.claudeBody }}"),
  openRouterHttp('grs2', 'Grok Stage2', [2750, 700], "={{ $('Build Stage2 Bodies').item.json.grokBody }}"),

  mergeAppend('ms2', 'Merge Stage2', [3000, 300], 4),

  // --- Stage 3: Deliberation ---
  codeNode('bs3', 'Build Stage3 Bodies', [3250, 300], buildStage3BodiesCode),

  openRouterHttp('gs3', 'GPT Stage3', [3500, -50], "={{ $('Build Stage3 Bodies').item.json.gptBody }}"),
  openRouterHttp('ges3', 'Gemini Stage3', [3500, 200], "={{ $('Build Stage3 Bodies').item.json.geminiBody }}"),
  anthropicHttp('cs3', 'Claude Stage3', [3500, 450], "={{ $('Build Stage3 Bodies').item.json.claudeBody }}"),
  openRouterHttp('grs3', 'Grok Stage3', [3500, 700], "={{ $('Build Stage3 Bodies').item.json.grokBody }}"),

  mergeAppend('ms3', 'Merge Stage3', [3750, 300], 4),

  // --- Stage 4: Consensus ---
  codeNode('bs4', 'Build Stage4 Body', [4000, 300], buildStage4BodyCode),

  anthropicHttp('s4a', 'Stage4 Aggregation', [4250, 300], '={{ $json.requestBody }}'),

  codeNode('fmr1', 'Format Result', [4500, 300], formatResultCode),

  {
    id: 'snd1', name: 'Send Result', type: 'n8n-nodes-base.httpRequest', typeVersion: 4.2,
    position: [4750, 300],
    parameters: {
      method: 'POST', url: 'https://nashsatoshi.com/api/webhook/gumloop', authentication: 'none',
      sendBody: true, specifyBody: 'json', jsonBody: '={{ $json.webhookBody }}',
      sendHeaders: true,
      headerParameters: { parameters: [{ name: 'Content-Type', value: 'application/json' }] },
      options: { timeout: 30000 }
    },
    retryOnFail: true, maxTries: 2, waitBetweenTries: 5000, onError: 'continueRegularOutput'
  },

  // --- Error Handling ---
  {
    id: 'et1', name: 'Error Trigger', type: 'n8n-nodes-base.errorTrigger', typeVersion: 1,
    position: [0, 1000], parameters: {}
  },

  codeNode('ef1', 'Error Format', [250, 1000], errorFormatCode),

  {
    id: 'sf1', name: 'Send Failure', type: 'n8n-nodes-base.httpRequest', typeVersion: 4.2,
    position: [500, 1000],
    parameters: {
      method: 'POST', url: 'https://nashsatoshi.com/api/webhook/gumloop', authentication: 'none',
      sendBody: true, specifyBody: 'json', jsonBody: '={{ $json.webhookBody }}',
      sendHeaders: true,
      headerParameters: { parameters: [{ name: 'Content-Type', value: 'application/json' }] },
      options: { timeout: 30000 }
    },
    retryOnFail: true, maxTries: 2, waitBetweenTries: 5000
  }
];

// ============= CONNECTIONS =============

const connections = {
  'Webhook Trigger': { main: [[conn('Parse Webhook')]] },

  'Parse Webhook': { main: [[
    conn('Build Scrape URLs'),
    conn('Brave Team'),
    conn('Brave Fake'),
    conn('Brave Catalysts'),
    conn('Build X Queries')
  ]] },

  // Stage 1A: Fundamentals
  'Build Scrape URLs': { main: [[conn('Firecrawl Scrape')]] },
  'Firecrawl Scrape': { main: [[conn('Attach Label')]] },
  'Attach Label': { main: [[conn('Wait Fund Sources', 0)]] },
  'Brave Team': { main: [[conn('Wait Fund Sources', 1)]] },
  'Brave Fake': { main: [[conn('Wait Fund Sources', 2)]] },
  'Brave Catalysts': { main: [[conn('Wait Fund Sources', 3)]] },
  'Wait Fund Sources': { main: [[conn('Merge Fundamentals')]] },
  'Merge Fundamentals': { main: [[conn('Fundamentals Synthesis')]] },
  'Fundamentals Synthesis': { main: [[conn('Merge Research', 0)]] },

  // Stage 1B: Social
  'Build X Queries': { main: [[conn('X Search')]] },
  'X Search': { main: [[conn('Merge Social')]] },
  'Merge Social': { main: [[conn('Social Synthesis')]] },
  'Social Synthesis': { main: [[conn('Merge Research', 1)]] },

  // Stage 2
  'Merge Research': { main: [[conn('Combine Research')]] },
  'Combine Research': { main: [[conn('Build Stage2 Bodies')]] },
  'Build Stage2 Bodies': { main: [[
    conn('GPT Stage2'), conn('Gemini Stage2'), conn('Claude Stage2'), conn('Grok Stage2')
  ]] },
  'GPT Stage2': { main: [[conn('Merge Stage2', 0)]] },
  'Gemini Stage2': { main: [[conn('Merge Stage2', 1)]] },
  'Claude Stage2': { main: [[conn('Merge Stage2', 2)]] },
  'Grok Stage2': { main: [[conn('Merge Stage2', 3)]] },

  // Stage 3
  'Merge Stage2': { main: [[conn('Build Stage3 Bodies')]] },
  'Build Stage3 Bodies': { main: [[
    conn('GPT Stage3'), conn('Gemini Stage3'), conn('Claude Stage3'), conn('Grok Stage3')
  ]] },
  'GPT Stage3': { main: [[conn('Merge Stage3', 0)]] },
  'Gemini Stage3': { main: [[conn('Merge Stage3', 1)]] },
  'Claude Stage3': { main: [[conn('Merge Stage3', 2)]] },
  'Grok Stage3': { main: [[conn('Merge Stage3', 3)]] },

  // Stage 4
  'Merge Stage3': { main: [[conn('Build Stage4 Body')]] },
  'Build Stage4 Body': { main: [[conn('Stage4 Aggregation')]] },
  'Stage4 Aggregation': { main: [[conn('Format Result')]] },
  'Format Result': { main: [[conn('Send Result')]] },

  // Error handling
  'Error Trigger': { main: [[conn('Error Format')]] },
  'Error Format': { main: [[conn('Send Failure')]] }
};

// ============= OUTPUT =============

const workflow = {
  name: 'Nash Satoshi Token Analysis',
  nodes,
  connections,
  settings: { executionOrder: 'v1', callerPolicy: 'workflowsFromSameOwner' }
};

writeFileSync(OUT, JSON.stringify(workflow, null, 2));
console.log(`Wrote ${nodes.length} nodes to ${OUT}`);
