from typing import Any, TypedDict

from langchain_core.messages import BaseMessage


class AgentState(TypedDict, total=False):
    messages: list[BaseMessage]

    session_id: int
    user_id: int

    data_context: dict[str, Any]
    current_variables: dict[str, Any]

    thought: str
    tool_name: str | None
    python_code: str | None

    tool_result: dict[str, Any] | None
    figures: list[dict[str, Any]]

    final_answer: str | None