Validate all workflow files.

$ARGUMENTS: Optional client name. If provided, only validate that client's workflows.

Steps:
1. Find all .json workflow files:
   - If a client name is given: clients/[client]/workflows/*.json
   - If no client specified: find all .json files in workflows/ AND clients/*/workflows/
2. For each one, use n8n-mcp validation tools
3. Check for: missing error handling, unconnected nodes, invalid expressions,
   missing credentials, missing retry/timeout settings
4. Report results as a table showing: filename, client, status, issues found
5. If issues found, ask the user if they want you to fix them
6. After fixing, re-validate to confirm zero errors
