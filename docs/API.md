# API Documentation

## 1. Overview

The Agentic Data Analysis backend is implemented using FastAPI.

Default address:

```text
http://localhost:8000
```

Interactive OpenAPI documentation:

```text
http://localhost:8000/docs
```

OpenAPI schema:

```text
http://localhost:8000/openapi.json
```

The API provides:

- authentication;
- access/refresh JWT handling;
- analysis-session management;
- message persistence;
- dataset metadata;
- CSV upload;
- visualization persistence;
- asynchronous agent execution;
- Celery task-status polling;
- health monitoring;
- Prometheus metrics.

---

## 2. Authentication

Most application endpoints require an access token.

The HTTP header format is:

```http
Authorization: Bearer <access_token>
```

Access tokens are short-lived.

Refresh tokens allow the client to request a new token pair.

Protected routes use `get_current_user` and scope data access to the authenticated user.

---

## 3. Authentication Endpoints

### POST `/auth/register`

Create a new user.

Authentication:

```text
Public
```

Request content type:

```text
application/json
```

Example:

```json
{
  "email": "user@example.com",
  "password": "StrongPassword123"
}
```

Successful status:

```text
201 Created
```

The response contains public user information.

The password hash is never returned.

Example request:

```bash
curl -X POST \
  http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "StrongPassword123"
  }'
```

---

### POST `/auth/login`

Authenticate a user.

Authentication:

```text
Public
```

The endpoint uses OAuth2 password-form semantics.

Request content type:

```text
application/x-www-form-urlencoded
```

Fields:

```text
username=<email>
password=<password>
```

Example:

```bash
curl -X POST \
  http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=StrongPassword123"
```

Successful status:

```text
200 OK
```

Example response structure:

```json
{
  "access_token": "<jwt>",
  "refresh_token": "<jwt>",
  "token_type": "bearer"
}
```

---

### POST `/auth/refresh`

Exchange a valid refresh token for a new token pair.

Authentication:

```text
Refresh token in request body
```

Example request structure:

```json
{
  "refresh_token": "<refresh-jwt>"
}
```

Successful status:

```text
200 OK
```

Response structure:

```json
{
  "access_token": "<new-access-jwt>",
  "refresh_token": "<new-refresh-jwt>",
  "token_type": "bearer"
}
```

The implementation rotates the returned token pair.

The current JWT implementation is stateless; refresh-token identifiers are not persisted in a server-side revocation store.

---

### GET `/auth/me`

Return the currently authenticated user.

Authentication:

```text
Bearer access token required
```

Example:

```bash
curl \
  http://127.0.0.1:8000/auth/me \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Successful status:

```text
200 OK
```

---

## 4. Session Endpoints

All session endpoints require authentication.

Data is scoped to the current user.

---

### POST `/sessions`

Create an analysis session.

Authentication:

```text
Bearer token required
```

Request:

```json
{
  "title": "Sales analysis"
}
```

Successful status:

```text
201 Created
```

Example response structure:

```json
{
  "id": 1,
  "user_id": 1,
  "title": "Sales analysis",
  "created_at": "...",
  "updated_at": "..."
}
```

Example:

```bash
curl -X POST \
  http://127.0.0.1:8000/sessions \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Sales analysis"
  }'
```

---

### GET `/sessions`

List the authenticated user's sessions.

Authentication:

```text
Bearer token required
```

Successful status:

```text
200 OK
```

Only sessions owned by the authenticated user are returned.

Example:

```bash
curl \
  http://127.0.0.1:8000/sessions \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

---

### GET `/sessions/{session_id}`

Retrieve one owned session.

Authentication:

```text
Bearer token required
```

Example:

