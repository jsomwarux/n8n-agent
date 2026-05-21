# Lessons Learned — Altmark Group Engagement
## For use by n8n agents and JT on future client builds

---

## INFRASTRUCTURE

### Dedicated Machine vs Client Server
- Never install n8n on a client's production server. IT teams (like Navid) will resist installing Docker, opening ports, or giving admin access on machines running QuickBooks, file shares, or other critical systems. ThreatLocker and similar endpoint security tools will block unapproved software.
- Always propose a dedicated mini PC (Beelink, Mac Mini, Intel NUC). It eliminates every security objection in one move: nothing touches the production server, no ThreatLocker issues, no firewall changes on their infrastructure, fully reversible (unplug the box and their server is untouched).
- Budget $300-600 for the hardware. Include it as a line item in the proposal under "third-party costs paid by client."
- Set up the dedicated machine at home before delivering to the client site. Install Node.js, n8n, Tailscale, configure the Windows service, test everything. Delivery to the client is just plugging in power and ethernet.

### DO NOT USE WSL2 + Docker on Windows for Production n8n

WSL2 on Windows 11 Home is fundamentally unreliable for always-on background services. After extensive troubleshooting, the following ALL failed to keep n8n running 24/7:
- `vmIdleTimeout=-1` in .wslconfig — doesn't work on all Windows 11 builds
- Startup .bat files and scheduled tasks to start WSL/Docker — unreliable execution on boot
- Keepalive scheduled tasks pinging WSL every 5 minutes — WSL still dies
- `netsh interface portproxy` — breaks after every WSL restart, connection resets from Tailscale traffic
- `networkingMode=mirrored` in .wslconfig — doesn't work on all Windows versions
- Tailscale serve on Windows proxying to WSL localhost — returns 502 when WSL localhost forwarding breaks
- Tailscale installed inside WSL2 — WSL still dies overnight taking Tailscale with it
- Docker `--restart always` — only works if Docker is running; Docker dies when WSL dies

**The result:** n8n was never running at 7am. The schedule trigger silently missed every day. Days of debugging produced no stable solution within the WSL2/Docker stack.

### The Working Solution: Native Windows Service (Node.js + NSSM)

Install n8n directly on Windows using Node.js (no WSL2, no Docker). Run it as a Windows service using NSSM. This gives the same reliability as Tailscale — which ran flawlessly throughout the entire WSL2 debugging saga because it's a native Windows service.

**Architecture:**
```
Windows Service Control Manager → NSSM → Node.js → n8n → local .n8n data folder
```

**Key setup steps:**
1. Disable Windows sleep/hibernate/standby: `powercfg /change standby-timeout-ac 0` and `powercfg /hibernate off`
2. Install Node.js LTS on Windows via winget or manual MSI installer
3. Install n8n locally in a project folder (not globally): `cd C:\n8n\app && npm init -y && npm install n8n@<VERSION>`
4. Create a startup script (`C:\n8n\start-n8n.cmd`) that sets environment variables and runs n8n
5. Use NSSM 2.24-101+ (not the old 2.24 stable — has Windows 11 issues) to register n8n as a Windows service
6. Configure auto-restart on crash via NSSM and `sc.exe failure` settings
7. n8n listens on 0.0.0.0:5678, accessible directly via the Windows Tailscale IP

**Critical for data migration from Docker:** If migrating from an existing Docker n8n instance, copy the ENTIRE `.n8n` directory from the Docker volume (including `database.sqlite` and the `config` file containing the encryption key) to `C:\n8n\.n8n\`. Set `N8N_USER_FOLDER=C:\n8n` so n8n finds the data. This preserves all workflows, credentials, and OAuth tokens — no need to recreate anything.

**Why local install, not global npm:** Global npm installs have PATH issues when running under Windows service accounts. A local install in `C:\n8n\app\node_modules\.bin\n8n.cmd` works reliably regardless of which user account the service runs under.

**Why NSSM 2.24-101+:** The old stable NSSM 2.24 has known service start issues on Windows 10 Creators Update and newer. Use the pre-release build from `https://nssm.cc/ci/nssm-2.24-101-g897c7ad.zip`.

