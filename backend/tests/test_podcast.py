import pytest
from app.core.config import get_settings
from app.services.podcast import PodcastService

settings = get_settings()

async def create_test_environment(client, test_user, test_search_space):
    """Helper function to create test user, get token and create search space."""
    # Create user and get token
    test_user["apisecretkey"] = settings.API_SECRET_KEY
    await client.post("/register", json=test_user)
    login_response = await client.post(
        "/token",
        data={
            "username": test_user["username"],
            "password": test_user["password"]
        }
    )
    token = login_response.json()["access_token"]
    
    # Create search space
    create_response = await client.post(
        "/user/create/searchspace/",
        json={
            "token": token,
            "name": test_search_space["name"],
            "description": test_search_space["description"]
        }
    )
    search_space_id = create_response.json()["id"]
    
    return token, search_space_id

@pytest.mark.asyncio
async def test_create_podcast(client, test_user, test_search_space, test_podcast):
    """Test creating a podcast."""
    token, search_space_id = await create_test_environment(client, test_user, test_search_space)
    
    response = await client.post(
        f"/searchspace/{search_space_id}/podcasts/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": test_podcast["title"],
            "content": test_podcast["content"],
            "word_count": test_podcast["wordcount"]
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == test_podcast["title"]
    assert data["status"] == "pending"
    assert not data["is_completed"]

@pytest.mark.asyncio
async def test_get_podcasts(client, test_user, test_search_space, test_podcast):
    """Test retrieving podcasts in a search space."""
    token, search_space_id = await create_test_environment(client, test_user, test_search_space)
    
    # Create a podcast
    await client.post(
        f"/searchspace/{search_space_id}/podcasts/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": test_podcast["title"],
            "content": test_podcast["content"],
            "word_count": test_podcast["wordcount"]
        }
    )
    
    # Get podcasts
    response = await client.get(
        f"/searchspace/{search_space_id}/podcasts/",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["title"] == test_podcast["title"]

@pytest.mark.asyncio
async def test_get_podcast_by_id(client, test_user, test_search_space, test_podcast):
    """Test retrieving a specific podcast."""
    token, search_space_id = await create_test_environment(client, test_user, test_search_space)
    
    # Create a podcast
    create_response = await client.post(
        f"/searchspace/{search_space_id}/podcasts/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": test_podcast["title"],
            "content": test_podcast["content"],
            "word_count": test_podcast["wordcount"]
        }
    )
    podcast_id = create_response.json()["id"]
    
    # Get podcast by ID
    response = await client.get(
        f"/searchspace/{search_space_id}/podcasts/{podcast_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == podcast_id
    assert data["title"] == test_podcast["title"]

@pytest.mark.asyncio
async def test_update_podcast(client, test_user, test_search_space, test_podcast):
    """Test updating a podcast."""
    token, search_space_id = await create_test_environment(client, test_user, test_search_space)
    
    # Create a podcast
    create_response = await client.post(
        f"/searchspace/{search_space_id}/podcasts/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": test_podcast["title"],
            "content": test_podcast["content"],
            "word_count": test_podcast["wordcount"]
        }
    )
    podcast_id = create_response.json()["id"]
    
    # Update podcast
    updated_title = "Updated Test Podcast"
    response = await client.put(
        f"/searchspace/{search_space_id}/podcasts/{podcast_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": updated_title}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == updated_title

@pytest.mark.asyncio
async def test_delete_podcast(client, test_user, test_search_space, test_podcast):
    """Test deleting a podcast."""
    token, search_space_id = await create_test_environment(client, test_user, test_search_space)
    
    # Create a podcast
    create_response = await client.post(
        f"/searchspace/{search_space_id}/podcasts/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": test_podcast["title"],
            "content": test_podcast["content"],
            "word_count": test_podcast["wordcount"]
        }
    )
    podcast_id = create_response.json()["id"]
    
    # Delete podcast
    response = await client.delete(
        f"/searchspace/{search_space_id}/podcasts/{podcast_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Podcast deleted successfully"
    
    # Verify deletion
    get_response = await client.get(
        f"/searchspace/{search_space_id}/podcasts/{podcast_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert get_response.status_code == 404
