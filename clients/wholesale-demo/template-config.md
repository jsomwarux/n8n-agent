# Wholesale Inventory Reorder — T2 Template Config

## What Changes Per Prospect

**Only one node needs to change:** `load-inventory` (node id: `load-inventory`, "Load Inventory Data")
**Specifically:** the `inventory` array inside the `jsCode` parameter

Everything else — AI analysis logic, PO formatting, Gmail send, Sheets logging, Slack notification — is fully generic and works on any inventory array.

---

## Config Map

| Field | Source | Notes |
|---|---|---|
| `sku` | Research agent or Eve-generated | Use `[CATEGORY_ABBREV]-001` pattern (e.g. `PIPE-001`) if real SKUs unavailable |
| `name` | Prospect's website / catalog / LinkedIn posts | Use actual product names — this is what makes it feel custom |
| `category` | Grouped from product lines | 2–4 categories max, keep consistent |
| `current_stock` | **Mock — set intentionally** | Set 3–4 items BELOW threshold so demo triggers reorders |
| `reorder_threshold` | **Mock — estimate** | Consumables: 20–40. Equipment/tools: 8–15. Hardware: 15–25 |
| `max_stock` | **Mock — estimate** | 3–4× the threshold |
| `unit_cost` | Research agent or industry estimate | Round numbers fine. Focus on accuracy for high-value items |
| `supplier` | Research agent (LinkedIn, website, distributor listings) | Real supplier names if findable. Plausible invented names OK |
| `supplier_email` | **Always use demo pattern** | `jtsomwaru+[slug]+supplier[N]@gmail.com` — routes all demo PO emails to JT |

---

## SKU Count and Supplier Grouping

- **Total SKUs:** 8–12 items per prospect
- **Suppliers:** 2–4 suppliers, 2–4 SKUs each
- **Reorder triggers:** Set exactly 4–5 items with `current_stock` below `reorder_threshold` so the demo produces a meaningful alert
- **At least 1 critical item:** Set one item with stock at 10–25% of threshold to demonstrate urgency detection

---

## Supplier Email Pattern

```
jtsomwaru+[slug]+supplier1@gmail.com
jtsomwaru+[slug]+supplier2@gmail.com
jtsomwaru+[slug]+supplier3@gmail.com
```

All PO emails land in JT's Gmail inbox under the prospect's tag. No emails go to real suppliers.

---

## What Stays Unchanged (Do Not Touch)

- All nodes except `load-inventory`
- Google Sheets doc ID (`1i-kSUmO0jCOZ1pJyNUV_NITseZTWzWoxR0maN1MDeaU`) — use the shared demo sheet
- Gmail credential ID (`r3IbVQkW0d0j3icY`) — already connected
- Google Sheets credential ID (`QeZOA9lJuS7gGgES`) — already connected
- OpenRouter API key in the Claude HTTP node — already working
- Slack webhook URL — already configured

---

## Step-by-Step: How n8n-Agent Runs a T2 Config

1. **Read** `~/projects/jt-consulting-pipeline/clients/[slug]/brief.json` — pull `company`, product categories, any supplier names from research
2. **Read** `~/projects/n8n-agent/clients/wholesale-demo/workflow.json` — this is the base template
3. **Replace** the `inventory` array in the `load-inventory` node's `jsCode` with prospect-specific data (8–12 SKUs following the config map above)
4. **Update** the workflow `name` field to: `[Company Name] — Inventory Reorder`
5. **Write** modified workflow to `~/projects/jt-consulting-pipeline/clients/[slug]/workflow.json`
6. **Import** into local n8n via n8n-mcp
7. **Run** the workflow via webhook test trigger
8. **Capture** outputs → write `demo-results.json` (minimum 3 test runs: normal check, critical alert, no-reorder-needed)
9. **Flag** the "wow case" in demo-results.json notes — usually the critical item catch with PO auto-generated

---

## Identifying Prospect SKUs (for Research Agent)

Research agent should look for:
- Website product catalog or category pages
- LinkedIn posts mentioning specific products or materials
- Job postings (often mention product lines handled)
- Industry supplier directories
- Google: `"[Company Name]" products OR catalog OR "we carry"`

If specific SKUs are unavailable, use plausible niche-specific product names.
For a plumbing wholesale distributor: copper pipe fittings, gate valves, PVC couplings, press-fit connectors.
For an HVAC wholesale distributor: air handlers, thermostats, refrigerant, duct tape, flex duct.

---

## Output Naming

- Workflow name in n8n: `[Company Name] — Inventory Reorder`
- workflow.json path: `~/projects/jt-consulting-pipeline/clients/[slug]/workflow.json`
- Mark in brief.json: `"tier": 2, "template_used": "wholesale-inventory-reorder", "jt_review_required": true`