**Reference commands:**
```
C:\n8n\nssm.exe install n8n C:\Windows\System32\cmd.exe "/c C:\n8n\start-n8n.cmd"
C:\n8n\nssm.exe set n8n AppDirectory C:\n8n\app
C:\n8n\nssm.exe set n8n AppStdout C:\n8n\logs\n8n-out.log
C:\n8n\nssm.exe set n8n AppStderr C:\n8n\logs\n8n-err.log
C:\n8n\nssm.exe set n8n Start SERVICE_AUTO_START
C:\n8n\nssm.exe set n8n AppExit Default Restart
sc.exe failure n8n actions= restart/60000/restart/60000/restart/60000 reset= 86400
C:\n8n\nssm.exe start n8n
```

### Tailscale Setup
- Install Tailscale on Windows only. It runs as a Windows service and auto-starts on boot.
- n8n running natively on Windows listens on 0.0.0.0:5678, which is directly accessible via the Windows Tailscale IP (e.g., `http://100.94.117.7:5678`).
- No port proxy, no Tailscale serve, no WSL networking — direct access.
- For Google OAuth HTTPS: use `tailscale serve --bg 5678` on Windows. Since n8n is now a real Windows-local process, Tailscale serve reliably proxies HTTPS to localhost:5678 without the WSL2 forwarding issues.

### Windows Power Management — CRITICAL
- Disable sleep, hibernate, and standby BEFORE deploying any always-on service. If the machine enters Modern Standby or sleep overnight, nothing runs at 7am — not even a Windows service.
```
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0
powercfg /hibernate off
powercfg /change monitor-timeout-ac 0
```
- This should be Step 0 of any dedicated machine setup. We missed this initially and it may have contributed to overnight failures.

### Windows Auto-Login
- Required so that after a power loss + reboot, Windows logs in without human intervention.
- Configure via registry:
```powershell
$RegPath = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon"
Set-ItemProperty -Path $RegPath -Name "AutoAdminLogon" -Value "1"
Set-ItemProperty -Path $RegPath -Name "DefaultUserName" -Value "[USERNAME]"
Set-ItemProperty -Path $RegPath -Name "DefaultPassword" -Value "[PASSWORD]"
```
- Also configure BIOS "Restore on AC Power Loss" to "Power On" so the machine turns itself on after a power outage without someone pressing the button. Access BIOS by pressing Delete or F2 during boot.
- Note: with NSSM configured to run as a Windows service with `SERVICE_AUTO_START`, n8n starts at boot even before any user logs in. Auto-login is still useful for other startup tasks and remote desktop access.

### Windows Firewall
- Firewall rules need to allow inbound TCP on port 5678:
```
netsh advfirewall firewall add rule name="n8n Dashboard" dir=in action=allow protocol=TCP localport=5678 profile=any interfacetype=any
```
- Firewall rules persist across reboots.
- If using Tailscale serve (port 443), you may not need port 5678 open at all since Tailscale handles the traffic internally.

### Ethernet vs WiFi
- Always use ethernet for the dedicated machine. WiFi can disconnect overnight, after router reboots, or when signal is weak. Ethernet is plug-and-forget.
- Forget any home WiFi networks before delivering the machine to the client's office to avoid routing confusion.
- Ethernet is plug-and-play — no passwords, no configuration. Just plug in and it connects.

---

## GOOGLE OAUTH CREDENTIALS IN n8n

### The 7-Day Token Expiry Problem
- When a Google Cloud project's OAuth consent screen is in "Testing" mode, refresh tokens expire after 7 days. Every Google credential in n8n (Gmail, Google Sheets) stops working after 7 days and must be manually re-authenticated.
- Fix: Publish the OAuth app to "Production" in Google Cloud Console. Published apps issue permanent refresh tokens.

