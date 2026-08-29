import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.agent.tools import (
    execute_data_cleaning,
    execute_statistical_analysis,
    execute_visualization,
)
from backend.app.models import (
    ChatSession,
    Dataset,
    Message,
    Visualization,
)
from backend.app.agent.planner import Planner


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

    def load_dataframe_context(self) -> dict[str, Any]:
        self.get_session()

        datasets = self.db.scalars(
            select(Dataset).where(
                Dataset.user_id == self.user_id,
                Dataset.session_id == self.session_id,
            )
        ).all()

        loaded = {}

        allowed_root = Path("uploads").resolve()

        for dataset in datasets:
            path = Path(dataset.storage_path).resolve()

            try:
                path.relative_to(allowed_root)
            except ValueError:
                raise ValueError(
                    f"Dataset path outside allowed storage: {dataset.id}"
                )

            if path.suffix.lower() != ".csv":
                raise ValueError(
                    f"Unsupported dataset format: {path.suffix}"
                )

            if not path.exists():
                raise FileNotFoundError(
                    f"Dataset file not found: {dataset.storage_path}"
                )

            variable_name = f"dataset_{dataset.id}"

            dataframe = pd.read_csv(path)

            self.variables[variable_name] = dataframe

            loaded[variable_name] = {
                "dataset_id": dataset.id,
                "filename": dataset.filename,
                "description": dataset.description,
                "rows": len(dataframe),
                "columns": list(dataframe.columns),
            }

        return loaded

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

    def run_agent_turn(
        self,
        user_query: str,
        planner: Planner,
    ) -> dict[str, Any]:
        from backend.app.agent.graph import create_agent_graph

        self.get_session()

        user_message = self.save_message(
            role="user",
            content=user_query,
        )

        history = self.load_history()
        data_context = self.load_dataframe_context()

        graph = create_agent_graph(
            manager=self,
            planner=planner,
        )

        result = graph.invoke({
            "session_id": self.session_id,
            "user_id": self.user_id,
            "user_query": user_query,
            "data_context": data_context,
            "current_variables": self.variables,
            "figures": [],
            "final_answer": None,
        })

        final_answer = result.get("final_answer")

        if not final_answer:
            raise ValueError(
                "Agent did not produce a final answer"
            )

        figures = result.get("figures", [])

        assistant_message = self.save_message(
            role="assistant",
            content=final_answer,
            figures=figures,
        )

        return {
            "user_message_id": user_message.id,
            "assistant_message_id": assistant_message.id,
            "answer": final_answer,
            "figures": figures,
            "thought": result.get("thought"),
            "tool_result": result.get("tool_result"),
        }