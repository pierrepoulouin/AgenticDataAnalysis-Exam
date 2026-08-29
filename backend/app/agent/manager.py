from typing import Any

from backend.app.agent.tools import (
    execute_data_cleaning,
    execute_statistical_analysis,
    execute_visualization,
)


class AgentManager:
    def __init__(
        self,
        session_id: int,
        variables: dict[str, Any] | None = None,
    ):
        self.session_id = session_id
        self.variables = dict(variables or {})

        self.tools = {
            "execute_data_cleaning": execute_data_cleaning,
            "execute_statistical_analysis": execute_statistical_analysis,
            "execute_visualization": execute_visualization,
        }

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