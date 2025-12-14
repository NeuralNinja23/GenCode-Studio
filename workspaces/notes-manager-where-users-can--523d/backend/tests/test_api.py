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
# NOTE CRUD TESTS
# ═══════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_list_notes(client):
    """Test listing notes, including when notes exist."""
    # Ensure the collection is empty initially for a clean test state
    await client.delete("/api/notes/clear_all_for_tests") # Assuming a test-only endpoint to clear data

    response = await client.get("/api/notes")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list) # Expecting a list of notes directly
    assert len(data) == 0

    # Create a note and then list again
    note_data = {
        "title": fake.sentence(nb_words=4),
        "description": fake.paragraph(nb_sentences=2),
    }
    await client.post("/api/notes", json=note_data)

    response = await client.get("/api/notes")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["title"] == note_data["title"]


@pytest.mark.anyio
async def test_create_note(client):
    """Test creating a new note."""
    note_data = {
        "title": fake.sentence(nb_words=4),
        "description": fake.paragraph(nb_sentences=2),
    }
    response = await client.post("/api/notes", json=note_data)
    assert response.status_code in [200, 201]
    data = response.json()

    # Check for the created entity's ID and data
    note_id = data.get("id") or data.get("_id")
    assert note_id is not None
    assert data["title"] == note_data["title"]
    assert data["description"] == note_data["description"]


@pytest.mark.anyio
async def test_get_note_not_found(client):
    """Test getting a non-existent note returns 404."""
    # Use a valid but non-existent ObjectId
    fake_id = "507f1f77bcf86cd799439011"
    response = await client.get(f"/api/notes/{fake_id}")
    assert response.status_code == 404
    assert "Note not found" in response.json()["detail"]


@pytest.mark.anyio
async def test_get_note_by_id(client):
    """Test getting an existing note by ID."""
    # First create a note
    create_data = {
        "title": fake.sentence(nb_words=4),
        "description": fake.paragraph(nb_sentences=2),
    }
    create_response = await client.post("/api/notes", json=create_data)
    assert create_response.status_code in [200, 201]
    created_note = create_response.json()
    note_id = created_note.get("id") or created_note.get("_id")
    assert note_id is not None

    # Then get it by ID
    response = await client.get(f"/api/notes/{note_id}")
    assert response.status_code == 200
    retrieved_note = response.json()
    assert retrieved_note["id"] == note_id
    assert retrieved_note["title"] == create_data["title"]
    assert retrieved_note["description"] == create_data["description"]


@pytest.mark.anyio
async def test_update_note(client):
    """Test updating an existing note."""
    # First create a note
    create_data = {
        "title": fake.sentence(nb_words=4),
        "description": fake.paragraph(nb_sentences=2),
    }
    create_response = await client.post("/api/notes", json=create_data)
    assert create_response.status_code in [200, 201]
    created_note = create_response.json()
    note_id = created_note.get("id") or created_note.get("_id")
    assert note_id is not None
    
    # Then update it
    update_data = {
        "title": fake.sentence(nb_words=3),
        "description": fake.paragraph(nb_sentences=1),
    }
    response = await client.put(f"/api/notes/{note_id}", json=update_data)
    assert response.status_code == 200
    updated_note = response.json()
    assert updated_note["id"] == note_id
    assert updated_note["title"] == update_data["title"]
    assert updated_note["description"] == update_data["description"]

    # Verify the update by fetching it again
    get_response = await client.get(f"/api/notes/{note_id}")
    assert get_response.status_code == 200
    fetched_note = get_response.json()
    assert fetched_note["title"] == update_data["title"]


@pytest.mark.anyio
async def test_delete_note(client):
    """Test deleting a note."""
    # First create
    create_data = {
        "title": fake.sentence(nb_words=4),
        "description": fake.paragraph(nb_sentences=2),
    }
    create_response = await client.post("/api/notes", json=create_data)
    assert create_response.status_code in [200, 201]
    created_note = create_response.json()
    note_id = created_note.get("id") or created_note.get("_id")
    assert note_id is not None
    
    # Then delete
    response = await client.delete(f"/api/notes/{note_id}")
    assert response.status_code in [200, 204]

    # Try to get the deleted note, should return 404
    get_response = await client.get(f"/api/notes/{note_id}")
    assert get_response.status_code == 404


@pytest.mark.anyio
async def test_search_notes_by_title(client):
    """Test searching notes by title."""
    # Clear existing notes for a clean search test
    await client.delete("/api/notes/clear_all_for_tests") # Assuming a test-only endpoint to clear data

    # Create several notes with distinct titles
    note1_title = "Meeting Agenda for Project X"
    note2_title = "Follow-up on Project Y Tasks"
    note3_title = "Daily Standup Notes"
    note4_title = "Project X Brainstorming Ideas"

    await client.post("/api/notes", json={"title": note1_title, "description": fake.paragraph()})
    await client.post("/api/notes", json={"title": note2_title, "description": fake.paragraph()})
    await client.post("/api/notes", json={"title": note3_title, "description": fake.paragraph()})
    await client.post("/api/notes", json={"title": note4_title, "description": fake.paragraph()})

    # Search for "Project X"
    response = await client.get("/api/notes?search=Project X")
    assert response.status_code == 200
    search_results = response.json()
    assert len(search_results) == 2
    titles = {note["title"] for note in search_results}
    assert note1_title in titles
    assert note4_title in titles
    assert note2_title not in titles

    # Search for "Daily"
    response = await client.get("/api/notes?search=Daily")
    assert response.status_code == 200
    search_results = response.json()
    assert len(search_results) == 1
    assert search_results[0]["title"] == note3_title

    # Search for a non-existent term
    response = await client.get("/api/notes?search=NonExistent")
    assert response.status_code == 200
    search_results = response.json()
    assert len(search_results) == 0
