# API Contracts for Todo App

This document outlines the data models, API endpoints, and integration details for the Todo application's backend, ensuring seamless communication with the frontend.

## 1. Data Models

### TaskStatus (Enum)
Represents the possible statuses for a task.

```typescript
type TaskStatus = "Active" | "Pending" | "Completed";
```

### Task (Response Model)
Represents a single task as returned by the API. Matches `mockTasks` structure.

```typescript
interface Task {
  id: string; // Unique identifier, e.g., MongoDB ObjectId or UUID
  title: string;
  content: string;
  status: TaskStatus;
  created_at: string; // ISO 8601 formatted date string
}
```

### TaskCreate (Request Model)
Represents the data required to create a new task.

```typescript
interface TaskCreate {
  title: string;
  content: string;
  status?: TaskStatus; // Optional, defaults to 'Active' or 'Pending' on backend
}
```

### TaskUpdate (Request Model)
Represents the data for updating an existing task. All fields are optional for partial updates.

```typescript
interface TaskUpdate {
  title?: string;
  content?: string;
  status?: TaskStatus;
}
```

### TaskStats (Response Model)
Represents aggregated statistics for tasks. Matches `mockTaskStats` structure.

```typescript
interface TaskStats {
  total: number;
  active: number;
  completed: number;
  pending: number;
}
```

## 2. REST API Endpoints

All backend API routes MUST be prefixed with `/api`.

### 2.1. List Tasks
- **Endpoint**: `GET /api/tasks`
- **Description**: Retrieves a list of tasks, with optional filtering and pagination.
- **Query Parameters**:
  - `status`: `TaskStatus` (Optional) - Filters tasks by their status (e.g., `Active`, `Completed`, `Pending`).
  - `page`: `number` (Optional, default: `1`) - The page number for pagination.
  - `limit`: `number` (Optional, default: `10`) - The number of items per page.
- **Response**: `200 OK`
```json
{
  "data": [
    { "id": "1", "title": "Plan sprint goals", "content": "...", "status": "Active", "created_at": "..." },
    // ... more tasks
  ],
  "total": 5,
  "page": 1,
  "limit": 10
}
```

### 2.2. Create Task
- **Endpoint**: `POST /api/tasks`
- **Description**: Creates a new task.
- **Request Body**: `TaskCreate`
```json
{
  "title": "Buy groceries",
  "content": "Milk, eggs, bread",
  "status": "Active"
}
```
- **Response**: `201 Created`
```json
{
  "data": { "id": "new-id", "title": "Buy groceries", "content": "...", "status": "Active", "created_at": "..." }
}
```

### 2.3. Get Task by ID
- **Endpoint**: `GET /api/tasks/{id}`
- **Description**: Retrieves a single task by its unique ID.
- **Path Parameters**:
  - `id`: `string` (Task ID)
- **Response**: `200 OK`
```json
{
  "data": { "id": "1", "title": "Plan sprint goals", "content": "...", "status": "Active", "created_at": "..." }
}
```
- **Error**: `404 Not Found` if the task does not exist.

### 2.4. Update Task by ID
- **Endpoint**: `PUT /api/tasks/{id}`
- **Description**: Updates an existing task by its unique ID. Supports partial updates.
- **Path Parameters**:
  - `id`: `string` (Task ID)
- **Request Body**: `TaskUpdate`
```json
{
  "status": "Completed"
}
```
- **Response**: `200 OK`
```json
{
  "data": { "id": "1", "title": "Plan sprint goals", "content": "...", "status": "Completed", "created_at": "..." }
}
```
- **Error**: `404 Not Found` if the task does not exist.

### 2.5. Delete Task by ID
- **Endpoint**: `DELETE /api/tasks/{id}`
- **Description**: Deletes a task by its unique ID.
- **Path Parameters**:
  - `id`: `string` (Task ID)
- **Response**: `200 OK`
```json
{
  "data": { "id": "1", "title": "Plan sprint goals", "content": "...", "status": "Active", "created_at": "..." }
}
```
- **Error**: `404 Not Found` if the task does not exist.

### 2.6. Get Task Statistics
- **Endpoint**: `GET /api/tasks/stats`
- **Description**: Retrieves aggregated statistics for tasks (total, active, completed, pending).
- **Response**: `200 OK`
```json
{
  "data": { "total": 5, "active": 3, "completed": 1, "pending": 1 }
}
```

## 3. Response & Error Format (MUST FOLLOW)

- Successful list responses:
  - `200 OK`
  - Body:
    ```json
    {
      "data": [<Entity>],
      "total": number,
      "page": number,
      "limit": number
    }
    ```

- Successful single-item responses:
  - `200 OK` or `201 Created`
  - Body:
    ```json
    { "data": <Entity> }
    ```

- Error responses:
  - `4xx` / `5xx`
  - Body:
    ```json
    {
      "error": {
        "code": "<MACHINE_READABLE_CODE>",
        "message": "<Human readable message>",
        "details": "optional"
      }
    }
    ```

This format MUST be consistent across all endpoints.
Routers and tests will rely on it.

## 4. Integration Notes

### 4.1. Frontend API Client (`frontend/src/lib/api.js`)
- The frontend will utilize a centralized API client (e.g., `lib/api.js`) to interact with these endpoints.
- It will construct API URLs using `import.meta.env.VITE_API_URL` and append the `/api` prefix.
- Example functions in `api.js`:
  - `getTasks(status, page, limit)`
  - `createTask(taskData)`
  - `getTask(id)`
  - `updateTask(id, taskData)`
  - `deleteTask(id)`
  - `getTaskStats()`

### 4.2. Mock Data Replacement
- The existing `mockTasks` array in `frontend/src/data/mock.js` will be replaced by calls to `GET /api/tasks`.
- The `mockTaskStats` object will be replaced by calls to `GET /api/tasks/stats`.

### 4.3. Error Handling
- The frontend will check the HTTP status code and the `response.ok` property of fetch responses.
- If an error occurs (e.g., `4xx` or `5xx` status), the frontend will parse the error body according to the specified error format and display user-friendly messages based on `error.message`.

### 4.4. Pagination
- The `GET /api/tasks` endpoint supports `page` and `limit` query parameters.
- The frontend will manage the current page and limit state to request specific pages of tasks and display pagination controls to the user.