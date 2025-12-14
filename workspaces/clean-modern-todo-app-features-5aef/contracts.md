## API Contracts for Todo App

This document outlines the data models, API endpoints, and integration guidelines for the Todo application's backend, ensuring seamless communication with the frontend.

### 1. Data Models

#### Task
Represents a single todo item.

| Field Name | Type     | Description                                     | Required | Default   | Example Value                  |
| :--------- | :------- | :---------------------------------------------- | :------- | :-------- | :----------------------------- |
| `id`       | `string` | Unique identifier for the task (MongoDB `_id`)  | Yes      | -         | `"65c7b3b9d2e7f8a1b2c3d4e5"`   |
| `title`    | `string` | Title of the task                               | Yes      | -         | `"Design homepage mockup"`     |
| `content`  | `string` | Detailed description of the task                | Yes      | -         | `"Create initial wireframes..."` |
| `status`   | `string` | Current status of the task (`"Active"`, `"Completed"`) | Yes      | `"Active"` | `"Active"`                     |
| `priority` | `string` | Priority level (`"High"`, `"Medium"`, `"Low"`) | Yes      | `"Medium"` | `"High"`                       |
| `dueDate`  | `string` | Due date in `YYYY-MM-DD` format                 | No       | -         | `"2024-07-25"`                 |
| `created_at` | `string` | ISO 8601 timestamp of creation                  | Yes      | Auto-gen  | `"2024-07-18T10:00:00Z"`       |

### 2. REST API Endpoints

All API routes will be prefixed with `/api`.

#### 2.1. Get All Tasks
- **Endpoint:** `GET /api/tasks`
- **Description:** Retrieves a list of all tasks, with optional filtering and pagination.
- **Query Parameters:**
  - `status`: `string` (Optional) - Filter tasks by status (`"Active"`, `"Completed"`).
  - `page`: `integer` (Optional) - Page number for pagination (default: `1`).
  - `limit`: `integer` (Optional) - Number of items per page (default: `10`).
- **Response:** `200 OK`
  ```json
  {
    "data": [
      { "id": "1", "title": "Design homepage mockup", "content": "...", "status": "Active", "priority": "High", "dueDate": "2024-07-25", "created_at": "2024-07-18T10:00:00Z" },
      // ... more tasks
    ],
    "total": 5,
    "page": 1,
    "limit": 10
  }
  ```

#### 2.2. Get Task by ID
- **Endpoint:** `GET /api/tasks/{id}`
- **Description:** Retrieves a single task by its unique ID.
- **Path Parameters:**
  - `id`: `string` - The unique identifier of the task.
- **Response:** `200 OK`
  ```json
  {
    "data": { "id": "1", "title": "Design homepage mockup", "content": "...", "status": "Active", "priority": "High", "dueDate": "2024-07-25", "created_at": "2024-07-18T10:00:00Z" }
  }
  ```
- **Error:** `404 Not Found` if the task does not exist.

#### 2.3. Create New Task
- **Endpoint:** `POST /api/tasks`
- **Description:** Creates a new task.
- **Request Body:**
  ```json
  {
    "title": "Implement user authentication",
    "content": "Set up user registration, login, and session management using JWT.",
    "status": "Active",
    "priority": "High",
    "dueDate": "2024-07-30"
  }
  ```
- **Response:** `201 Created`
  ```json
  {
    "data": { "id": "2", "title": "Implement user authentication", "content": "...", "status": "Active", "priority": "High", "dueDate": "2024-07-30", "created_at": "2024-07-19T11:30:00Z" }
  }
  ```
- **Error:** `422 Unprocessable Entity` for validation errors.

#### 2.4. Update Task
- **Endpoint:** `PUT /api/tasks/{id}`
- **Description:** Updates an existing task identified by its ID. All fields in the request body are optional; only provided fields will be updated.
- **Path Parameters:**
  - `id`: `string` - The unique identifier of the task.
- **Request Body:**
  ```json
  {
    "title": "Updated Task Title",
    "status": "Completed"
  }
  ```
- **Response:** `200 OK`
  ```json
  {
    "data": { "id": "1", "title": "Updated Task Title", "content": "...", "status": "Completed", "priority": "High", "dueDate": "2024-07-25", "created_at": "2024-07-18T10:00:00Z" }
  }
  ```
- **Error:** `404 Not Found` if the task does not exist, `422 Unprocessable Entity` for validation errors.

#### 2.5. Delete Task
- **Endpoint:** `DELETE /api/tasks/{id}`
- **Description:** Deletes a task identified by its ID.
- **Path Parameters:**
  - `id`: `string` - The unique identifier of the task.
- **Response:** `204 No Content` (Successful deletion with no content returned).
- **Error:** `404 Not Found` if the task does not exist.

### 3. Response & Error Format (MUST FOLLOW)

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

### 4. Integration Notes

- **API Client (`frontend/src/lib/api.js`):** The frontend will use a dedicated API client to encapsulate all backend interactions. This client will construct requests using `import.meta.env.VITE_API_URL` as the base URL, appending the `/api` prefix and specific endpoint paths.
- **Data Fetching:** Frontend components will utilize `TanStack Query` or similar hooks to manage data fetching, caching, and state updates, calling the `lib/api.js` functions.
- **Error Handling:** The API client will check the `response.ok` property. If `false`, it will parse the response body according to the specified error format and throw an error object containing `error.code` and `error.message` for frontend display.
- **Pagination & Filtering:** For the `GET /api/tasks` endpoint, the frontend will pass `status`, `page`, and `limit` query parameters. It will expect the `total`, `page`, and `limit` fields in the response to manage pagination UI and display total counts.
- **ID Handling:** The frontend will send and receive task IDs as strings. The backend will handle the conversion to/from MongoDB's `ObjectId` type internally.