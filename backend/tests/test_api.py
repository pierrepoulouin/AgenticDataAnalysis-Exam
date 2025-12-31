"""
API tests for FastAPI backend.
Run with: pytest backend/tests/test_api.py -v
"""
import pytest
import httpx
from fastapi.testclient import TestClient

# NOTE: Import will work after backend implementation
# from backend.api.main import app
# from backend.api.dependencies import get_db


@pytest.fixture
async def client():
    """Create async client for API testing."""
    TODO: Implement after backend creation
    pass


@pytest.mark.asyncio
async def test_health_check(client):
    """Test that health endpoint returns 200."""
    pytest.skip("Backend not implemented yet - students will complete this")


@pytest.mark.asyncio
async def test_auth_register(client):
    """
    Test: User registration endpoint
    Expected: User created with hashed password
    """
    pytest.skip("Backend not implemented yet - students will complete this")


@pytest.mark.asyncio
async def test_auth_login(client):
    """
    Test: User login endpoint
    Expected: JWT token returned
    """
    pytest.skip("Backend not implemented yet - students will complete this")


@pytest.mark.asyncio
async def test_upload_dataset(client):
    """
    Test: Dataset upload endpoint
    Expected: Dataset saved and metadata returned
    """
    pytest.skip("Backend not implemented yet - students will complete this")


@pytest.mark.asyncio
async def test_analysis_session(client):
    """
    Test: Analysis session creation and querying
    Expected: Session persists across requests
    """
    pytest.skip("Backend not implemented yet - students will complete this")


@pytest.mark.security
async def test_unauthorized_access(client):
    """
    Test: Unauthorized access attempt
    Expected: 401 Unauthorized returned
    """
    pytest.skip("Backend not implemented yet - students will complete this")
