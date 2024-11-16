import pytest
from httpx import AsyncClient
from app.core.config import get_settings
from app.core.security import create_access_token

settings = get_settings()

@pytest.mark.asyncio
async def test_register_user(client, test_user):
    """Test user registration."""
    # Add API secret key for registration
    test_user["apisecretkey"] = settings.API_SECRET_KEY
    
    response = await client.post("/register", json=test_user)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user["username"]
    assert "hashed_password" in data
    assert data["hashed_password"] != test_user["password"]

@pytest.mark.asyncio
async def test_register_existing_user(client, test_user):
    """Test registering an existing user."""
    # First registration
    test_user["apisecretkey"] = settings.API_SECRET_KEY
    await client.post("/register", json=test_user)
    
    # Second registration attempt
    response = await client.post("/register", json=test_user)
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"

@pytest.mark.asyncio
async def test_login(client, test_user):
    """Test user login."""
    # Register user first
    test_user["apisecretkey"] = settings.API_SECRET_KEY
    await client.post("/register", json=test_user)
    
    # Login
    response = await client.post(
        "/token",
        data={
            "username": test_user["username"],
            "password": test_user["password"]
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_invalid_login(client):
    """Test login with invalid credentials."""
    response = await client.post(
        "/token",
        data={
            "username": "nonexistent",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"

@pytest.mark.asyncio
async def test_verify_token(client, test_user):
    """Test token verification."""
    # Register and login user
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
    
    # Verify token
    response = await client.get(f"/verify-token/{token}")
    assert response.status_code == 200
    assert response.json()["message"] == "Token is valid"

@pytest.mark.asyncio
async def test_invalid_token(client):
    """Test verification with invalid token."""
    response = await client.get("/verify-token/invalid_token")
    assert response.status_code == 403
    assert response.json()["detail"] == "Token is invalid or expired"
