# Kanban Board Architecture Plan

As a Senior Solutions Architect, I've designed a scalable, clean, and maintainable architecture for your Kanban board application, aligning with the `project_management` archetype and `modern_gradient` UI vibe.

## 1. Tech Stack

*   **Frontend:** React, TypeScript, shadcn/ui (New York v4), Tailwind CSS, React DnD (for drag-and-drop functionality), Zustand (for global state management).
*   **Backend:** FastAPI, Python, Pydantic (for data validation), Beanie ODM (for MongoDB object-document mapping).
*   **Database:** MongoDB (NoSQL document database).
*   **Deployment:** Docker, Kubernetes (optional for scaling), Vercel/Netlify (Frontend), Render/AWS ECS (Backend).

## 2. Frontend Component Hierarchy

Leveraging shadcn/ui and React, the frontend will follow a modular component-based structure:

*   `App`
    *   `BoardLayout` (Provides context for the current board, handles global state)
        *   `ProjectSidebar` (Left navigation for different boards/projects)
        *   `BoardPage` (Main Kanban board view)
            *   `BoardHeader` (Board title, filters, 'Add Task' button)
                *   `FilterPanel` (Dropdowns/inputs for filtering by assignee, tag)
                *   `Button` (shadcn/ui for 'Add Task')
            *   `KanbanBoard` (Container for all columns, handles drag-and-drop logic)
                *   `KanbanColumn` (Represents a task status, e.g., Backlog, In Progress)
                    *   `ColumnHeader` (Column title, task count)
                    *   `ScrollArea` (shadcn/ui for scrollable task list)
                    *   `TaskCard` (Draggable card representing a task)
                        *   `AssigneeAvatar` (Displays assignee's profile picture)
                        *   `Badge` (shadcn/ui for tags, priority)
            *   `TaskModal` (shadcn/ui Dialog for creating/editing task details)
                *   `Form` (shadcn/ui for task fields: title, description, assignee, tags, due date, priority)
                *   `Combobox` (shadcn/ui for assignee/tag selection)

## 3. Backend Module Structure

The FastAPI backend will be organized for clarity and maintainability:

```
app/
âââ main.py                 # FastAPI application entry point
âââ config.py               # Application settings, environment variables
âââ database.py             # MongoDB connection and Beanie ODM initialization
âââ models/                 # Beanie ODM document models
â   âââ board.py
â   âââ column.py           # Embedded or referenced within Board
â   âââ task.py
â   âââ user.py             # For assignees
â   âââ tag.py
âââ schemas/                # Pydantic schemas for request/response validation
â   âââ board.py
â   âââ column.py
â   âââ task.py
â   âââ user.py
â   âââ tag.py
âââ routers/                # FastAPI APIRoutes for different resources
â   âââ boards.py
â   âââ tasks.py
â   âââ users.py
â   âââ tags.py
âââ services/               # Business logic, e.g., task reordering
    âââ board_service.py
```

## 4. Database Schema Overview (MongoDB + Beanie ODM)

We'll use Beanie ODM to define our MongoDB document structures, focusing on embedding where appropriate for performance and denormalization, especially for board-specific entities like columns and tags.

**`Board` Document:**
```python
class Board(Document):
    name: str
    description: Optional[str] = None
    owner_id: PydanticObjectId # Reference to User
    columns: List[BoardColumn] = [] # Embedded list of columns
    tags: List[Tag] = [] # Embedded list of board-specific tags
    assignees: List[PydanticObjectId] = [] # References to User documents

    class Settings:
        name = "boards"

class BoardColumn(BaseModel):
    id: UUID4 = Field(default_factory=uuid4) # Client-side stable ID
    name: str
    order: int
    task_ids: List[PydanticObjectId] = [] # Ordered list of Task IDs

class Tag(BaseModel):
    id: UUID4 = Field(default_factory=uuid4)
    name: str
    color: Optional[str] = None # Hex code or Tailwind class
```

**`Task` Document:**
```python
class Task(Document):
    title: str
    description: Optional[str] = None
    board_id: PydanticObjectId # Reference to Board
    column_id: UUID4 # Reference to BoardColumn.id (embedded in Board)
    assignee_id: Optional[PydanticObjectId] = None # Reference to User
    tags: List[UUID4] = [] # References to Tag.id (embedded in Board)
    priority: Optional[str] = None # e.g., 'Low', 'Medium', 'High'
    due_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "tasks"
```

**`User` Document (for Assignees):**
```python
class User(Document):
    name: str
    email: EmailStr
    avatar_url: Optional[HttpUrl] = None

    class Settings:
        name = "users"
```

## 5. API Endpoints Summary

**Boards:**
*   `POST /boards` - Create a new board.
*   `GET /boards` - Retrieve a list of all boards.
*   `GET /boards/{board_id}` - Retrieve a specific board with its columns and task IDs.
*   `PUT /boards/{board_id}` - Update board details.
*   `DELETE /boards/{board_id}` - Delete a board.
*   `PATCH /boards/{board_id}/columns/reorder` - Reorder columns within a board.

**Tasks:**
*   `POST /boards/{board_id}/tasks` - Create a new task for a board.
*   `GET /boards/{board_id}/tasks` - Retrieve all tasks for a board (with optional filters: `assignee_id`, `tag_id`).
*   `GET /boards/{board_id}/tasks/{task_id}` - Retrieve a specific task.
*   `PUT /boards/{board_id}/tasks/{task_id}` - Update task details.
*   `DELETE /boards/{board_id}/tasks/{task_id}` - Delete a task.
*   `PATCH /boards/{board_id}/tasks/{task_id}/move` - Move a task between columns or reorder within a column. Payload includes `source_column_id`, `destination_column_id`, `new_position`.

**Assignees:**
*   `GET /boards/{board_id}/assignees` - Get assignees associated with a board.
*   `POST /boards/{board_id}/assignees` - Add an assignee to a board.

**Tags:**
*   `POST /boards/{board_id}/tags` - Create a new tag for a board.
*   `GET /boards/{board_id}/tags` - Get tags associated with a board.
*   `PUT /boards/{board_id}/tags/{tag_id}` - Update a tag.
*   `DELETE /boards/{board_id}/tags/{tag_id}` - Delete a tag.

## 6. Folder Structure

**Frontend (`frontend/src/`):**
```
frontend/src/
âââ api/                    # API client functions
âââ assets/                 # Images, icons
âââ components/             # Reusable UI components
â   âââ ui/                 # shadcn/ui components (auto-generated)
â   âââ common/             # Generic components (e.g., AssigneeAvatar)
â   âââ board/              # Board-specific components (KanbanColumn, TaskCard)
â   âââ forms/              # Form components (TaskModalForm)
âââ context/                # React Context providers (e.g., BoardContext)
âââ hooks/                  # Custom React hooks
âââ lib/                    # Utility functions, constants
âââ pages/                  # Top-level page components
â   âââ BoardPage.tsx
â   âââ AuthPage.tsx        # (If authentication is added later)
âââ styles/                 # Tailwind CSS configuration, global styles
âââ App.tsx                 # Main application component
```

**Backend (`backend/app/`):**
```
backend/app/
âââ main.py
âââ config.py
âââ database.py
âââ models/
â   âââ __init__.py
â   âââ board.py
â   âââ task.py
â   âââ user.py
â   âââ tag.py
âââ schemas/
â   âââ __init__.py
â   âââ board.py
â   âââ task.py
â   âââ user.py
â   âââ tag.py
âââ routers/
â   âââ __init__.py
â   âââ boards.py
â   âââ tasks.py
â   âââ users.py
â   âââ tags.py
âââ services/
â   âââ __init__.py
â   âââ board_service.py
âââ tests/                  # Unit and integration tests
```

## 7. UI Design System

**Vibe:** `modern_gradient`
**Archetype:** `project_management`

The design system will leverage shadcn/ui's New York v4 theme as a base, customized with gradients, subtle shadows, and a clean, spacious layout to embody a modern and professional aesthetic suitable for project management. Typography will be clean sans-serifs for readability.

**Color Palette:**
*   **Primary Accent:** A gradient from a vibrant indigo to a soft purple (`#6366F1` to `#A855F7`).
*   **Secondary Accent:** A softer, complementary gradient or solid color, perhaps a teal or light blue.
*   **Backgrounds:** Light, subtle gradients or off-white tones for main content areas, with slightly darker or more saturated gradients for headers/footers or interactive elements.
*   **Text:** Dark charcoal for primary text, medium gray for secondary/muted text.
*   **Borders/Separators:** Light gray or subtle gradient lines.

**Typography:**
*   **Font Family:** Inter (or similar modern sans-serif) for all text.
*   **Headings:** Bold, slightly larger, with good letter spacing.
*   **Body Text:** Readable size, good line height.

**Layout & Spacing:**
*   **Grid-based:** Consistent spacing and alignment using Tailwind's utility classes.
*   **Spacious:** Ample padding and margins to prevent visual clutter, enhancing readability and focus.
*   **Responsive:** Adapts gracefully to various screen sizes.

**Components (shadcn/ui based):**
*   **Buttons:** Primary buttons will feature the indigo-purple gradient. Secondary buttons will be outlined or have a muted background.
*   **Cards:** Rounded corners, subtle shadows, clean backgrounds, often with a light border.
*   **Inputs/Forms:** Clean, minimalist design with clear focus states.
*   **Dialogs/Modals:** Modern, centered, with clear headers and actions.
*   **Badges/Tags:** Small, rounded, with colors reflecting their purpose (e.g., tag color, priority level).
*   **Avatars:** Circular, often with a subtle border or shadow.

### UI Tokens (machine readable)

```json
{
  