```bash
curl \
  http://127.0.0.1:8000/sessions/1 \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Cross-user access is rejected.

A resource owned by another user is not exposed.

---

## 5. Message Endpoints

### POST `/sessions/{session_id}/messages`

Persist a message in an owned session.

Authentication:

```text
Bearer token required
```

Successful status:

```text
201 Created
```

The request follows the `MessageCreate` schema.

A typical message contains a role/content pair appropriate to the application message model.

Messages are persisted in PostgreSQL and linked to the session.

---

### GET `/sessions/{session_id}/messages`

Retrieve the persisted chat history for an owned session.

Authentication:

```text
Bearer token required
```

Successful status:

```text
200 OK
```

Messages are returned in chronological order.

This endpoint is used by the frontend to restore conversation history after:

- browser refresh;
- backend restart;
- container recreation.

---

## 6. Dataset Endpoints

Dataset access is tenant-scoped.

A user cannot list or retrieve another user's dataset metadata.

---

### POST `/datasets`

Create dataset metadata.

Authentication:

```text
Bearer token required
```

Successful status:

```text
201 Created
```

The request follows the `DatasetCreate` schema.

This route stores dataset metadata.

For normal CSV ingestion through the frontend, the session upload endpoint is preferred.

---

### GET `/datasets`

List datasets owned by the authenticated user.

Authentication:

```text
Bearer token required
```

Successful status:

```text
200 OK
```

Example:

```bash
curl \
  http://127.0.0.1:8000/datasets \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

---

### GET `/datasets/{dataset_id}`

Retrieve metadata for one owned dataset.

Authentication:

```text
Bearer token required
```

A user attempting to access another tenant's dataset does not receive the other user's data.

---

### POST `/sessions/{session_id}/datasets/upload`

Upload a CSV file into an owned analysis session.

Authentication:

```text
Bearer token required
```

Content type:

```text
multipart/form-data
```

Fields:

```text
file
description (optional)
```

Successful status:

```text
201 Created
```

Example:

```bash
curl -X POST \
  http://127.0.0.1:8000/sessions/1/datasets/upload \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@sales.csv" \
  -F "description=Sales test data"
```

Upload protections include:

- session ownership validation;
- CSV extension restriction;
- sanitized filename handling;
- maximum upload size;
- pandas CSV validation;
- controlled storage root.

Maximum configured upload size:

```text
10 MiB
```

The physical CSV is written below `UPLOAD_ROOT`.

Inside Docker:

```text
/app/uploads
```

The directory is backed by the shared `uploads_data` volume.

---

## 7. Visualization Endpoints

Plotly visualizations are persisted as JSON.

Visualization access is authorized through the owning message/session/user relationship.

---

### POST `/messages/{message_id}/visualizations`

Persist a visualization associated with a message.

Authentication:

```text
Bearer token required
```

Successful status:

```text
201 Created
```

The request follows the `VisualizationCreate` schema and contains the Plotly figure representation.

The figure is serialized into PostgreSQL.

---

### GET `/visualizations/{visualization_id}`

Retrieve one persisted visualization.

Authentication:

```text
Bearer token required
```

Successful status:

```text
200 OK
```

Cross-user visualization access is rejected.

---

### GET `/messages/{message_id}/visualizations`

List all visualizations associated with an owned message.

Authentication:

```text
Bearer token required
```

Successful status:

```text
200 OK
```

The Streamlit frontend uses this data to restore figures after refresh or restart.

---

## 8. Agent Endpoints

Agent analyses are asynchronous.

FastAPI does not perform the potentially long analysis directly inside the HTTP request.

Instead:

```text
FastAPI
   ↓
Celery
   ↓
Redis
   ↓
Worker
   ↓
AgentManager
   ↓
LangGraph
   ↓
Tools
```

---

### POST `/sessions/{session_id}/agent`

Submit an asynchronous agent turn.

Authentication:

```text
Bearer token required
```

Successful status:

```text
202 Accepted
```

The request follows the `AgentTurnRequest` schema.

The request contains the user's analysis query.

Conceptual example:

```json
{
  "query": "Quel est le total des montants ?"
}
```

The endpoint:

1. verifies that the session belongs to the current user;
2. submits `agent.run_turn` to Celery;
3. immediately returns a task identifier.

