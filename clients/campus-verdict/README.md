# Campus Verdict

College analysis platform. n8n handles webhook intake and relay to a Python analysis engine on localhost:8002.

## Workflows

| Workflow | Description | Webhook Path |
|----------|-------------|--------------|
| College Analysis Trigger | Thin webhook relay — validates input, POSTs to engine, returns 202 | `/webhook/college-analysis` |

## Architecture

- **Frontend**: Next.js (separate repo)
- **n8n**: Webhook intake + validation + relay (this repo)
- **Engine**: Python on `localhost:8002` — handles all analysis asynchronously
