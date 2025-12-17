## Entity Classification

- **Task**
  - Type: AGGREGATE
  - Evidence: Top-level export (`mockTasks = [...]`), has unique `id` at root level, has independent lifecycle.
  - Endpoints: Will create `/api/tasks`

- **Assignee**
  - Type: AGGREGATE
  - Evidence: Top-level export (`mockAssignees = [...]`), has unique `id` at root level, has independent lifecycle, required for filtering tasks.
  - Endpoints: Will create `/api/assignees`

- **Tag**
  - Type: AGGREGATE
  - Evidence: Top-level export (`mockTags = [...]`), has unique `id` at root level, has independent lifecycle, required for filtering tasks.
  - Endpoints: Will create `/api/tags`

## Data Models

These models define the structure of data exchanged with the API, matching `mock.js`.

```python
from typing import List, Optional, Literal
from pydantic import BaseModel, Field

# --- Assignee Models ---
class Assignee(BaseModel):
    id: str
    name: str
    avatar: str

class AssigneeCreate(BaseModel):
    name: str
    avatar: Optional[str] = None

class AssigneeUpdate(BaseModel):
    name: Optional[str] = None
    avatar: Optional[str] = None

# --- Tag Models ---
class Tag(BaseModel):
    id: str
    name: str
    color: str

class TagCreate(BaseModel):
    name: str
    color: Optional[str] = None

class TagUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None

# --- Subtask Model (nested in Task) ---
class Subtasks(BaseModel):
    completed: int
    total: int

# --- Task Models ---
class Task(BaseModel):
    id: str
    title: str
    description: str
    status: Literal["backlog", "in-progress", "review", "done"]
    priority: Literal["low", "medium", "high"]
    assignee: Assignee  # Full Assignee object embedded
    dueDate: str  # ISO date string (e.g., "YYYY-MM-DD")
    labels: List[Tag]  # List of full Tag objects embedded
    subtasks: Subtasks
    created_at: str  # ISO datetime string

class TaskCreate(BaseModel):
    title: str
    description: str
    status: Literal["backlog", "in-progress", "review", "done"] = "backlog"
    priority: Literal["low", "medium", "high"] = "medium"
    assignee_id: Optional[str] = None  # ID of assignee to link
    dueDate: Optional[str] = None
    label_ids: Optional[List[str]] = Field(default_factory=list)  # List of tag IDs to link
    subtasks: Optional[Subtasks] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[Literal["backlog", "in-progress", "review", "done"]] = None
    priority: Optional[Literal["low", "medium", "high"]] = None
    assignee_id: Optional[str] = None
    dueDate: Optional[str] = None
    label_ids: Optional[List[str]] = None
    subtasks: Optional[Subtasks] = None

class TaskStatusUpdate(BaseModel):
    status: Literal["backlog", "in-progress", "review", "done"]
```

## REST API Endpoints

All API routes will be prefixed with `/api`.

### 1. Assignee Endpoints (`/api/assignees`)

-   **GET `/api/assignees`**
    -   Description: Retrieve a list of all assignees.
    -   Query Parameters: `page` (int, optional, default 1), `limit` (int, optional, default 10)
    -   Response: `200 OK` with `{"data": [Assignee], "total": number, "page": number, "limit": number}`

-   **GET `/api/assignees/{id}`**
    -   Description: Retrieve a single assignee by ID.
    -   Response: `200 OK` with `{"data": Assignee}`

-   **POST `/api/assignees`**
    -   Description: Create a new assignee.
    -   Request Body: `AssigneeCreate`
    -   Response: `201 Created` with `{"data": Assignee}`

-   **PUT `/api/assignees/{id}`**
    -   Description: Update an existing assignee.
    -   Request Body: `AssigneeUpdate`
    -   Response: `200 OK` with `{"data": Assignee}`

-   **DELETE `/api/assignees/{id}`**
    -   Description: Delete an assignee.
    -   Response: `200 OK` with `{"data": {"message": "Assignee deleted successfully"}}`

### 2. Tag Endpoints (`/api/tags`)

