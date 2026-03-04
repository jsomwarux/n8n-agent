# AI Insurance Claims Triage & Document Extraction — Demo

An n8n workflow demonstrating AI-powered insurance claims processing with intelligent triage, specialist routing, and full audit trail.

## What It Does

1. **Receives** new claim submissions via webhook
2. **Extracts** structured data from unstructured claim descriptions using Claude AI
3. **Triages** claims by priority (CRITICAL/HIGH/STANDARD/LOW) based on loss amount, injury indicators, fraud flags
4. **Routes** HIGH/CRITICAL claims to the appropriate specialist with full context
5. **Notifies** via Slack (ops alerts) and Gmail (adjuster briefs + claimant acknowledgments)
6. **Logs** every claim decision to Google Sheets with AI reasoning

## Business Value

- **Time saved**: 30–45 min → ~10 seconds per claim
- **Consistency**: AI applies the same triage rules to every claim
- **Audit trail**: Complete log of every decision with reasoning
- **SLA tracking**: Auto-calculated deadlines based on priority

---

## Setup

### Prerequisites

- n8n instance running (local or cloud)
- Gmail OAuth2 credential configured
- Google Sheets OAuth2 credential configured
- Slack webhook URL (already embedded in workflow)
- OpenRouter API key (already embedded in workflow)

### Import Workflow

1. Open n8n
2. Go to **Workflows** → **Import from File**
3. Select `workflow.json`
4. Click **Import**

### Verify Credentials

The workflow references these credentials (IDs must match your n8n instance):

| Credential | ID | Name |
|-----------|-----|------|
| Gmail OAuth2 | `r3IbVQkW0d0j3icY` | Gmail account |
| Google Sheets OAuth2 | `QeZOA9lJuS7gGgES` | Google Sheets account |

If your credential IDs differ, update them in:
- `Email: Adjuster Notification` node
- `Email: Claimant Acknowledgment` node
- `Log to Sheets (High)` node
- `Log to Sheets (Standard)` node

### Prepare Google Sheet

Create a Google Sheet with ID `1i-kSUmO0jCOZ1pJyNUV_NITseZTWzWoxR0maN1MDeaU` (or update the workflow with your sheet ID).

Add a tab named **Claims Log** with these columns:

| Date | Claim ID | Claimant | Claim Type | Priority | Est. Loss | SLA Hours | Assigned To | Queue | Red Flags | Confidence | Reasoning | Processed At |
|------|----------|----------|------------|----------|-----------|-----------|-------------|-------|-----------|------------|-----------|--------------|

### Activate Workflow

1. Open the imported workflow
2. Toggle **Active** to ON
3. Note your webhook URL: `https://your-n8n-instance/webhook/new-claim`

---

## Testing

### Test Data

See `tests/test-data.json` for 3 pre-built test scenarios:

| Test | Priority | Scenario |
|------|----------|----------|
| Test 1 | CRITICAL | Commercial warehouse fire with fraud flags, $1.85M loss |
| Test 2 | HIGH | Workers comp injury, surgery required, OSHA involved |
| Test 3 | STANDARD | Residential water damage, straightforward claim |

### Run Test 1 (CRITICAL)

```bash
curl -X POST http://localhost:5678/webhook/new-claim \
  -H 'Content-Type: application/json' \
  -d '{
    "claim_id": "CLM-2026-0847",
    "policy_number": "POL-COM-88821",
    "claimant_name": "Riverfront Properties LLC",
    "claimant_email": "jtsomwaru+riverfront@gmail.com",
    "date_of_loss": "2026-03-03",
    "claim_type": "commercial_property",
    "description": "Total loss of warehouse facility at 4400 Commerce Blvd following reported electrical fire. Building contained high-value electronics inventory. Claimant states fire suppression system was non-operational at time of loss. Third-party witness reports seeing claimant on premises 2 hours prior to fire with unknown individuals. Prior claim filed 18 months ago for similar loss at adjacent property under different LLC name.",
    "estimated_loss": "$1,850,000",
    "location": "Newark, NJ",
    "policy_type": "commercial_property"
  }'
```

**Expected behavior:**
- Priority: CRITICAL
- Specialist: Victor Chen (Fraud Investigator)
- Slack: 🚨 urgent alert with red flags
- Email: Adjuster notification sent
- Sheets: Row logged with full analysis

### Run Test 3 (STANDARD)

