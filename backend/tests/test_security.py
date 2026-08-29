"""
Security tests for the sandboxed Python execution and API protection.
Run with: pytest backend/tests/test_security.py -v
"""
import pytest
import asyncio

# NOTE: Import will work after backend implementation
# from backend.agents.agent_manager import AgentManager
# from backend.security.sandbox import execute_sandboxed_code


@pytest.mark.security
def test_code_execution_sandbox():
    """
    Malicious Python operations must be rejected
    before exec() is reached.
    """

    from backend.app.agent.executor import execute_python

    malicious_code_attempts = [
        "__import__('os').system('echo HACKED')",
        "__import__('subprocess').call(['echo', 'HACKED'])",
        "open('/etc/passwd', 'r').read()",
        "__import__('socket').socket()",
    ]

    for attempt in malicious_code_attempts:
        with pytest.raises(ValueError):
            execute_python(attempt)

@pytest.mark.security
def test_resource_limits():
    """
    Infinite loops must be terminated by timeout
    and excessive allocations by a memory limit.
    """

    import time

    from backend.app.agent.executor import (
        SandboxMemoryLimitError,
        SandboxTimeoutError,
        execute_python,
    )

    infinite_loop = (
        "while True:\n"
        "    pass"
    )

    started_at = time.monotonic()

    with pytest.raises(
        SandboxTimeoutError
    ):
        execute_python(
            infinite_loop,
            timeout_seconds=0.5,
            memory_limit_mb=64,
        )

    elapsed = (
        time.monotonic()
        - started_at
    )

    # Le test prouve aussi que pytest
    # n'est pas resté bloqué.
    assert elapsed < 3

    memory_heavy = (
        "x = [list(range(10000)) "
        "for _ in range(10000)]"
    )

    with pytest.raises(
        SandboxMemoryLimitError
    ):
        execute_python(
            memory_heavy,
            timeout_seconds=5,
            memory_limit_mb=64,
        )


@pytest.mark.asyncio
@pytest.mark.security
async def test_sql_injection(client):
    """
    SQL-like payloads must be treated as plain data,
    never as executable SQL.
    """

    email = "sql-test@example.com"
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

    token = login_response.json()[
        "access_token"
    ]

    headers = {
        "Authorization": f"Bearer {token}"
    }

    malicious_title = (
        "Robert'); DROP TABLE users;--"
    )

    create_response = await client.post(
        "/sessions",
        headers=headers,
        json={
            "title": malicious_title,
        },
    )

    assert create_response.status_code == 201

    session = create_response.json()

    # La chaîne est stockée telle quelle :
    # elle n'a jamais été interprétée comme SQL.
    assert session["title"] == malicious_title

    # La table users existe toujours et
    # l'authentification fonctionne toujours.
    second_register = await client.post(
        "/auth/register",
        json={
            "email": "still-alive@example.com",
            "password": password,
        },
    )

    assert second_register.status_code == 201

    # Une tentative d'injection dans un paramètre
    # typé int est refusée par FastAPI/Pydantic.
    path_attack = await client.get(
        "/sessions/1%20OR%201=1",
        headers=headers,
    )

    assert path_attack.status_code == 422

@pytest.mark.security
def test_secret_management():
    """
    JWT secret must come from configuration and
    must never appear in generated tokens.
    """

    from backend.app import security

    secret = security.SECRET_KEY

    assert secret
    assert len(secret) > 10

    token = security.create_access_token(
        subject="123"
    )

    assert secret not in token

@pytest.mark.asyncio
@pytest.mark.security
async def test_tenant_isolation(client):
    """
    User B must not access a session owned by user A.
    """

    password = "MotDePasse123"

    for email in (
        "user_a@example.com",
        "user_b@example.com",
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
            "username": "user_a@example.com",
            "password": password,
        },
    )

    login_b = await client.post(
        "/auth/login",
        data={
            "username": "user_b@example.com",
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

    session_response = await client.post(
        "/sessions",
        headers=headers_a,
        json={
            "title": "Private analysis A",
        },
    )

    assert session_response.status_code == 201

    session_id = session_response.json()[
        "id"
    ]

    # A peut accéder à sa session.
    response_a = await client.get(
        f"/sessions/{session_id}",
        headers=headers_a,
    )

    assert response_a.status_code == 200

    # B reçoit volontairement 404.
    # On ne révèle même pas l'existence
    # de la ressource.
    response_b = await client.get(
        f"/sessions/{session_id}",
        headers=headers_b,
    )

    assert response_b.status_code == 404

    # Elle ne doit pas non plus apparaître
    # dans la liste de B.
    list_b = await client.get(
        "/sessions",
        headers=headers_b,
    )

    assert list_b.status_code == 200
    assert all(
        session["id"] != session_id
        for session in list_b.json()
    )
