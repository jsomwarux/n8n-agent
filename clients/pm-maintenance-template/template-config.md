# PM Maintenance Triage — T2 Template Config

## What Changes Per Prospect

Unlike the wholesale template (single node swap), this template has **parameterized placeholders** spread across multiple nodes. All placeholders use `{{PLACEHOLDER}}` format inside Code node strings and `={{PLACEHOLDER}}` in n8n expression fields.

---

## Config Map

| Placeholder | Where It Appears | What To Set |
|---|---|---|
| `VENDOR_SHEET_ID` | Vendor Lookup node → `documentId.value` | Google Sheet ID containing the prospect's vendor routing table |
| `LOG_SHEET_ID` | Log to Google Sheets node → `documentId.value` | Google Sheet ID for the maintenance request log |
| `GOOGLE_SHEETS_CREDENTIAL_ID` | Vendor Lookup + Log to Google Sheets → `credentials.googleSheetsOAuth2Api.id` | n8n credential ID for Google Sheets OAuth |
| `SMTP_CREDENTIAL_ID` | Email Vendor + Email Tenant → `credentials.smtp.id` | n8n credential ID for SMTP (or swap nodes to Gmail) |
| `PM_FROM_EMAIL` | Email Vendor + Email Tenant → `fromEmail` | Prospect's maintenance email (e.g. `maintenance@acmepm.com`) |
| `PM_ALERT_WEBHOOK_URL` | PM Office Emergency Alert → `url` | Slack webhook URL or other alert endpoint for emergency notifications |
| `PM_OFFICE_PHONE` | Prep Dispatch Data → `jsCode` (tenant email body) | PM office phone number for emergency fallback |
| `COMPANY_NAME` | Prep Dispatch Data → `jsCode` (email signatures) | Prospect's company name |
| `FALLBACK_VENDOR_EMAIL` | Prep Dispatch Data → `jsCode` | Fallback email if vendor lookup returns no match |
| `EMERGENCY_SLA_HOURS` | Prep Dispatch Data → `jsCode` (slaWindows object) | Emergency SLA window (default: `2`) |
| `URGENT_SLA_HOURS` | Prep Dispatch Data → `jsCode` (slaWindows object) | Urgent SLA window (default: `24`) |
| `ROUTINE_SLA_HOURS` | Prep Dispatch Data → `jsCode` (slaWindows object) | Routine SLA window (default: `72`) |

---

## Vendor Sheet Structure

The Vendor Lookup node reads from a Google Sheet with tab name **"Vendors"** and these columns:

| Column | Example |
|---|---|
| Vendor Name | ABC Plumbing Corp |
| Category | plumbing |
| Email | jtsomwaru+prospect+vendor1@gmail.com |
| Phone | (212) 555-0101 |
| SLA Response | 2 hours |
| Notes | Licensed, insured, 24/7 emergency |

**Categories must match AI output exactly:** `plumbing`, `electrical`, `hvac`, `structural`, `cosmetic`

Populate with 5-8 vendors covering all 5 categories. At minimum: 1 plumber, 1 electrician, 1 HVAC tech.

---

## Log Sheet Structure

The Log to Google Sheets node appends to a tab named **"Maintenance Log"** with these headers:

| Ticket ID | Date | Unit | Tenant | Description | Category | Urgency | Vendor | Vendor Email | SLA Window | Status | Tenant Notified |

Create this tab with the header row before first run.

---

## Step-by-Step: How n8n-Agent Configures Per Prospect

1. **Read** `~/projects/jt-consulting-pipeline/clients/[slug]/brief.json` — pull company name, any vendor info
2. **Read** `~/projects/n8n-agent/clients/pm-maintenance-template/workflows/pm-maintenance-triage.json` — base template
3. **Find-and-replace** all `{{PLACEHOLDER}}` values in Code node `jsCode` strings with prospect-specific data
4. **Replace** `={{PLACEHOLDER}}` values in node parameters (sheet IDs, credential IDs, URLs, emails)
5. **Update** workflow `name` to: `[Company Name] — Maintenance Triage`
6. **Create** a Google Sheet with two tabs: "Vendors" (populated with prospect vendors) and "Maintenance Log" (header row only)
7. **Write** modified workflow to `~/projects/jt-consulting-pipeline/clients/[slug]/workflow.json`
8. **Import** into local n8n via n8n-mcp
9. **Run** 3 test cases via webhook: routine plumbing, urgent HVAC, emergency flooding
10. **Capture** outputs → write `demo-results.json`

---

## Vendor Email Pattern (Demo)

```
jtsomwaru+[slug]+plumber@gmail.com
jtsomwaru+[slug]+electrician@gmail.com
jtsomwaru+[slug]+hvac@gmail.com
jtsomwaru+[slug]+structural@gmail.com
jtsomwaru+[slug]+cosmetic@gmail.com
```

All dispatch emails land in JT's Gmail. No emails go to real vendors during demo.

---

## What Stays Unchanged (Do Not Touch)

- AI Triage prompt and Claude API call structure
- Normalize Request logic (handles AppFolio, Tally, Typeform)
- Parse AI Response logic
- IF node emergency routing logic
- Prep Sheets Log node (maps to standard header row)
- Build Response node (webhook response format)
- Error Trigger + Log Error nodes

---

## Swapping Email Provider

The template uses **SMTP Send Email** nodes. To swap to Gmail:
1. Change node type from `n8n-nodes-base.emailSend` to `n8n-nodes-base.gmail`
2. Update credential reference to Gmail OAuth
3. Map `toEmail` → `sendTo`, `message` → `message`, `subject` → `subject`
4. Remove `fromEmail` (Gmail uses the authenticated account)

---

## Output Naming

- Workflow name in n8n: `[Company Name] — Maintenance Triage`
- workflow.json path: `~/projects/jt-consulting-pipeline/clients/[slug]/workflow.json`
- Mark in brief.json: `"tier": 2, "template_used": "pm-maintenance-triage", "jt_review_required": true`
