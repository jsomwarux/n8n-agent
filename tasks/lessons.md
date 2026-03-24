# Lessons Learned

1. **n8n expressions do not support optional chaining (`?.`)**. Use ternary operators instead:
   `$json.workflow ? $json.workflow.name : 'fallback'` not `$json.workflow?.name`.

2. **Webhook responseNode mode requires `onError: "continueRegularOutput"`** on the Webhook node,
   otherwise validation fails.

3. **If node with error routing needs `onError: "continueErrorOutput"`** when connections
   exist on the second (false/error) output.

4. **N8N_API_URL and N8N_API_KEY must be set** as environment variables for deploy/test via MCP tools.
   Without them, workflow can only be saved as JSON and imported manually.

5. **If node `conditions.options` requires a `version` field**. For typeVersion 2.2, set `version: 2`.
   Without it, workflow creation via API fails with: `Missing required field "conditions.options.version"`.

6. **Use `activateWorkflow` operation type** (not `activate`) in `n8n_update_partial_workflow` to activate a workflow.

7. - [glow-index/skincare-analysis]: **Code node `}}` triggers false positive expression validation errors**. The validator misinterprets `return [{ json: {...}}]` closing braces as unmatched n8n expression brackets. These are safe to ignore — Code nodes execute JavaScript, not n8n expressions.

8. - [glow-index/skincare-analysis]: **For large Code nodes, use `n8n_update_partial_workflow` with `updateNode` + `parameters.jsCode`** after creating the workflow with placeholders. Avoids hitting parameter size limits on the initial create call.

9. - [glow-index/skincare-analysis]: **Merge node in append mode (typeVersion 3.2) with `numberInputs: 4`** collects items from 4 parallel branches. Connect each branch to a different input index (0-3). Items arrive in input index order.

10. - [glow-index/skincare-analysis]: **For 4-LLM ensemble, build API request bodies in a Code node and pass via `JSON.stringify()` expression** in HTTP Request jsonBody. Pattern: Code node outputs `{ claudeBody: {...}, gptBody: {...}, ... }`, HTTP Request uses `={{ JSON.stringify($('CodeNode').item.json.claudeBody) }}`.

11. - [glow-index/skincare-analysis]: **Credential types from database**: anthropicApi, openAiApi, googlePalmApi (for Gemini), xAiApi (for Grok). Use `authentication: "predefinedCredentialType"` with matching `nodeCredentialType` on HTTP Request nodes.

12. - [glow-index/skincare-analysis]: **Anthropic API needs explicit `anthropic-version: 2023-06-01` header** via sendHeaders even when using predefined credentials. The credential handles `x-api-key` but not the version header.

13. - [construction-demo]: **n8n Code nodes cannot use `require('fs')` — the JS Task Runner sandbox disallows Node.js modules**. Use HTTP Request nodes to send data externally (webhook.site) instead of writing to local files. Generate demo output files by extracting execution data via the API post-run.

14. - [construction-demo]: **n8n Set node (typeVersion 3.4) only outputs assigned fields by default — drops all input fields**. Use Code nodes with spread operator (`{ ...d, newField: value }`) instead of Set nodes when you need to preserve upstream data.

15. - [construction-demo]: **HTTP Request nodes replace `$json` with their response body**. Any downstream nodes referencing `$json.field` will get the HTTP response, not the workflow data. Place HTTP Request nodes at the END of the data pipeline, or use `$('NodeName').item.json.field` to reference upstream data.

16. - [construction-demo]: **Webhook responseMode "immediately" is not valid in n8n 2.10+**. Use `"onReceived"` instead. The valid values are: `onReceived`, `lastNode`, `responseNode`.

17. - [construction-demo]: **n8n API PATCH /workflows/{id} does NOT update nodes** — it only updates top-level workflow fields (name, active, settings). To update nodes, delete the workflow and recreate it, or use the n8n editor UI.

18. - [construction-demo]: **Gmail and Google Sheets nodes do NOT pass `$json` forward** — after either node executes, `$json` in all downstream nodes contains the API response (Gmail message metadata or Sheets row result), NOT the original workflow data. Always use explicit upstream references: `$('NodeName').item.json.field` for any node that runs after Gmail or Sheets.

19. - [construction-demo]: **Wait nodes break `$json` data continuity** — after a Wait node resumes, `$json` from before the wait is not reliably available. Any node after a Wait node must reference upstream data explicitly with `$('NodeName').item.json.field` rather than `$json.field`.

20. - [construction-demo]: **Gmail node `.split` error means `sendTo` received undefined** — this is caused by `$json.customer_email` being empty because a data-losing node (Gmail, Sheets, Wait) ran upstream. Fix: replace `$json.customer_email` with `$('UpstreamNode').item.json.customer_email` pointing to the last node that still had the original payload.

21. - [construction-demo]: **Designate one pre-branch node as the canonical data source** — when a workflow has an IF branch (e.g. emergency vs standard), data on each branch path is independent. Pick one upstream node that runs before the branch (e.g. `Build Invoice Summary`) and reference ALL downstream data from it using `$('Build Invoice Summary').item.json.field`. Never assume `$json` has the full payload after a branch rejoins.

