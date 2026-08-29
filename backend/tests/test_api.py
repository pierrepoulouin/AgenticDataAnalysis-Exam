"""
API tests for FastAPI backend.

Run with:
    python -m pytest backend/tests/test_api.py -v
"""

import httpx
import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app


@pytest.fixture
async def client(
    tmp_path,
    monkeypatch,
):
    """
    Client HTTP utilisant une base SQLite isolée.

    Les tests ne touchent pas à la base PostgreSQL
    utilisée par l'application locale.
    """

    monkeypatch.setenv(
        "UPLOAD_ROOT",
        str(tmp_path / "uploads"),
    )

    engine = create_engine(
        "sqlite://",
        connect_args={
            "check_same_thread": False,
        },
        poolclass=StaticPool,
    )

    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    Base.metadata.create_all(
        bind=engine
    )

    def override_get_db():
        db = TestingSessionLocal()

        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[
        get_db
    ] = override_get_db

    transport = httpx.ASGITransport(
        app=app
    )

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as async_client:
        yield async_client

    app.dependency_overrides.clear()

    Base.metadata.drop_all(
        bind=engine
    )

    engine.dispose()


@pytest.mark.asyncio
async def test_health_check(client):
    """Health endpoint must return HTTP 200."""

    response = await client.get(
        "/health"
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["status"] == "ok"

@pytest.mark.asyncio
async def test_auth_register(client):
    response = await client.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "password": "MotDePasse123",
        },
    )

    assert response.status_code == 201

    payload = response.json()

    assert payload["email"] == "test@example.com"
    assert "hashed_password" not in payload


@pytest.mark.asyncio
async def test_auth_login(client):
    await client.post(
        "/auth/register",
        json={
            "email": "login@example.com",
            "password": "MotDePasse123",
        },
    )

    response = await client.post(
        "/auth/login",
        data={
            "username": "login@example.com",
            "password": "MotDePasse123",
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["token_type"] == "bearer"
    assert payload["access_token"]
    assert payload["refresh_token"]

@pytest.mark.asyncio
async def test_upload_dataset(client):
    email = "upload@example.com"
    password = "MotDePasse123"

    # Création utilisateur
    register_response = await client.post(
        "/auth/register",
        json={
            "email": email,
            "password": password,
        },
    )

    assert register_response.status_code == 201

    # Login
    login_response = await client.post(
        "/auth/login",
        data={
            "username": email,
            "password": password,
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()[
        "access_token"
    ]

    headers = {
        "Authorization": (
            f"Bearer {access_token}"
        )
    }

    # Création de la session
    session_response = await client.post(
        "/sessions",
        headers=headers,
        json={
            "title": "CSV upload test",
        },
    )

    assert session_response.status_code == 201

    session_id = session_response.json()[
        "id"
    ]

    # CSV envoyé directement en mémoire
    csv_content = (
        "produit,montant\n"
        "A,100\n"
        "B,250\n"
        "C,50\n"
        "D,300\n"
    )

    upload_response = await client.post(
        (
            f"/sessions/{session_id}"
            "/datasets/upload"
        ),
        headers=headers,
        files={
            "file": (
                "ventes_test.csv",
                csv_content.encode("utf-8"),
                "text/csv",
            )
        },
        data={
            "description": (
                "Dataset utilisé par pytest"
            ),
        },
    )

    assert upload_response.status_code == 201

    dataset = upload_response.json()

    assert dataset["filename"] == "ventes_test.csv"
    assert dataset["session_id"] == session_id
    assert (
        dataset["description"]
        == "Dataset utilisé par pytest"
    )

    # Vérifie également que le dataset
    # est récupérable via l'API.
    datasets_response = await client.get(
        "/datasets",
        headers=headers,
    )

    assert datasets_response.status_code == 200

    datasets = datasets_response.json()

    assert any(
        item["id"] == dataset["id"]
        and item["session_id"] == session_id
        and item["filename"] == "ventes_test.csv"
        for item in datasets
    )

@pytest.mark.asyncio
async def test_analysis_session(client):
    email = "session@example.com"
    password = "MotDePasse123"

    register_response = await client.post(
        "/auth/register",
        json={
            "email": email,
            "password": password,
        },
    )

    assert register_response.status_code == 201

    login_response = await client.post(
        "/auth/login",
        data={
            "username": email,
            "password": password,
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()[
        "access_token"
    ]

    headers = {
        "Authorization": (
            f"Bearer {access_token}"
        )
    }

    create_response = await client.post(
        "/sessions",
        headers=headers,
        json={
            "title": "Persistent analysis",
        },
    )

    assert create_response.status_code == 201

    created_session = (
        create_response.json()
    )

    session_id = created_session["id"]

    assert (
        created_session["title"]
        == "Persistent analysis"
    )

    list_response = await client.get(
        "/sessions",
        headers=headers,
    )

    assert list_response.status_code == 200

    sessions = list_response.json()

    assert any(
        session["id"] == session_id
        and session["title"]
        == "Persistent analysis"
        for session in sessions
    )

    get_response = await client.get(
        f"/sessions/{session_id}",
        headers=headers,
    )

    assert get_response.status_code == 200
    assert get_response.json()["id"] == session_id

@pytest.mark.security
@pytest.mark.asyncio
async def test_unauthorized_access(client):
    response = await client.get(
        "/sessions"
    )

    assert response.status_code == 401
