# Altmark COI Expiration Tracking — Hand-off

**Workflow file:** `clients/altmark/workflows/coi-expiration-tracking.json`
**n8n workflow ID (local):** `InVTJEEsGnQzaoTB` — currently **INACTIVE**
**Ships with DRY_RUN=true AND ALLOW_PRODUCTION_CC=false AND points at DUPLICATE test sheet.** See Safety Flags section below before flipping any of these to production.
**Duplicate test sheet:** `1OhI2JWEf9ZyWhW_TLvqRkPeBsU0NxTHYuHQvSJfEf40` (tenant emails replaced with jtsomwaru@gmail.com)
**Production sheet:** `17ZHhmjSoUg7KKBD4jnvzlcH88lqlyEHCORTzBTpJISY` (real tenant emails)
**Spreadsheet:** Altmark Group - Portfolio Wide COI Dashboard FINAL VERSION — converted from uploaded .xlsx to native Google Sheet on 2026-04-24 (ID `17ZHhmjSoUg7KKBD4jnvzlcH88lqlyEHCORTzBTpJISY`). The original uploaded .xlsx (ID `1FaTjfQTeZSkpeA6-h7R3Y94r96K_RfF4`) is unreadable by the Google Sheets API — do NOT revert.

## Required setup before activating (3 items)

### 1. Reconnect Google Sheets credential
The existing credential `Google Sheets Credential 1` (ID `WO50ACWsQ8uamjp2`) has an
expired/revoked refresh token. Verified during the end-to-end test — both sheet reads
returned "The provided authorization grant...is invalid, expired, revoked..."

Fix in n8n UI:
  1. Credentials → `Google Sheets Credential 1` → **Sign in with Google**
  2. Complete the OAuth flow for an account that has access to the COI spreadsheet
  3. Save

Lesson #22/#57: after re-auth, a full credential delete+recreate is sometimes needed
if the Sheets API was enabled after the original token was issued.

