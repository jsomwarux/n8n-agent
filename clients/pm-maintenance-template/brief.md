# Property Management — n8n T2 Template Brief

## Purpose
Reusable T2 outreach template for NYC property management companies using AppFolio/Buildium.
Configurable per prospect in ~2 hours. Demonstrates automation on top of their existing PM software.

## Target ICP
- NYC property managers, co-op/condo management, residential portfolio managers
- 10–50 employees, managing 500–5000 units
- Using AppFolio, Buildium, or manual processes
- No Salesforce (those go to Agentforce/insurance pipeline)

## Core Pain to Solve
**Maintenance request triage eats staff time.**
PMs spend 40%+ of their day routing maintenance requests:
call tenant to clarify, call vendor to check availability, follow up when vendor no-shows,
update tenant on timeline. All manual. All reactive. All logged inconsistently.

## Template Workflow: Maintenance Request Triage & Auto-Routing

### What it does:
1. **Request intake** — triggered by email/webhook from AppFolio or a Tally/Typeform
   embedded on the PM's tenant portal. Captures: unit, issue type, urgency (tenant-stated),
   description, optional photo.
2. **AI triage** — Claude classifies: urgency (emergency / urgent / routine),
   category (plumbing / electrical / HVAC / structural / cosmetic),
   and drafts a vendor dispatch message.
3. **Vendor routing** — looks up the right vendor from a Google Sheet (vendor list by category).
   Sends the dispatch message via email or SMS. Logs the assignment.
4. **Tenant auto-update** — sends tenant a confirmation: "We've received your request.
   A [plumber/electrician/etc.] will contact you within [X hours/days]."
5. **Google Sheets log** — appends: unit, date, category, urgency, vendor assigned,
   tenant notified, expected resolution.
6. **No-show escalation** — if vendor hasn't marked resolved within SLA window (configurable),
   sends an alert to the PM office for manual follow-up.

### Demo value prop:
"Tenant submits a request. It gets classified, routed to the right vendor, and the tenant
gets a confirmation — without anyone in your office touching it. You only see it again
if the vendor no-shows."

### Configurable parameters (per prospect):
- Intake method (AppFolio webhook, email parser, Tally form URL)
- Vendor routing table (Google Sheet with vendor name, category, contact, SLA)
- Tenant notification channel (email or SMS)
- SLA windows by urgency tier (emergency: 2h, urgent: 24h, routine: 72h)
- Escalation recipient (PM office email/phone)
- Google Sheet ID for the request log

## Template name: pm-maintenance-triage
## Output location: ~/projects/n8n-agent/clients/pm-maintenance-template/workflows/
## T2 config spec: ~/projects/n8n-agent/clients/pm-maintenance-template/template-config.md
