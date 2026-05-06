Validate all workflow files.

$ARGUMENTS: Optional client name. If provided, only validate that client's workflows.

Steps:
1. Find all .json workflow files:
   - If a client name is given: `clients/[client]/workflows/*.json`
   - If no client specified: find all .json files in `workflows/` AND
     `clients/*/workflows/`
2. For each file, run `validate_workflow({workflow: <parsed JSON>})`. This
   covers node configs, connections, and expressions in a single pass —
   including the recurring lessons.md issues (IF combinator, sendBody flag,
   webhookId, authentication: "none" string, conditions.options.version).
3. If a workflow is also deployed (matched by name in `n8n_list_workflows`),
   additionally run `n8n_validate_workflow({id})` to validate against the live
   instance.
4. Report results as a table: filename | client | error count | warning count |
   first error. Group output by node so fixes can be batched.
5. If issues are found, ask the user if they want you to fix them.
6. For deployed workflows with auto-fixable issues, use
   `n8n_autofix_workflow({id})`. For local files, fix in-place by re-running
   `validate_node` on each problem node and patching the JSON.
7. Re-run `validate_workflow` until zero errors before reporting done.
