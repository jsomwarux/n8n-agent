# Construction Job Tracker — T2 Template Configuration

## Overview

This document maps every parameterized value in `construction-job-tracker.json`
to the prospect-specific value that should replace it. When configuring for a new
prospect, work through this checklist top-to-bottom.

## Quick Start

1. Import `workflows/construction-job-tracker.json` into n8n
2. Replace placeholder values per the config map below
3. Create a Google Sheet with the "Job Log" tab and required headers
4. Connect Gmail and Google Sheets OAuth credentials in n8n
5. Set the Anthropic API key
6. Activate and test with a sample webhook POST

---

## Config Map

### 1. Anthropic API Key

| Node | Field | Placeholder | Replace With |
|---|---|---|---|
| AI Triage (Claude) | `headerParameters.parameters[0].value` | `sk-ant-CONFIGURE-YOUR-ANTHROPIC-KEY-HERE` | Your Anthropic API key |

### 2. Google Sheets

| Node | Field | Placeholder | Replace With |
|---|---|---|---|
| Log Job Update | `documentId.value` | `CONFIGURE-YOUR-GOOGLE-SHEET-ID` | Prospect's Google Sheet ID (from URL) |
| Log Job Update | `sheetName.value` | `Job Log` | Tab name (keep as "Job Log" or rename) |
| Log Job Update | `credentials.googleSheetsOAuth2Api` | `CONFIGURE_ME` | Your n8n Google Sheets credential |

**Required Sheet Headers** (create a tab called "Job Log" with these exact column names):

```
Date | Job Site | Foreman | Percent Complete | Status | Foreman Note | Client Summary | Blockers | Client Notified | Photo URL
```

### 3. Client Notification Email

| Node | Field | Placeholder | Replace With |
|---|---|---|---|
| Prep Client Email | `jsCode` → `send_to` value | `client@example.com` | Prospect's client email address |
| Notify Client | `credentials.gmailOAuth2` | `CONFIGURE_ME` | Your n8n Gmail credential |

### 4. Owner Alert Email

| Node | Field | Placeholder | Replace With |
|---|---|---|---|
| Prep Owner Alert | `jsCode` → `send_to` value | `owner@example.com` | Owner/PM email for blocked alerts |
| Alert Owner | `credentials.gmailOAuth2` | `CONFIGURE_ME` | Your n8n Gmail credential (same as above) |

### 5. Webhook Path

| Node | Field | Current Value | Replace With |
|---|---|---|---|
| Webhook: Foreman Update | `path` | `construction-job-tracker` | Custom path per prospect (e.g., `acme-plumbing-updates`) |
| Webhook: Foreman Update | `webhookId` | `construction-job-tracker-webhook` | Unique ID per prospect |

---

## Per-Prospect Customization Checklist

For each new prospect demo:

- [ ] Copy `construction-job-tracker.json` to prospect's client folder
- [ ] Replace Anthropic API key
- [ ] Create Google Sheet with "Job Log" tab + headers
- [ ] Set Google Sheet ID in workflow
- [ ] Connect Google Sheets OAuth credential
- [ ] Set client email in "Prep Client Email" Code node
- [ ] Set owner email in "Prep Owner Alert" Code node
- [ ] Connect Gmail OAuth credential (all 2 Gmail nodes share the same credential)
- [ ] Update webhook path to be prospect-specific
- [ ] Import into n8n and activate
- [ ] Test with sample curl command (see below)

---

## Test Command

```bash
curl -X POST http://localhost:5678/webhook/construction-job-tracker \
  -H "Content-Type: application/json" \
  -d '{
    "job_site": "123 Main St - Kitchen Renovation",
    "foreman_name": "Mike Rodriguez",
    "percent_complete": 65,
    "blockers": "",
    "foreman_note": "Cabinets installed today. Countertop template scheduled for Thursday. Plumbing rough-in passed inspection.",
    "photo_url": "https://example.com/photos/123main-day12.jpg"
  }'
```

---

## Sample Prospect Configuration

**Example: Ace Plumbing & HVAC (prospect)**

| Field | Value |
|---|---|
| Webhook path | `ace-plumbing-updates` |
| Google Sheet ID | `1abc123def456...` (from their sheet URL) |
| Sheet tab | `Job Log` |
| Client email | `scheduling@aceplumbing.com` |
| Owner email | `tony@aceplumbing.com` |
| Job sites | "45 W 72nd St - Boiler Replacement", "890 Amsterdam Ave - Kitchen Reno" |

## Claude Model

The template uses `claude-sonnet-4-20250514`. To change the model, edit the
`AI Triage (Claude)` node's `jsonBody` parameter and replace the model string.
