from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import ChatSession, User
from backend.app.security import get_current_user


router = APIRouter(
    prefix="/sessions",
    tags=["sessions"],
)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_session(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = ChatSession(
        user_id=current_user.id,
        title="New analysis",
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    return {
        "id": session.id,
        "user_id": session.user_id,
        "title": session.title,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
    }


@router.get("")
def list_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sessions = db.scalars(
        select(ChatSession)
        .where(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.created_at.desc())
    ).all()

    return [
        {
            "id": session.id,
            "title": session.title,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
        }
        for session in sessions
    ]


@router.get("/{session_id}")
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.scalar(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id,
        )
    )

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    return {
        "id": session.id,
        "title": session.title,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
    }