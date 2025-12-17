# CRM Architecture Plan

This document outlines the high-level architecture for a simple CRM application, designed as an `admin_dashboard` with a `minimal_light` UI aesthetic.

## 1. Tech Stack

*   **Frontend:** React.js (with Vite), shadcn/ui (New York v4), Tailwind CSS, TanStack Query (for data fetching).
*   **Backend:** FastAPI (Python), Uvicorn.
*   **Database:** MongoDB.
*   **ODM (Object Document Mapper):** Beanie (for MongoDB).
*   **Deployment:** Docker (containerization).

## 2. Frontend Component Hierarchy

Following the `admin_dashboard` archetype, the frontend will feature a persistent sidebar and a main content area.

```mermaid
graph TD
    A[App.jsx] --> B(Layout.jsx)
    B --> C(Sidebar.jsx)
    B --> D(Header.jsx)
    B --> E(MainContent.jsx)
    E --> F{Pages}
    F --> G[DashboardPage.jsx]
    F --> H[LeadsPage.jsx]
    F --> I[CustomerDetailPage.jsx]

    H --> J[LeadTable.jsx]
    H --> K[LeadFormDialog.jsx]
    J --> L[DataTable.jsx (shadcn/ui)]
    J --> M[FilterBar.jsx]

    I --> N[CustomerDetailCard.jsx]
    I --> O[NotesTimeline.jsx]
    I --> P[CustomerFormDialog.jsx]
    N --> Q[StatusBadge.jsx]
    O --> R[NoteForm.jsx]

    G --> S[StatsCard.jsx]
    G --> T[RecentLeadsTable.jsx]
```

**Key Components:**

*   `Layout.jsx`: Provides the overall structure with `Sidebar` and `Header`.
*   `Sidebar.jsx`: Navigation for Leads, Customers, Dashboard.
*   `DashboardPage.jsx`: Overview with `StatsCard`s (e.g., New Leads, Qualified Leads, Total Customers) and potentially recent activity tables.
*   `LeadsPage.jsx`: Displays a sortable, filterable, and paginated table of leads (`LeadTable`), with actions for editing, viewing, and converting leads.
*   `CustomerDetailPage.jsx`: Shows detailed information for a customer, including contact info, company, and a `NotesTimeline`.
*   `DataTable.jsx`: A reusable component built on shadcn/ui's `Table` for displaying tabular data with common features.
*   `StatsCard.jsx`: Displays key metrics.
*   `NotesTimeline.jsx`: Displays a chronological list of notes associated with a customer.

## 3. Backend Module Structure

The backend will be structured for clarity and separation of concerns.

```
backend/
âââ app/
â   âââ api/v1/
â   â   âââ __init__.py
â   â   âââ leads.py        # FastAPI router for lead endpoints
â   â   âââ customers.py    # FastAPI router for customer endpoints
â   âââ crud/
â   â   âââ __init__.py
â   â   âââ lead.py         # CRUD operations for Lead model
â   â   âââ customer.py     # CRUD operations for Customer model
â   âââ models/
â   â   âââ __init__.py
â   â   âââ lead.py         # Beanie Document for Lead
â   â   âââ customer.py     # Beanie Document for Customer
â   â   âââ note.py         # Beanie EmbeddedDocument for Note
â   âââ schemas/
â   â   âââ __init__.py
â   â   âââ lead.py         # Pydantic schemas for Lead (request/response)
â   â   âââ customer.py     # Pydantic schemas for Customer (request/response)
â   â   âââ note.py         # Pydantic schemas for Note (request/response)
â   âââ config.py           # Application configuration
â   âââ database.py         # MongoDB connection and Beanie initialization
â   âââ main.py             # Main FastAPI application entry point
âââ tests/
â   âââ ...
âââ .env.example
âââ Dockerfile
âââ requirements.txt
âââ README.md
```

## 4. Database Schema Overview (MongoDB + Beanie ODM)

Using Beanie, we define MongoDB documents and embedded documents.

### `Lead` Document
Represents a potential customer.

```python
from beanie import Document
from datetime import datetime
from enum import Enum

class LeadStatus(str, Enum):
    NEW = "New"
    CONTACTED = "Contacted"
    QUALIFIED = "Qualified"
    WON = "Won"
    LOST = "Lost"

class Lead(Document):
    name: str
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    status: LeadStatus = LeadStatus.NEW
    source: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "leads"
```

### `Note` Embedded Document
Represents a note associated with a customer.

```python
from beanie import EmbeddedDocument
from datetime import datetime

class Note(EmbeddedDocument):
    content: str
    created_by: str # e.g., user ID or name
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

### `Customer` Document
Represents a converted lead or an existing customer.

```python
from beanie import Document
from datetime import datetime
from typing import List
from app.models.note import Note

