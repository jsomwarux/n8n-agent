# Construction Job Tracker — Demo Test Results

Template: `construction-job-tracker.json`
Test date: 2026-03-15
Status: **Template validated** (not deployed — placeholder credentials)

---

## Test Case 1: On Track Update

**Input (webhook POST):**
```json
{
  "job_site": "456 Park Ave - Bathroom Renovation",
  "foreman_name": "Carlos Mendez",
  "percent_complete": 72,
  "blockers": "",
  "foreman_note": "Tile work in master bath 90% done. Vanity arrives tomorrow. On schedule for Friday walkthrough with client.",
  "photo_url": "https://photos.example.com/456park-day15.jpg"
}
```

**Expected AI Classification:**
- Status: `on_track`
- Foreman summary: Tile work nearly complete, vanity delivery tomorrow, on schedule for Friday walkthrough.
- Client summary: "Your bathroom renovation at 456 Park Ave is progressing well at 72% completion. Tile work in the master bath is nearly finished, and the vanity is arriving tomorrow. We're on track for the walkthrough on Friday."
- Next milestone: Friday client walkthrough

**Expected Actions:**
1. Google Sheets: Row appended to "Job Log" — Date, "456 Park Ave - Bathroom Renovation", "Carlos Mendez", "72", "ON_TRACK", note, summary, "None", "Yes", photo URL
2. Gmail (client): Email sent to `client@example.com` with subject "456 Park Ave - Bathroom Renovation — Job Update (72% Complete)"
3. Owner alert: NOT sent (status is on_track)

**Expected Webhook Response:**
```json
{
  "success": true,
  "job_site": "456 Park Ave - Bathroom Renovation",
  "status": "on_track",
  "percent_complete": 72,
  "actions": ["AI classified as ON_TRACK", "Logged to Google Sheets", "Client notified via email"],
  "foreman_summary": "...",
  "client_summary": "..."
}
```

---

## Test Case 2: At Risk Update

**Input (webhook POST):**
```json
{
  "job_site": "789 Broadway - Office Build-Out",
  "foreman_name": "Jimmy Walsh",
  "percent_complete": 35,
  "blockers": "",
  "foreman_note": "Electrical rough-in taking longer than expected. Waiting on GC to confirm HVAC duct routing before we can close up walls. Might push drywall back a few days.",
  "photo_url": ""
}
```

**Expected AI Classification:**
- Status: `at_risk`
- Foreman summary: Electrical behind schedule, waiting on GC for HVAC routing, drywall may be delayed.
- Client summary: "The office build-out at 789 Broadway is at 35% completion. Electrical work is progressing but coordination with HVAC duct routing is needed before walls can be closed. The team is working to keep the timeline on track."
- Next milestone: GC confirms HVAC routing, then drywall can proceed
- Risk factors: ["Electrical rough-in behind schedule", "HVAC duct routing dependency", "Potential drywall delay"]

**Expected Actions:**
1. Google Sheets: Row appended — Status = "AT_RISK"
2. Gmail (client): Email sent with professional summary (no mention of internal delays)
3. Owner alert: NOT sent (status is at_risk, not blocked)

**Expected Webhook Response:**
```json
{
  "success": true,
  "job_site": "789 Broadway - Office Build-Out",
  "status": "at_risk",
  "percent_complete": 35,
  "actions": ["AI classified as AT_RISK", "Logged to Google Sheets", "Client notified via email"],
  "foreman_summary": "...",
  "client_summary": "..."
}
```

---

## Test Case 3: Blocked Update

**Input (webhook POST):**
```json
{
  "job_site": "123 Main St - Kitchen Renovation",
  "foreman_name": "Mike Rodriguez",
  "percent_complete": 45,
  "blockers": "DOB permit for gas line relocation rejected. Need engineer to resubmit with updated drawings. Cannot proceed with plumbing until approved.",
  "foreman_note": "Everything else is ready but we are dead in the water on plumbing. Cabinets and countertop on hold until gas line is resolved. Told the guys to move to punch list items in other rooms.",
  "photo_url": "https://photos.example.com/123main-day8.jpg"
}
```

**Expected AI Classification:**
- Status: `blocked`
- Foreman summary: Blocked by DOB permit rejection for gas line. Crew reassigned to punch list while waiting.
- Client summary: "The kitchen renovation at 123 Main St has encountered a permitting issue at 45% completion. Our team is working with the engineer to resolve a gas line permit requirement. In the meantime, the crew is making progress on other areas of the project. We will update you as soon as the permit is cleared."
- Next milestone: Engineer resubmits permit drawings to DOB
- Risk factors: ["DOB permit rejected", "Gas line relocation blocked", "Plumbing on hold", "Cabinets/countertop installation delayed"]

**Expected Actions:**
1. Google Sheets: Row appended — Status = "BLOCKED", Blockers = "DOB permit for gas line..."
2. Gmail (client): Email sent with professional summary (reassuring tone, no panic)
3. Gmail (owner alert): **SENT** to `owner@example.com` with subject "BLOCKED: 123 Main St - Kitchen Renovation — Immediate Attention Required"
   - Body includes: foreman name, blocker detail, progress %, foreman note, risk factors

**Expected Webhook Response:**
```json
{
  "success": true,
  "job_site": "123 Main St - Kitchen Renovation",
  "status": "blocked",
  "percent_complete": 45,
  "actions": ["AI classified as BLOCKED", "Logged to Google Sheets", "Client notified via email", "Owner alerted via email"],
  "foreman_summary": "...",
  "client_summary": "..."
}
```

---

## Summary

| Test | Status | Sheets | Client Email | Owner Alert |
|---|---|---|---|---|
| #1 On Track | on_track | Yes | Yes | No |
| #2 At Risk | at_risk | Yes | Yes | No |
| #3 Blocked | blocked | Yes | Yes | **Yes** |

All 3 paths exercise distinct workflow branches. The IF node fires only on `blocked`, routing to the owner alert Gmail node. On_track and at_risk both take the normal path.
