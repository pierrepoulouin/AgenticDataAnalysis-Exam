import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import (
    ChatSession,
    Message,
    User,
    Visualization,
)
from backend.app.schemas import (
    VisualizationCreate,
    VisualizationResponse,
)
from backend.app.security import get_current_user

router = APIRouter(
    tags=["visualizations"],
)


@router.post(
    "/messages/{message_id}/visualizations",
    response_model=VisualizationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_visualization(
    message_id: int,
    payload: VisualizationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    message = db.scalar(
        select(Message)
        .join(ChatSession)
        .where(
            Message.id == message_id,
            ChatSession.user_id == current_user.id,
        )
    )

    if message is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found",
        )

    visualization = Visualization(
        message_id=message.id,
        figure_json=json.dumps(payload.figure_json),
    )

    db.add(visualization)
    db.commit()
    db.refresh(visualization)

    return {
        "id": visualization.id,
        "message_id": visualization.message_id,
        "figure_json": json.loads(visualization.figure_json),
        "created_at": visualization.created_at,
    }


@router.get(
    "/visualizations/{visualization_id}",
    response_model=VisualizationResponse,
)
def get_visualization(
    visualization_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    visualization = db.scalar(
        select(Visualization)
        .join(Message)
        .join(ChatSession)
        .where(
            Visualization.id == visualization_id,
            ChatSession.user_id == current_user.id,
        )
    )

    if visualization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visualization not found",
        )

    return {
        "id": visualization.id,
        "message_id": visualization.message_id,
        "figure_json": json.loads(visualization.figure_json),
        "created_at": visualization.created_at,
    }

@router.get(
    "/messages/{message_id}/visualizations",
    response_model=list[VisualizationResponse],
)
def list_message_visualizations(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    message = db.scalar(
        select(Message)
        .join(ChatSession)
        .where(
            Message.id == message_id,
            ChatSession.user_id == current_user.id,
        )
    )

    if message is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found",
        )

    visualizations = db.scalars(
        select(Visualization)
        .where(
            Visualization.message_id == message_id
        )
        .order_by(Visualization.id)
    ).all()

    return [
        VisualizationResponse(
            id=visualization.id,
            message_id=visualization.message_id,
            figure_json=json.loads(
                visualization.figure_json
            ),
            created_at=visualization.created_at,
        )
        for visualization in visualizations
    ]