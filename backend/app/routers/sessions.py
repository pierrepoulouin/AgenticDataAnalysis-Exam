from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import ChatSession, Message, User
from backend.app.schemas import (
    MessageCreate,
    MessageResponse,
    SessionCreate,
    SessionResponse,
)
from backend.app.security import get_current_user


router = APIRouter(
    prefix="/sessions",
    tags=["sessions"],
)


@router.post(
    "",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_session(
    payload: SessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = ChatSession(
        user_id=current_user.id,
        title=payload.title.strip(),
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    return session


@router.get(
    "",
    response_model=list[SessionResponse],
)
def list_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sessions = db.scalars(
        select(ChatSession)
        .where(
            ChatSession.user_id == current_user.id
        )
        .order_by(
            ChatSession.created_at.desc()
        )
    ).all()

    return sessions


@router.get(
    "/{session_id}",
    response_model=SessionResponse,
)
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

    return session


@router.post(
    "/{session_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_message(
    session_id: int,
    payload: MessageCreate,
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

    message = Message(
        session_id=session.id,
        role="user",
        content=payload.content,
    )

    db.add(message)
    db.commit()
    db.refresh(message)

    return message


@router.get(
    "/{session_id}/messages",
    response_model=list[MessageResponse],
)
def list_messages(
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

    messages = db.scalars(
        select(Message)
        .where(
            Message.session_id == session.id
        )
        .order_by(
            Message.created_at.asc()
        )
    ).all()

    return messages