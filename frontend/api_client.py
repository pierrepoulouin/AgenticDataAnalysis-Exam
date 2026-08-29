import os
from typing import Any

import requests


API_BASE_URL = os.getenv(
    "API_BASE_URL",
    "http://127.0.0.1:8000",
).rstrip("/")


class APIError(Exception):
    """Erreur lors d'un appel au backend FastAPI."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code


def _handle_response(
    response: requests.Response,
) -> Any:
    """
    Transforme une réponse HTTP en donnée Python.

    En cas d'erreur backend, lève APIError avec
    le status HTTP lorsque celui-ci est disponible.
    """

    try:
        payload = response.json()
    except ValueError:
        payload = None

    if response.ok:
        return payload

    if isinstance(payload, dict):
        detail = payload.get("detail")

        if detail:
            raise APIError(
                str(detail),
                status_code=response.status_code,
            )

    raise APIError(
        f"Backend returned HTTP {response.status_code}",
        status_code=response.status_code,
    )


def _request(
    method: str,
    path: str,
    **kwargs,
) -> Any:
    """
    Point d'entrée HTTP commun à tous les appels frontend.

    Permet notamment de convertir les erreurs réseau requests
    en APIError exploitable proprement dans Streamlit.
    """

    try:
        response = requests.request(
            method=method,
            url=f"{API_BASE_URL}{path}",
            **kwargs,
        )

    except requests.RequestException as exc:
        raise APIError(
            "Backend API unavailable"
        ) from exc

    return _handle_response(response)


def _auth_headers(
    token: str,
) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
    }


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


def register(
    email: str,
    password: str,
) -> dict:
    return _request(
        "POST",
        "/auth/register",
        json={
            "email": email,
            "password": password,
        },
        timeout=10,
    )


def login(
    email: str,
    password: str,
) -> dict:
    return _request(
        "POST",
        "/auth/login",
        data={
            "username": email,
            "password": password,
        },
        timeout=10,
    )


def refresh_tokens(
    refresh_token: str,
) -> dict:
    """
    Échange un refresh token valide contre
    un nouvel access token + refresh token.
    """

    return _request(
        "POST",
        "/auth/refresh",
        json={
            "refresh_token": refresh_token,
        },
        timeout=10,
    )


def get_current_user(
    token: str,
) -> dict:
    return _request(
        "GET",
        "/auth/me",
        headers=_auth_headers(token),
        timeout=10,
    )


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


def list_sessions(
    token: str,
) -> list[dict]:
    return _request(
        "GET",
        "/sessions",
        headers=_auth_headers(token),
        timeout=10,
    )


def create_session(
    token: str,
    title: str,
) -> dict:
    return _request(
        "POST",
        "/sessions",
        headers=_auth_headers(token),
        json={
            "title": title,
        },
        timeout=10,
    )


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------


def get_messages(
    token: str,
    session_id: int,
) -> list[dict]:
    return _request(
        "GET",
        f"/sessions/{session_id}/messages",
        headers=_auth_headers(token),
        timeout=10,
    )


# ---------------------------------------------------------------------------
# Agent / Celery
# ---------------------------------------------------------------------------


def send_agent_message(
    token: str,
    session_id: int,
    message: str,
) -> dict:
    """
    Envoie une requête agentique.

    FastAPI renvoie normalement 202 Accepted
    avec un task_id Celery.
    """

    return _request(
        "POST",
        f"/sessions/{session_id}/agent",
        headers=_auth_headers(token),
        json={
            "message": message,
        },
        timeout=10,
    )


def get_agent_task_status(
    token: str,
    session_id: int,
    task_id: str,
) -> dict:
    return _request(
        "GET",
        (
            f"/sessions/{session_id}"
            f"/agent/tasks/{task_id}"
        ),
        headers=_auth_headers(token),
        timeout=10,
    )


# ---------------------------------------------------------------------------
# Visualizations
# ---------------------------------------------------------------------------


def list_message_visualizations(
    token: str,
    message_id: int,
) -> list[dict]:
    return _request(
        "GET",
        f"/messages/{message_id}/visualizations",
        headers=_auth_headers(token),
        timeout=10,
    )


# ---------------------------------------------------------------------------
# Datasets
# ---------------------------------------------------------------------------


def list_datasets(
    token: str,
) -> list[dict]:
    return _request(
        "GET",
        "/datasets",
        headers=_auth_headers(token),
        timeout=10,
    )


def upload_dataset(
    token: str,
    session_id: int,
    uploaded_file,
    description: str = "",
) -> dict:
    """
    Upload d'un CSV Streamlit vers FastAPI.

    uploaded_file correspond à l'objet renvoyé
    par st.file_uploader().
    """

    return _request(
        "POST",
        f"/sessions/{session_id}/datasets/upload",
        headers=_auth_headers(token),
        files={
            "file": (
                uploaded_file.name,
                uploaded_file.getvalue(),
                uploaded_file.type or "text/csv",
            )
        },
        data={
            "description": description,
        },
        timeout=30,
    )