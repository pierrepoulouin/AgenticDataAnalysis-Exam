"""
Persistence tests for durable application state.

Run with:
    python -m pytest backend/tests/test_persistence.py -v
"""

import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.agent.manager import AgentManager
from backend.app.database import Base
from backend.app.models import (
    ChatSession,
    User,
)


@pytest.fixture
def persistence_db(tmp_path):
    """
    Base SQLite sur disque.

    Contrairement à une base SQLite purement en mémoire,
    elle permet de fermer complètement une connexion puis
    d'en ouvrir une nouvelle afin de simuler un redémarrage.
    """

    database_path = (
        tmp_path / "persistence_test.db"
    )

    engine = create_engine(
        f"sqlite:///{database_path}",
        connect_args={
            "check_same_thread": False,
        },
    )

    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    Base.metadata.create_all(
        bind=engine
    )

    yield TestingSessionLocal

    Base.metadata.drop_all(
        bind=engine
    )

    engine.dispose()


def create_user_and_session(
    SessionLocal,
    *,
    email: str = "persistence@example.com",
    title: str = "Persistent analysis",
) -> tuple[int, int]:
    """
    Crée les données minimales nécessaires
    à un AgentManager.
    """

    db = SessionLocal()

    try:
        user = User(
            email=email,
            hashed_password="not-used-in-this-test",
            is_active=True,
        )

        db.add(user)
        db.flush()

        session = ChatSession(
            user_id=user.id,
            title=title,
        )

        db.add(session)
        db.commit()

        return user.id, session.id

    finally:
        db.close()


@pytest.mark.persistence
def test_session_recovery(
    persistence_db,
):
    """
    CRITICAL TEST:
    une nouvelle instance AgentManager retrouve
    l'historique enregistré avant un "restart".
    """

    SessionLocal = persistence_db

    user_id, session_id = (
        create_user_and_session(
            SessionLocal
        )
    )

    # ---------------------------------------------------------
    # Processus / instance n°1
    # ---------------------------------------------------------

    db_before_restart = SessionLocal()

    manager_before_restart = AgentManager(
        session_id=session_id,
        user_id=user_id,
        db=db_before_restart,
    )

    manager_before_restart.save_message(
        role="user",
        content="Quel est le total des ventes ?",
    )

    manager_before_restart.save_message(
        role="assistant",
        content="Le total est de 700.",
    )

    # On ferme complètement la session SQLAlchemy.
    db_before_restart.close()

    # ---------------------------------------------------------
    # Simulation du redémarrage
    # Nouvelle session DB + nouvel AgentManager.
    # ---------------------------------------------------------

    db_after_restart = SessionLocal()

    try:
        manager_after_restart = AgentManager(
            session_id=session_id,
            user_id=user_id,
            db=db_after_restart,
        )

        history = (
            manager_after_restart.load_history()
        )

        assert len(history) == 2

        assert history[0]["role"] == "user"
        assert (
            history[0]["content"]
            == "Quel est le total des ventes ?"
        )

        assert (
            history[1]["role"]
            == "assistant"
        )

        assert (
            history[1]["content"]
            == "Le total est de 700."
        )

        assert (
            history[0]["created_at"]
            is not None
        )

        assert (
            history[1]["created_at"]
            is not None
        )

    finally:
        db_after_restart.close()


@pytest.mark.asyncio
@pytest.mark.persistence
async def test_user_data_isolation(
    client,
):
    """
    User B ne doit voir ni accéder
    au dataset de User A.
    """

    password = "MotDePasse123"

    # ---------------------------------------------------------
    # Création A et B
    # ---------------------------------------------------------

    for email in (
        "dataset-a@example.com",
        "dataset-b@example.com",
    ):
        response = await client.post(
            "/auth/register",
            json={
                "email": email,
                "password": password,
            },
        )

        assert response.status_code == 201

    login_a = await client.post(
        "/auth/login",
        data={
            "username": "dataset-a@example.com",
            "password": password,
        },
    )

    login_b = await client.post(
        "/auth/login",
        data={
            "username": "dataset-b@example.com",
            "password": password,
        },
    )

    token_a = login_a.json()[
        "access_token"
    ]

    token_b = login_b.json()[
        "access_token"
    ]

    headers_a = {
        "Authorization": f"Bearer {token_a}"
    }

    headers_b = {
        "Authorization": f"Bearer {token_b}"
    }

    # ---------------------------------------------------------
    # A crée une session
    # ---------------------------------------------------------

    session_response = await client.post(
        "/sessions",
        headers=headers_a,
        json={
            "title": "Private dataset A",
        },
    )

    assert (
        session_response.status_code
        == 201
    )

    session_id = session_response.json()[
        "id"
    ]

    # ---------------------------------------------------------
    # A upload un CSV
    # ---------------------------------------------------------

    csv_content = (
        "produit,montant\n"
        "A,100\n"
        "B,250\n"
    )

    upload_response = await client.post(
        (
            f"/sessions/{session_id}"
            "/datasets/upload"
        ),
        headers=headers_a,
        files={
            "file": (
                "private_a.csv",
                csv_content.encode("utf-8"),
                "text/csv",
            )
        },
    )

    assert (
        upload_response.status_code
        == 201
    )

    dataset_id = upload_response.json()[
        "id"
    ]

    # ---------------------------------------------------------
    # A voit son dataset
    # ---------------------------------------------------------

    list_a = await client.get(
        "/datasets",
        headers=headers_a,
    )

    assert list_a.status_code == 200

    assert any(
        dataset["id"] == dataset_id
        for dataset in list_a.json()
    )

    # ---------------------------------------------------------
    # B ne le voit pas
    # ---------------------------------------------------------

    list_b = await client.get(
        "/datasets",
        headers=headers_b,
    )

    assert list_b.status_code == 200

    assert all(
        dataset["id"] != dataset_id
        for dataset in list_b.json()
    )

    # ---------------------------------------------------------
    # B ne peut pas y accéder directement
    # ---------------------------------------------------------

    get_b = await client.get(
        f"/datasets/{dataset_id}",
        headers=headers_b,
    )

    assert get_b.status_code == 404


