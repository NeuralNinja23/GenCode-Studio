## Entity Classification

- **Lead**
  - Type: AGGREGATE
  - Evidence: Top-level export (mockLeads = [...]) in `src/data/mock.js`.
  - Endpoints: Will create `/api/leads` for CRUD operations.

- **Note**
  - Type: AGGREGATE
  - Evidence: Implied by the user request ('notes timeline on each customer') and frontend components (`NotesTimeline.jsx`, `NoteForm.jsx`). Will have an independent lifecycle but be linked to a Lead via `lead_id`.
  - Endpoints: Will create `/api/notes` for CRUD operations.

- **LeadStats**
  - Type: EMBEDDED / DERIVED
  - Evidence: Used in `Home.jsx` as `mockLeadStats` for dashboard statistics. It's an aggregation of Lead data, not a standalone entity with its own CRUD lifecycle.
  - Endpoints: Will be returned by a specific statistics endpoint (e.g., `/api/leads/stats`).

## Data Models

### Lead Model
Matches the structure of `mockLeads`.

- `id`: `str` (MongoDB ObjectId, auto-generated)
- `name`: `str`
- `company`: `str`
- `email`: `str`
- `phone`: `str`
- `status`: `str` (Enum: "New", "Contacted", "Qualified", "Won", "Lost")
- `created_at`: `datetime` (ISO 8601 string)
- `last_contacted`: `datetime` (ISO 8601 string, optional)

### Note Model