class Customer(Document):
    name: str
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    notes: List[Note] = [] # Embedded documents
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "customers"
```

## 5. API Endpoints Summary

All API endpoints will be prefixed with `/api/v1`.

### Leads
*   `GET /api/v1/leads`: Retrieve a list of leads. Supports pagination (`skip`, `limit`), filtering (`status`, `source`), and search (`name`, `email`, `company`).
*   `POST /api/v1/leads`: Create a new lead.
*   `GET /api/v1/leads/{lead_id}`: Retrieve details of a specific lead.
*   `PUT /api/v1/leads/{lead_id}`: Update an existing lead.
*   `PATCH /api/v1/leads/{lead_id}/status`: Update the status of a lead.
*   `DELETE /api/v1/leads/{lead_id}`: Delete a lead.
*   `POST /api/v1/leads/{lead_id}/convert`: Convert a lead to a customer.

### Customers
*   `GET /api/v1/customers`: Retrieve a list of customers. Supports pagination (`skip`, `limit`), and search (`name`, `email`, `company`).
*   `POST /api/v1/customers`: Create a new customer (e.g., manually, or from lead conversion).
*   `GET /api/v1/customers/{customer_id}`: Retrieve details of a specific customer.
*   `PUT /api/v1/customers/{customer_id}`: Update an existing customer.
*   `DELETE /api/v1/customers/{customer_id}`: Delete a customer.
*   `POST /api/v1/customers/{customer_id}/notes`: Add a new note to a customer's timeline.

### Dashboard Statistics
*   `GET /api/v1/dashboard/stats`: Retrieve aggregated statistics (e.g., lead counts by status, total customers).

## 6. Folder Structure

```
. (project root)
âââ backend/
â   âââ app/
â   â   âââ api/v1/
â   â   â   âââ customers.py
â   â   â   âââ leads.py
â   â   âââ crud/
â   â   â   âââ customer.py
â   â   â   âââ lead.py
â   â   âââ models/
â   â   â   âââ customer.py
â   â   â   âââ lead.py
â   â   â   âââ note.py
â   â   âââ schemas/
â   â   â   âââ customer.py
â   â   â   âââ lead.py
â   â   â   âââ note.py
â   â   âââ config.py
â   â   âââ database.py
â   â   âââ main.py
â   âââ .env.example
â   âââ Dockerfile
â   âââ requirements.txt
â   âââ README.md
âââ frontend/
â   âââ public/
â   âââ src/
â   â   âââ assets/
â   â   âââ components/
â   â   â   âââ common/
â   â   â   â   âââ DataTable.jsx
â   â   â   â   âââ FilterBar.jsx
â   â   â   â   âââ StatsCard.jsx
â   â   â   âââ customers/
â   â   â   â   âââ CustomerDetailCard.jsx
â   â   â   â   âââ CustomerFormDialog.jsx
â   â   â   â   âââ NoteForm.jsx
â   â   â   â   âââ NotesTimeline.jsx
â   â   â   â   âââ StatusBadge.jsx
â   â   â   âââ layout/
â   â   â   â   âââ Header.jsx
â   â   â   â   âââ Layout.jsx
â   â   â   â   âââ Sidebar.jsx
â   â   â   âââ leads/
â   â   â   â   âââ LeadFormDialog.jsx
â   â   â   â   âââ LeadTable.jsx
â   â   â   âââ ui/ # shadcn/ui components (auto-generated)
â   â   âââ hooks/
â   â   â   âââ useLeads.js
â   â   âââ lib/
â   â   â   âââ api.js
â   â   â   âââ utils.js
â   â   âââ pages/
â   â   â   âââ CustomerDetailPage.jsx
â   â   â   âââ DashboardPage.jsx
â   â   â   âââ LeadsPage.jsx
â   â   âââ App.jsx
â   â   âââ globals.css
â   â   âââ main.jsx
â   âââ .env.example
â   âââ index.html
â   âââ package.json
â   âââ postcss.config.js
â   âââ tailwind.config.js
â   âââ vite.config.js
âââ README.md
```

## 7. UI Design System (minimal_light)

The UI design system is built upon shadcn/ui (New York v4) and Tailwind CSS, adhering to a `minimal_light` aesthetic suitable for an `admin_dashboard`.

### General Principles
*   **Cleanliness:** Minimalist design with ample whitespace.
*   **Readability:** High contrast for text, clear typography.
*   **Efficiency:** Focus on data presentation and quick actions.
*   **Subtlety:** Muted colors with a single accent color for primary actions.

### Typography
*   **Font Family:** Sans-serif, e.g., Inter (default for shadcn/ui New York).
*   **Headings:** `text-2xl` for page titles, `text-xl` for section titles, `text-lg` for card titles.
*   **Body Text:** `text-base` for general content, `text-sm` for secondary information.

### Colors
*   **Primary Accent:** A subtle blue or green (e.g., `blue-600` or `emerald-600`).
*   **Backgrounds:** Light grays and whites.
*   **Text:** Dark grays for primary text, lighter grays for muted/secondary text.
*   **Borders/Dividers:** Light gray.

### Spacing
*   **Consistent Grid:** Use a consistent spacing scale (e.g., Tailwind's default `space-x-N`, `space-y-N`, `p-N`, `m-N`).
*   **Whitespace:** Generous use of whitespace to reduce visual clutter.

### Components (shadcn/ui)
*   **Table:** `Table` component for data display, with sorting, pagination, and filtering capabilities.
*   **Card:** `Card` component for grouping related information, often with `shadow-sm` and `border` for a subtle lift.
*   **Button:** `Button` component with `default` (primary), `secondary`, `ghost`, `outline` variants.
*   **Input/Select:** `Input` and `Select` components for form elements, with clear focus states.
*   **Dialog:** `Dialog` for forms (e.g., creating/editing leads/customers, adding notes).
*   **Badge:** `Badge` for displaying lead statuses.
*   **Calendar/Date Picker:** For date-related inputs.

## UI Tokens (machine readable)

```json
{
  