### 2. Create the `COI Alert Log` tab with a header row
n8n cannot create tabs — only rows (lesson #39). Manually add a tab to the COI
spreadsheet with these column headers in row 1 (A1:H1), exact spelling:

```
tenant_name | entity_name | property_address | unit | escalation_stage | date_sent | expiration_date | source
```

The `Append to Alert Log` node uses `autoMapInputData` and writes to these exact
column names. Any mismatch → silent blank writes (lesson #44).

### 3. Gmail OAuth credential — DONE (JT placeholder)
Status: a Gmail OAuth2 credential named `Altmark Insurance Gmail`
(ID `pk48J92vFO9rAOWe`) is set up and bound to both Gmail nodes. Currently
authenticated as `jtsomwaru@gmail.com` for test-phase use only.

**Swap to `insurance@altmarkgroup.com` when Yair's mailbox is live:**
  1. n8n UI → **Credentials → Altmark Insurance Gmail**
  2. Click **Sign in with Google** → pick `insurance@altmarkgroup.com` → **Allow**
  3. **Save**. The credential ID stays the same, so no workflow edits needed.
  4. (Optional) Google Cloud Console → project `Altmark COI` → OAuth consent screen →
     add `insurance@altmarkgroup.com` as a test user if still in Testing mode.

## Safety flags (critical)

The `Classify Tenants` Code node has TWO independent flags at the top:

```js
const DRY_RUN = true;                 // default: safe
const ALLOW_PRODUCTION_CC = false;    // default: safe
const DRY_RUN_REDIRECT = 'jtsomwaru@gmail.com';
```

The four valid combinations correspond to three useful modes + one "default-safe" override case:

| Mode | DRY_RUN | ALLOW_PRODUCTION_CC | Behavior |
|---|---|---|---|
| **DRY_RUN (default)** | `true` | `false` | Tenant emails → JT only. CC empty. Subject `[DRY RUN -> real@email]`. Body has DRY RUN banner. Summary to JT with `[DRY RUN]` prefix. Alert Log NOT written. |
| **TEST** | `false` | `false` | Tenant emails → real addresses from the sheet. CC empty (Yair/Matt NOT copied). Subject/body clean. Alert Log writes. Summary to JT with `[TEST]` prefix and banner. Safe when the sheet is the duplicate (tenant emails are all JT's). |
| **PRODUCTION** | `false` | `true` | Tenant emails → real addresses. CC `yair@altmarkgroup.com,matt@altmarkgroup.com`. Subject/body clean. Alert Log writes. Summary to yair+matt, no prefix. Full live behavior. |
| (DRY_RUN override) | `true` | `true` | DRY_RUN takes precedence. Same as DRY_RUN mode — ALLOW_PRODUCTION_CC is ignored when DRY_RUN is on. |

**Go-live sequence — never flip both flags in the same edit:**

1. On DUPLICATE sheet, run with `DRY_RUN=true, ALLOW_PRODUCTION_CC=false` → verify redirect, no CC, no log writes, [DRY RUN] labels everywhere
2. On DUPLICATE sheet, flip `DRY_RUN=false` (keep `ALLOW_PRODUCTION_CC=false`) → verify emails hit real sheet addresses (which are all JT's), Alert Log writes, no CC, [TEST] prefix on summary
3. Flip `DRY_RUN=true` back on. Repoint the 3 Sheets nodes to the PRODUCTION sheet. Run one more dry-run against prod to confirm routing
4. Only now flip `DRY_RUN=false` AND `ALLOW_PRODUCTION_CC=true` together → genuinely live

All four mode combinations are covered by the offline test harness at `/tmp/altmark-coi/test-matrix.js` — runs in ~200ms.

## Email template configuration (Classify Tenants Code node)

Yair-tunable constants live near the top of `Classify Tenants` under the safety flags. Edit any of these without touching workflow logic; deploy with the same `build_workflow.py`.

```js
const CERT_HOLDER_MAILING_ADDRESS = '2447 Third Ave, Bronx, NY 10451';
const COI_INTAKE_EMAIL = 'insurance@altmarkgroup.com';
const DEADLINE_DAYS_INITIAL = 30;
const DEADLINE_DAYS_FOLLOWUP = 14;
const DEADLINE_DAYS_FINAL = 7;
```

Tenant outreach emails are rendered as HTML (eliminates RFC 2822 plain-text line wrapping that was making bodies look fixed-width in Gmail). Signature is a simple "Thank you, / The Altmark Group" — no individual name, no phone, per Yair's confirmation on 2026-04-27.

Deadlines (the "Please provide the updated certificate by [date]" line) are computed as N days from the current run, per stage. If Yair wants different urgency, change the constants. Final Notice retains the lease/license-agreement compliance language — automatically swaps "lease" for "license agreement" when the entity is one of: Markland 486 LLC, Markland 713 LLC, Bronx Canvas LLC, Bronx Canvas Canal LLC.

If per-entity mailing addresses are ever needed, add a `Mailing Address` column to the COI Policy Data tab and switch `CERT_HOLDER_MAILING_ADDRESS` to a per-row read in Classify Tenants.

## Activation

Only flip the workflow to Active AFTER all 3 setup items above are done AND you've verified in DRY_RUN mode that the run produces the expected counts without errors. Steps:
  - n8n UI → workflow list → Altmark — COI Expiration Tracking → toggle **Active**
  - First run fires at the next 7:00 AM ET tick.

## Email authentication (SPF / DKIM / DMARC) — required before going live

When DRY_RUN is flipped to false, tenant emails leave from `insurance@altmarkgroup.com`. Without email-authentication records on the `altmarkgroup.com` DNS, Gmail and Outlook recipients will likely junk-folder or silently drop the outbound emails. Three records:

- **SPF** (Sender Policy Framework): a TXT DNS record on `altmarkgroup.com` listing which mail services are authorized to send as the domain. If Altmark uses Google Workspace: `v=spf1 include:_spf.google.com ~all`
- **DKIM** (DomainKeys Identified Mail): a cryptographic signature Google Workspace appends to every outbound email. Enable via **Google Workspace Admin Console → Apps → Google Workspace → Gmail → Authenticate email → Generate new record → Start authentication** → add the provided DNS TXT record
- **DMARC** (Domain-based Message Authentication, Reporting & Conformance): a TXT DNS record telling receivers what to do if SPF/DKIM fails. Start with `v=DMARC1; p=none; rua=mailto:yair@altmarkgroup.com` (monitor-only), then graduate to `p=quarantine` once you've confirmed legitimate mail is passing

Without these, expect 10–30% of tenant emails to silently land in spam even after the incident-recovery clarification email. Takes ~30 minutes once Yair gets his Workspace admin to run it. Check current state at https://mxtoolbox.com/SuperTool.aspx?action=mx%3aaltmarkgroup.com — if SPF/DKIM/DMARC rows are missing, fix before going live.

## Manual / test runs

Separate webhook trigger exists for ad-hoc runs: POST to
`http://localhost:5678/webhook/coi-manual-run` (empty body is fine). Fires the full
pipeline on demand. Useful for:
  - Smoke-testing after changes
  - Catching up if the scheduled run missed (n8n was off)
  - The once-off expiring-soon audit Yair might want mid-month

Requires the workflow to be active.

## Known spreadsheet concern

The spreadsheet URL contains `rtpof=true`, which is Drive's "retain format" flag for
uploaded Excel files. If the file is a native Google Sheet, the workflow runs fine.
If it's an `.xlsx` uploaded to Drive and never converted, the Google Sheets node will
error on read. If you see `"Requested entity was not found"` or a similar 404-style
error during the first run, open the file in Drive → **File → Save as Google Sheets**,
update the workflow's `documentId` on both Sheets read nodes + the append node to the
new Sheet's ID, save.

## Data flow reference

```
Schedule Trigger (7 AM ET, daily)  or  Manual Webhook
          ↓
Read COI Policy Data (row 2 = headers, row 4+ = data, A:K)
          ↓
Read Alert Log  (executeOnce=true, alwaysOutputData=true for empty log)
          ↓
Classify Tenants (Code: one item per row, action-tagged)
          ↓
 ┌────────┴─────────┐
 IF action=send_email
   true → Send Tenant Email (CC: yair@, matt@)
           → Prep Log Row → Append to Alert Log
   false → (drops)
          ↓                       ↓
          └──────────┬────────────┘
                     ↓
          Build Daily Summary (executeOnce=true, aggregates all classified items)
                     ↓
          Send Daily Summary Email (to yair@, matt@)
```

## Classification rules (source of truth)

| days_until_expiration | Alert Log state                       | Action |
|---|---|---|
| 60 | no prior `initial_request`            | Send Initial Request (scheduled) |
| 30 | no prior `second_followup`            | Send Second Follow-Up (scheduled) |
| 7  | no prior `final_notice`               | Send Final Notice (scheduled) — license-entity swap for Markland/Bronx Canvas LLCs |
| other positive | —                            | compliant / no action |
| 0 (expires today) | —                           | NO tenant email — internal alert in summary |
| < 0 (expired) | no log entry                  | Send Initial Request (backlog) |
| < 0 | last log = initial_request, ≥14d ago | Send Second Follow-Up (backlog) |
| < 0 | last log = second_followup, ≥7d ago  | Send Final Notice (backlog) |
| < 0 | last log = final_notice, ≥7d ago     | escalation_needed — internal alert |
| < 0 | otherwise                            | no action (waiting for next escalation) |

## Always skipped (never emailed)

- `Certificate Received` = `Vacant` or `Not Required`
- `Tenant Name` blank or `Vacant`
- Both `Tenant Email #1` and `Tenant Email #2` blank → flagged in summary "DATA ISSUES"
- `COI Expiration Date` blank or before 2020-01-01 → flagged in summary "DATA ISSUES"

## Offline test matrix (11/11 pass)

Run `/tmp/altmark-coi/test-matrix.js` with `node test-matrix.js` to rerun. Covers:
60-day, 30-day, 7-day, today (day 0), 6-month future, expired-no-log (backlog),
Vacant, no-email, bad-date (1900), Markland license-entity 7-day, backlog with
15-day-old initial_request.

## Flag for Yair (separate from this workflow)

The Dashboard tab of the spreadsheet is broken — its formula reports "all COIs
compliant" while 61 are currently expired. This workflow intentionally does NOT read
from Dashboard (reads `COI Policy Data` directly). The daily summary email from this
workflow replaces the Dashboard as the source of truth. Fix the Dashboard formula
separately when there's time.
