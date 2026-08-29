from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.agent.manager import AgentManager
from backend.app.agent.planner import MockPlanner
from backend.app.database import get_db
from backend.app.models import User
from backend.app.schemas import AgentTurnRequest, AgentTurnResponse
from backend.app.security import get_current_user


router = APIRouter(
    prefix="/sessions",
    tags=["agent"],
)


@router.post(
    "/{session_id}/agent",
    response_model=AgentTurnResponse,
)
def run_agent(
    session_id: int,
    payload: AgentTurnRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    manager = AgentManager(
        session_id=session_id,
        user_id=current_user.id,
        db=db,
    )

    try:
        result = manager.run_agent_turn(
            user_query=payload.message,
            planner=MockPlanner(),
        )
    except ValueError as exc:
        if str(exc) == "Session not found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            ) from exc

        raise

    return AgentTurnResponse(
        answer=result["answer"],
        figures=result["figures"],
    )