22. - [construction-demo]: **Google Sheets "Forbidden" error = API not enabled OR credential issued before API was enabled** — fix order: (1) enable Google Sheets API in Google Cloud Console, (2) delete and reconnect the credential in n8n so the token is reissued with correct scopes. Re-authorizing alone is not enough if the API wasn't enabled when the token was first issued.

23. - [construction-demo]: **Sheets `defineBelow` mapping silently writes empty for undefined expressions** — if `$json.field` is undefined, the column writes blank with no error. Only ternary expressions like `$json.flag ? 'Y' : 'N'` write a value because they evaluate to a default. This makes data flow bugs invisible in Sheets output. Validate all column expressions resolve to real values before deploying.

24. - [construction-demo]: **n8n PUT /workflows/{id} body must contain ONLY: name, nodes, connections, settings, staticData** — sending any additional top-level fields (id, createdAt, updatedAt, active, etc.) returns "request/body must NOT have additional properties". Always strip the response object down to these five fields before PUT.

25. - [construction-demo]: **Always fetch a fresh copy of the workflow immediately before making changes**

26. - [wholesale-demo]: **n8n API responses for workflows containing Code nodes include raw tab/newline characters inside jsCode strings** — these are valid JSON escape sequences within the code but cause Python's `json.load()` to throw "Invalid control character" errors. Fix: read the raw bytes, run `re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', ' ', raw)` before parsing. Always use this pattern when fetching workflows with Code nodes.

27. - [wholesale-demo]: **Setting `authentication: "genericCredentialType"` without a matching credential defined causes HTTP Request nodes to silently fail** — use `authentication: "none"` and pass API keys explicitly via `headerParameters` when you don't have an n8n credential object for the service. This is the correct pattern for OpenRouter, Slack, and any other service where the key is embedded directly.

28. - [wholesale-demo]: **Google Sheets append fails with column mismatch when a sheet tab already has different column headers** — if the tab has Construction Demo columns (Job ID, Customer Name...) and you try to append Wholesale Demo columns (PO Number, Supplier...), n8n errors. Fix: target a different named tab per workflow (e.g. "Wholesale PO Log"). Set `onError: continueRegularOutput` on the Sheets node so the workflow completes for demo purposes even before the tab is created.

30. - [general]: **Each failed POST /workflows creates a new duplicate workflow** — failed deployments don't clean up after themselves. Always check for and delete duplicate workflows after a debugging session: `curl "http://localhost:5678/api/v1/workflows" | grep -count the name`. Keep only the active/Published one, delete the rest via DELETE /workflows/{id}.

29. - [wholesale-demo]: **New Google Sheets tab must be created manually before first append** — n8n's Sheets `append` operation cannot create a new tab; it only writes to an existing one. When targeting a new tab name ("Wholesale PO Log"), the tab must exist in the spreadsheet first. Manual step: open the sheet, click + to add tab, name it correctly, add header row. Alternative: set `continueOnFail` so demo runs to Slack/Gmail regardless.

30. - [general]: **Always fetch a fresh copy of the workflow immediately before making changes** — never reuse a previously saved local file. Each fix must start with a fresh API fetch (`GET /workflows/{id} > /tmp/wf_fresh.json`), or earlier fixes already pushed will be silently overwritten by the stale local copy.

31. - [lead-qualification-demo]: **`authentication: null` (JSON null) vs `authentication: "none"` (string) are not equivalent** — when authentication is null, n8n does not send custom `headerParameters` at all, even if `sendHeaders: true`. The Authorization Bearer token is silently dropped. Always explicitly set `authentication: "none"` (the string) for any HTTP Request node using manual header-based auth. Root cause: Opus sometimes writes `authentication: None` in Python which serializes to JSON null.

32. - [lead-qualification-demo]: **HubSpot CRM v3 API rejects unknown contact properties with 400 PROPERTY_DOESNT_EXIST** — custom properties (`lead_tier`, `lead_score`, `notes_last_body`) must be created in HubSpot before they can be written via the API. For demo workflows, restrict the contact payload to standard properties only: `email`, `firstname`, `lastname`, `phone`, `company`, `hs_lead_status`. If AI metadata must be stored, use the `message` field (free-text) and write the score/tier/reasoning as a concatenated string.

33. - [lead-qualification-demo / support-triage-demo]: **`JSON.stringify` in `jsonBody` behaves differently depending on the target API and body mode — know which pattern to use:**
   - **Slack / simple outgoing webhooks**: use `specifyBody: "json"` + `sendBody: true` + `jsonBody: "={{ JSON.stringify({ text: '...' + $json.field }) }}"` — this works because n8n passes the resulting string directly as the raw body. Required pattern for Slack.
   - **REST APIs expecting structured JSON objects (HubSpot, OpenRouter, etc.)**: use `specifyBody: "json"` + `sendBody: true` + `jsonBody: "={{ { "properties": { "email": $('Node').item.json.email } } }}"` — no JSON.stringify. n8n serializes the returned object automatically. Using JSON.stringify here causes blank/empty properties.
   - **Root rule**: `JSON.stringify` works when n8n should treat your expression output as a raw string body. Direct object expression works when n8n should serialize the object itself. When in doubt, match the pattern used by other working nodes in the same workspace.

34. - [lead-qualification-demo]: **Sheets `defineBelow` column names must exactly match the tab's header row** — if the workflow maps `"First Name"` and `"Last Name"` but the sheet header says `"Lead Name"`, the append node returns success but writes zero data (silently). Always check the actual header names in the sheet before defining the column mapping. For combined name fields, use a single column `"Lead Name"` mapped to `={{ $('Node').item.json.first_name + ' ' + $('Node').item.json.last_name }}`.

35. - [lead-qualification-demo]: **For multi-path IF workflows (hot/cold branches), duplicate the Sheets/summary nodes on each path** rather than trying to merge branches with a Merge node. Two separate Sheets append nodes targeting the same tab is cleaner and avoids Merge node item-count issues in n8n 2.10+.

36. - [insurance-claims-demo]: **`defineBelow` column mapping with complex expressions throws "Could not get parameter" silently** — n8n evaluates all column expressions at node-config time, not just runtime. Complex expressions referencing nested fields or using operators like `?.` cause the entire Sheets node to fail with `{"error": "Could not get parameter"}` routed as regular output (invisible if `onError: continueRegularOutput` is set). **Permanent fix: always add a dedicated Code node ("Prep Sheets") immediately before any Google Sheets node** — build a flat object with keys matching headers exactly, then use `mappingMode: "autoMapInputData"` on the Sheets node. This is the only reliable pattern for Sheets in n8n.

37. - [support-triage-demo]: **HTTP Request nodes require `sendBody: true` explicitly** — without this flag, the `jsonBody` expression is ignored entirely and no body is sent. Target APIs return errors like `"400 - invalid_payload"` (Slack), `"Bad request"`, or `"JSON parsing failed"`. The error looks like a payload format issue but is actually a missing body entirely. Always include `sendBody: true` alongside `specifyBody: "json"` and `jsonBody`. Root cause: the property is not inferred from the presence of `jsonBody`. Tip: compare against a known working Slack node in the same workspace — if it has `sendBody: true` and yours doesn't, that's the bug.

38. - [support-triage-demo]: **Webhook nodes require a `webhookId` field for proper registry registration** — when creating workflows via the API, Webhook nodes must include a `webhookId` field (e.g. `"webhookId": "support-triage-webhook"`) in addition to `parameters.path`. Without it, the webhook returns 404 even after the workflow is activated. This field is what n8n uses to track and register the endpoint in its webhook registry.

39. - [support-triage-demo]: **n8n IF node (v2.2) filter `conditions` structure: `combinator` must be a TOP-LEVEL field of the `conditions` object, not inside `options`** — the correct shape is `{ "combinator": "or", "conditions": [...], "options": {} }`. Placing `combinator` inside `options` (`{ "options": { "combinator": "or" }, "conditions": [...] }`) causes `executeFilter` to receive `undefined` for `value.combinator`, which makes it return `false` regardless of input — BUT n8n's `getNodeParameter` with `extractValue: true` resolves this to a truthy default, routing ALL items to branch 0 (true). Symptom: every ticket hits the escalation path, no matter what the condition evaluates to.

40. - [support-triage-demo]: **When multiple data-consuming nodes are chained (Slack HTTP → Gmail → Sheets), EACH one resets `$json`** — the data loss compounds. After Slack runs, `$json` = Slack API response. After Gmail runs, `$json` = Gmail metadata. After Sheets runs, `$json` = Sheets row result. By the time you're 3 nodes deep, every `$json.ticket_id` etc. is undefined. Symptom: only fields with hardcoded values (like `new Date()`) appear in Sheets; all dynamic fields are blank. **Fix**: designate the last Code/prep node BEFORE the first HTTP/Gmail/Sheets node as the canonical data source. Reference ALL downstream data from it: `$('Prep Escalation Data').item.json.field`. Never rely on `$json` after any data-consuming node in a multi-step output chain.

41. - [support-triage-demo]: **String concatenation inside `jsonBody` n8n expressions breaks with real-world data containing special characters** (em-dashes, curly quotes, newlines, etc.) — `JSON.stringify({ text: '...' + $json.subject + '...' })` works fine with clean test data but fails with `400 - "invalid_payload"` when field values contain characters the n8n expression engine mishandles. **Permanent fix**: build message strings in the upstream Code node using proper Node.js template literals, add as a `slack_text` field to the output, then reference it simply in the Slack node: `jsonBody: "={{ JSON.stringify({ text: $json.slack_text }) }}"`. No string concatenation in n8n expressions — all string work happens in Code nodes.

42. - [general]: **`webhook-test/{path}` serves the editor in-memory state, NOT the saved workflow** — API changes (PUT /workflows/{id}) update the saved workflow only. The test endpoint (`webhook-test/`) reflects whatever is currently loaded in the n8n browser tab. If the tab was open before API changes were made, it runs the old version. Always close and reopen the workflow in the editor after API updates before using `webhook-test`. For reliable testing of API-deployed changes, use the production endpoint `webhook/{path}` instead.

43. - [pm-maintenance-triage]: **Reusable T2 templates need a 'configurable parameters' section upfront** — document all per-prospect variables (intake method, vendor routing sheet ID, SLA windows, escalation contact) before building, not after. Makes the 2-hour configuration handoff clean. Template-config.md as a standalone file separate from the brief is the right pattern.

44. - [construction-job-tracker]: **WhatsApp-triggered workflows need the foreman input structured upfront** — the workflow is only as good as what the foreman sends. Design the intake prompt (job site, % complete, blockers, photo URL) as a WhatsApp message template foremen can copy-paste, not free-form text. Claude can handle variance but structured input cuts triage errors significantly. Include the intake prompt in template-config.md, not just the n8n webhook spec.

45. - [pm-maintenance-triage]: **n8n Code node sandbox blocks ALL external HTTP — require(), fetch(), AND axios are all disallowed.** The only way to make an HTTP call from a workflow is via an HTTP Request node. If you need Claude/OpenRouter in a workflow, it MUST be an HTTP Request node, not a Code node. Rule-based logic in Code nodes is a valid demo fallback that proves the routing/dispatch pattern end-to-end.

46. - [pm-maintenance-triage]: **httpHeaderAuth credential bound to HTTP Request node still returns "Invalid bearer token" in some n8n versions** — even when the credential is correctly created with `name: Authorization, value: Bearer sk-or-...` and the API key tests as valid via direct curl. Root cause unclear (possible n8n version-specific bug or header name conflict). Working workaround per lesson #27: use `authentication: "none"` (string, NOT null) + explicit `headerParameters` with `name: Authorization, value: Bearer [key]`. If that also fails, fall back to rule-based Code node for demos.

47. - [pm-maintenance-triage]: **Google Sheets OAuth token issued before the Sheets API is enabled in Google Cloud Console will silently fail even after API enablement** — the token must be re-issued (delete + reconnect the credential in n8n UI) after enabling the API. See lesson #22. Enabling the API alone is not enough. Lesson #22 covers this but it's worth repeating: API enable → delete credential → reconnect → test.

48. - [general]: **For n8n builds: Eve should spawn the Claude Code ACP agent (coding-agent skill), not build via Python exec scripts directly.** The n8n agent reads lessons.md at session start per CLAUDE.md. Eve running Python scripts directly bypasses the entire lessons system. If Eve builds n8n workflows herself, she MUST read lessons.md before starting and apply all relevant lessons. The failure to do this on pm-maintenance-triage caused 6+ failed iterations on issues already documented (auth:none, Code node HTTP, Sheets API timing).

49. - [general]: **Clean up orphaned/failed workflows after every debugging session.** Each failed POST /workflows creates a new duplicate. Always delete test workflows before ending the session. Pattern: `curl "http://localhost:5678/api/v1/workflows" | grep id+name`, delete all but the active one. Left 4 orphaned workflows (LZICFo0c47qhUxvx, UH2UdGiFgVkhtmA3, RxKJ55LcH3tZUI2n, LjTtERNQbYP3ZyZv) during pm-maintenance-triage debugging.

50. - [glow-index/skincare-analysis]: **n8n webhook node typeVersion 2+ (including 2.1) generates a compound path: `workflowId/nodeName/path` instead of just `path`.** The registered URL becomes `webhook/LNae5xv5dmIi6nBP/webhook/skincare-analysis` not `webhook/skincare-analysis`. This is confirmed by checking the `webhook_entity` table in `~/.n8n/database.sqlite`. The node name is URL-encoded into the path ("Webhook Trigger" → "webhook%20trigger"). To use a clean simple path, the node name must contain no spaces (e.g. rename to "Webhook"). But even then, compound path generation persists in some workflows. **Safest approach**: after activating a webhook workflow, always verify the actual registered path by querying the DB directly: `sqlite3 ~/.n8n/database.sqlite "SELECT webhookPath FROM webhook_entity WHERE workflowId='<id>'"`. Use that exact path in all downstream integrations.

51. - [glow-index/skincare-analysis]: **`n8n-nodes-base.webhook` typeVersion 2+ nodes have an `executeData` field added to them at runtime** — this is not a valid schema field and causes `PUT /workflows/{id}` to return `400: request/body/nodes/{n} must NOT have additional properties`. Always strip `executeData` (and `webhookId` from old workflows) from all nodes before PUTting. Pattern: `for node in nodes: node.pop('executeData', None); node.pop('webhookId', None)`.

52. - [glow-index/skincare-analysis]: **For existing workflows being updated via API: fetch fresh, strip invalid fields, apply changes, PUT — in that exact order every time.** Never use a locally cached copy of the workflow JSON from a previous API call or source file. The workflow state in n8n includes runtime fields (`executeData`, `versionId`, `activeVersionId`, `versionCounter`) that change on every PUT and cause stale-copy PUTs to fail silently or partially. Always GET → modify in-memory → PUT.

## n8n Version & DB Management

53. - [ops/n8n-recovery]: **n8n crashes with "EntityMetadataNotFoundError: No metadata for InstalledPackages" when the SQLite DB has a corrupted community packages table.** Fix: set env var `N8N_COMMUNITY_PACKAGES_ENABLED=false` before starting. Add permanently to `~/.zshrc`. Do NOT rely on `~/.n8n/config` file — the entity registers before config loads, so the file-based disable doesn't work. Only the env var works reliably.

54. - [ops/n8n-recovery]: **Always pin n8n to `@latest` and keep it updated.** Workflows built on a newer version will show "Install this node" errors on older installs — not because they use community nodes, but because `typeVersion` numbers advance with n8n releases. httpRequest v4.4, googleSheets v4.7 require a recent n8n. Running `npm install -g n8n@latest` fixes these without any workflow changes.

55. - [ops/n8n-recovery]: **After any n8n reinstall or DB restore, credentials must be relinked in the UI even if they exist in the DB.** The credential data is there, but node→credential associations need to be re-selected. Open each greyed node → click credential dropdown → select existing credential. Do not re-enter keys.

56. - [ops/n8n-recovery]: **Export all workflow JSONs to `~/projects/n8n-agent/` after every build session.** If only the SQLite DB is the backup, a version mismatch during reinstall can make workflows uneditable until n8n is updated. JSON exports are version-agnostic and importable on any n8n instance. Command: in n8n UI → workflow → ⋮ menu → Download.

57. - [ops/n8n-recovery]: **Slack credential type is `slackApi` (requires bot token `xoxb-...`), NOT `slackIncomingWebhook`.** Webhook URLs work for HTTP Request nodes only. Slack node requires OAuth bot token from api.slack.com/apps → OAuth & Permissions. HubSpot credential type is `hubspotApi` with field name `apiKey` (not `accessToken`) — despite HubSpot calling it a "private app access token."

58. - [georgetown-city-services]: **OpenRouter model IDs use dots not dashes for version numbers** — `anthropic/claude-3.5-haiku` NOT `anthropic/claude-3-5-haiku-20241022`. Always verify model ID against OpenRouter's /api/v1/models endpoint before building. The `-20241022` date suffix is not used by OpenRouter.

59. - [georgetown-city-services]: **AI classification prompts need explicit department routing rules** — listing department names as pipe-separated options is not enough. The AI will pick any department that sounds reasonable. Add a dedicated "ROUTING RULES" section with explicit mappings: `drainage or flooding -> "D&I Authority"`, `garbage -> "M&CC Sanitation"`, etc. This eliminates department misclassification.

60. - [georgetown-city-services]: **n8n IF node v2.2+ conditions.options requires: version (2), leftValue (""), caseSensitive (true), typeValidation ("strict")** — the MCP validator rejects IF nodes missing any of these fields. The existing working Support Triage workflow only has `caseSensitive` because it was created via the UI (which doesn't validate as strictly). When creating via API/MCP, include all four fields.

61. - [georgetown-city-services]: **Slack API credential with `incoming-webhook` scope cannot post via chat.postMessage** — it needs `chat:write` scope. If the Slack app only has webhook permissions, use the webhook URL with an HTTP Request node instead of the Slack API endpoint. Check scopes at api.slack.com/apps before choosing the integration method.

62. - [georgetown-city-services]: **For Code node jsCode updates via API, write .js files to disk and use Python to construct the JSON payload** — avoids JSON string escaping issues with newlines, quotes, and special characters in JavaScript code. Pattern: write .js files → Python reads files → constructs proper JSON → PUT /workflows/{id}. The MCP partial update tool works for simple code but the file-based approach is more reliable for complex multi-line Code nodes.

## Prisma 7 + PostgreSQL (Supabase)

[glow-index/supabase-migration]: Prisma 7 does NOT support `url = env("DATABASE_URL")` in schema.prisma. The datasource block must be URL-free (`provider = "postgresql"` only). URL goes in `prisma.config.ts` under `datasource.url`. Putting it in the schema causes P1012 validation error.

[glow-index/supabase-migration]: Prisma 7 requires a driver adapter even for standard PostgreSQL — `new PrismaClient()` alone throws "needs non-empty PrismaClientOptions". Use `@prisma/adapter-pg` with a `pg.Pool`: `const pool = new pg.Pool({ connectionString: process.env.DATABASE_URL }); const adapter = new PrismaPg(pool); new PrismaClient({ adapter })`.

[glow-index/supabase-migration]: When switching from SQLite to PostgreSQL in Prisma 7, remove `@prisma/adapter-better-sqlite3` import and install `@prisma/adapter-pg` + `pg` + `@types/pg`. Update lib/db.ts, seed script, and any other direct PrismaClient instantiation.

[georgetown/city-services-agent]: When replacing a node type via API (e.g. HTTP Request → Gmail), the connections object uses node **names** not node IDs. If you rename the node, update both the connection key AND any edge `"node"` values pointing to it — otherwise the workflow silently loses its connections and fails to activate.

[georgetown/city-services-agent]: When swapping a node type via PUT /workflows/{id}, match the `typeVersion` exactly to another working node of the same type already in the workflow. Mismatched typeVersion (e.g. 2.1 vs 2.2 for Gmail) causes "could not be started" activation errors with no clear error message.

[georgetown/city-services-agent]: When updating a Code node's output fields, audit ALL downstream nodes that reference those fields before saving. Removing a field (e.g. `citizen_email`) breaks every node that references it, even nodes not directly connected to the Code node.

63. - [nash-satoshi/token-analysis]: **MCP validator reports false positives for Merge node input counts** — when a Merge node uses `numberInputs: 4`, the validator still reports "exceeds its input count (2)" for connections targeting inputs 2 and 3. These are safe to ignore — the `numberInputs` parameter dynamically expands inputs at runtime. The workflow activates and executes correctly despite these validation errors.

64. - [nash-satoshi/token-analysis]: **For IF node reconvergence without a Merge node, connect both branch outputs to the same downstream node(s)** — instead of using a Merge node after an IF branch (which would hang waiting for the inactive branch), connect both true-branch and false-branch end nodes directly to the same downstream node at input 0. Only one branch fires, so the downstream node receives exactly one item. This avoids the need for Merge "chooseBranch" mode.

65. - [nash-satoshi/token-analysis]: **`n8n_update_partial_workflow` uses `updates` not `properties`** — the correct structure is `{type: "updateNode", nodeName: "My Node", updates: {"parameters.jsCode": "..."}}`. Using `properties` instead of `updates` causes "Missing required parameter 'updates'" error.

66. - [nash-satoshi/token-analysis]: **For multi-stage LLM pipelines, `responseMode: "onReceived"` is essential** — webhook should respond immediately (202 Accepted) because the full pipeline (research + 4-LLM analysis + deliberation + aggregation) takes several minutes. The caller gets an immediate response; results are sent back via callback webhook when complete.

67. - [nash-satoshi/token-analysis]: **Reuse existing n8n credentials by ID** — instead of creating new credentials or hardcoding API keys, reference existing credentials: `credentials: {"httpHeaderAuth": {"id": "eKuUbdByJmAQfvxu", "name": "OpenRouter Header Auth"}}`. Check working workflows for credential IDs.

68. - [nash-satoshi/token-analysis]: **Multi-stage LLM pipelines (10+ API calls) take ~4 minutes, not seconds** — webhook-triggered executions that appear "stuck" with 0 nodes may simply be running. The n8n execution API shows `status: "running"` and `executedNodes: 0` while early nodes execute. Check back after 3-5 minutes before debugging. Both test executions completed successfully with all 27 nodes in ~255 seconds.

69. - [nash-satoshi/token-analysis]: **`jsonBody: "={{ $json.requestBody }}"` (no JSON.stringify) works for passing OpenRouter API bodies** — Code nodes output `{ requestBody: { model: '...', messages: [...] } }` and HTTP Request nodes reference it directly. This matches the Glow Index pattern and avoids double-serialization issues. The `specifyBody: "json"` mode handles serialization automatically.

70. - [nash-satoshi/token-analysis]: **38-node 4-LLM ensemble workflow architecture (v2 with real research)**: Webhook → Extract → IF(source) → CoinGecko|DexScreener → Parse → parallel(2x Brave Search + LunarCrush + Brave Social) → Merge nodes → Code synthesis → OpenRouter synthesis LLMs → Merge Research → Combine → Build S2 → 4x parallel LLM → Merge → Build S3 → 4x parallel LLM → Merge → Build S4 → Aggregation → Format → Send. Error Trigger → Error Format → Send Failure. 38 nodes, 12 LLM/API calls per execution.

71. - [nash-satoshi/token-analysis]: **For parallel HTTP requests that must merge before a Code node, use a Merge node (append, numberInputs: 2) as a "wait gate"** — Code nodes only have 1 input. To collect results from 2 parallel HTTP Request nodes (e.g. two Brave searches), connect each to a separate Merge node input, then connect the Merge output to the Code node. The Code node receives all items via `$input.all()` and can reference specific items by index (input 0 = first branch, input 1 = second branch).

72. - [nash-satoshi/token-analysis]: **Brave Search API uses `X-Subscription-Token` header (not `Authorization: Bearer`)** — pass via inline `headerParameters` with `authentication: "none"`, NOT via stored credentials. URL pattern: `https://api.search.brave.com/res/v1/web/search?q={encoded_query}&count=5`. Response structure: `{ web: { results: [{ title, description, url }] } }`.

