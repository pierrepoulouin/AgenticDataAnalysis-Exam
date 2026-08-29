from backend.app.agent.manager import AgentManager
from backend.app.agent.planner import get_planner
from backend.app.celery_app import celery_app
from backend.app.database import SessionLocal


@celery_app.task(name="health.ping")
def celery_ping() -> dict[str, str]:
    return {
        "status": "ok",
        "worker": "celery",
    }


@celery_app.task(name="agent.run_turn")
def run_agent_turn_task(
    session_id: int,
    user_id: int,
    user_query: str,
) -> dict:
    db = SessionLocal()

    try:
        manager = AgentManager(
            session_id=session_id,
            user_id=user_id,
            db=db,
        )

        result = manager.run_agent_turn(
            user_query=user_query,
            planner=get_planner(),
        )

        return {
            "status": "completed",
            "session_id": session_id,
            "answer": result["answer"],
            "figures": result["figures"],
        }

    finally:
        db.close()