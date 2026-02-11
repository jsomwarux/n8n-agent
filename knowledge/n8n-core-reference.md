# n8n Core Reference

## Key Concepts

### Workflows
- A workflow is a series of connected nodes that process data
- Workflows can be triggered by: webhooks, schedules (cron), manual execution, or other workflows
- Every workflow should have error handling

### Nodes
- Nodes are the building blocks of workflows
- Types: Trigger nodes (start a workflow), Action nodes (do something), Logic nodes (control flow)
- Key nodes for ensemble workflows:
  - HTTP Request: call external APIs (used for LLM calls)
  - Code: run JavaScript or Python
  - Merge: combine data from parallel branches (use "Wait for All" mode for ensembles)
  - Set: transform or create data
  - If: conditional routing
  - Switch: multi-path routing
  - Error Trigger: catch errors from other nodes
  - Webhook: receive incoming HTTP requests

### Expressions
- n8n uses its own expression syntax: {{ $json.fieldName }}
- Access previous node data: {{ $('NodeName').item.json.field }}
- Access all items: {{ $('NodeName').all() }}
- Current item index: {{ $itemIndex }}
- Built-in methods: $now, $today, $if(condition, true, false)

### Error Handling
- Error Trigger node: catches errors from any node in the workflow
- Retry on Fail: set on individual nodes (Settings tab → Retry on Fail)
- Continue on Fail: node continues even if it errors (use sparingly)
- Try/catch in Code nodes: ALWAYS wrap code in try/catch

### Credentials
- Store API keys in Settings → Credentials, never in workflow JSON
- Reference by name in node configuration
- Credential types: Header Auth, Bearer Token, OAuth2, Basic Auth, etc.

### Data Flow
- Data flows as arrays of items (objects with a .json property)
- Each node receives items from the previous node
- Merge node combines items from multiple branches
- Code nodes must return an array of items: return [{ json: { ... } }]

## Common Patterns

### Webhook → Process → Respond
The simplest workflow pattern. Webhook receives data, Code node processes it,
Respond to Webhook node sends the result back.

### Parallel Processing (Ensemble Pattern)
Webhook → Preprocess → Split into parallel branches → Merge (Wait for All) → Consensus → Respond
Used for 4-LLM ensemble workflows.

### Schedule → Fetch → Store
Cron trigger → HTTP Request to fetch data → Database or file node to store results.
Used for periodic data collection.

### Error Handling Pattern
Every production workflow needs:
1. An Error Trigger node connected to a notification node (email, Slack, webhook)
2. Retry settings on all HTTP Request nodes
3. try/catch in all Code nodes
4. A Set node logging success/failure for monitoring

## Documentation Lookup
For any n8n topic not covered here, use the context7 MCP server to look up
current documentation. Do NOT try to fetch URLs from docs.n8n.io directly.
