"""
Security tests for the sandboxed Python execution and API protection.
Run with: pytest backend/tests/test_security.py -v
"""
import pytest
import asyncio

# NOTE: Import will work after backend implementation
# from backend.agents.agent_manager import AgentManager
# from backend.security.sandbox import execute_sandboxed_code


@pytest.mark.asyncio
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

@pytest.mark.asyncio
@pytest.mark.security
async def test_resource_limits():
    """
    Test: Timeouts and resource limits enforced
    
    Steps:
    1. Submit infinite loop code
    2. Submit memory-intensive code
    3. Verify timeouts and limits enforced
    
    Expected: Code terminates within limits
    """
    infinite_loop = "while True: pass"
    memory_heavy = "x = [list(range(10000)) for _ in range(10000)]"
    
    # TODO: Test after sandbox implementation
    pytest.skip("Backend not implemented yet - students will implement this")


@pytest.mark.asyncio
@pytest.mark.security
async def test_sql_injection():
    """
    Test: SQL injection attempts are blocked
    
    Steps:
    1. Try SQL injection in dataset upload
    2. Try injection in API parameters
    3. Verify ORM escapes properly
    
    Expected: Queries fail/escaped
    """
    injection_attempts = [
        "Robert'); DROP TABLE Users;--",
        "'; SELECT password FROM Users WHERE username='admin';"
    ]
    
    # TODO: Test after API implementation
    pytest.skip("Backend not implemented yet - students will implement this")


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
