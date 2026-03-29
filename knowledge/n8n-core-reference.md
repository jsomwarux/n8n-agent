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

## MCP Integration (Bidirectional — Shipped April 2025, now stable)

n8n supports MCP on BOTH sides of the equation. This is a significant architecture shift.

### What It Means
n8n can now act as either an MCP **client** (consuming external tools) or an MCP **server** (exposing workflows as tools). Combined, this makes n8n a bidirectional agentic hub — AI agents can call n8n workflows as tools, and n8n AI Agent nodes can consume MCP servers.

### MCP Client Tool Node (n8n consumes MCP servers)
- Add an **MCP Client Tool** sub-node to any AI Agent node
- Points to an external MCP server URL (SSE or Streamable HTTP)
- Agent discovers available tools from the MCP server and invokes them during reasoning
- Supports Bearer token, custom headers, OAuth2 auth
- Tool selection: can expose all tools, select specific ones, or exclude too-powerful ones
- Use case: give an n8n agent access to external capabilities (CRM, Salesforce, custom data sources)

### MCP Server Trigger Node (n8n exposes workflows as tools)
- Add an **MCP Server Trigger** as the entry node of a workflow
- n8n generates a production URL that any MCP-capable client can call
- Clients can list available tools and invoke individual workflows as tools
- Expose n8n sub-workflows using **Custom n8n Workflow Tool** nodes attached to the trigger
- Authentication: Bearer auth or Header auth (configure on the trigger node)
- Test URL vs Production URL: test URL is ephemeral, production URL is stable after workflow publish
- Use case: make n8n workflows callable by Claude, Claude Desktop, any MCP-compatible agent

### Claude Desktop Integration
Connect Claude Desktop to an n8n MCP Server Trigger:
```json
{
  "mcpServers": {
    "n8n": {
      "command": "npx",
      "args": ["mcp-remote", "<MCP_PRODUCTION_URL>", "--header", "Authorization: Bearer <token>"]
    }
  }
}
```

### JT Consulting Relevance
**New pitch pattern (March 2026):** Instead of building a custom webhook endpoint for each Agentforce integration, expose client n8n workflows as MCP tools. Agentforce agents can then call them natively — no custom connector tier needed.

Workflow:
1. Build the automation logic in n8n (workflow handles data fetching, CRM writes, external API calls)
2. Wrap with MCP Server Trigger node
3. Pass the MCP URL to Agentforce as a tool endpoint
4. Result: Agentforce agent calls n8n as a tool, n8n executes the business logic

**Why this matters for the Agentforce pitch:** The integration layer becomes n8n, not a custom Salesforce connector. Client already has n8n. Already has Agentforce on Salesforce. MCP bridges them natively. This reduces scope (no custom platform integration) and uses existing infrastructure.

**Use cases to pitch:**
- Insurance: Agentforce agent calls n8n → n8n queries Epic AMS, returns renewal status
- Wholesale distribution: Agentforce agent calls n8n → n8n queries inventory system, returns stock levels
- Construction/PM: Agentforce agent calls n8n → n8n queries job tracking system, returns open punch list

### Common Patterns

#### Agentforce → n8n (via MCP)
MCP Server Trigger → Custom n8n Workflow Tool (sub-workflow for each capability) → [CRM / API / DB nodes] → Return result

#### n8n AI Agent → External MCP Server
AI Agent Node + MCP Client Tool (points to Salesforce MCP server or any external MCP) → Agent invokes tools as needed

### Nodes Involved
- `MCP Server Trigger` (`@n8n/n8n-nodes-langchain.mcpTrigger`) — expose n8n as MCP server
- `MCP Client Tool` (`@n8n/n8n-nodes-langchain.toolMcp`) — consume external MCP server
- `Custom n8n Workflow Tool` (`@n8n/n8n-nodes-langchain.toolWorkflow`) — expose sub-workflow as tool

## Documentation Lookup
For any n8n topic not covered here, use the context7 MCP server to look up
current documentation. Do NOT try to fetch URLs from docs.n8n.io directly.
