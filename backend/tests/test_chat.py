import pytest
from app.core.config import get_settings

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
async def test_create_chat(client, test_user, test_search_space, test_chat):
    """Test creating a chat in a search space."""
    token, search_space_id = await create_test_environment(client, test_user, test_search_space)
    
    response = await client.post(
        f"/searchspace/{search_space_id}/chat/create",
        json={
            "token": token,
            "type": "text",
            "title": test_chat["title"],
            "chats_list": test_chat["messages"]
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "chat_id" in data

@pytest.mark.asyncio
async def test_get_chat_by_id(client, test_user, test_search_space, test_chat):
    """Test retrieving a specific chat."""
    token, search_space_id = await create_test_environment(client, test_user, test_search_space)
    
    # Create chat
    create_response = await client.post(
        f"/searchspace/{search_space_id}/chat/create",
        json={
            "token": token,
            "type": "text",
            "title": test_chat["title"],
            "chats_list": test_chat["messages"]
        }
    )
    chat_id = create_response.json()["chat_id"]
    
    # Get chat by ID
    response = await client.get(
        f"/searchspace/{search_space_id}/chat/{token}/{chat_id}"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == test_chat["title"]

@pytest.mark.asyncio
async def test_update_chat(client, test_user, test_search_space, test_chat):
    """Test updating a chat."""
    token, search_space_id = await create_test_environment(client, test_user, test_search_space)
    
    # Create chat
    create_response = await client.post(
        f"/searchspace/{search_space_id}/chat/create",
        json={
            "token": token,
            "type": "text",
            "title": test_chat["title"],
            "chats_list": test_chat["messages"]
        }
    )
    chat_id = create_response.json()["chat_id"]
    
    # Update chat
    updated_messages = [{"role": "user", "content": "Test message"}]
    response = await client.post(
        f"/searchspace/{search_space_id}/chat/update",
        json={
            "token": token,
            "chatid": chat_id,
            "chats_list": updated_messages
        }
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Chat Updated"
    
    # Verify update
    get_response = await client.get(
        f"/searchspace/{search_space_id}/chat/{token}/{chat_id}"
    )
    assert get_response.json()["chats_list"] == updated_messages

@pytest.mark.asyncio
async def test_delete_chat(client, test_user, test_search_space, test_chat):
    """Test deleting a chat."""
    token, search_space_id = await create_test_environment(client, test_user, test_search_space)
    
    # Create chat
    create_response = await client.post(
        f"/searchspace/{search_space_id}/chat/create",
        json={
            "token": token,
            "type": "text",
            "title": test_chat["title"],
            "chats_list": test_chat["messages"]
        }
    )
    chat_id = create_response.json()["chat_id"]
    
    # Delete chat
    response = await client.get(
        f"/searchspace/{search_space_id}/chat/delete/{token}/{chat_id}"
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Chat Deleted"
    
    # Verify deletion
    get_response = await client.get(
        f"/searchspace/{search_space_id}/chat/{token}/{chat_id}"
    )
    assert get_response.status_code == 404
