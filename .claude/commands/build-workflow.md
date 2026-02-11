Build a production-ready n8n workflow.

$ARGUMENTS: A description of what the workflow should do.

Follow the CLAUDE.md workflow building steps exactly:
1. Understand the request — ask clarifying questions if needed
2. Check niche-briefs/ for relevant industry context
3. Plan — write plan to tasks/todo.md, check in with user
4. Search for nodes using n8n-mcp tools (NEVER guess)
5. Build the workflow with proper node configuration
6. Add error handling on every branch
7. Validate using n8n-mcp validation — fix all errors before proceeding
8. Save to workflows/ folder with a descriptive filename
9. Deploy to n8n instance
10. Generate a curl test command and show it to the user
11. Commit: git add -A && git commit -m "Add [name] workflow"
12. Update tasks/todo.md and tasks/lessons.md