- `id`: `str` (MongoDB ObjectId, auto-generated)
- `lead_id`: `str` (Reference to Lead's `id`)
- `content`: `str`
- `created_at`: `datetime` (ISO 8601 string)

### LeadStats Model (for `/api/leads/stats`)

- `totalLeads`: `int`
- `newLeads`: `int`
- `contactedLeads`: `int`
- `qualifiedLeads`: `int`
- `wonLeads`: `int`
- `lostLeads`: `int`

## REST API Endpoints

All backend API routes MUST be prefixed with '/api'.

### Leads Endpoints (`/api/leads`)

- **GET /api/leads**
  - Description: Retrieve a list of all leads, with optional filtering and pagination.
  - Query Parameters:
    - `status`: `str` (optional, e.g., "New", "Contacted")
    - `search`: `str` (optional, search by name, company, email, or phone)
    - `page`: `int` (optional, default 1)
    - `limit`: `int` (optional, default 10)
  - Response: `200 OK`
    ```json
    {
      "data": [
        { "id": "1", "name": "Alice Johnson", ... },
        { "id": "2", "name": "Bob Williams", ... }
      ],
      "total": 100,
      "page": 1,
      "limit": 10
    }
    ```

- **POST /api/leads**
  - Description: Create a new lead.
  - Request Body (LeadCreate):
    ```json
    {
      "name": "New Lead Name",
      "company": "New Company Inc.",
      "email": "new.lead@example.com",
      "phone": "+1-555-000-1111",
      "status": "New"
    }
    ```
  - Response: `201 Created`
    ```json
    {
      "data": { "id": "<new_id>", "name": "New Lead Name", ... }
    }
    ```

- **GET /api/leads/{id}**
  - Description: Retrieve a single lead by its ID.
  - Path Parameters:
    - `id`: `str` (Lead ID)
  - Response: `200 OK`
    ```json
    {
      "data": { "id": "1", "name": "Alice Johnson", ... }
    }
    ```

- **PUT /api/leads/{id}**
  - Description: Update an existing lead by its ID.
  - Path Parameters:
    - `id`: `str` (Lead ID)
  - Request Body (LeadUpdate - partial update):
    ```json
    {
      "status": "Qualified",
      "last_contacted": "2024-03-15T10:00:00Z"
    }
    ```
  - Response: `200 OK`
    ```json
    {
      "data": { "id": "1", "name": "Alice Johnson", "status": "Qualified", ... }
    }
    ```

- **DELETE /api/leads/{id}**
  - Description: Delete a lead by its ID.
  - Path Parameters:
    - `id`: `str` (Lead ID)
  - Response: `200 OK`
    ```json
    {
      "data": { "message": "Lead deleted successfully" }
    }
    ```

### Notes Endpoints (`/api/notes`)

- **GET /api/notes?lead_id={lead_id}**
  - Description: Retrieve a list of notes for a specific lead.
  - Query Parameters:
    - `lead_id`: `str` (required, Lead ID)
    - `page`: `int` (optional, default 1)
    - `limit`: `int` (optional, default 10)
  - Response: `200 OK`
    ```json
    {
      "data": [
        { "id": "note1", "lead_id": "lead1", "content": "Called Alice.", ... }
      ],
      "total": 5,
      "page": 1,
      "limit": 10
    }
    ```

- **POST /api/notes**
  - Description: Create a new note for a lead.
  - Request Body (NoteCreate):
    ```json
    {
      "lead_id": "<lead_id>",
      "content": "Followed up with client about proposal."
    }
    ```
  - Response: `201 Created`
    ```json
    {
      "data": { "id": "<new_note_id>", "lead_id": "<lead_id>", "content": "Followed up...", ... }
    }
    ```

- **GET /api/notes/{id}**
  - Description: Retrieve a single note by its ID.
  - Path Parameters:
    - `id`: `str` (Note ID)
  - Response: `200 OK`
    ```json
    {
      "data": { "id": "note1", "lead_id": "lead1", "content": "Called Alice.", ... }
    }
    ```

- **PUT /api/notes/{id}**
  - Description: Update an existing note by its ID.
  - Path Parameters:
    - `id`: `str` (Note ID)
  - Request Body (NoteUpdate - partial update):
    ```json
    {
      "content": "Updated note content."
    }
    ```
  - Response: `200 OK`
    ```json
    {
      "data": { "id": "note1", "content": "Updated note content.", ... }
    }
    ```

- **DELETE /api/notes/{id}**
  - Description: Delete a note by its ID.
  - Path Parameters:
    - `id`: `str` (Note ID)
  - Response: `200 OK`
    ```json
    {
      "data": { "message": "Note deleted successfully" }
    ```

### Lead Statistics Endpoint (`/api/leads/stats`)

- **GET /api/leads/stats**
  - Description: Retrieve aggregated statistics for leads, used for the dashboard.
  - Response: `200 OK`
    ```json
    {
      "data": {
        "totalLeads": 100,
        "newLeads": 20,
        "contactedLeads": 30,
        "qualifiedLeads": 25,
        "wonLeads": 15,
        "lostLeads": 10
      }
    }
    ```

## Response & Error Format (MUST FOLLOW)

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
    {
      "data": <Entity>
    }
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

## Integration Notes

1.  **API Client (`frontend/src/lib/api.js`)**: This file will encapsulate all API calls. It will export functions like `getLeads()`, `getLead(id)`, `createLead(data)`, `updateLead(id, data)`, `deleteLead(id)`, `getNotes(leadId)`, `createNote(data)`, `getLeadStats()`, etc. These functions will use `import.meta.env.VITE_API_URL` as the base URL.
2.  **Data Fetching**: The frontend will use `TanStack Query` (or similar) to manage data fetching, caching, and synchronization with the backend. This will involve defining query keys and mutation functions for each API interaction.
3.  **Error Handling**: The API client will be responsible for catching HTTP errors (e.g., 4xx, 5xx) and transforming them into a consistent error format that the frontend can display to the user. The `error` object structure defined above will be used.
4.  **Pagination and Filtering**: For list endpoints (`/api/leads`, `/api/notes`), the frontend will pass `page`, `limit`, `status`, and `search` parameters as query strings. The backend should return `total`, `page`, and `limit` in the response to facilitate pagination controls on the frontend.
5.  **Date Formats**: Dates (`created_at`, `last_contacted`) will be sent and received as ISO 8601 strings (e.g., `"2024-03-01T10:00:00Z"`).