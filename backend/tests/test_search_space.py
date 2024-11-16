import pytest
from app.models.search_space import SearchSpace
from app.core.config import get_settings

settings = get_settings()

async def create_test_token(client, test_user):
    """Helper function to create a test user and get token."""
    test_user["apisecretkey"] = settings.API_SECRET_KEY
    await client.post("/register", json=test_user)
    response = await client.post(
        "/token",
        data={
            "username": test_user["username"],
            "password": test_user["password"]
        }
    )
    return response.json()["access_token"]

@pytest.mark.asyncio
async def test_create_search_space(client, test_user, test_search_space):
    """Test creating a search space."""
    token = await create_test_token(client, test_user)
    
    response = await client.post(
        "/user/create/searchspace/",
        json={
            "token": token,
            "name": test_search_space["name"],
            "description": test_search_space["description"]
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == test_search_space["name"]
    assert data["description"] == test_search_space["description"]

@pytest.mark.asyncio
async def test_get_user_search_spaces(client, test_user, test_search_space):
    """Test retrieving user's search spaces."""
    token = await create_test_token(client, test_user)
    
    # Create a search space
    await client.post(
        "/user/create/searchspace/",
        json={
            "token": token,
            "name": test_search_space["name"],
            "description": test_search_space["description"]
        }
    )
    
    # Get user's search spaces
    response = await client.get(f"/user/{token}/searchspaces/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["name"] == test_search_space["name"]

@pytest.mark.asyncio
async def test_get_search_space_by_id(client, test_user, test_search_space):
    """Test retrieving a specific search space."""
    token = await create_test_token(client, test_user)
    
    # Create a search space
    create_response = await client.post(
        "/user/create/searchspace/",
        json={
            "token": token,
            "name": test_search_space["name"],
            "description": test_search_space["description"]
        }
    )
    search_space_id = create_response.json()["id"]
    
    # Get the search space by ID
    response = await client.get(f"/user/{token}/searchspace/{search_space_id}/")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == search_space_id
    assert data["name"] == test_search_space["name"]

@pytest.mark.asyncio
async def test_get_nonexistent_search_space(client, test_user):
    """Test retrieving a nonexistent search space."""
    token = await create_test_token(client, test_user)
    
    response = await client.get(f"/user/{token}/searchspace/99999/")
    assert response.status_code == 404
    assert response.json()["detail"] == "Search space not found or does not belong to the user"

@pytest.mark.asyncio
async def test_get_search_space_unauthorized(client, test_user, test_search_space):
    """Test accessing a search space with invalid token."""
    # Create a search space with valid token
    token = await create_test_token(client, test_user)
    create_response = await client.post(
        "/user/create/searchspace/",
        json={
            "token": token,
            "name": test_search_space["name"],
            "description": test_search_space["description"]
        }
    )
    search_space_id = create_response.json()["id"]
    
    # Try to access with invalid token
    response = await client.get(f"/user/invalid_token/searchspace/{search_space_id}/")
    assert response.status_code == 403
    assert response.json()["detail"] == "Token is invalid or expired"
