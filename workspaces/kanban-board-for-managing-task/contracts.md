## Entity Classification

- **Task**
  - Type: AGGREGATE
  - Evidence: Top-level export `mockTasks = [...]`, each item has a unique `id`.
  - Endpoints: Will create `/api/tasks` for full CRUD operations.

- **Assignee**
  - Type: AGGREGATE
  - Evidence: Top-level export `mockAssignees = [...]`, each item has a unique `id`.
  - Endpoints: Will create `/api/assignees` for full CRUD operations, though current frontend