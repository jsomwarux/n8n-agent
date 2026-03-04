# Construction & Skilled Trades — Job Completion Automation

**Client Demo for:** Opticfy — targeting ServiceTitan/Jobber shop owners  
**Industry:** Plumbing, HVAC, Electrical, General Contractors  
**Personas:** 5-30 employee service companies, $500K–$5M revenue  

## The Problem

Every completed job triggers 15-20 minutes of manual post-job work:
- Log the job in the tracker
- Send the customer an invoice
- Follow up with a review request
- Notify the team on Slack
- Flag high-value jobs for upsell opportunities

For a shop doing 50+ jobs/month, that's **12-16 hours/month** of admin work.

## The Solution

One webhook from ServiceTitan/Jobber → entire post-job sequence fires automatically.

## Workflow: Job Completion Automation

**n8n Workflow ID:** Hd0eJo1uRKb1JJHy  
**Webhook URL:** `http://localhost:5678/webhook/job-complete`  
**webhook.site URL:** https://webhook.site/1582945c-8636-40de-984e-55fa460c20fb

### Flow
1. **Webhook Trigger** — receives POST from ServiceTitan/Jobber
2. **Parse & Validate** — extracts fields, calculates total with 15% materials markup
3. **Build Invoice** — formats professional invoice with line items
4. **Emergency Check** — routes emergency jobs to URGENT: prefix path
5. **Send Invoice Email** — (mocked) sends invoice to customer
6. **Log Job** — appends to CSV tracker (simulates Google Sheets)
7. **Wait** — 6-second cooldown (2-min in production)
8. **Review Request** — (mocked) sends warm follow-up asking for Google review
9. **Upsell Check** — flags jobs > $500 for maintenance contract upsell
10. **Final Status** — logs all actions taken
11. **Slack Notification** — POSTs summary to webhook.site (real HTTP request)
12. **Error Handler** — catches failures, sends alert to webhook.site

### Test Scenarios

| Test | Type | Customer | Total | Emergency | Upsell |
|------|------|----------|-------|-----------|--------|
| 1 | Standard Plumbing | Maria Rodriguez | $290.63 | No | No |
| 2 | HVAC Installation | James Whitfield | $2,547.50 | No | Yes |
| 3 | Emergency Pipe Burst | Tony Marchetti | $624.75 | Yes | Yes |

### Quick Test Commands

```bash
# Test 1 — Standard Plumbing
curl -X POST http://localhost:5678/webhook/job-complete \
  -H "Content-Type: application/json" \
  -d '{"job_id":"JOB-2026-0847","customer_name":"Maria Rodriguez","customer_email":"m.rodriguez.test@mailinator.com","customer_phone":"347-555-0182","job_type":"Plumbing","technician_name":"Mike Ferrara","address":"2847 Grand Concourse, Bronx, NY 10468","job_description":"Replaced kitchen faucet and fixed P-trap leak under sink. Installed new shut-off valves.","labor_hours":2,"labor_rate":95,"materials_cost":87.50,"is_emergency":false,"completion_timestamp":"2026-03-04T14:30:00Z"}'

# Test 2 — HVAC Installation (triggers upsell)
curl -X POST http://localhost:5678/webhook/job-complete \
  -H "Content-Type: application/json" \
  -d '{"job_id":"JOB-2026-0848","customer_name":"James Whitfield","customer_email":"j.whitfield.test@mailinator.com","customer_phone":"718-555-0294","job_type":"HVAC","technician_name":"Carlos Reyes","address":"1104 Flatbush Ave, Brooklyn, NY 11226","job_description":"Full HVAC system replacement - removed old 2008 unit, installed new Carrier 3-ton split system, tested all zones.","labor_hours":8,"labor_rate":110,"materials_cost":1450,"is_emergency":false,"completion_timestamp":"2026-03-04T16:00:00Z"}'

# Test 3 — Emergency Pipe Burst (URGENT prefix + upsell)
curl -X POST http://localhost:5678/webhook/job-complete \
  -H "Content-Type: application/json" \
  -d '{"job_id":"JOB-2026-0849","customer_name":"Tony Marchetti","customer_email":"t.marchetti.test@mailinator.com","customer_phone":"212-555-0731","job_type":"Plumbing","technician_name":"Dave Kim","address":"540 W 43rd St, New York, NY 10036","job_description":"Emergency response - burst pipe in basement utility room. Shut off main, replaced 8ft section of 3/4-inch copper pipe, tested pressure.","labor_hours":3,"labor_rate":145,"materials_cost":165,"is_emergency":true,"completion_timestamp":"2026-03-04T09:15:00Z"}'
```

### Demo Outputs

Check `demo-outputs/` for real output from test runs:
- `invoice-email-*.txt` — what the customer invoice email would look like
- `review-request-*.txt` — what the review follow-up would look like
- `job-completion-log.csv` — what the Google Sheets tracker would contain
- `final-status-*.json` — workflow completion summary with all actions taken

### Viewing Live HTTP Requests

Open https://webhook.site/#!/1582945c-8636-40de-984e-55fa460c20fb to see real HTTP requests fire when the workflow runs. This shows the Slack notification payload in real-time during demos.

## File Structure

```
clients/construction-demo/
├── README.md              # This file
├── workflows/
│   └── job-completion-automation.json
├── tests/
│   └── test-data.json     # All 3 test scenarios
├── tasks/
│   └── todo.md
└── demo-outputs/          # Real output from test runs
    ├── invoice-email-JOB-2026-0847.txt
    ├── invoice-email-JOB-2026-0848.txt
    ├── invoice-email-JOB-2026-0849.txt
    ├── review-request-JOB-2026-0847.txt
    ├── review-request-JOB-2026-0848.txt
    ├── review-request-JOB-2026-0849.txt
    ├── job-completion-log.csv
    ├── final-status-JOB-2026-0847.json
    ├── final-status-JOB-2026-0848.json
    └── final-status-JOB-2026-0849.json
```