Example response structure:

```json
{
  "task_id": "<celery-task-id>",
  "status": "queued"
}
```

The exact response is defined by `AgentTaskResponse`.

---

### GET `/sessions/{session_id}/agent/tasks/{task_id}`

Retrieve the state of an asynchronous analysis task.

Authentication:

```text
Bearer token required
```

Successful status:

```text
200 OK
```

Possible logical states include:

```text
pending
started
completed
failed
```

When completed, the response can include the agent answer and generated visualizations.

The endpoint verifies session ownership before returning task information.

The frontend polls this route until the analysis completes.

---

## 9. Operational Endpoints

### GET `/health`

Authentication:

```text
Public
```

Purpose:

- Docker health checking;
- availability verification.

Example:

```bash
curl http://127.0.0.1:8000/health
```

Response:

```json
{
  "status": "ok",
  "service": "backend"
}
```

---

### GET `/metrics`

Authentication:

```text
Public in the examination environment
```

Returns Prometheus-compatible metrics.

Example:

```bash
curl http://127.0.0.1:8000/metrics
```

Metrics include:

- HTTP request count;
- HTTP request duration.

In a real public production environment, the metrics endpoint would normally be exposed only to internal monitoring infrastructure.

---

## 10. HTTP Request IDs

Every request receives a UUID request identifier.

The identifier is returned through:

```http
X-Request-ID: <uuid>
```

Structured logs include the same identifier.

Example application log:

```json
{
  "method": "GET",
  "path": "/health",
  "status_code": 200,
  "duration_ms": 1.21,
  "event": "request_completed",
  "request_id": "06df673e-cf28-4966-b065-9ddda73502a9",
  "timestamp": "2026-08-29T16:00:35.784249Z",
  "level": "info"
}
```

This allows a client-side error report to be correlated with server-side logs.

---

## 11. Error Handling

Unexpected exceptions are handled globally.

The API does not return Python stack traces to clients.

Example generic error response:

```json
{
  "detail": "Internal server error",
  "request_id": "<request-id>"
}
```

The detailed exception remains in structured server logs.

Expected domain errors use standard FastAPI HTTP errors such as:

- `400 Bad Request`;
- `401 Unauthorized`;
- `404 Not Found`;
- `422 Unprocessable Entity`.

---

## 12. Tenant Isolation

Authorization is enforced server-side.

The frontend is not considered a security boundary.

For protected resources, ownership is checked using relationships such as:

```text
current user
    ↓
session
    ↓
message
    ↓
visualization
```

and:

```text
current user
    ↓
dataset
```

Automated tests verify that User B cannot access User A's resources.

---

## 13. JWT Behavior

### Access Token

Used for protected API requests.

Configured expiry:

```env
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### Refresh Token

Used to obtain a new token pair.

Configured expiry:

```env
REFRESH_TOKEN_EXPIRE_DAYS=7
```

Tokens contain a token type so that refresh tokens cannot be used as access tokens.

A never-expiring access token is intentionally avoided because compromise would otherwise provide indefinite access.

---

## 14. Password Security

Passwords are hashed using bcrypt.

The stored database value is a password hash, not the original password.

A password hash cannot be submitted directly as a normal password to authenticate because login performs password verification against the hash.

Passwords and JWT secrets must never appear in application logs or API responses.

---

## 15. Dataset Execution Context

When an agent turn begins, `AgentManager` loads datasets owned by the current user and associated with the session.

CSV files are made available to the controlled execution context through generated variable names such as:

```text
dataset_<id>
```

The generated analysis code can operate on these in-memory DataFrames without receiving arbitrary filesystem access.

---

## 16. Agent Tools

The agent currently exposes a controlled tool whitelist.

Major tool categories include:

- data cleaning;
- statistical analysis;
- visualization.

Tools delegate generated Python execution to the sandbox layer.

The planner cannot directly invoke arbitrary Python functions outside the registered tools.

---

## 17. Python Sandbox API Boundary

The sandbox is internal and is not exposed as a public HTTP endpoint.

The execution flow is:

```text
Agent
  ↓
