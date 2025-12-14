import pytest
from faker import Faker

# Initialize Faker for realistic test data
fake = Faker()


# ═══════════════════════════════════════════════════════
# HEALTH CHECK (Always include - validates API is running)
# ═══════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_health_check(client):
    """Test the health check endpoint."""
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "healthy"


# ═══════════════════════════════════════════════════════
# TASK CRUD TESTS
# ═══════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_list_tasks_empty(client):
    """Test listing tasks when none exist."""
    response = await client.get("/api/tasks")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0

@pytest.mark.anyio
async def test_create_task(client):
    """Test creating a new task."""
    task_data = {
        "title": fake.sentence(nb_words=4),
        "description": fake.paragraph(nb_sentences=2),
        "status": "active"
    }
    response = await client.post("/api/tasks", json=task_data)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["title"] == task_data["title"]
    assert data["description"] == task_data["description"]
    assert data["status"] == "active"

@pytest.mark.anyio
async def test_get_task_not_found(client):
    """Test getting a non-existent task returns 404."""
    # Use a valid but non-existent ObjectId format
    fake_id = "507f1f77bcf86cd799439011"
    response = await client.get(f"/api/tasks/{fake_id}")
    assert response.status_code == 404

@pytest.mark.anyio
async def test_get_task_by_id(client):
    """Test getting an existing task by ID."""
    # First create a task
    create_data = {
        "title": fake.sentence(nb_words=4),
        "description": fake.paragraph(nb_sentences=2),
        "status": "active"
    }
    create_response = await client.post("/api/tasks", json=create_data)
    assert create_response.status_code == 201
    created_task = create_response.json()
    task_id = created_task["id"]

    # Then get it by ID
    response = await client.get(f"/api/tasks/{task_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == task_id
    assert data["title"] == create_data["title"]

@pytest.mark.anyio
async def test_update_task(client):
    """Test updating an existing task."""
    # First create a task
    create_data = {
        "title": fake.sentence(nb_words=4),
        "description": fake.paragraph(nb_sentences=2),
        "status": "active"
    }
    create_response = await client.post("/api/tasks", json=create_data)
    assert create_response.status_code == 201
    created_task = create_response.json()
    task_id = created_task["id"]
    
    # Then update it
    update_data = {
        "title": "Updated " + fake.sentence(nb_words=3),
        "description": "Updated " + fake.paragraph(nb_sentences=1),
        "status": "completed"
    }
    response = await client.put(f"/api/tasks/{task_id}", json=update_data)
    assert response.status_code == 200
    updated_task = response.json()
    assert updated_task["id"] == task_id
    assert updated_task["title"] == update_data["title"]
    assert updated_task["description"] == update_data["description"]
    assert updated_task["status"] == "completed"

@pytest.mark.anyio
async def test_delete_task(client):
    """Test deleting a task."""
    # First create
    create_data = {
        "title": fake.sentence(nb_words=4),
        "description": fake.paragraph(nb_sentences=2),
        "status": "active"
    }
    create_response = await client.post("/api/tasks", json=create_data)
    assert create_response.status_code == 201
    created_task = create_response.json()
    task_id = created_task["id"]
    
    # Then delete
    response = await client.delete(f"/api/tasks/{task_id}")
    assert response.status_code == 204 # No Content

    # Verify it's gone
    get_response = await client.get(f"/api/tasks/{task_id}")
    assert get_response.status_code == 404


# ═══════════════════════════════════════════════════════
# TASK FILTERING TESTS
# ═══════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_list_tasks_filter_active(client):
    """Test listing tasks filtered by 'active' status."""
    # Create some tasks with different statuses
    await client.post("/api/tasks", json={"title": "Active Task 1", "description": "Desc 1", "status": "active"})
    await client.post("/api/tasks", json={"title": "Completed Task 1", "description": "Desc 2", "status": "completed"})
    await client.post("/api/tasks", json={"title": "Active Task 2", "description": "Desc 3", "status": "active"})

    response = await client.get("/api/tasks?status=active")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2 # May include tasks from other tests, but at least 2 active
    for task in data:
        assert task["status"] == "active"

@pytest.mark.anyio
async def test_list_tasks_filter_completed(client):
    """Test listing tasks filtered by 'completed' status."""
    # Create some tasks with different statuses
    await client.post("/api/tasks", json={"title": "Active Task X", "description": "Desc X", "status": "active"})
    await client.post("/api/tasks", json={"title": "Completed Task Y", "description": "Desc Y", "status": "completed"})
    await client.post("/api/tasks", json={"title": "Completed Task Z", "description": "Desc Z", "status": "completed"})

    response = await client.get("/api/tasks?status=completed")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2 # May include tasks from other tests, but at least 2 completed
    for task in data:
        assert task["status"] == "completed"

@pytest.mark.anyio
async def test_list_tasks_filter_invalid_status(client):
    """Test listing tasks with an invalid status filter."""
    response = await client.get("/api/tasks?status=invalid_status")
    assert response.status_code == 422 # Unprocessable Entity for validation error
