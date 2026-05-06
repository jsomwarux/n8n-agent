Build a production-ready n8n workflow.

$ARGUMENTS: A description of what the workflow should do.

Follow the CLAUDE.md workflow building steps exactly. The "n8n-mcp Tool Routing"
table in CLAUDE.md → "Rules You Must Follow → n8n API Operations" maps every
n8n API operation to the right MCP tool — use it instead of curl/Python.

1. Understand the request — ask clarifying questions if needed.
2. Check if there is an active client context. If so, read clients/[client]/brief.md
   for industry context. Otherwise check niche-briefs/ for relevant context.
3. Plan — write the plan to the appropriate todo.md (client-specific or root),
   check in with the user.
4. Discover nodes / templates:
   - `search_templates({searchMode: "by_task"})` first — reuse a vetted pattern
     when one exists, then customize.
   - `search_nodes({query})` for each capability not covered by a template.
   - `get_node({nodeType, detail: "standard"})` before configuring any node.
5. Build the workflow node by node. After configuring each node, run
   `validate_node({nodeType, config, mode: "minimal"})`. Do not move on until
   the node validates.
6. Add error handling on every branch (Error Trigger, retries on HTTP, try/catch
   in Code nodes).
7. Run `validate_workflow({workflow})` on the full assembled JSON. Fix every
   error and re-run until clean.
8. Save the workflow JSON:
   - If working on a client: `clients/[client]/workflows/[name].json`
   - If no client context: `workflows/[name].json`
9. Deploy with `n8n_create_workflow` (NOT curl). Run
   `n8n_validate_workflow({id})` against the live instance; if errors are
   auto-fixable, run `n8n_autofix_workflow({id})`. Activate the workflow.
10. Test:
    - For webhooks: generate a curl command, run it, show the response.
    - For other triggers: `n8n_test_workflow(...)`.
    - Inspect with `n8n_executions({action: "list", workflowId, limit: 1})`.
11. Commit: `git add -A && git commit -m "Add [workflow name] for [client name]"`
    (omit "for [client]" if no client context).
12. Update the appropriate todo.md and the global tasks/lessons.md.