Tool
  ↓
validate_python_code()
  ↓
sandbox subprocess
  ↓
restricted execution
  ↓
result
```

Protections include:

- AST validation;
- blocked imports;
- blocked dangerous builtins;
- blocked filesystem helpers;
- blocked network/external-data helpers;
- restricted exposed modules;
- subprocess isolation;
- timeout;
- memory limit.

---

## 18. Asynchronous Analysis Example

A typical client interaction is:

```text
POST /sessions/1/agent
      ↓
202 Accepted
      ↓
task_id

GET /sessions/1/agent/tasks/<task_id>
      ↓
pending

GET /sessions/1/agent/tasks/<task_id>
      ↓
started

GET /sessions/1/agent/tasks/<task_id>
      ↓
completed
      ↓
answer + figures
```

This design prevents the HTTP request from remaining blocked while the analysis executes.

---

## 19. Example End-to-End API Flow

### 1. Register

```bash
curl -X POST \
  http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "demo@example.com",
    "password": "StrongPassword123"
  }'
```

### 2. Login

```bash
curl -X POST \
  http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=demo@example.com&password=StrongPassword123"
```

Store the returned access token:

```bash
export ACCESS_TOKEN="<access-token>"
```

### 3. Create Session

```bash
curl -X POST \
  http://127.0.0.1:8000/sessions \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Demo analysis"
  }'
```

### 4. Upload Dataset

Create:

```text
sales.csv
```

with:

```csv
produit,montant
A,100
B,250
C,50
D,300
```

Upload:

```bash
curl -X POST \
  http://127.0.0.1:8000/sessions/1/datasets/upload \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@sales.csv"
```

### 5. Submit Analysis

```bash
curl -X POST \
  http://127.0.0.1:8000/sessions/1/agent \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Quel est le total des montants ?"
  }'
```

Store the returned task identifier.

### 6. Poll Task

```bash
curl \
  http://127.0.0.1:8000/sessions/1/agent/tasks/<task-id> \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

The expected analysis result for the example dataset is:

```text
700
```

---

## 20. Endpoint Summary

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| POST | `/auth/register` | No | Register |
| POST | `/auth/login` | No | Login |
| POST | `/auth/refresh` | Refresh token | Refresh JWT pair |
| GET | `/auth/me` | Yes | Current user |
| POST | `/sessions` | Yes | Create session |
| GET | `/sessions` | Yes | List sessions |
| GET | `/sessions/{session_id}` | Yes | Retrieve session |
| POST | `/sessions/{session_id}/messages` | Yes | Create message |
| GET | `/sessions/{session_id}/messages` | Yes | Retrieve history |
| POST | `/datasets` | Yes | Create dataset metadata |
| GET | `/datasets` | Yes | List datasets |
| GET | `/datasets/{dataset_id}` | Yes | Retrieve dataset |
| POST | `/sessions/{session_id}/datasets/upload` | Yes | Upload CSV |
| POST | `/messages/{message_id}/visualizations` | Yes | Persist figure |
| GET | `/visualizations/{visualization_id}` | Yes | Retrieve figure |
| GET | `/messages/{message_id}/visualizations` | Yes | List message figures |
| POST | `/sessions/{session_id}/agent` | Yes | Submit agent task |
| GET | `/sessions/{session_id}/agent/tasks/{task_id}` | Yes | Poll agent task |
| GET | `/health` | No | Health check |
| GET | `/metrics` | No | Prometheus metrics |

---

## 21. OpenAPI as Source of Truth

FastAPI automatically generates the OpenAPI schema from the implemented:

- routes;
- Pydantic schemas;
- response models.

For exact current field-level schemas, use:

```text
http://localhost:8000/docs
```

or:

```text
http://localhost:8000/openapi.json
```

This document provides the architecture-level API contract, while FastAPI's generated schema remains the executable field-level reference.