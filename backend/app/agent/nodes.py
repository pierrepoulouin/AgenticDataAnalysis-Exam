from collections.abc import Callable
from typing import Any

from backend.app.agent.manager import AgentManager
from backend.app.agent.state import AgentState


def make_tool_execution_node(
    manager: AgentManager,
) -> Callable[[AgentState], dict[str, Any]]:
    def execute_tool_node(
        state: AgentState,
    ) -> dict[str, Any]:
        tool_name = state.get("tool_name")
        thought = state.get("thought", "")
        python_code = state.get("python_code")

        if not tool_name:
            raise ValueError(
                "No tool selected for execution"
            )

        if not python_code:
            raise ValueError(
                "No Python code provided for tool execution"
            )

        result = manager.execute_tool(
            tool_name=tool_name,
            thought=thought,
            python_code=python_code,
        )

        return {
            "tool_result": result,
            "current_variables": manager.variables,
            "figures": result.get("figures", []),
        }

    return execute_tool_node