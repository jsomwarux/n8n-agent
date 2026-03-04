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

25. - [construction-demo]: **Always fetch a fresh copy of the workflow immediately before making changes** — never reuse a previously saved local file. Each fix must start with a fresh API fetch, or earlier fixes already pushed will be silently overwritten by the stale local version.
