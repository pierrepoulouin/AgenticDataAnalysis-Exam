import os
from pathlib import Path
from uuid import uuid4

import pandas as pd
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import (
    ChatSession,
    Dataset,
    User,
)
from backend.app.schemas import (
    DatasetCreate,
    DatasetResponse,
)
from backend.app.security import get_current_user


router = APIRouter(
    tags=["datasets"],
)


MAX_UPLOAD_BYTES = 10 * 1024 * 1024


@router.post(
    "/datasets",
    response_model=DatasetResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_dataset(
    payload: DatasetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.session_id is not None:
        session = db.scalar(
            select(ChatSession).where(
                ChatSession.id == payload.session_id,
                ChatSession.user_id == current_user.id,
            )
        )

        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )

    dataset = Dataset(
        user_id=current_user.id,
        session_id=payload.session_id,
        filename=payload.filename,
        storage_path=payload.storage_path,
        description=payload.description,
    )

    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    return dataset


@router.get(
    "/datasets",
    response_model=list[DatasetResponse],
)
def list_datasets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.scalars(
        select(Dataset)
        .where(
            Dataset.user_id == current_user.id
        )
        .order_by(Dataset.id)
    ).all()


@router.get(
    "/datasets/{dataset_id}",
    response_model=DatasetResponse,
)
def get_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dataset = db.scalar(
        select(Dataset).where(
            Dataset.id == dataset_id,
            Dataset.user_id == current_user.id,
        )
    )

    if dataset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found",
        )

    return dataset


@router.post(
    "/sessions/{session_id}/datasets/upload",
    response_model=DatasetResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_dataset(
    session_id: int,
    file: UploadFile = File(...),
    description: str | None = Form(default=None),
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

    original_filename = Path(
        file.filename or ""
    ).name

    if not original_filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing filename",
        )

    if (
        Path(original_filename)
        .suffix
        .lower()
        != ".csv"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are allowed",
        )

    upload_root = Path(
        os.getenv(
            "UPLOAD_ROOT",
            "uploads",
        )
    ).resolve()

    target_directory = (
        upload_root
        / f"user_{current_user.id}"
        / f"session_{session_id}"
    )

    target_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    stored_filename = (
        f"{uuid4().hex}_{original_filename}"
    )

    target_path = (
        target_directory
        / stored_filename
    ).resolve()

    try:
        target_path.relative_to(
            upload_root
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid upload path",
        ) from exc

    total_size = 0

    try:
        with target_path.open(
            "wb"
        ) as destination:
            while True:
                chunk = file.file.read(
                    1024 * 1024
                )

                if not chunk:
                    break

                total_size += len(chunk)

                if (
                    total_size
                    > MAX_UPLOAD_BYTES
                ):
                    raise HTTPException(
                        status_code=(
                            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
                        ),
                        detail=(
                            "CSV file is too large"
                        ),
                    )

                destination.write(
                    chunk
                )

        try:
            pd.read_csv(
                target_path,
                nrows=5,
            )

        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid CSV file",
            ) from exc

        dataset = Dataset(
            user_id=current_user.id,
            session_id=session_id,
            filename=original_filename,
            storage_path=str(target_path),
            description=description,
        )

        db.add(dataset)
        db.commit()
        db.refresh(dataset)

        return dataset

    except Exception:
        db.rollback()

        if target_path.exists():
            target_path.unlink()

        raise