```bash
curl -X POST http://localhost:5678/webhook/new-claim \
  -H 'Content-Type: application/json' \
  -d '{
    "claim_id": "CLM-2026-0849",
    "policy_number": "POL-HOM-77634",
    "claimant_name": "James Whitfield",
    "claimant_email": "jtsomwaru+james.whitfield@gmail.com",
    "date_of_loss": "2026-03-01",
    "claim_type": "homeowners",
    "description": "Water damage to finished basement following burst pipe in utility room. Damage includes flooring (approx 800 sq ft), drywall, and personal property. Plumber already repaired the pipe. Photos provided.",
    "estimated_loss": "$18,500",
    "location": "Paramus, NJ",
    "policy_type": "homeowners"
  }'
```

**Expected behavior:**
- Priority: STANDARD
- Queue: Standard Processing
- Slack: 📋 routine alert
- Email: Claimant acknowledgment sent
- Sheets: Row logged

---

## Node Architecture

```
Webhook: New Claim
  └── Normalize Claim Input
      └── Build Extraction Prompt
          └── Claude: Extract & Triage
              └── Parse Triage Result
                  └── High Priority? (IF)
                      ├── [TRUE] Assign Specialist
                      │   └── Send Urgent Alert (Slack)
                      │       └── Email: Adjuster Notification
                      │           └── Log to Sheets (High)
                      │               └── Claim Summary (High)
                      │
                      └── [FALSE] Standard Queue
                          └── Send Routine Alert (Slack)
                              └── Email: Claimant Acknowledgment
                                  └── Log to Sheets (Standard)
                                      └── Claim Summary (Standard)

Error Trigger
  └── Log Error Details
      └── Error Alert (Slack)
```

## Specialist Routing

| Specialist | Email | Queue |
|------------|-------|-------|
| Marcus Webb | jtsomwaru+marcus.webb@gmail.com | Property Claims |
| Diana Torres | jtsomwaru+diana.torres@gmail.com | Liability |
| Kevin Park | jtsomwaru+kevin.park@gmail.com | Auto Claims |
| Sandra Mills | jtsomwaru+sandra.mills@gmail.com | Workers Comp |
| Victor Chen | jtsomwaru+victor.chen@gmail.com | SIU — Fraud |
| Patricia Okafor | jtsomwaru+patricia.okafor@gmail.com | Senior Review |

---

## API Reference

### Webhook Endpoint

**POST** `/webhook/new-claim`

#### Request Body

```json
{
  "claim_id": "string (optional, auto-generated if missing)",
  "policy_number": "string",
  "claimant_name": "string",
  "claimant_email": "string",
  "date_of_loss": "YYYY-MM-DD",
  "claim_type": "string (e.g., homeowners, commercial_property, workers_compensation)",
  "description": "string — full claim narrative",
  "estimated_loss": "string (e.g., $18,500)",
  "location": "string",
  "policy_type": "string (optional)"
}
```

#### Response

```json
{
  "status": "processed",
  "claim_id": "CLM-2026-0849",
  "priority": "STANDARD",
  "claim_category": "property_damage",
  "claimant_name": "James Whitfield",
  "estimated_loss": "$18,500",
  "assigned_to": "Standard Queue",
  "queue": "Standard Processing",
  "sla_hours": 24,
  "confidence": 0.92,
  "reasoning": "Straightforward residential water damage claim...",
  "processing_timestamp": "2026-03-04T21:38:00.000Z",
  "message": "Claim #CLM-2026-0849 triaged as STANDARD. Queued for standard processing. SLA: 24 hours."
}
```

---

## Cost Estimate

- **Claude 3.5 Sonnet via OpenRouter**: ~$0.003 per claim (1K tokens)
- **At 100 claims/day**: ~$9/month
- **At 500 claims/day**: ~$45/month

---

## Files

```
insurance-claims-demo/
├── workflow.json          # n8n workflow (import this)
├── README.md              # This file
└── tests/
    └── test-data.json     # 3 test scenarios with curl commands
```

---

## Customization

### Change Priority Thresholds

Edit the prompt in the **Build Extraction Prompt** Code node. Current rules:
- CRITICAL: >$500K, injuries, fraud flags
- HIGH: $100K–$500K, commercial, multiple parties
- STANDARD: <$100K, residential, single claimant
- LOW: <$10K, straightforward

### Add Specialists

Edit the **Assign Specialist** Code node to add entries to `specialistMap`.

### Change Slack Channel

Update the webhook URL in both Slack HTTP Request nodes.

---

## Production Considerations

Before deploying to production:

1. **Replace test emails** — Update `jtsomwaru+*@gmail.com` with real adjuster emails
2. **Secure credentials** — Move API keys to n8n credentials store
3. **Add rate limiting** — Implement throttling for high-volume scenarios
4. **Enable retries** — Configure retry policies on HTTP nodes
5. **Add monitoring** — Connect error workflow to alerting system
6. **HIPAA/compliance** — Review data handling for regulatory requirements

---

Built by [JT Somwaru](https://jtsomwaru.com) / Opticfy
