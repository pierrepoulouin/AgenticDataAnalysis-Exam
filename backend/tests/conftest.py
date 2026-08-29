import httpx
import pytest_asyncio

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app

# Important : enregistre bien tous les modèles
# dans Base.metadata avant create_all().
import backend.app.models  # noqa: F401


@pytest_asyncio.fixture
async def client(
    tmp_path,
    monkeypatch,
):
    """
    Client FastAPI avec base SQLite isolée
    et répertoire d'upload temporaire.
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