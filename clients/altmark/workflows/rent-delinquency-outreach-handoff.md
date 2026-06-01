# Altmark — Rent Delinquency Outreach — Handoff & Setup

Built offline (not deployed). Two importable workflows are in this folder:

| File | Purpose |
|---|---|
| `rent-delinquency-outreach.json` | The full workflow (25 nodes), **DRY_RUN, inactive**. |
| `rent-delinquency-step3-verifier.json` | Throwaway isolation test for Step 3 — Manual Trigger → Read File → Parse Excel → Step 3. No Gmail, no Sheets, no sends. |

## What it does
When AppFolio emails the "They Owe Us Money" delinquency report (Excel attachment), the workflow parses it, identifies tenants owing ≥2× their monthly rent, and sends escalating outreach (Initial → Follow-Up after 14d → Final after 7d → flagged for personal outreach after 7 more days). It honors a Do-Not-Contact list, a manual-contact override, and a cooldown between stages, logs every action to Google Sheets, and emails Yair + Matt a daily summary. **AI: none** — the Excel is parsed natively.

## Step 3 parsing — VERIFIED
The critical entity-association step was validated against the real `delinquency-20260519.xlsx` using SheetJS (the exact library n8n's Spreadsheet File node uses), and again against the exact code in the saved artifact:

- **112 tenant rows** output (24 entity headers consumed, 18 subtotals + 1 grand total skipped).
- **0** rows missing `_entity_name` / `_property_address`; **0** leftover entity-header/subtotal rows.
- First = `Sparkz Iron Works Corp` @ `122 Bruckner Development LLC`; last = `Thaler, Sarah` @ `MPM 67 LLC`.

Key config that makes this work: **Spreadsheet File → `range = "10"`** (0-indexed, so row 11 becomes the header), `headerRow = true`, `includeEmptyCells = true`. (`range = "11"` is wrong — off-by-one makes row 12 the header and breaks parsing.)

### How to verify Step 3 yourself in the UI
1. Confirm the test file is at `C:\n8n\test-data\delinquency-20260519.xlsx` on the Beelink.
2. Import `rent-delinquency-step3-verifier.json`.
3. Click **Execute Workflow**.
4. Click the **Parse Excel** node output → 155 rows. Click **Step 3 - Entity Association** output → **112 items**, each with `_entity_name` and `_property_address`. No entity-header or subtotal rows present.
5. Delete the verifier workflow when satisfied.

## If it fired right now (activation side-effects)
Current config: `DRY_RUN = true`, `BATCH_LIMIT = 5`, Gmail Trigger watches subject **"[TEST] Delinquency Report"**.

With the full May 19 report (112 tenants, **38 meet the 2× threshold**): 38 > BATCH_LIMIT(5) → the workflow **stops before sending any outreach** and sends **exactly one** batch-limit alert email to **jtsomwaru@gmail.com**. Zero tenant emails, zero CC to Yair/Matt, no summary, no outreach-log writes.

If instead a trimmed report with ≤5 qualifying tenants arrived: each qualifying tenant would get an Initial/Follow-Up/Final notice — but because `DRY_RUN = true`, **every email is redirected to jtsomwaru@gmail.com with CC emptied**, plus a `[TEST MODE]` summary to jtsomwaru@gmail.com, plus outreach-log rows tagged `source: "test"`. **No real tenant is ever contacted while DRY_RUN is true.**

Additional guard: the trigger only matches "[TEST] Delinquency Report", so a real AppFolio report (different subject) will not even start the workflow.

## Beelink n8n version constraint — IMPORTANT
The Beelink runs **n8n 2.18.4**. Any node typeVersion above what 2.18.4 ships with shows "Install this node to use it" on import. This build now targets 2.18.4-safe versions throughout (gmailTrigger **1.2**, gmail 2.2, googleSheets 4.7, if 2.3, code 2, spreadsheetFile 2, readWriteFile 1, noOp 1, errorTrigger 1). The Gmail Trigger is the historical offender — never use 1.4 here.

## Gmail Trigger config (source of truth — matches JT's manually-rebuilt node)
- **Credential**: `Altmark Insurance Gmail` (gmailOAuth2)
- **Poll Times**: Every Minute
- **Event**: Message Received
- **Simplify**: **OFF** (raw Gmail message + binary attachment flow through)
- **Filters → Search (q)**: `subject:"[TEST] Delinquency Report" has:attachment`
- **Options**: Download Attachments **ON** (attachments land in binary property `attachment_0`)

Why `has:attachment`: the workflow only fires when the AppFolio xlsx is actually attached — no false triggers, no no-binary items reaching Parse Excel. Gmail tokenizes punctuation, so `[TEST]` matches the word "TEST" rather than literal brackets; acceptable for testing.

Downstream code is compatible with Simplify=OFF:
- `Process & Decide` reads `$('Gmail Trigger').first().json.id` — `id` is at the top level of the raw Gmail API message resource (same path as simplified mode).
- `Parse Excel` reads `binaryPropertyName: "attachment_0"` — matches the default attachment prefix.

## Setup before it can run end-to-end
1. **Import** `rent-delinquency-outreach.json` (stays inactive). Credentials and the Sheets doc id are pre-wired to your real Beelink values, so on this instance everything should auto-link.
2. **Create 3 Google Sheets tabs** in your Rent Delinquency Tracking sheet (`1YoE91mQSxP2yGaYPIWZtDILhULjPXIXIGyxxazKvqoo`), headers in row 1:
   - **Rent Delinquency Outreach Log**: `tenant_name, entity_name, property_address, unit, monthly_rent, accrued_balance, balance_ratio, escalation_stage, date_sent, source, manual_contact`
   - **Delinquency Report Processing Log**: `email_message_id, date_processed, tenants_in_report, emails_sent`
   - **Delinquency Do Not Contact**: `tenant_name, unit, reason, added_by, date_added`
   The **Read COI Alert Log** node already points at the existing COI dashboard spreadsheet (`17ZHh…`, tab "COI Alert Log") — nothing to do for that one.
3. **Set the workflow's own Error Workflow to itself** (Workflow Settings → Error Workflow → this workflow) so the Error Trigger catches failures.
4. Run the verifier first; then send yourself a test email "[TEST] Delinquency Report" with the May 19 xlsx attached and have Yair review the `[TEST MODE]` summary before any go-live.

## Go-live (only after Yair approves — three SEPARATE edits)
1. **Gmail Trigger filter**: replace `subject:"[TEST] Delinquency Report" has:attachment` with a Sender filter (dedicated Sender field, or `from:<appfolio-sender>` in the Search query) plus `has:attachment`. Remove the [TEST] subject gate.
2. Set `DRY_RUN = false` in the **Safety Flags** node.
3. Raise `BATCH_LIMIT` in **Safety Flags** to the expected volume.

## Open questions / assumptions (flag for Yair)
- **Email templates are DRAFT placeholders** (playbook says "build with placeholders for now"). Final Initial/Follow-Up/Final copy still needed.
- **Sending address & reply-to**: currently sends from the Altmark Insurance Gmail credential. Yair still owes the dedicated rent-delinquency sending address + reply-to confirmation.
- **AppFolio sender + real subject**: needed for the go-live filter swap.
- **Cooldown reconciliation**: the playbook mentions both a "30-day cooldown" and a staged 14d/7d/7d cadence. These conflict (14 < 30), so this build uses the **staged cadence** as authoritative (Step 10) and labels the skip section "recently contacted (cooldown not elapsed)". Confirm this is the intended behavior.
- **Processing-log timing**: this build appends the processing-log row at the end of the run (with counts) rather than pre-logging at the start. Dedupe still works; on a mid-run crash a retry could reprocess (harmless under DRY_RUN). Flag if you want strict pre-logging.
- **Batch behavior on full report**: 38 tenants qualify, so the first real run will hit the batch limit and only send an alert. To exercise actual dry-run sends + summary, send a trimmed test file with ≤5 qualifying tenants.

## Credentials referenced (already linked on the Beelink)
- **gmailOAuth2** → `Altmark Insurance Gmail` (id `pk48J92vFO9rAOWe`) — trigger + 4 send nodes.
- **googleSheetsOAuth2Api** → `Google Sheets Credential 1` (id `IBe8J2kDvrYhaQIv`) — 4 read + 2 append nodes.
