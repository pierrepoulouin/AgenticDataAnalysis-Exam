# Setup Guide

## 1. Overview

This document explains how to install, configure, run and validate the modernized Agentic Data Analysis platform.

The recommended execution mode for the examination is Docker Compose.

The final stack contains:

| Service | Port |
|---|---:|
| PostgreSQL | 5432 |
| Redis | 6379 |
| FastAPI | 8000 |
| Streamlit | 8501 |
| Flower | 5555 |
| Celery Worker | internal |

The main application flow is:

```text
Browser
  ↓
Streamlit
  ↓
FastAPI
  ↓
Redis → Celery → LangGraph → Analysis Tools
  ↓
PostgreSQL

FastAPI + Celery
       ↓
shared uploads_data volume
```

---

## 2. Prerequisites

Recommended environment:

- Linux;
- Docker Engine;
- Docker Compose v2;
- Git.

For local development without Docker:

- Python 3.12;
- PostgreSQL;
- Redis.

Check Docker:

```bash
docker --version
docker compose version
```

---

## 3. Clone the Repository

```bash
git clone <repository-url>
cd AgenticDataAnalysis-Exam
```

During development, the modernization work is performed on:

```bash
git checkout feat/modernization
```

The final submission should be merged into `main`.

---

## 4. Environment Configuration

The application uses environment variables for configuration and secrets.

Create the local environment file from the template:

```bash
cp .env.example .env
```

Never commit `.env`.

The repository `.gitignore` excludes it.

---

## 5. Generate Secrets

Generate secure random values:

```bash
openssl rand -hex 32
```

Generate separate values for:

- `JWT_SECRET_KEY`;
- `COOKIE_PASSWORD`.

Example:

```env
JWT_SECRET_KEY=replace-with-a-random-value
COOKIE_PASSWORD=replace-with-another-random-value
```

Do not reuse example or default secrets in production.

---

## 6. Environment Variables

A typical Docker configuration is:

```env
DATABASE_URL=postgresql://agentic:agentic@postgres:5432/agentic_db

JWT_SECRET_KEY=change-me-with-a-random-secret
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

COOKIE_PASSWORD=change-me-with-a-random-secret

CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1

UPLOAD_ROOT=/app/uploads

SANDBOX_TIMEOUT_SECONDS=10
SANDBOX_MEMORY_LIMIT_MB=512

AGENT_PLANNER=mock

# Optional. Required only when using the LLM planner.
OPENAI_API_KEY=
```

### `DATABASE_URL`

Inside Docker Compose, PostgreSQL is reached using the service name:

```text
postgres
```

Therefore:

```env
DATABASE_URL=postgresql://agentic:agentic@postgres:5432/agentic_db
```

Do not use `localhost` between Docker services.

### Redis

Inside Docker Compose:

```env
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1
```

### Planner

For deterministic local development and tests:

```env
AGENT_PLANNER=mock
```

For an optional LLM-backed planner:

```env
AGENT_PLANNER=llm
OPENAI_API_KEY=<provider-key>
```

The mock planner allows the complete application architecture to run without requiring a paid external model API.

---

## 7. Sandbox Configuration

Generated analysis code runs in a dedicated subprocess.

Default limits:

```env
SANDBOX_TIMEOUT_SECONDS=10
SANDBOX_MEMORY_LIMIT_MB=512
```

The timeout prevents non-terminating code from permanently blocking execution.

The memory limit prevents excessive memory allocation from exhausting the worker.

Automated security tests use stricter explicit values to validate these protections.

---

## 8. Docker Images

The project contains dedicated Dockerfiles.

### Backend and Celery Worker

```text
Dockerfile.backend
```

This image contains:

- FastAPI;
- SQLAlchemy;
- Alembic;
- Celery;
- LangGraph;
- pandas;
- NumPy;
- SciPy;
- scikit-learn;
- Plotly;
- sandbox dependencies.

The same application image can be used by the backend and worker with different commands.

### Frontend

```text
Dockerfile.frontend
```

This image runs Streamlit.

### Flower

```text
Dockerfile.flower
```

Flower uses a dedicated lightweight image.

It only requires Celery, Redis support and Flower itself.

This avoids installing the full scientific Python stack in the monitoring container.

---

## 9. Build the Stack

Build all images:

```bash
docker compose build
```

For a clean rebuild:

