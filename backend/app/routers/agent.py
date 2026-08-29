from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.celery_app import celery_app
from backend.app.database import get_db
from backend.app.models import ChatSession, User
from backend.app.schemas import (
    AgentTaskResponse,
    AgentTaskStatusResponse,
    AgentTurnRequest,
)
from backend.app.security import get_current_user
from backend.app.tasks import run_agent_turn_task


router = APIRouter(
    prefix="/sessions",
    tags=["agent"],
)


def get_owned_session(
    session_id: int,
    user_id: int,
    db: Session,
) -> ChatSession:
    session = db.scalar(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == user_id,
        )
    )

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    return session


@router.post(
    "/{session_id}/agent",
    response_model=AgentTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def run_agent(
    session_id: int,
    payload: AgentTurnRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_owned_session(
        session_id=session_id,
        user_id=current_user.id,
        db=db,
    )

    task = run_agent_turn_task.delay(
        session_id=session_id,
        user_id=current_user.id,
        user_query=payload.message,
    )

    return AgentTaskResponse(
        task_id=task.id,
        status="queued",
    )


@router.get(
    "/{session_id}/agent/tasks/{task_id}",
    response_model=AgentTaskStatusResponse,
)
def get_agent_task_status(
    session_id: int,
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_owned_session(
        session_id=session_id,
        user_id=current_user.id,
        db=db,
    )

    task = AsyncResult(
        task_id,
        app=celery_app,
    )

    if task.state == "PENDING":
        return AgentTaskStatusResponse(
            task_id=task_id,
            status="pending",
        )

    if task.state == "STARTED":
        return AgentTaskStatusResponse(
            task_id=task_id,
            status="started",
        )

    if task.state == "SUCCESS":
        result = task.result

        # Empêche d'exposer le résultat d'une tâche appartenant
        # à une autre session.
        if result.get("session_id") != session_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found",
            )

        return AgentTaskStatusResponse(
            task_id=task_id,
            status="completed",
            answer=result.get("answer"),
            figures=result.get("figures", []),
        )

    if task.state == "FAILURE":
        return AgentTaskStatusResponse(
            task_id=task_id,
            status="failed",
        )

    return AgentTaskStatusResponse(
        task_id=task_id,
        status=task.state.lower(),
    )