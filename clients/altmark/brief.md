# Altmark Group — Build Brief

## Build Order
1. Insurance Expiration Tracking (quick win, no QB dependency)
2. Loan Management (top priority for Yair)
3. WhatsApp AI Bot (highest-frequency pain point)
4. Flagstar → QuickBooks Automation (saves 2 hours daily)
5. Cash Management & Overdraft Prevention
6. Rent Delinquency Outreach

## Use Case 1: Insurance Expiration Tracking
- Reads insurance spreadsheet (Google Sheets preferred, Excel on server as fallback)
- Runs daily at 7:00 AM Eastern
- Calculates days until expiration for each policy
- Sends personalized email alerts at 60, 30, 14, 7, and 0 days
- Sends OVERDUE alert for expired policies (days < 0)
- Logs alerts to "Insurance Alert Log" Google Sheet to prevent duplicates
- Sends daily summary to Yair
- AI Model: NONE — pure logic
- Known pitfall: Day 0 must be its own threshold ("EXPIRES TODAY"), not grouped with overdue

## Use Case 2: Loan Management
- Two separate workflows: Weekly Summary + Daily Alerts
- Weekly (Mondays 8am): reads Loan Master sheet, pulls balances from QB via Conductor, sends all data to Claude Sonnet for AI analysis, emails summary
- Daily (8am): reads Loan Master sheet, checks payment dates and covenant thresholds, sends alert emails
- Covenant math must handle BOTH types: "Minimum" (must stay ABOVE threshold, like DSCR) and "Maximum" (must stay BELOW threshold, like LTV). Loan Master sheet has a "Covenant Type" column.
- AI Model: Claude Sonnet for weekly analysis only
- Needs Conductor error handling on every QB call

## Use Case 3: WhatsApp AI Bot
- Twilio webhook receives WhatsApp messages
- Rate limiting via n8n Static Data (NOT Google Sheets — avoids latency and API quota burn)
- Step 1: Claude Haiku routes intent to data source (appfolio/quickbooks/insurance/unknown). Prompt should include instruction to normalize typos in names.
- Step 2: Query the appropriate data source. Use Fuse.js fuzzy search for tenant name lookups against CSV/sheet data.
- Step 3: Claude Sonnet generates answer from retrieved data
- Step 4: Send response back via Twilio API
- Step 5: Log to Bot Activity Log Google Sheet
- Fallback: if bot can't answer, send response to user AND notify Yair via separate WhatsApp message
- AI Models: Haiku for routing, Sonnet for answer generation

## Use Case 4: Flagstar → QuickBooks Automation
- Ingests daily Flagstar bank deposit report (PDF via email or watched folder)
- Claude Sonnet parses PDF into structured transaction JSON
- DO NOT use regex to strip numbers — it destroys check numbers and invoice IDs. The Claude prompt should instruct it to exclude account/routing numbers while preserving check/invoice reference numbers.
- Rule-based categorization for known transaction types (IF/Switch nodes)
- Claude Haiku categorizes unmatched transactions against chart of accounts
- Push to QuickBooks via Conductor API. Tag AI-categorized items with memo "AI-CATEGORIZED — REVIEW NEEDED"
- NEVER generate IIF import files — they can corrupt QuickBooks data
- Daily summary email to Yair showing rule-categorized count, AI-categorized count, and details of AI items
- Needs Conductor error handling on every QB call

## Use Case 5: Cash Management & Overdraft Prevention
- Runs daily at 7:00 AM Eastern
- Pulls bank balances from Plaid (use balances.available, NOT balances.current)
- Pulls uncleared checks from QuickBooks via Conductor
- CRITICAL — Double-count prevention: before subtracting each uncleared check, cross-reference against last 72 hours of Plaid transactions. If a check amount matches a recent Plaid transaction (exact amount, within 5 days), exclude it from the outstanding total — it already cleared at the bank but hasn't been reconciled in QB yet.
- Calculate: Available = Bank Available Balance - Verified Uncleared Checks
- If any account drops below its threshold, send urgent alert email with check-level detail
- Daily digest email with HTML table showing all accounts
- AI Model: NONE — pure logic and templating
- Needs Conductor error handling on every QB call

## Use Case 6: Rent Delinquency Outreach
- Gmail trigger watches for AppFolio report emails (filter by sender address and subject)
- Parse report (Claude Sonnet if PDF/HTML, direct parse if CSV)
- Calculate balance_ratio = accrued_balance / monthly_rent
- Filter to tenants where ratio >= 3
- Check Outreach Log Google Sheet — skip tenants contacted within last 30 days
- DRY RUN MODE for first 2 weeks: compile summary of who WOULD be contacted, email to Yair only
- Live mode: send outreach emails to tenants using client's template, log to Outreach Log, send summary to Yair
- AI Model: Sonnet for report parsing only (if needed)

## Global Rules for ALL Altmark Workflows
- Every Conductor API call MUST have error handling: IF node after HTTP Request, if non-200 or error → send email to Navid and Yair: "Automation Paused — QuickBooks may be in Single-User Mode or offline"
- Schedule triggers use America/New_York timezone
- All alert emails sent via Gmail SMTP
- All logs stored in Google Sheets
- No ensemble patterns — every AI call is single-model