-   **GET `/api/tags`**
    -   Description: Retrieve a list of all tags.
    -   Query Parameters: `page` (int, optional, default 1), `limit` (int, optional, default 10)
    -   Response: `200 OK` with `{"data": [Tag], "total": number, "page": number, "limit": number}`

-   **GET `/api/tags/{id}`**
    -   Description: Retrieve a single tag by ID.
    -   Response: `200 OK` with `{"data": Tag}`

-   **POST `/api/tags`**
    -   Description: Create a new tag.
    -   Request Body: `TagCreate`
    -   Response: `201 Created` with `{"data": Tag}`

-   **PUT `/api/tags/{id}`**
    -   Description: Update an existing tag.
    -   Request Body: `TagUpdate`
    -   Response: `200 OK` with `{"data": Tag}`

-   **DELETE `/api/tags/{id}`**
    -   Description: Delete a tag.
    -   Response: `200 OK` with `{"data": {"message": "Tag deleted successfully"}}`

### 3. Task Endpoints (`/api/tasks`)

-   **GET `/api/tasks`**
    -   Description: Retrieve a list of all tasks, with optional filtering and pagination.
    -   Query Parameters:
        -   `status`: (str, optional) Filter tasks by status (e.g., `?status=in-progress`)
        -   `assignee_id`: (str, optional) Filter tasks by assignee ID (e.g., `?assignee_id=a1`)
        -   `tag_id`: (str, optional) Filter tasks by tag ID (e.g., `?tag_id=t1`)
        -   `page`: (int, optional, default 1) For pagination.
        -   `limit`: (int, optional, default 10) For pagination.
    -   Response: `200 OK` with `{"data": [Task], "total": number, "page": number, "limit": number}`

-   **GET `/api/tasks/{id}`**
    -   Description: Retrieve a single task by ID.
    -   Response: `200 OK` with `{"data": Task}`

-   **POST `/api/tasks`**
    -   Description: Create a new task.
    -   Request Body: `TaskCreate`
    -   Response: `201 Created` with `{"data": Task}`

-   **PUT `/api/tasks/{id}`**
    -   Description: Update an existing task.
    -   Request Body: `TaskUpdate`
    -   Response: `200 OK` with `{"data": Task}`

-   **DELETE `/api/tasks/{id}`**
    -   Description: Delete a task.
    -   Response: `200 OK` with `{"data": {"message": "Task deleted successfully"}}`

-   **PATCH `/api/tasks/{id}/status`**
    -   Description: Update the status of a task (e.g., for drag-and-drop).
    -   Request Body: `TaskStatusUpdate`
    -   Response: `200 OK` with `{"data": Task}`

## Response & Error Format (MUST FOLLOW)

-   Successful list responses:
    -   `200 OK`
    -   Body:
        ```json
        {
          "data": [<Entity>],
          "total": number,
          "page": number,
          "limit": number
        }
        ```

-   Successful single-item responses:
    -   `200 OK` or `201 Created`
    -   Body:
        ```json
        { "data": <Entity> }
        ```

-   Error responses:
    -   `4xx` / `5xx`
    -   Body:
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

## Integration Notes

1.  **API Client (`frontend/src/lib/api.js`):** The frontend's API client will be updated to make calls to these defined endpoints. It will handle constructing URLs, sending request bodies, and parsing responses.
2.  **Data Transformation:** When creating or updating tasks, the frontend will send `assignee_id` (string) and `label_ids` (list of strings). The backend will be responsible for resolving these IDs to the full `Assignee` and `Tag` objects, respectively, before storing the task and returning the complete `Task` object in the response.
3.  **Error Handling:** The frontend will check for the `error` key in the response body for `4xx` or `5xx` status codes and display user-friendly messages based on `error.message`.
4.  **Pagination:** For list endpoints (`GET /api/tasks`, `GET /api/assignees`, `GET /api/tags`), the frontend will pass `page` and `limit` query parameters to control data fetching and display pagination controls.
5.  **Drag and Drop:** The `PATCH /api/tasks/{id}/status` endpoint will be used by the frontend's drag-and-drop functionality to update a task's status when it's moved between columns.