```bash
docker compose build --no-cache
```

A complete rebuild can consume significant disk space because the backend contains scientific Python libraries.

Use `--no-cache` only when necessary.

---

## 10. Start the Platform

Start all services:

```bash
docker compose up -d
```

Check status:

```bash
docker compose ps
```

Expected final state:

```text
postgres    healthy
redis       healthy
backend     healthy
worker      healthy
frontend    healthy
flower      healthy
```

---

## 11. Service URLs

### Streamlit

```text
http://localhost:8501
```

### FastAPI

```text
http://localhost:8000
```

### FastAPI OpenAPI

```text
http://localhost:8000/docs
```

### Backend Health

```text
http://localhost:8000/health
```

### Prometheus Metrics

```text
http://localhost:8000/metrics
```

### Flower

```text
http://localhost:5555
```

When running on a remote VM such as EC2, replace `localhost` in the browser with the public IP or hostname of the instance.

Relevant firewall/security-group ports must be allowed when external access is required.

---

## 12. Verify Backend Health

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "service": "backend"
}
```

---

## 13. Verify Streamlit Health

```bash
curl http://127.0.0.1:8501/_stcore/health
```

Expected response:

```text
ok
```

---

## 14. Verify Flower

```bash
curl -I http://127.0.0.1:5555/
```

Flower should return an HTTP response and appear healthy in:

```bash
docker compose ps
```

---

## 15. Verify Celery Queues

Inspect the queues consumed by the worker:

```bash
docker compose exec worker \
  celery -A backend.app.celery_app:celery_app inspect active_queues
```

The worker should expose:

```text
analysis
default
```

Routing:

```text
health.ping
    ↓
default queue

agent.run_turn
    ↓
analysis queue
```

---

## 16. Database Migrations

Alembic manages PostgreSQL schema migrations.

The backend container automatically executes:

```bash
alembic upgrade head
```

before starting FastAPI.

To inspect the current migration manually:

```bash
alembic current
```

To inspect migration history:

```bash
alembic history
```

---

## 17. Persistent Volumes

Docker Compose defines two important volumes.

### PostgreSQL

```text
postgres_data
```

Contains durable relational data:

- users;
- sessions;
- messages;
- dataset metadata;
- visualizations.

### Uploaded Files

```text
uploads_data
```

Contains uploaded CSV files.

The volume is mounted by both:

- backend;
- Celery worker.

This allows FastAPI to write a dataset and Celery to read the same file.

---

## 18. Persistence Test

Create:

- an account;
- an analysis session;
- a dataset;
- messages;
- a visualization.

Then stop the stack:

```bash
docker compose down
```

Restart it:

```bash
docker compose up -d
```

The persisted information should still be available.

This validates that application state does not depend on container-local memory.

Do not use:

```bash
docker compose down -v
```

during this test.

The `-v` option intentionally deletes Docker volumes.

---

## 19. End-to-End Functional Test

Open Streamlit:

```text
http://localhost:8501
```

Create an account and login.

Create a session such as:

```text
Docker E2E Test
```

Upload:

```csv
produit,montant
A,100
B,250
C,50
D,300
```

Ask:

```text
Quel est le total des montants ?
```

Expected result:

```text
700
```

Then ask for a visualization.

Example:

```text
Fais-moi un graphique des montants par produit
```

A Plotly visualization should be generated and persisted.

Refresh the browser.

The following data should remain available:

- authenticated account;
- analysis session;
- uploaded dataset;
- chat history;
- answer;
- visualization.

---

## 20. Worker Logs

Inspect Celery activity:

```bash
docker compose logs --tail=100 worker
```

Follow logs live:

```bash
docker compose logs -f worker
```

An agent query should create a Celery task such as:

```text
agent.run_turn
```

---

## 21. Backend Logs

Inspect FastAPI logs:

```bash
docker compose logs --tail=100 backend
```

Application request logs are structured JSON.

Example:

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

---

## 22. Run Tests Locally

Activate the virtual environment:

```bash
source .venv/bin/activate
```

Install test dependencies if necessary:

```bash
pip install -r requirements-test.txt
```

Run all backend tests:

```bash
python -m pytest backend/tests/ -v
```

Run with coverage:

```bash
python -m pytest backend/tests/ -v \
  --cov=backend \
  --cov-report=term-missing
