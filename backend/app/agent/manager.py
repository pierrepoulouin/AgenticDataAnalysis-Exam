import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.agent.tools import (
    execute_data_cleaning,
    execute_statistical_analysis,
    execute_visualization,
)
from backend.app.models import (
    ChatSession,
    Message,
    Visualization,
)


class AgentManager:
    def __init__(
        self,
        session_id: int,
        user_id: int,
        db: Session,
        variables: dict[str, Any] | None = None,
    ):
        self.session_id = session_id
        self.user_id = user_id
        self.db = db
        self.variables = dict(variables or {})

        self.tools = {
            "execute_data_cleaning": execute_data_cleaning,
            "execute_statistical_analysis": execute_statistical_analysis,
            "execute_visualization": execute_visualization,
        }

    def get_session(self) -> ChatSession:
        session = self.db.scalar(
            select(ChatSession).where(
                ChatSession.id == self.session_id,
                ChatSession.user_id == self.user_id,
            )
        )

        if session is None:
            raise ValueError("Session not found")

        return session

    def load_history(self) -> list[dict[str, Any]]:
        self.get_session()

        messages = self.db.scalars(
            select(Message)
            .where(Message.session_id == self.session_id)
            .order_by(Message.created_at.asc())
        ).all()

        history = []

        for message in messages:
            figures = []

            for visualization in message.visualizations:
                figures.append(
                    json.loads(visualization.figure_json)
                )

            history.append(
                {
                    "id": message.id,
                    "role": message.role,
                    "content": message.content,
                    "figures": figures,
                    "created_at": message.created_at,
                }
            )

        return history

    def save_message(
        self,
        role: str,
        content: str,
        figures: list[dict[str, Any]] | None = None,
    ) -> Message:
        session = self.get_session()

        message = Message(
            session_id=self.session_id,
            role=role,
            content=content,
        )

        self.db.add(message)
        self.db.flush()

        for figure in figures or []:
            visualization = Visualization(
                message_id=message.id,
                figure_json=json.dumps(figure),
            )

            self.db.add(visualization)

        session.updated_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(message)

        return message

    def execute_tool(
        self,
        tool_name: str,
        thought: str,
        python_code: str,
    ) -> dict[str, Any]:
        tool = self.tools.get(tool_name)

        if tool is None:
            raise ValueError(
                f"Unknown tool: {tool_name}"
            )

        result = tool(
            thought=thought,
            python_code=python_code,
            variables=self.variables,
        )

        self.variables = result["variables"]

        return result