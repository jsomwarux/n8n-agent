Test a deployed n8n workflow.

$ARGUMENTS: The workflow name or webhook path to test.

Steps:
1. Find the workflow in the workflows/ folder
2. Identify the trigger type (webhook, schedule, etc.)
3. If webhook: generate a curl command with realistic sample data
   - If a niche brief exists, use it to create realistic test data
   - Show the curl command to the user
   - Run the curl command
   - Display the response
4. If schedule: trigger a manual execution via n8n-mcp
5. Check the execution result for errors
6. Report: success/failure, response time, any error details
