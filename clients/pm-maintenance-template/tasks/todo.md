# PM Maintenance Triage Template — Tasks

## Completed
- [x] Create client folder structure
- [x] Research n8n node schemas (Webhook, HTTP Request, Google Sheets, IF, Code, Send Email)
- [x] Build workflow JSON (16 nodes: webhook, normalizer, AI prompt builder, Claude HTTP, response parser, vendor lookup, dispatch prep, IF emergency branch, emergency alert, vendor email, tenant email, sheets prep, sheets log, response builder, error trigger, error handler)
- [x] Validate workflow with n8n-mcp (0 errors)
- [x] Write template-config.md (12 parameterized fields, vendor sheet schema, log sheet schema)
- [x] Write demo-results.md (3 test cases: routine/urgent/emergency)

## To Do (Before First Prospect Use)
- [ ] Create demo Google Sheet with "Vendors" tab (5 vendors) and "Maintenance Log" tab (header row)
- [ ] Set up SMTP credential in n8n (or swap Email Send nodes to Gmail nodes)
- [ ] Configure Slack webhook URL for emergency alerts (or use another alert channel)
- [ ] Import template into n8n and run 3 live test cases
- [ ] Capture actual demo-results.json with real latency numbers