@pytest.mark.persistence
def test_visualization_storage(
    persistence_db,
):
    """
    Une figure Plotly sérialisée en JSON
    doit rester disponible après reconstruction
    de l'AgentManager.
    """

    SessionLocal = persistence_db

    user_id, session_id = (
        create_user_and_session(
            SessionLocal,
            email="visualization@example.com",
        )
    )

    figure_json = {
        "data": [
            {
                "type": "bar",
                "x": [
                    "A",
                    "B",
                    "C",
                ],
                "y": [
                    100,
                    250,
                    50,
                ],
            }
        ],
        "layout": {
            "title": {
                "text": "Montants"
            }
        },
    }

    # ---------------------------------------------------------
    # Avant restart
    # ---------------------------------------------------------

    db_before_restart = SessionLocal()

    manager_before_restart = AgentManager(
        session_id=session_id,
        user_id=user_id,
        db=db_before_restart,
    )

    manager_before_restart.save_message(
        role="assistant",
        content="Voici le graphique.",
        figures=[
            figure_json
        ],
    )

    db_before_restart.close()

    # ---------------------------------------------------------
    # Après restart
    # ---------------------------------------------------------

    db_after_restart = SessionLocal()

    try:
        manager_after_restart = AgentManager(
            session_id=session_id,
            user_id=user_id,
            db=db_after_restart,
        )

        history = (
            manager_after_restart.load_history()
        )

        assert len(history) == 1

        message = history[0]

        assert (
            message["content"]
            == "Voici le graphique."
        )

        assert len(
            message["figures"]
        ) == 1

        assert (
            message["figures"][0]
            == figure_json
        )

    finally:
        db_after_restart.close()


@pytest.mark.persistence
def test_analysis_history(
    persistence_db,
):
    """
    L'historique complet doit conserver
    ordre, rôles, contenus et timestamps.
    """

    SessionLocal = persistence_db

    user_id, session_id = (
        create_user_and_session(
            SessionLocal,
            email="history@example.com",
        )
    )

    db_first_request = SessionLocal()

    manager = AgentManager(
        session_id=session_id,
        user_id=user_id,
        db=db_first_request,
    )

    manager.save_message(
        role="user",
        content="Analyse mes données.",
    )

    manager.save_message(
        role="assistant",
        content="Que souhaitez-vous analyser ?",
    )

    manager.save_message(
        role="user",
        content="Le montant total.",
    )

    manager.save_message(
        role="assistant",
        content="Le total est de 700.",
    )

    db_first_request.close()

    # Nouvelle connexion DB pour s'assurer
    # que l'historique ne vient pas de la RAM.
    db_second_request = SessionLocal()

    try:
        manager_reloaded = AgentManager(
            session_id=session_id,
            user_id=user_id,
            db=db_second_request,
        )

        history = (
            manager_reloaded.load_history()
        )

        assert len(history) == 4

        assert [
            message["role"]
            for message in history
        ] == [
            "user",
            "assistant",
            "user",
            "assistant",
        ]

        assert [
            message["content"]
            for message in history
        ] == [
            "Analyse mes données.",
            "Que souhaitez-vous analyser ?",
            "Le montant total.",
            "Le total est de 700.",
        ]

        assert all(
            message["created_at"]
            is not None
            for message in history
        )

    finally:
        db_second_request.close()