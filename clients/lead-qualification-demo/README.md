# AI Lead Qualification & CRM Entry — Property Management

A production-ready n8n workflow that uses Claude AI to qualify inbound leads for property management companies. Hot leads get fast-tracked to HubSpot + personalized email + Slack alert. Warm/cold leads get nurture sequences.

## What This Workflow Does

1. **Receives lead data** via webhook from website form
2. **Sends to Claude AI** for intelligent scoring (1-10 scale)
3. **Routes based on score:**
   - **Hot leads (7+):** HubSpot CRM entry → Personalized email → Slack alert → Sheets log
   - **Warm/Cold leads (<7):** Nurture email → Sheets log
4. **Logs everything** to Google Sheets for tracking
5. **Error handling** with Slack alerts on failures

## Workflow Architecture

```
┌─────────────────┐
│ Webhook: Lead   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Parse Lead Data │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Build Prompt    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Claude: Score   │──────────────────────────────┐
└────────┬────────┘                              │
         │                                       │
         ▼                                       │
┌─────────────────┐                              │
│ Parse AI Score  │                              │
└────────┬────────┘                              │
         │                                       │
         ▼                                       │
    ┌────────┐                                   │
    │Score≥7?│                                   │
    └───┬────┘                                   │
   YES  │  NO                                    │
   ┌────┴────┐                                   │
   │         │                                   │
   ▼         ▼                                   │
┌──────┐  ┌──────────┐                           │
│HubSpt│  │Nurture   │                           │
└──┬───┘  │Email     │                           │
   │      └────┬─────┘                           │
   ▼           │                                 │
┌──────┐       │                                 │
│Hot   │       ▼                                 │
│Email │  ┌──────────┐                           │
└──┬───┘  │Log Nurture│                          │
   │      │to Sheets  │                          │
   ▼      └───────────┘                          │
┌──────┐                                         │
│Slack │                                         │
│Alert │     ┌────────────────────────────┐      │
└──┬───┘     │ Error Trigger → Log → Slack│◀─────┘
   │         └────────────────────────────┘
   ▼
┌──────────┐
│Log Hot   │
│to Sheets │
└────┬─────┘
     │
     ▼
┌──────────┐
│Final     │
│Summary   │
└──────────┘
```

## Prerequisites

### 1. n8n Instance
- n8n running at `http://localhost:5678`
- Admin access to import workflows

### 2. Required Credentials

| Service | Credential Name | How to Get |
|---------|-----------------|------------|
| Gmail | `Gmail account` | n8n OAuth2 flow with Google Cloud Console |
| Google Sheets | `Google Sheets account` | n8n OAuth2 flow with Google Cloud Console |
| OpenRouter | (hardcoded) | Already configured with API key |
| HubSpot | Manual replacement | Get API key from HubSpot Settings → Integrations → Private Apps |
| Slack | (hardcoded webhook) | Already configured |

### 3. Google Sheets Setup

