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

async def _create_note_helper(client, title=None, description=None):
    """Helper to create a note and return its data."""
    note_data = {
        "title": title or fake.sentence(nb_words=4),
        "description": description or fake.paragraph(nb_sentences=2),
    }
    response = await client.post("/api/notes", json=note_data)
    assert response.status_code in [200, 201]
    created_note = response.json()
    return created_note.get("data") or created_note # Handle both direct and data-wrapped responses


@pytest.mark.anyio
async def test_list_notes_empty(client):
    """Test listing notes when none exist."""
    response = await client.get("/api/notes")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict) and "data" in data # Expect a data wrapper
    assert len(data["data"]) == 0


@pytest.mark.anyio
async def test_create_note(client):
    """Test creating a new note."""
    original_title = fake.sentence(nb_words=4)
    original_description = fake.paragraph(nb_sentences=2)
    note_data = {
        "title": original_title,
        "description": original_description,
    }
    response = await client.post("/api/notes", json=note_data)
    assert response.status_code in [200, 201]
    data = response.json()
    created_note = data.get("data") or data

    assert "id" in created_note or "_id" in created_note
    assert created_note["title"] == original_title
    assert created_note["description"] == original_description


@pytest.mark.anyio
async def test_get_note_not_found(client):
    """Test getting a non-existent note returns 404."""
    # Use a valid but non-existent ObjectId
    fake_id = "507f1f77bcf86cd799439011"
    response = await client.get(f"/api/notes/{fake_id}")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_list_notes_with_data(client):
    """Test listing notes when some exist."""
    await _create_note_helper(client)
    await _create_note_helper(client)

    response = await client.get("/api/notes")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict) and "data" in data
    assert len(data["data"]) >= 2 # Should contain at least the two we just created


@pytest.mark.anyio
async def test_get_single_note(client):
    """Test retrieving a single note by ID."""
    created = await _create_note_helper(client)
    note_id = created.get("id") or created.get("_id")

    response = await client.get(f"/api/notes/{note_id}")
    assert response.status_code == 200
    retrieved_note = response.json().get("data") or response.json()

    assert retrieved_note["id"] == note_id
    assert retrieved_note["title"] == created["title"]
    assert retrieved_note["description"] == created["description"]


@pytest.mark.anyio
async def test_update_note(client):
    """Test updating an existing note."""
    # First create a note
    created = await _create_note_helper(client)
    note_id = created.get("id") or created.get("_id")

    # Then update it
    updated_title = fake.sentence(nb_words=3)
    updated_description = fake.paragraph(nb_sentences=1)
    update_data = {
        "title": updated_title,
        "description": updated_description,
    }
    response = await client.put(f"/api/notes/{note_id}", json=update_data)
    assert response.status_code == 200
    updated_note = response.json().get("data") or response.json()

    assert updated_note["id"] == note_id
    assert updated_note["title"] == updated_title
    assert updated_note["description"] == updated_description

    # Verify the update by fetching it again
    get_response = await client.get(f"/api/notes/{note_id}")
    assert get_response.status_code == 200
    verified_note = get_response.json().get("data") or get_response.json()
    assert verified_note["title"] == updated_title
    assert verified_note["description"] == updated_description


@pytest.mark.anyio
async def test_delete_note(client):
    """Test deleting a note."""
    # First create
    created = await _create_note_helper(client)
    note_id = created.get("id") or created.get("_id")

    # Then delete
    response = await client.delete(f"/api/notes/{note_id}")
    assert response.status_code in [200, 204]

    # Verify it's gone
    get_response = await client.get(f"/api/notes/{note_id}")
    assert get_response.status_code == 404


@pytest.mark.anyio
async def test_search_notes_by_title(client):
    """Test searching notes by title keyword."""
    # Create several notes, some with a specific keyword
    keyword = "unique_search_term"
    await _create_note_helper(client, title=f"Note with {keyword} in title 1")
    await _create_note_helper(client, title=f"Another {keyword} note")
    await _create_note_helper(client, title="Regular note without keyword")

    # Search for the keyword
    response = await client.get(f"/api/notes?title={keyword}")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict) and "data" in data
    search_results = data["data"]

    assert len(search_results) >= 2 # Should find at least the two we created
    for note in search_results:
        assert keyword in note["title"].lower() # Ensure all results contain the keyword

    # Test search with no results
    response_no_results = await client.get("/api/notes?title=nonexistentkeyword123")
    assert response_no_code == 200
    data_no_results = response_no_results.json()
    assert len(data_no_results["data"]) == 0