73. - [nash-satoshi/token-analysis]: **LunarCrush public API v4 requires no auth** — endpoint: `https://lunarcrush.com/api4/public/coins/{ticker}/v1`. Returns: galaxy_score, alt_rank, social_dominance, social_volume, sentiment, interactions_24h. Use `$json.ticker.toLowerCase()` in the URL expression.

74. - [nash-satoshi/token-analysis]: **n8n API POST /workflows creates duplicates on retry** — if the first POST succeeds but response parsing fails (e.g. control chars in Code node jsCode per lesson #26), subsequent retries create additional copies. Always list workflows after import and delete duplicates. The newest (latest createdAt) is the correct one.

75. - [nash-satoshi/token-analysis]: **n8n API POST /workflows/\{id\}/activate uses POST not PATCH** — PATCH returns empty/malformed response. POST returns the full workflow with `"active": true`.

76. - [nash-satoshi/token-analysis]: **n8n v2+ blocks `executeCommand` node by default** — activation fails with "Unrecognized node type: n8n-nodes-base.executeCommand". Root cause: n8n v2 added default `NODES_EXCLUDE` that blocks executeCommand and localFileTrigger for security. Fix: set `NODES_EXCLUDE='["n8n-nodes-base.localFileTrigger"]'` env var (removing executeCommand from blocklist) OR add `"nodes": { "exclude": ["n8n-nodes-base.localFileTrigger"] }` to `~/.n8n/config`. Requires n8n restart. Source: community.n8n.io/t/234260.

77. - [nash-satoshi/token-analysis]: **n8n API key lives in `user_api_keys` table, not `user`** — in n8n 2.12.x, `sqlite3 ~/.n8n/database.sqlite "SELECT apiKey FROM user_api_keys LIMIT 1;"` (not `SELECT apiKey FROM user`).

78. - [nash-satoshi/token-analysis]: **Deactivate before deleting n8n workflows via API** — `DELETE /api/v1/workflows/{id}` may silently fail if the workflow is active. Always `POST /workflows/{id}/deactivate` first, then delete.

79. - [glow-index/skincare-analysis-v2]: **Ensemble build rules: n8n = thin wrapper (max 7 nodes), Python FastAPI = all logic.** Moving LLM calls, prompt management, retry/fallback, and aggregation out of n8n Code nodes into a Python FastAPI engine eliminates: n8n sandbox restrictions (no require/fetch/axios), Code node `}}` false-positive validation errors, and the 20+ node complexity of in-n8n ensemble workflows. Pattern: Webhook → Validate → HTTP POST to Python engine → Log Status. Python engine runs as a background service (uvicorn) and handles all async LLM calls with proper asyncio.gather parallelism.

80. - [glow-index/skincare-analysis-v2]: **Store prompts as .txt files in prompts/ dir — never inline.** Assert `len(prompt) > 500` before every LLM call. Prompt templates use Python `str.format()` with named placeholders `{productName}`, `{brand}`, etc. This makes prompts version-controllable and prevents accidental truncation.

81. - [glow-index/skincare-analysis-v2]: **ALL OpenRouter responses use `choices[0].message.content`** — regardless of which model (Claude, GPT, Gemini, Grok). The old n8n workflow used model-specific extractors (content[0].text for Claude, candidates[0].content.parts[0].text for Gemini) but OpenRouter normalizes all responses to the OpenAI format. Never use Anthropic or Google native response formats when going through OpenRouter.

82. - [glow-index/skincare-analysis-v2]: **BRAVE_API_KEY is stored as an n8n `$env` variable, not in ~/.config/env/global.env.** When moving Brave search calls from n8n to Python, the key needs to be added to global.env manually. The Nash Satoshi workflow references it as `={{ $env.BRAVE_API_KEY }}` which only works inside n8n expression context.

## Ensemble Pipeline Builds

**glow-index/nash-satoshi: Always verify model IDs on OpenRouter before hardcoding.**
OpenRouter model IDs use dot separators (claude-sonnet-4.6, claude-opus-4.6), NOT hyphens (claude-sonnet-4-6). GPT-5 and GPT-5.4 do not exist on OpenRouter — use openai/o3 for max OpenAI intelligence. Always run `curl openrouter.ai/api/v1/models | grep <provider>` before finalizing model config.

**glow-index/nash-satoshi: n8n Code nodes cannot use fetch() or $env.VARIABLE — use specific alternatives.**
- HTTP calls from Code nodes: use `this.helpers.httpRequest({method, url, headers, body})` not fetch()
- Environment variables: blocked by default in Code nodes. Hardcode API keys directly OR use n8n Credential Manager for native nodes (HTTP Request node with auth configured)
- localhost vs 127.0.0.1: n8n may resolve localhost as IPv6 (::1) while uvicorn listens on IPv4. Always use 127.0.0.1 explicitly.

**glow-index/nash-satoshi: Validate the callback endpoint exists and accepts unauthenticated test requests before assuming 404 = missing route.**
The Glow Index callback returned 404 because the secret didn't match (intentional — wrong secret = 404). A 404 from a secret-protected route looks identical to a missing route. Test with the correct secret before debugging the route itself.

**glow-index: Python FastAPI engine on Mac mini requires nohup + log redirect for persistence.**
Running uvicorn from terminal means it dies when the terminal closes. Use:
`nohup python3 -m uvicorn main:app --port 8001 --host 127.0.0.1 > /tmp/glow-engine.log 2>&1 &`
Then set up a LaunchAgent after end-to-end flow is confirmed. Log file at /tmp/glow-engine.log is critical for diagnosing silent failures.

**glow-index/nash-satoshi: Model cost optimization for ensemble pipelines (confirmed March 2026).**
Best intelligence-per-dollar on OpenRouter:
- OpenAI: openai/o3 ($2/$8 per M) — better than gpt-4.1, same price. NOT gpt-5 (doesn't exist).
- Google: google/gemini-2.5-pro ($1.25/$10 per M) — cheaper than gemini-3.1-pro-preview ($2/$12), confirmed available.
- Anthropic: anthropic/claude-sonnet-4.6 ($3/$15 per M) — use dot separator, not hyphen.
- xAI: x-ai/grok-4 ($3/$15 per M) — confirmed available and correct.
Cost per ensemble analysis with these models: ~$0.75-0.80 (13 LLM calls, ~31k max output tokens).

**glow-index: n8n HTTP Request jsonBody double-serialization bug with specifyBody: "json".**
When `specifyBody: "json"` and the `jsonBody` field contains `={{ JSON.stringify($json.payload) }}`, n8n double-serializes — the string result gets wrapped in another JSON object, sending malformed body to the target API. Fix: switch to `contentType: "raw"`, `rawContentType: "application/json"`, and set `body` to the stringify expression. This sends the raw string directly without n8n re-wrapping it.

> For Python engine lessons (asyncio, OpenRouter model IDs, Gemini response_format, Python 3.9 types): see docs/agents/ensemble-build-lessons.md

**glow-index: validate the full data chain whenever you change a prompt's output schema.**
When prompts were rewritten to output `base_score` instead of `total`, the validators still checked `total`, stage4 still read `total`, and the frontend verdict component still expected old crypto string values ("CONSUMER WINS"). The system didn't error — it silently produced NaN scores and blank verdicts. Rule: changing a prompt field name requires updating validators.py, stage4_aggregate.py, callback payload, and frontend types simultaneously, not one at a time.

**glow-index: prompt for structured output fields, not free-form reasoning, when frontend needs to display specific data.**
Frontend components were extracting pros, cons, quick takes, and dupe recommendations from raw LLM reasoning text using regex. This produces inconsistent results across models and misses data when phrasing varies. The correct pattern: add explicit structured fields to the prompt output schema (key_findings, red_flags, quick_take, best_dupe) and pass them through the callback payload. Frontend reads fields directly — no regex scraping needed.

[glow-index-engine]: Tailscale Serve is tailnet-only — cloud services (Replit, external webhooks) CANNOT reach it. Use `tailscale funnel --bg --https=<PORT> <local-port>` for any endpoint that needs to be publicly reachable. Serve = private, Funnel = public internet.
[glow-index-engine]: When Replit calls a webhook URL, it's calling from Cloudflare's servers, not from your tailnet. Always test with `curl` from a context outside your network before assuming a URL works.

[ranking-app-factory]: Nash Satoshi framing (game theory, coordination game, exit liquidity) must NEVER leak into other niche apps. When using a reference implementation as a template, strip all domain-specific analytical framing and keep only structural patterns (JSON schema, section headers, scoring rubrics). The meta-prompt for generate-prompts.ts must be domain-neutral — the only framing is "does this [entity] deliver genuine [outcome] relative to [cost/investment]?" Nash Satoshi is crypto-specific and must never be referenced in the prompt generator.

83. - [ranking-app-factory]: **Always include imageStrategy in NicheConfig when seeding products.** Products seeded without images show letter badge fallbacks instead of actual product photos. The imageStrategy field in NicheConfig defines how images are populated: "brave_search" for auto-fetch via Brave Image Search API, "manual" for admin-uploaded, "none" for letter badge only. For brave_search niches, run the backfill script (`scripts/fetch-product-images.py`) immediately after seeding. The admin `/api/fetch-images` endpoint supports both bulk mode (all null-image products) and single-product mode (engine sends `{productId, imageUrl}` after analysis). Brave Image Search uses `X-Subscription-Token` header (not Authorization Bearer) — same as lesson #72.

[ranking-app-factory]: **Replit requires BRAVE_API_KEY in Secrets for image fetch to work.** The /api/fetch-images endpoint reads BRAVE_API_KEY from process.env. Even if the code is deployed, the endpoint returns 500/no-ops silently if the secret is missing. When deploying any ranking app to Replit: add BRAVE_API_KEY to Replit Secrets before running the backfill curl. The backfill curl is: `curl -X POST https://[your-app].replit.app/api/fetch-images -H "x-admin-key: [admin-key]"` — note the path is /api/fetch-images NOT /api/admin/fetch-images.

[ranking-app-factory]: **After any Replit git pull, always run `npm run build` + redeploy.** Pull alone does not rebuild the Next.js bundle. New API routes, component changes, and schema updates are invisible until a fresh build runs. The Replit Deployments tab redeploy button uses the last build — it does NOT re-run `npm run build`. You must run `npm run build` in the Replit Shell first, then redeploy.
