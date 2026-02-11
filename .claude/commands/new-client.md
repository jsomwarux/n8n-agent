Set up a new client project folder.

$ARGUMENTS: The client name (use lowercase-with-dashes, e.g., "apex-plumbing").

Steps:
1. Create the folder structure:
   - clients/$ARGUMENTS/
   - clients/$ARGUMENTS/workflows/
   - clients/$ARGUMENTS/tasks/
   - clients/$ARGUMENTS/tests/

2. Create clients/$ARGUMENTS/README.md with:
   - Client name as heading
   - Sections: Overview, Contact, Workflows Built, Notes
   - Fill in what the user provides, leave placeholders for the rest

3. Create clients/$ARGUMENTS/brief.md using the niche-briefs/TEMPLATE.md format.
   Ask the user to fill in the industry details, or fill in what they provide.

4. Create clients/$ARGUMENTS/tasks/todo.md with:
   "# [Client Name] Tasks\n\nNo active tasks."

5. Create clients/$ARGUMENTS/tests/test-data.json with an empty array: []

6. Do NOT create a per-client lessons.md. All lessons go in the global
   tasks/lessons.md file at the project root.

7. Git commit: git add -A && git commit -m "Set up project folder for [client name]"

8. Tell the user the client project is ready and ask what workflow they want to build.