1. Open the sheet: https://docs.google.com/spreadsheets/d/1i-kSUmO0jCOZ1pJyNUV_NITseZTWzWoxR0maN1MDeaU
2. Create a tab named **"Lead Log"** (if it doesn't exist)
3. Add these column headers in row 1:
   ```
   Date | First Name | Last Name | Email | Company | Portfolio Size | Monthly Budget | Score | Tier | Urgency | Key Signal | Action Taken | HubSpot Created
   ```

### 4. HubSpot Setup (Required for Hot Leads)

1. Go to HubSpot Settings → Integrations → Private Apps
2. Create a new private app with these scopes:
   - `crm.objects.contacts.write`
   - `crm.objects.contacts.read`
3. Copy the API key
4. In `workflow.json`, find `HUBSPOT_API_KEY_PLACEHOLDER` and replace with your key

**Custom Properties (Optional):**
- Create custom contact properties `lead_score` (number) and `lead_tier` (dropdown) in HubSpot for full functionality

## Deployment

### Step 1: Import Workflow

```bash
# Using n8n CLI
n8n import:workflow --input=workflow.json

# Or via API
curl -X POST http://localhost:5678/api/v1/workflows \
  -H "Content-Type: application/json" \
  -d @workflow.json
```

### Step 2: Activate Workflow

After importing, activate the workflow in the n8n UI or via API:

```bash
curl -X PATCH http://localhost:5678/api/v1/workflows/{WORKFLOW_ID} \
  -H "Content-Type: application/json" \
  -d '{"active": true}'
```

### Step 3: Test the Webhook

The webhook URL will be:
```
http://localhost:5678/webhook/new-lead
```

## Testing

### Test Hot Lead (Sarah Chen - Expected Score: 8-10)

```bash
curl -X POST http://localhost:5678/webhook/new-lead \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Sarah",
    "last_name": "Chen",
    "email": "jtsomwaru+sarah.chen@gmail.com",
    "phone": "212-555-0147",
    "company": "Chen Property Group",
    "portfolio_size": 28,
    "monthly_budget": 4500,
    "primary_need": "AI-powered tenant screening and lease management automation",
    "timeline": "Ready to start within 2 weeks",
    "current_pain": "Manually reviewing 50+ applications per month. Losing good tenants to faster landlords.",
    "property_type": "Residential multifamily",
    "location": "Brooklyn, NY",
    "heard_about_us": "LinkedIn post"
  }'
```

**Expected:** HubSpot contact created, personalized email sent, Slack alert posted, logged to Sheets.

### Test Warm Lead (Marcus Reeves - Expected Score: 5-7)

```bash
curl -X POST http://localhost:5678/webhook/new-lead \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Marcus",
    "last_name": "Reeves",
    "email": "jtsomwaru+marcus.reeves@gmail.com",
    "phone": "718-555-0203",
    "company": "Reeves Holdings LLC",
    "portfolio_size": 9,
    "monthly_budget": 1800,
    "primary_need": "Maintenance request tracking and vendor coordination",
    "timeline": "Exploring options for Q2",
    "current_pain": "Spreadsheets are getting unmanageable with 9 units.",
    "property_type": "Mixed residential/commercial",
    "location": "Queens, NY",
    "heard_about_us": "Google search"
  }'
```

**Expected:** Nurture email sent, logged to Sheets. No HubSpot/Slack.

### Test Cold Lead (Tom Nguyen - Expected Score: 1-4)

```bash
curl -X POST http://localhost:5678/webhook/new-lead \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Tom",
    "last_name": "Nguyen",
    "email": "jtsomwaru+tom.nguyen@gmail.com",
    "phone": "347-555-0088",
    "company": "Self-managed",
    "portfolio_size": 2,
    "monthly_budget": 500,
    "primary_need": "Just curious about AI tools",
    "timeline": "No specific timeline",
    "current_pain": "Managing my 2 units myself, wondering if AI can help.",
    "property_type": "Residential",
    "location": "Bronx, NY",
    "heard_about_us": "Friend referral"
  }'
```

**Expected:** Nurture email sent, logged to Sheets. No HubSpot/Slack.

## Scoring Rubric

| Criterion | Points | Hot Signal |
|-----------|--------|------------|
| Budget $2,000+/mo | 0-3 | Strong budget fit |
| Portfolio 10+ units | 0-2 | Scale for AI ROI |
| Immediate timeline | 0-2 | Ready to buy |
| AI/tenant screening need | 0-2 | Perfect service match |
| Company + specific pain | 0-1 | Decision maker |
| **Total** | **0-10** | |

**Tier Mapping:**
- **Hot (8-10):** Fast-track sales engagement
- **Warm (5-7):** Nurture sequence
- **Cold (1-4):** Low-touch nurture

## Troubleshooting

### Webhook Not Responding
1. Check workflow is active in n8n UI
2. Verify webhook path is `/webhook/new-lead`
3. Check n8n logs: `docker logs n8n` or server logs

### Claude API Errors
1. Check OpenRouter API key is valid
2. Verify rate limits haven't been exceeded
3. Check response format in Parse AI Score node

### HubSpot Contact Creation Fails
1. Verify API key is correctly replaced
2. Check required scopes are enabled
3. Verify custom properties exist (or remove from payload)

### Gmail Not Sending
1. Re-authenticate Gmail OAuth in n8n credentials
2. Check Google Cloud Console app permissions
3. Verify sender email has appropriate quotas

### Google Sheets Not Logging
1. Verify "Lead Log" tab exists in the spreadsheet
2. Check column headers match expected names
3. Re-authenticate if OAuth expired

## Files

```
lead-qualification-demo/
├── workflow.json           # Complete n8n workflow (16 nodes)
├── tests/
│   └── test-data.json      # Test payloads with curl commands
└── README.md               # This file
```

## Credentials Summary

| Credential | Status | Notes |
|------------|--------|-------|
| Gmail OAuth | Pre-configured | ID: `r3IbVQkW0d0j3icY` |
| Google Sheets OAuth | Pre-configured | ID: `QeZOA9lJuS7gGgES` |
| OpenRouter API | Hardcoded | In Claude HTTP Request node |
| Slack Webhook | Hardcoded | In Slack Alert nodes |
| HubSpot API | **NEEDS REPLACEMENT** | Replace `HUBSPOT_API_KEY_PLACEHOLDER` |

## Demo Value Proposition

This workflow demonstrates:
- **AI-powered business decisions** — Claude doesn't just route data, it makes nuanced qualification decisions
- **Real-time CRM integration** — Hot leads instantly appear in HubSpot
- **Personalized outreach** — Emails reference specific prospect details and AI-identified hooks
- **Full audit trail** — Every lead logged with AI reasoning and actions taken
- **Error resilience** — Graceful handling with Slack alerts on failures

Perfect for property management companies processing 50-500 leads/month who want to ensure hot leads never slip through the cracks.
