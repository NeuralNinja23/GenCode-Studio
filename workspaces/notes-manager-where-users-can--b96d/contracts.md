# API Contracts for Notes Manager

This document outlines the data models, REST API endpoints, and response formats for the Notes Manager application. These contracts are designed to match the existing frontend implementation with mock data, ensuring a seamless transition to a full-stack application.

## 1. Data Models

### Note
Represents a single note entry. The `id` field will correspond to MongoDB's `_id` but will be exposed as `id` in the API.

```typescript
interface Note {
  id: string; // Unique identifier for the note
  title: string; // Title of the note
  content: string; // Full content of the note
  status: 'Active' | 'Draft'; // Current status of the note
  created_at: string; // ISO 8601 datetime string when the note was created
  updated_at?: string; // Optional: ISO 8601 datetime string when the note was last updated
}

interface CreateNoteRequest {
  title: string;
  content: string;
  status: 'Active' | 'Draft';
}

interface UpdateNoteRequest {
  title?: string;
  content?: string;
  status?: 'Active' | 'Draft';
}
```

## 2. REST API Endpoints

All API routes will be prefixed with `/api`.

### 2.1. List All Notes
- **Endpoint**: `GET /api/notes`
- **Description**: Retrieves a list of all notes, with optional search and pagination.
- **Query Parameters**:
  - `search` (optional, string): Filters notes by title (case-insensitive partial match).
  - `page` (optional, integer, default: 1): The page number for pagination.
  - `limit` (optional, integer, default: 10): The number of items per page.
- **Response**: `200 OK`
  ```json
  {
    "data": [
      { "id": "1", "title": "Project Kick-off Meeting Notes", "content": "...", "status": "Active", "created_at": "2024-03-10T10:00:00Z", "updated_at": "2024-03-10T10:00:00Z" },
      // ... more Note objects
    ],
    "total": 5,
    "page": 1,
    "limit": 10
  }
  ```

### 2.2. Create New Note
- **Endpoint**: `POST /api/notes`
- **Description**: Creates a new note entry.
- **Request Body**: `application/json`
  ```json
  {
    "title": "New Feature Idea",
    "content": "Outline for a new user dashboard feature.",
    "status": "Draft"
  }
  ```
- **Response**: `201 Created`
  ```json
  {
    "data": { "id": "new-id", "title": "New Feature Idea", "content": "...", "status": "Draft", "created_at": "2024-03-11T12:00:00Z", "updated_at": "2024-03-11T12:00:00Z" }
  }
  ```

### 2.3. Get Single Note
- **Endpoint**: `GET /api/notes/{id}`
- **Description**: Retrieves a single note by its unique ID.
- **Path Parameters**:
  - `id` (string, required): The unique ID of the note.
- **Response**: `200 OK`
  ```json
  {
    "data": { "id": "1", "title": "Project Kick-off Meeting Notes", "content": "...", "status": "Active", "created_at": "2024-03-10T10:00:00Z", "updated_at": "2024-03-10T10:00:00Z" }
  }
  ```

### 2.4. Update Note
- **Endpoint**: `PUT /api/notes/{id}`
- **Description**: Updates an existing note identified by its ID. Supports partial updates.
- **Path Parameters**:
  - `id` (string, required): The unique ID of the note to update.
- **Request Body**: `application/json` (all fields optional for partial update)
  ```json
  {
    "title": "Updated Project Notes",
    "status": "Active"
  }
  ```
- **Response**: `200 OK`
  ```json
  {
    "data": { "id": "1", "title": "Updated Project Notes", "content": "...", "status": "Active", "created_at": "2024-03-10T10:00:00Z", "updated_at": "2024-03-11T13:30:00Z" }
  }
  ```

### 2.5. Delete Note
- **Endpoint**: `DELETE /api/notes/{id}`
- **Description**: Deletes a note identified by its ID.
- **Path Parameters**:
  - `id` (string, required): The unique ID of the note to delete.
- **Response**: `200 OK`
  ```json
  {
    "data": { "id": "1", "message": "Note deleted successfully" }
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
The frontend will utilize a centralized API client (`api.js`) to interact with these endpoints. This client will construct requests using the `VITE_API_URL` environment variable as the base URL, ensuring environment-specific configuration.

Example usage:
```javascript
// In lib/api.js
const API_BASE_URL = import.meta.env.VITE_API_URL;

async function fetchNotes(search = '', page = 1, limit = 10) {
  const response = await fetch(`${API_BASE_URL}/api/notes?search=${search}&page=${page}&limit=${limit}`);
  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.error.message || 'Failed to fetch notes');
  }
  return response.json();
}

async function createNote(noteData) {
  const response = await fetch(`${API_BASE_URL}/api/notes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(noteData),
  });
  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.error.message || 'Failed to create note');
  }
  return response.json();
}
// ... similar functions for getNote, updateNote, deleteNote
```

### 4.2. Error Handling
Frontend components should implement robust error handling by catching exceptions thrown by the API client. The client will parse the standardized error response format to extract `code` and `message` for user feedback.

### 4.3. Pagination and Search
The `GET /api/notes` endpoint supports `search`, `page`, and `limit` query parameters. The frontend will pass these parameters to fetch filtered and paginated results. The response will include `total`, `page`, and `limit` fields to facilitate pagination controls in the UI.