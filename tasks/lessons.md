# Lessons Learned

1. **n8n expressions do not support optional chaining (`?.`)**. Use ternary operators instead:
   `$json.workflow ? $json.workflow.name : 'fallback'` not `$json.workflow?.name`.

2. **Webhook responseNode mode requires `onError: "continueRegularOutput"`** on the Webhook node,
   otherwise validation fails.

3. **If node with error routing needs `onError: "continueErrorOutput"`** when connections
   exist on the second (false/error) output.

4. **N8N_API_URL and N8N_API_KEY must be set** as environment variables for deploy/test via MCP tools.
   Without them, workflow can only be saved as JSON and imported manually.
