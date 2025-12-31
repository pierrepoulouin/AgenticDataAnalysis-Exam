# 🎓 Final Exam — Modernizing an Analytic Agent Platform

## Context

You are a **Senior AI Engineer** at *DataStream AI*. A fragile POC must be upgraded into a scalable, secure SaaS. The CEO just onboarded 500 clients—production readiness is critical.

## Objective

Build a production-grade, single-agent data analysis platform with **FastAPI + LangGraph + Streamlit**, backed by **PostgreSQL**, **Redis**, and **Celery**, with secure code execution and persistence.

![alt text](assets/target_streamlit_app.gif)

## Critical Risks to Fix
1) **Reboot Amnesia**: History lost on restart.  
   - Persist sessions/messages in PostgreSQL.  
   - Bonus: LangGraph checkpointer.

2) **Multi-User Data Leak**: No auth; data visible across users.  
   - Add JWT auth; enforce `user_id` isolation everywhere.

3) **Analysis Volatility**: Charts not saved.  
   - Store visualizations in PostgreSQL (Plotly JSON).

4) **Scalability Bottleneck**: Monolithic Streamlit.  
   - Stateless FastAPI, Celery workers, microservice-friendly.

5) **Unsafe Code Execution**: Raw `exec()`.  
   - RestrictedPython, time/memory limits, module whitelist.



## Deliverables (Pass/Fail Gate)

- **Code**: Production-ready on `main`; clear commits; proper `.gitignore`; no secrets.  
- **Tests**: `backend/tests/test_*.py` with ≥70% coverage; `pytest backend/tests/ -v` must pass.  
- **Docker Compose**: `docker-compose up -d` brings up Postgres (5432), Redis (6379), FastAPI (8000), Streamlit (8501), Celery worker, Flower (5555); all healthy.  

- **Docs**:
  - `docs/ARCHITECTURE.md` — target architecture.
  - `docs/SETUP.md` — how to run.
  - `docs/API.md` — endpoints.
  - `docs/ARCHITECTURE_ANALYSIS.md` — current vs target analysis and answers to guided questions.



## Phases and Requirements

### Phase 1 — Analysis & Design (2 pts)
Run the POC and document findings in `docs/ARCHITECTURE_ANALYSIS.md`.

Guided experiments:
- **Session persistence**: Restart app; does history survive? Where is it stored (`backend.py`)? Impact at 100 users?  
- **Multi-user isolation**: Two browser windows; can one see the other’s data? Any auth in `data_analysis_streamlit_app.py`?  
- **Code execution security**: Try `__import__('os').system('echo HACKED')`; where is code executed? What could an attacker do?  
- **Scalability**: Review `backend.py`; is it stateless? What happens with 10 simultaneous users? Can it scale horizontally?  
- **Visualization persistence**: Create chart, restart; is it retained? Where are visuals stored?

Include: findings, root causes for 5 risks, proposed fixes, and a C4/UML diagram (current vs target).



### Phase 2 — Production-Ready Backend (6 pts)
**FastAPI API**
- Create `backend/api/main.py`; add CORS, global error handling, structured JSON logging.

**Pre-work to document in `ARCHITECTURE_ANALYSIS.md`:**
- Why FastAPI (vs Streamlit backend)? Stateless vs stateful; scaling implications.
- Why CORS; why not `origins=["*"]` in prod.
- Why global error handling; no stack traces to users.
- Why structured logging (vs `print`); value at scale.

**Auth & Users**
- SQLAlchemy `User`.
- `/api/auth/register`, `/api/auth/login` with JWT (expiring).
- Protect routes via `get_current_user`.

Security rationale:
- Hash passwords (bcrypt/argon2); risk of plaintext; can a hash be used to log in?
- JWT expiry: risks of never-expiring tokens; refresh approach; sensible TTL.

**Data Models**
- `User`, `Dataset` (FK user), `AnalysisSession` (messages, status), `Visualization` (figure_json).

**Agent Integration**
- `backend/agents/agent_manager.py`; load history from DB.

**Session Management**
- Persist sessions/messages. Bonus: Postgres checkpointer (handle DataFrame serialization).

**Security: Code Sandbox**
- `backend/security/code_sandbox.py`; RestrictedPython, timeouts, module whitelist (pandas, numpy, sklearn).
- Prove blocking of: filesystem access, network calls, infinite loop, memory bomb.

**Celery & Async**
- Celery with Redis; tasks for analysis; queue separation.

**Critical test to satisfy (Problem #1)**: session persists after restart; agent recalls “Alice”.



### Phase 3 — Robust Persistence (4 pts)
- PostgreSQL + Alembic migrations.
- Manual session/message persistence; optional Postgres checkpointer.
- Persist user sessions and visualizations (JSON) with timestamps.

### Phase 4 — Frontend & Integration (4 pts)
- Refactor Streamlit to call FastAPI.
- API client with session handling.
- Login/Register UI.
- Session list + selection → auto-load chat history & saved visualizations.
- Show analysis history; UX polish.

### Phase 5 — Deployment & Testing (4 pts)
- Dockerfiles: backend, frontend, celery.
- Complete `docker-compose.yml`.
- Health checks, structlog, basic metrics.
- Mandatory tests:
  - `backend/tests/test_agent_integration.py`: dataset description, session persistence, sandbox blocking.
  - `backend/tests/test_api.py`: register, unauthorized access.
  - `backend/tests/test_persistence.py`: user data isolation, visualization storage.
  - `backend/tests/test_security.py`: SQL injection prevention, resource limits.

Run: `pip install -r requirements-test.txt && pytest backend/tests/ -v --cov=backend`.



## Reference Architecture
Current: Streamlit frontend + embedded logic; FastAPI (planned), Celery, Redis, Postgres, LLM.  
Target structure:

```sh
.
├── backend/
│   ├── api/            # FastAPI routes & auth
│   ├── agents/         # LangGraph & checkpointer
│   ├── db/             # SQLAlchemy models & migrations
│   ├── security/       # Code sandbox
│   └── worker/         # Celery tasks
├── frontend/           # Streamlit UI (calls backend)
├── infrastructure/     # Dockerfiles, docker-compose
└── tests/              # Functional tests
```



## Common Pitfalls
- Not persisting chat (only `st.session_state`) → must use Postgres `messages` linked to `AnalysisSession`.
- Not scoping by `user_id` → GDPR breach.
- Secrets in code → use env vars.
- Backend statefulness → must be stateless to scale.
- Blocking requests with long tasks → offload to Celery.



## Self-Check Before Submission
**Security**
- Malicious code blocked; passwords hashed; no secrets committed; cross-user access impossible.

**Persistence**
- Restart backend: chat history loads from Postgres; sessions/messages persisted.

**Scalability**
- Stateless backend; multiple instances OK; long tasks via Celery.



## Getting Started

1) Clone & branch:

```bash
git clone <repo>
cd AgenticDataAnalysis-Exam
git checkout -b feat/modernization
```

2) Analyze current app: `data_analysis_streamlit_app.py`, `Pages/backend.py`, `Pages/graph/*`; document 5 problems in `docs/ARCHITECTURE_ANALYSIS.md`.
3) Propose target architecture diagram (Streamlit frontend, FastAPI backend, Postgres, Redis, Celery, LangGraph checkpointer).



## Submission

- GitHub repo URL.
- Proof `docker-compose up` works (all services healthy).
- Test results: `pytest backend/tests/ -v` USING DOCKER.

**Good luck! 🎯**
