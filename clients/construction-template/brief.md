# Construction & Skilled Trades — n8n T2 Template Brief

## Purpose
Reusable T2 outreach template for NYC construction/HVAC/plumbing/electrical contractors.
This is NOT a custom build — it's a configurable template that can be demo'd to any
contractor prospect in ~2 hours with prospect-specific data swapped in.

## Target ICP
- NYC construction companies, GCs, HVAC/plumbing/electrical contractors
- 10–50 employees, $5M–$20M revenue
- Using ServiceTitan, Jobber, or manual scheduling (spreadsheets/WhatsApp)
- No Salesforce

## Core Pain to Solve
**Job progress coordination without a foreman phone call.**
Contractors waste 30–60 min/day calling foremen for status updates.
Clients constantly email asking "where are you with my job?"
Change orders create disputes because there's no paper trail.

## Template Workflow: Construction Job Progress Tracker

### What it does:
1. **Foreman daily update** — WhatsApp/SMS message or simple web form (Typeform/Tally)
   triggers the workflow. Foreman sends: job site, % complete, blockers, photo URL.
2. **AI enrichment** — Claude classifies status (on track / at risk / blocked),
   extracts key facts, generates a one-line client-ready summary.
3. **Client notification** — sends an email/SMS to the client with the summary +
   next expected milestone. No manual write-up by office staff.
4. **Google Sheets log** — appends to a running job log (job name, date, % complete,
   status, foreman note, client notified Y/N).
5. **Alert on block** — if status = "blocked", sends Slack/email to the owner/PM
   immediately with the blocker detail.

### Demo value prop:
"Your foreman sends one WhatsApp message. Your client gets a professional update.
You get an alert only when something's actually wrong. No more status calls."

### Configurable parameters (per prospect):
- Job site names / active project list
- Foreman contact method (WhatsApp webhook, SMS, Tally form)
- Client notification channel (email or SMS)
- Alert recipient (owner email/phone)
- Google Sheet ID for the job log

## Template name: construction-job-tracker
## Output location: ~/projects/n8n-agent/clients/construction-template/workflows/
## T2 config spec: ~/projects/n8n-agent/clients/construction-template/template-config.md