```

Current validated status:

```text
21 passed
```

Current validated coverage:

```text
83%
```

The examination requires at least:

```text
70%
```

---

## 23. Run Tests in Docker

The examination requests validation using Docker.

Once the backend image is running, tests can be executed inside the application environment.

Example:

```bash
docker compose exec backend \
  python -m pytest backend/tests/ -v --cov=backend
```

If test-only packages are not part of the runtime image in a future production optimization, use a dedicated test image instead.

---

## 24. Run Individual Test Files

Agent integration:

```bash
python -m pytest \
  backend/tests/test_agent_integration.py \
  -v
```

API:

```bash
python -m pytest \
  backend/tests/test_api.py \
  -v
```

Persistence:

```bash
python -m pytest \
  backend/tests/test_persistence.py \
  -v
```

Security:

```bash
python -m pytest \
  backend/tests/test_security.py \
  -v
```

---

## 25. Security Tests

Security tests validate:

- malicious import rejection;
- filesystem access blocking;
- external-data/network helper blocking;
- SQL injection resistance;
- tenant isolation;
- execution timeout;
- memory limits;
- secret handling.

The infinite-loop test verifies code such as:

```python
while True:
    pass
```

is terminated.

The memory test deliberately runs code with a restrictive sandbox memory allowance and verifies that excessive allocation fails.

---

## 26. Local Development Without Docker

A local Python environment can be created with:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Load environment variables:

```bash
set -a
source .env
set +a
```

### Start FastAPI

```bash
uvicorn backend.app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --reload
```

### Start Celery

```bash
celery \
  -A backend.app.celery_app:celery_app \
  worker \
  --loglevel=info \
  --queues=analysis,default
```

### Start Streamlit

```bash
PYTHONPATH=. streamlit run frontend/app.py \
  --server.address 0.0.0.0 \
  --server.port 8501
```

PostgreSQL and Redis must also be available.

For local processes outside Docker, environment hostnames normally use `localhost` instead of Docker service names.

---

## 27. Common Docker Port Conflicts

If a service reports:

```text
address already in use
```

identify the process or container using the port.

Example:

```bash
sudo ss -ltnp | grep ':8000'
```

List Docker mappings:

```bash
docker ps --format "table {{.Names}}\t{{.Ports}}"
```

Stop obsolete containers if necessary.

Example:

```bash
docker stop <container-name>
```

Do not delete persistent volumes unless the data should intentionally be removed.

---

## 28. Docker Disk Space

Scientific Python images can consume several gigabytes.

Inspect usage:

```bash
df -h
docker system df
```

Clean build cache safely:

```bash
docker builder prune -af
```

Remove unused images:

```bash
docker image prune -f
```

Unused stopped containers can be removed with:

```bash
docker container prune -f
```

Do not run:

```bash
docker volume prune
```

unless deleting persistent PostgreSQL and upload data is intentional.

---

## 29. Docker and Kubernetes on the Same Host

A development machine that previously ran Kubernetes, Flannel or kube-router may contain networking rules that interfere with Docker forwarding.

A symptom can be:

```text
Temporary failure in name resolution
```

inside Docker containers even when the host itself has network access.

Inspect:

```bash
sudo iptables -S FORWARD
```

Docker traffic normally requires the Docker forwarding chains to be reachable.

This is an infrastructure-host concern rather than an application configuration requirement.

A clean production host should avoid unmanaged competition between multiple container-networking systems.

---

## 30. Stop the Platform

Stop and remove containers while keeping persistent volumes:

```bash
docker compose down
```

Restart:

```bash
docker compose up -d
```

---

## 31. Full Reset

To intentionally remove the stack and its persisted data:

```bash
docker compose down -v
```

Warning:

This deletes the Docker volumes used by PostgreSQL and uploads.

Only use it when a complete reset is desired.

---

## 32. Final Examination Validation

Before submission, verify:

```bash
docker compose up -d
docker compose ps
```

All required services should be healthy:

```text
postgres    healthy
redis       healthy
backend     healthy
worker      healthy
frontend    healthy
flower      healthy
```

Then execute:

```bash
docker compose exec backend \
  python -m pytest backend/tests/ -v --cov=backend
```

Expected test result:

```text
21 passed
```

Coverage should remain above:

```text
70%
```

Finally check Git:

```bash
git status
```

Verify that no secrets or generated runtime data are staged.

In particular:

```text
.env
```

must never be committed.