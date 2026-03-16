# AI Multi-Channel Support Triage — n8n Demo

**Purpose:** Demonstrates AI-powered customer support ticket triage with intelligent routing, VIP detection, and automated responses.

## What It Does

1. **Multi-Channel Intake** — Accepts tickets via webhook (simulates email, chat, web form, social)
2. **AI Classification** — Claude analyzes sentiment, urgency, category, churn risk in one pass
3. **Smart Routing** — Routes to appropriate team based on priority + VIP status
4. **Automated Actions:**
   - Escalation alerts to Slack for CRITICAL/URGENT/VIP
   - Agent notification emails with full context
   - Auto-response emails to customers (standard path)
   - Full audit trail to Google Sheets

## Workflow Architecture

```
Webhook → Normalize → Build Prompt → Claude AI → Parse Result → IF (Urgent/VIP?)
                                                                    │
                    ┌───────────────────────────────────────────────┼───────────────────────────────────────────────┐
                    │ TRUE (Escalation Path)                        │ FALSE (Standard Path)                         │
                    ▼                                               ▼                                               │
              Prep Escalation                                 Prep Standard                                         │
                    │                                               │                                               │
                    ▼                                               ▼                                               │
           Slack: Escalation Alert                        Slack: Standard Digest                                    │
                    │                                               │                                               │
                    ▼                                               ▼                                               │
         Email: Agent Notification                         Email: Auto-Response                                     │
                    │                                               │                                               │
                    ▼                                               ▼                                               │
          Prep Sheets (Urgent)                            Prep Sheets (Standard)                                    │
                    │                                               │                                               │
                    ▼                                               ▼                                               │
             Log to Sheets                               Log to Sheets (Standard)                                   │
                    │                                               │                                               │
                    ▼                                               ▼                                               │
        Ticket Summary (Urgent)                         Ticket Summary (Standard)                                   │
                    │                                               │                                               │
                    └───────────────────────────────────────────────┴───────────────────────────────────────────────┘
```

## Priority Rules

| Priority | Triggers | SLA |
|----------|----------|-----|
| CRITICAL | Cancellation threat, complete outage, data loss, payment failure on large account | 1 hour |
| URGENT | VIP customer any issue, billing error >$500, security concern, significant business impact | 2 hours |
| HIGH | Partial degradation, billing questions, account changes | 4 hours |
| STANDARD | General questions, feature requests, minor bugs | 8-24 hours |
| LOW | Compliments, feedback, non-urgent feature requests | 48 hours |

## VIP Detection

Customer is flagged as VIP if any of these are true:
- `account_value > $10,000/yr`
- `customer_tier === "enterprise"`
- `customer_tier === "platinum"`

VIP customers ALWAYS route through the escalation path, regardless of issue priority.

## Integrations

| Service | Purpose | Credential Required |
|---------|---------|---------------------|
| OpenRouter (Claude 3.5 Sonnet) | AI classification & response drafting | API key in workflow |
| Slack | Real-time alerts (webhook) | Webhook URL in workflow |
| Gmail | Agent notifications + customer auto-responses | OAuth2 credential |
| Google Sheets | Audit trail / ticket log | OAuth2 credential |

## Deployment

### Prerequisites

1. n8n running (local or cloud)
2. Gmail OAuth2 credential configured in n8n
3. Google Sheets OAuth2 credential configured in n8n
4. Google Sheet with "Support Log" tab containing headers:
   ```
   Date | Ticket ID | Channel | Customer | Tier | Subject | Priority | Category | Sentiment | Churn Risk | Assigned Team | SLA Hours | VIP | Tags | Reasoning | Processed At
   ```

### Import Workflow

1. Open n8n
2. Go to Settings → Import from File
3. Select `workflow.json`
4. Activate the workflow

### Test

Use the curl commands from `tests/test-data.json`:

```bash
# Test CRITICAL ticket
curl -X POST http://localhost:5678/webhook/support-ticket \
  -H 'Content-Type: application/json' \
  -d '{
    "ticket_id": "TKT-2026-4401",
    "channel": "email",
    "customer_name": "Diane Mercer",
    "customer_email": "jtsomwaru+diane.mercer@gmail.com",
    "customer_tier": "enterprise",
    "account_value": "$48,000/yr",
    "subject": "Completely unacceptable — cancelling our contract",
    "message": "This is the THIRD time this month...",
    "prior_tickets_30d": 3
  }'
```

## Input Schema

```json
{
  "ticket_id": "string (optional, auto-generated if missing)",
  "channel": "email | live_chat | web_form | social | phone",
  "customer_name": "string",
  "customer_email": "string",
  "customer_tier": "starter | professional | enterprise | platinum",
  "account_value": "string (e.g., '$6,200/yr')",
  "subject": "string",
  "message": "string (full ticket body)",
  "prior_tickets_30d": "number"
}
```

## Output (Webhook Response)

```json
{
  "status": "escalated | queued",
  "ticket_id": "TKT-2026-4401",
  "customer": "Diane Mercer",
  "priority": "CRITICAL",
  "category": "cancellation_risk",
  "assigned_team": "retention_team",
  "sla_hours": 1,
  "churn_risk": "high",
  "vip": true,
  "actions_taken": [
    "Slack escalation alert sent",
    "Agent notification email sent",
    "Logged to Support Log sheet"
  ],
  "processed_at": "2026-03-04T21:58:00.000Z"
}
```

## Files

- `workflow.json` — n8n workflow definition (import this)
- `tests/test-data.json` — Test scenarios with expected routing + curl commands
- `README.md` — This file

## Demo Value Proposition

**For the prospect:** Shows exactly how their support queue transforms:
- Manual triage (15-20 min/ticket) → Instant AI classification
- Missed VIP escalations → Automatic VIP detection & routing
- Inconsistent first responses → AI-drafted, personalized replies
- No audit trail → Complete logging with sentiment + churn risk

**ROI example:** 200 tickets/day × 15 min saved × $25/hr = $1,250/day in agent efficiency gains.

---

*Built by Opticfy — AI implementation for operations teams.*