### Publishing Requires HTTPS
- Google requires all OAuth redirect URIs to use HTTPS (except localhost) before allowing the app to be published.
- Raw Tailscale IPs (http://100.x.x.x) are rejected. HTTP URLs with domain names are also rejected.
- Solution: Use Tailscale serve which provides HTTPS with a valid Let's Encrypt certificate at `https://[hostname].ts.net`. Set this as the OAuth redirect URI:
```
https://[hostname].ts.net/rest/oauth2-credential/callback
```
- Keep `http://localhost:5678/rest/oauth2-credential/callback` as a fallback URI.

### After Publishing
- Re-authenticate ALL Google credentials in n8n after publishing the app. Old tokens were issued under "Testing" mode and will still expire. New tokens issued after publishing are permanent.

### Gmail: OAuth vs SMTP
- Gmail OAuth credentials require the Google Cloud Console setup, token management, and the HTTPS/publishing dance described above.
- Gmail SMTP with App Passwords is simpler: no OAuth, no tokens, no expiry. But it requires 2-Step Verification enabled on the Gmail account and an App Password generated.
- If the client controls the Gmail account (e.g., insurance@altmarkgroup.com), you may need them to enable 2-Step Verification and generate the App Password for you.
- For long-term reliability, OAuth with a published app is better. SMTP App Passwords can be revoked if someone disables 2-Step Verification.

---

## WORKFLOW SAFETY

### The Accidental Email Blast Incident
- During testing of the COI Expiration Tracking workflow, activating the workflow to test webhook plumbing caused 58 real outreach emails to be sent to real tenants from the wrong email address (personal Gmail instead of insurance@altmarkgroup.com).
- Root cause: No DRY_RUN flag, no batch limit, workflow pointed at real data with real recipient emails, and the act of activating the workflow was treated as a configuration step rather than a state transition with real consequences.

### Mandatory Safety Rules for All Client Workflows
1. **DRY_RUN flag** in the first Code node after the trigger, defaulting to `true`. When true: all emails go to the developer's email only, all CC fields emptied, all API write calls skipped, summary prefixed with "[TEST MODE]".

2. **BATCH_LIMIT variable** (default: 5). If the workflow would process more items than the limit, it stops and sends an alert instead of processing. Prevents runaway fan-out.

3. **ALLOW_PRODUCTION_CC** — separate flag from DRY_RUN. When DRY_RUN is true and ALLOW_PRODUCTION_CC is true, the client gets CC'd on test emails so they can review output without tenants being contacted. Must be checked independently:
```javascript
if (DRY_RUN) {
  item.json._send_to = TEST_EMAIL;
  if (ALLOW_PRODUCTION_CC) {
    item.json._cc = 'client@email.com';
  } else {
    item.json._cc = '';
  }
}
```

4. **Build against test data.** Copy the real data, replace ALL recipient emails with your own. Never rely on DRY_RUN alone — defense in depth.

5. **Gmail Trigger safety.** During testing, set the trigger to watch for a fake subject like "[TEST] Report Name". Only swap to the real subject pattern when going live.

6. **Log writes BEFORE email sends.** If the send fails, the log entry prevents duplicates on retry. Never send without logging first.

7. **Report Processing Log.** Record the email message ID of each processed report. Check this log before processing to prevent the same report from being processed twice.

8. **Going live requires three separate edits:** (a) swap Gmail Trigger to real subject, (b) set DRY_RUN to false, (c) increase BATCH_LIMIT. Never combine these with other changes.

9. **Before activating any workflow, enumerate every side effect:** "If this fires right now: what gets sent, to whom, how many, from what address?" Wait for human confirmation.

10. **After a debugging sequence that ends with "now it works," ask: what was preventing the worst case before this fix? Is the only remaining protection my attention?** Each fix may have removed a safety barrier.

---

## n8n TECHNICAL LESSONS

### Docker Container Management
- Use `--restart always` on the Docker run command so the container auto-restarts after crashes.
- Use `-v n8n_data:/home/node/.n8n` to persist all workflows, credentials, and settings in a Docker volume. Removing and recreating the container (`docker rm` + `docker run`) preserves all data as long as the volume name stays the same.
- Set timezone: `-e GENERIC_TIMEZONE="America/New_York" -e TZ="America/New_York"`. Without this, schedule triggers fire at UTC time.
- Set `-e N8N_SECURE_COOKIE=false` when accessing n8n over HTTP (not HTTPS). Without this, n8n blocks non-HTTPS connections.
- Set `-e NODE_FUNCTION_ALLOW_EXTERNAL="fuse.js"` to allow Code nodes to `require('fuse.js')` for fuzzy search. n8n's sandbox blocks all `require()` calls by default.
- Never use `require('fs')` in Code nodes. Use n8n's native Read Binary File and Spreadsheet File nodes instead.

### n8n Environment Variables for Remote Access
- `WEBHOOK_URL` — set to the public URL (e.g., `https://[hostname].ts.net/`) so webhook triggers generate the correct URL.
- `N8N_EDITOR_BASE_URL` — set to the same public URL so OAuth callbacks route correctly.
- If using Tailscale serve, the WEBHOOK_URL should use the HTTPS Tailscale URL.

### Google Sheets in n8n
- Google Sheets OAuth credentials require the Google Sheets API to be enabled in Google Cloud Console (APIs & Services → Library → search "Google Sheets API" → Enable). Without this, reads silently fail or hang.
- Google Sheets credentials expire if the OAuth app is in Testing mode (7-day token expiry). Publish the app.
- When a Google Sheets read returns 0 rows (empty sheet or header-only), n8n treats it as "no output" and stops execution. Add `"alwaysOutputData": true` to the node settings if an empty result is valid.
- Google Sheets has two credential types: `googleSheetsOAuth2Api` (for regular nodes) and `googleSheetsTriggerOAuth2Api` (for trigger nodes). They are not interchangeable.

### Schedule Triggers
- n8n does NOT back-fill missed scheduled runs. If n8n is down at 7:00 AM, that run is simply skipped — it won't run late when n8n comes back up.
- This means persistent uptime is critical. Every minute n8n is down at the scheduled time = one silently skipped run.
- Always verify schedule triggers work by checking the Executions tab the morning after deployment.

---

## CLIENT MANAGEMENT

### NDA Negotiation
- Real estate family offices will require NDAs before any work begins. Standard items to push back on:
  - **AI API carve-out (Section 3):** The NDA will prohibit sending data to third-party systems. Get an explicit carve-out for AI APIs (Anthropic, OpenAI) used to perform the agreed services.
  - **Personal device for development (Section 4):** Get permission to temporarily store client data on your device for development/testing, with a deletion deadline after project completion.
  - **Methodology reuse (Section 5/6):** Ensure you retain the right to reuse general patterns and frameworks (not client data) for other clients. Without this, your ability to scale is restricted.
  - **Liability cap (Section 8/10):** Align NDA liability with the cap in your services agreement (total fees paid).
  - **Non-circumvention + referrals (Section 6):** If the client plans to refer you to other firms, get explicit language that the non-circumvention clause doesn't restrict providing services to referred clients.

### Conductor (QuickBooks Desktop API) Pricing
- List price is $49/month per company file connection. Always negotiate — they're flexible.
- For 20-30 connections, we negotiated down to $15/month per entity ($345/month total vs $1,127/month at list price).
- Contact sales directly. Their emails may go to spam — follow up if no response.
- Client pays Conductor directly — it's a third-party cost, not part of your fees.

### Payment Structure
- Foundation/infrastructure paid 100% upfront.
- Each use case: 50% to start, 50% upon delivery and approval.
- 10 business day approval window — if client doesn't respond, deliverable is deemed approved (put this in the contract).
- Don't start work before the contract is signed and first payment received.

### Client Communication Patterns
- When a client says "I'll get to it next week," send one check-in after the stated timeframe passes. Keep it casual: "Whenever you're ready, everything's set on my end."
- Don't send multiple follow-ups or checklists to an overwhelmed client. They know what you need — let them come to you.
- When delivering bad news (accidental email blast, delayed timeline), lead with the facts, then the fix, then the prevention plan. Don't over-apologize.

---

## DATA & SPREADSHEET LESSONS

### Always Inspect the Real Data
- Open every client spreadsheet yourself before building. Don't trust column names from conversation — verify them character by character.
- Look for: blank rows, subtotal rows, header rows that aren't in row 1, merged cells, dates stored as text, zero values in divisor columns (division by zero), and dates from 1900 (Excel epoch bug).
- The COI spreadsheet had a broken dashboard formula ("all COIs are compliant" while 61 were expired), an invalid date from 1900, and 42 rows without email addresses. All discovered by inspecting the actual data.

### PDF vs Excel for Report Ingestion
- Always ask the client if the report can be delivered as Excel/CSV instead of PDF. Excel is parsed natively by n8n with zero AI cost and perfect accuracy. PDF requires Claude Sonnet parsing which adds cost, latency, and a point of failure.
- If the client says "it's a PDF," ask: "Can AppFolio/QuickBooks/the system be configured to send it as a spreadsheet instead?" The answer is usually yes.

### Google Sheets vs Excel on Server
- Prefer Google Sheets. No file locking issues, multiple users can edit simultaneously, accessible via API from anywhere (including the dedicated machine that's not on the same server).
- If the client insists on Excel files on the server, the dedicated machine needs network access to the server's shared folders — adds complexity.
- Migration from Excel to Google Sheets is trivial: upload to Google Drive → Open with Google Sheets. Formulas and formatting transfer. Takes 5 minutes.

---

## DEPLOYMENT CHECKLIST — Use for Every Client

### Before Delivering the Dedicated Machine
- [ ] Windows sleep/hibernate/standby disabled via powercfg (Step 0 — do this FIRST)
- [ ] Windows timezone set to Eastern: `tzutil /s "Eastern Standard Time"`
- [ ] Node.js LTS installed on Windows
- [ ] n8n installed locally in `C:\n8n\app` (same version as any existing instance being migrated)
- [ ] `.n8n` data directory in place at `C:\n8n\.n8n` (migrated from Docker or fresh)
- [ ] `start-n8n.cmd` script created with correct environment variables
- [ ] NSSM 2.24-101+ installed; n8n registered as Windows service with auto-start and auto-restart
- [ ] Tailscale installed on Windows and connected
- [ ] n8n accessible from MacBook via Windows Tailscale IP (`http://[TAILSCALE_IP]:5678`)
- [ ] Windows firewall allows inbound TCP 5678
- [ ] Windows auto-login configured via registry
- [ ] BIOS "Restore on AC Power Loss" set to "Power On"
- [ ] Home WiFi network forgotten
- [ ] Full reboot test — machine comes up, n8n service starts, dashboard accessible without intervention
- [ ] 20-minute idle test — close laptop, wait, verify n8n still accessible
- [ ] Google OAuth app published to Production (requires HTTPS redirect URI via Tailscale serve)
- [ ] All Google credentials working after migration (encryption key preserved)

### Before Going Live on Any Workflow
- [ ] DRY_RUN = true, BATCH_LIMIT = 5 verified in Code node
- [ ] Gmail Trigger watching for test subject, not real subject
- [ ] All recipient emails in test data replaced with developer's email
- [ ] All Google Sheets logs created (Alert Log, Processing Log, Do Not Contact)
- [ ] Workflow tested with test data — summary email received
- [ ] Math verified manually against 5 rows
- [ ] Client reviewed dry-run summary and explicitly approved going live
- [ ] Go-live edits done separately: trigger subject, DRY_RUN, BATCH_LIMIT
