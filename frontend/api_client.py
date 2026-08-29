import os
from typing import Any

import requests


API_BASE_URL = os.getenv(
    "API_BASE_URL",
    "http://127.0.0.1:8000",
)


class APIError(Exception):
    """Erreur retournée par le backend FastAPI."""


def _handle_response(response: requests.Response) -> Any:
    try:
        payload = response.json()
    except ValueError:
        payload = None

    if response.ok:
        return payload

    if isinstance(payload, dict):
        detail = payload.get("detail")
        if detail:
            raise APIError(str(detail))

    raise APIError(
        f"API error {response.status_code}"
    )


def _auth_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
    }


def register(
    email: str,
    password: str,
) -> dict:
    response = requests.post(
        f"{API_BASE_URL}/auth/register",
        json={
            "email": email,
            "password": password,
        },
        timeout=10,
    )

    return _handle_response(response)


def login(
    email: str,
    password: str,
) -> dict:
    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        data={
            "username": email,
            "password": password,
        },
        timeout=10,
    )

    return _handle_response(response)


def get_current_user(
    token: str,
) -> dict:
    response = requests.get(
        f"{API_BASE_URL}/auth/me",
        headers=_auth_headers(token),
        timeout=10,
    )

    return _handle_response(response)


def list_sessions(
    token: str,
) -> list[dict]:
    response = requests.get(
        f"{API_BASE_URL}/sessions",
        headers=_auth_headers(token),
        timeout=10,
    )

    return _handle_response(response)


def create_session(
    token: str,
    title: str,
) -> dict:
    response = requests.post(
        f"{API_BASE_URL}/sessions",
        headers=_auth_headers(token),
        json={
            "title": title,
        },
        timeout=10,
    )

    return _handle_response(response)

def send_agent_message(
    token: str,
    session_id: int,
    message: str,
) -> dict:
    response = requests.post(
        f"{API_BASE_URL}/sessions/{session_id}/agent",
        headers=_auth_headers(token),
        json={
            "message": message,
        },
        timeout=10,
    )

    return _handle_response(response)


def get_agent_task_status(
    token: str,
    session_id: int,
    task_id: str,
) -> dict:
    response = requests.get(
        (
            f"{API_BASE_URL}/sessions/"
            f"{session_id}/agent/tasks/{task_id}"
        ),
        headers=_auth_headers(token),
        timeout=10,
    )

    return _handle_response(response)


def get_messages(
    token: str,
    session_id: int,
) -> list[dict]:
    response = requests.get(
        f"{API_BASE_URL}/sessions/{session_id}/messages",
        headers=_auth_headers(token),
        timeout=10,
    )

    return _handle_response(response)
