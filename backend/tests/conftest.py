import asyncio
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
from app.core.config import get_settings
from app.main import app
from app.db.session import get_db

settings = get_settings()

# Test database URL
TEST_DATABASE_URL = settings.POSTGRES_DATABASE_URL.replace(
    settings.POSTGRES_DB,
    f"{settings.POSTGRES_DB}_test"
)

# Create test engine
engine = create_async_engine(TEST_DATABASE_URL, echo=True)
TestingSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_db():
    """Create test database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def db_session(test_db):
    """Get test database session."""
    async with TestingSessionLocal() as session:
        yield session

@pytest.fixture
async def client(db_session):
    """Create test client with database session."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def test_user():
    """Test user data."""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123"
    }

@pytest.fixture
def test_search_space():
    """Test search space data."""
    return {
        "name": "Test Space",
        "description": "Test search space description"
    }

@pytest.fixture
def test_document():
    """Test document data."""
    return {
        "filename": "test.txt",
        "content": "Test document content",
        "file_type": "text/plain"
    }

@pytest.fixture
def test_chat():
    """Test chat data."""
    return {
        "title": "Test Chat",
        "messages": []
    }

@pytest.fixture
def test_podcast():
    """Test podcast data."""
    return {
        "title": "Test Podcast",
        "content": "Test podcast content",
        "wordcount": 500
    }
