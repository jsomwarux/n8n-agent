# Conductor QuickBooks Desktop API — n8n HTTP Request Pattern

NOTE: Verify exact endpoint paths and filter parameters against Conductor's live docs at docs.conductor.is before building. The patterns here are directional — confirm specifics using Conductor's API Explorer during setup.

## Headers (same for all calls)
- Authorization: Bearer [CONDUCTOR_API_KEY]
- Conductor-End-User-Id: [CONDUCTOR_END_USER_ID]
- Content-Type: application/json

## Base URL
https://api.conductor.is/v1/qbd

## Common Endpoints
- GET /accounts — list all accounts
- GET /accounts?accountType=LongTermLiability — loan accounts
- GET /accounts/{id} — specific account balance
- GET /customers — list customers/tenants
- GET /customers?fullName=John+Smith — search by name
- GET /checks — list checks (filter by cleared status for uncleared)
- GET /bill-payments — list bill payments
- POST /deposits — create a deposit entry

## CRITICAL: Error Handling
EVERY Conductor call must be followed by an IF node:
- If status !== 200 or error → send email to Navid + Yair
- Subject: "Automation Paused — QuickBooks Connection Issue"
- Body: explain QB may be in Single-User Mode or offline

## Notes
- Real-time — no cache. If QB machine is off, calls fail.
- QB must stay in Multi-User Mode 24/7
- $49/month per company file. Altmark needs ~30 files.
