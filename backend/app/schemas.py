from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    is_active: bool
    created_at: datetime

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str
    
class MessageCreate(BaseModel):
    content: str = Field(min_length=1)


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    role: str
    content: str
    created_at: datetime

class DatasetCreate(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    storage_path: str = Field(min_length=1, max_length=1024)
    description: str | None = None
    session_id: int | None = None


class DatasetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    session_id: int | None
    filename: str
    storage_path: str
    description: str | None
    created_at: datetime

class VisualizationCreate(BaseModel):
    figure_json: dict


class VisualizationResponse(BaseModel):
    id: int
    message_id: int
    figure_json: dict
    created_at: datetime

class AgentTurnRequest(BaseModel):
    message: str = Field(min_length=1)


class AgentTurnResponse(BaseModel):
    answer: str
    figures: list[dict]

class AgentTaskResponse(BaseModel):
    task_id: str
    status: str


class AgentTaskStatusResponse(BaseModel):
    task_id: str
    status: str
    answer: str | None = None
    figures: list[dict] = Field(default_factory=list)

class SessionCreate(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=200,
    )


class SessionResponse(BaseModel):
    id: int
    user_id: int
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )