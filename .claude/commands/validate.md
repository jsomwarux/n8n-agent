Validate all workflow files.

Steps:
1. Find all .json files in the workflows/ folder
2. For each one, use n8n-mcp validation tools
3. Check for: missing error handling, unconnected nodes, invalid expressions,
   missing credentials, missing retry/timeout settings
4. Report results as a table showing: filename, status, issues found
5. If issues found, ask the user if they want you to fix them
6. After fixing, re-validate to confirm zero errors
