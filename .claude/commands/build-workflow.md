Build a production-ready n8n workflow.

$ARGUMENTS: A description of what the workflow should do.

Follow the CLAUDE.md workflow building steps exactly:
1. Understand the request — ask clarifying questions if needed
2. Check if there is an active client context. If so, read clients/[client]/brief.md
   for industry context. Otherwise check niche-briefs/ for relevant context.
3. Plan — write plan to the appropriate todo.md (client-specific or root), check in with user
4. Search for nodes using n8n-mcp tools (NEVER guess)
5. Build the workflow with proper node configuration
6. Add error handling on every branch
7. Validate using n8n-mcp validation — fix all errors before proceeding
8. Save the workflow JSON:
   - If working on a client: clients/[client]/workflows/[name].json
   - If no client context: workflows/[name].json
9. Deploy to n8n instance
10. Generate a curl test command and show it to the user
11. Commit: git add -A && git commit -m "Add [workflow name] for [client name]"
    (omit "for [client]" if no client context)
12. Update the appropriate todo.md and the global tasks/lessons.md
