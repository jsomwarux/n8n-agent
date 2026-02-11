Switch context to a different client.

$ARGUMENTS: The client name (folder name under clients/).

Steps:
1. Verify clients/$ARGUMENTS/ exists. If not, list available clients.
2. Read tasks/lessons.md (GLOBAL lessons from all clients).
3. Read clients/$ARGUMENTS/tasks/todo.md for current state.
4. Read clients/$ARGUMENTS/brief.md for industry context.
5. Read clients/$ARGUMENTS/README.md for overview.
6. Summarize: what has been built so far, any open tasks, any relevant
   lessons from past workflows (any client).
7. Ask what the user wants to do next.

IMPORTANT: After switching, all workflow files go in clients/$ARGUMENTS/ only.
But lessons ALWAYS go in the global tasks/lessons.md.
