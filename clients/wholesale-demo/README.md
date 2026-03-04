# AI Inventory Reorder & Supplier Notification

A production-quality n8n workflow demo for wholesale distribution companies.

## What This Workflow Does

When triggered (via webhook), Claude AI analyzes current inventory levels, identifies items below reorder thresholds, generates structured purchase orders, emails suppliers, notifies the ops team via Slack, and logs the PO to Google Sheets.

**Real AI analysis** — not just data routing. Claude evaluates urgency levels, calculates order quantities, and provides reasoning for each reorder decision.

## Trigger

**Webhook POST** to `/webhook/inventory-reorder`

Accepts JSON payload:
```json
{
  "trigger": "scheduled",      // "scheduled" | "manual"
  "triggered_by": "daily-9am", // identifier for the trigger source
  "date": "2026-03-04"         // date of the check
}
```

## Workflow Steps

1. **Webhook Trigger** — receives the trigger payload
2. **Load Inventory Data** — loads 15 SKUs with stock levels, thresholds, costs, and supplier info
3. **Build AI Prompt** — formats inventory into a table and constructs the Claude prompt
4. **Claude: Analyze Inventory** — calls OpenRouter API (Claude 3.5 Sonnet) to analyze inventory
5. **Parse AI Response** — extracts reorder items, groups by supplier, calculates totals
6. **Any Reorders Needed?** — branches: true path for reorders, false path for "all stock nominal"
7. **Format PO by Supplier** — generates professional purchase order text for each supplier
8. **Send Supplier Email** — sends PO email via Gmail
9. **Log PO to Sheets** — appends PO record to Google Sheets
10. **Slack: Ops Team Alert** — posts summary notification to Slack
11. **PO Complete — Summary** — returns final execution report

**Error Handling Flow:**
- Error Trigger → Log Error Details → Error Alert (Slack notification)

## Test Commands

### Test 1: Standard Daily Reorder Check
```bash
curl -s -X POST http://localhost:5678/webhook/inventory-reorder \
  -H "Content-Type: application/json" \
  -d '{"trigger": "scheduled", "triggered_by": "daily-9am", "date": "2026-03-04"}'
```

### Test 2: Manual Spot Check
```bash
curl -s -X POST http://localhost:5678/webhook/inventory-reorder \
  -H "Content-Type: application/json" \
  -d '{"trigger": "manual", "triggered_by": "ops-manager", "date": "2026-03-04"}'
```

## Expected Results

With the mock inventory data:
- **9 items** need reorder
- **4 critical** items (stock <25% of threshold)
- **5 suppliers** contacted
- Total PO value: ~$3,500-4,500 depending on AI calculation

### Items Needing Reorder
| SKU | Item | Stock | Threshold | Urgency |
|-----|------|-------|-----------|---------|
| SAF-001 | Hard Hats (Class E) | 12 | 25 | high |
| SAF-002 | Cut-Resistant Gloves (L) | 8 | 30 | high |
| SAF-004 | Safety Glasses (ANSI Z87) | 6 | 40 | critical |
| PKG-001 | Stretch Wrap Film (18") | 3 | 10 | high |
| PKG-003 | Corrugated Boxes (12x12x12) | 4 | 20 | critical |
| CLN-002 | Microfiber Mop Heads | 2 | 12 | critical |
| CLN-003 | Paper Towels (Case/30 rolls) | 8 | 8 | medium |
| PWR-002 | Reciprocating Saw Blades (10-pk) | 5 | 15 | high |
| ELC-001 | Wire Connectors (100-pk) | 1 | 20 | critical |

## Credentials Required

| Credential | Type | Purpose |
|------------|------|---------|
| Gmail account | gmailOAuth2 | Send PO emails to suppliers |
| Google Sheets account | googleSheetsOAuth2Api | Log PO records |
| OpenRouter API Key | Header auth | Claude AI analysis |
| Slack Webhook | URL | Ops team notifications |

## Files

- `workflow.json` — the complete n8n workflow
- `tests/test-data.json` — test payloads and expected results
- `demo-outputs/` — captured execution outputs

## Deployment

1. Import `workflow.json` into n8n (or deploy via API)
2. Verify credentials are connected
3. Activate the workflow
4. Run test command to verify

## Technical Notes

- Uses `$('NodeName').item.json.field` pattern to preserve data after Gmail/Sheets nodes
- IF node uses typeVersion 2.2 with conditions.options.version: 2
- Webhook uses responseMode: "onReceived" (not deprecated "immediately")
- All Code nodes have try/catch for JSON parsing
- HTTP Request nodes have retry settings (2 tries, 5s delay)
