# PM Maintenance Triage — Demo Test Results

## Test Setup

- **Template**: pm-maintenance-triage
- **Trigger**: POST webhook at `/webhook/pm-maintenance-triage`
- **AI Model**: Claude Sonnet (via Anthropic API)
- **Vendor Sheet**: Pre-populated with 5 demo vendors (plumbing, electrical, HVAC, structural, cosmetic)

---

## Test Case 1: Routine Plumbing Request

**Input:**
```json
{
  "unit": "4B",
  "tenant_name": "Maria Rodriguez",
  "tenant_email": "maria.rodriguez@email.com",
  "tenant_phone": "(646) 555-0142",
  "issue_description": "Kitchen faucet has a slow drip. Not urgent but getting worse over the past week.",
  "urgency": "low"
}
```

**Expected Classification:**
- Urgency: `routine`
- Category: `plumbing`
- SLA: 72 hours

**Expected Actions:**
- Vendor dispatch email sent to plumber (from Vendors sheet)
- Tenant confirmation email sent to maria.rodriguez@email.com
- Row appended to Maintenance Log sheet
- No emergency alert triggered

**Expected Webhook Response:**
```json
{
  "status": "success",
  "ticket_id": "MR-XXXXXX",
  "classification": {
    "urgency": "routine",
    "category": "plumbing",
    "reasoning": "Slow drip is not an emergency or urgent issue..."
  },
  "vendor_assigned": {
    "name": "ABC Plumbing Corp",
    "email": "jtsomwaru+demo+plumber@gmail.com"
  },
  "sla_window": "72 hours",
  "tenant_notified": true,
  "emergency_alert_sent": false
}
```

---

## Test Case 2: Urgent HVAC Issue

**Input:**
```json
{
  "unit": "12A",
  "tenant_name": "James Chen",
  "tenant_email": "james.chen@email.com",
  "tenant_phone": "(212) 555-0198",
  "issue_description": "AC unit completely stopped working. It's 95 degrees outside and the apartment is getting dangerously hot. I have an elderly parent living with me.",
  "urgency": "high"
}
```

**Expected Classification:**
- Urgency: `urgent` (or `emergency` — AC failure in extreme heat with elderly resident could go either way)
- Category: `hvac`
- SLA: 24 hours (or 2 hours if classified as emergency)

**Expected Actions:**
- Vendor dispatch email sent to HVAC vendor
- Tenant confirmation email sent to james.chen@email.com
- Row appended to Maintenance Log sheet
- If classified as emergency: PM office alert triggered via webhook

**Expected Webhook Response:**
```json
{
  "status": "success",
  "ticket_id": "MR-XXXXXX",
  "classification": {
    "urgency": "urgent",
    "category": "hvac",
    "reasoning": "AC failure in extreme heat with elderly resident warrants urgent response..."
  },
  "vendor_assigned": {
    "name": "CoolAir HVAC Services",
    "email": "jtsomwaru+demo+hvac@gmail.com"
  },
  "sla_window": "24 hours",
  "tenant_notified": true,
  "emergency_alert_sent": false
}
```

---

## Test Case 3: Emergency Flooding (Wow Case)

**Input:**
```json
{
  "unit": "2C",
  "tenant_name": "David Park",
  "tenant_email": "david.park@email.com",
  "tenant_phone": "(917) 555-0067",
  "issue_description": "Pipe burst under the kitchen sink. Water is flooding the kitchen and starting to go into the hallway. I turned off the water valve but it's still leaking. The apartment below me might be getting water damage too.",
  "urgency": "emergency"
}
```

**Expected Classification:**
- Urgency: `emergency`
- Category: `plumbing`
- SLA: 2 hours

**Expected Actions:**
- **PM office emergency alert fired immediately** (Slack webhook / alert endpoint)
- Vendor dispatch email sent to plumber with EMERGENCY tag
- Tenant confirmation email with 2-hour SLA and office phone number
- Row appended to Maintenance Log sheet with urgency = emergency

**Expected Webhook Response:**
```json
{
  "status": "success",
  "ticket_id": "MR-XXXXXX",
  "classification": {
    "urgency": "emergency",
    "category": "plumbing",
    "reasoning": "Active pipe burst with flooding affecting multiple units — classified as emergency..."
  },
  "vendor_assigned": {
    "name": "ABC Plumbing Corp",
    "email": "jtsomwaru+demo+plumber@gmail.com"
  },
  "sla_window": "2 hours",
  "tenant_notified": true,
  "emergency_alert_sent": true
}
```

**Why this is the wow case:** The workflow detects active flooding, immediately alerts the PM office (no human needed to escalate), dispatches the plumber with an EMERGENCY tag, and tells the tenant "a plumber will be there within 2 hours." The PM sees the emergency alert on their phone in real-time. This is the moment prospects say "I need this."

---

## Demo Script Summary

| Test | Urgency | Category | Emergency Alert? | Key Demo Point |
|---|---|---|---|---|
| 1. Kitchen faucet drip | routine | plumbing | No | Shows routine auto-routing — PM never sees it |
| 2. AC failure, elderly tenant | urgent | hvac | No (or Yes) | Shows urgency detection from context, not just tenant's word |
| 3. Pipe burst flooding | emergency | plumbing | **Yes** | Shows instant escalation + vendor dispatch — wow moment |

---

## Notes

- Test case 2 may classify as `emergency` depending on Claude's assessment of the heat + elderly factor. Both outcomes are good demo material — if it escalates, it shows the AI errs on the side of safety.
- All vendor emails route to JT's Gmail via the `+tag` pattern. No real vendor contact during demos.
- The tenant confirmation messages are AI-drafted and context-aware — they reference the specific issue type and expected timeline, not a generic "we received your request."
