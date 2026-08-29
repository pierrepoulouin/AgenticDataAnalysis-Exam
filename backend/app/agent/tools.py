import json
from typing import Any

import plotly.graph_objects as go

from backend.app.agent.executor import execute_python


def execute_data_cleaning(
    thought: str,
    python_code: str,
    variables: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = execute_python(
        code=python_code,
        variables=variables,
    )

    return {
        "tool": "execute_data_cleaning",
        "thought": thought,
        "stdout": result["stdout"],
        "variables": result["variables"],
    }


def execute_statistical_analysis(
    thought: str,
    python_code: str,
    variables: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = execute_python(
        code=python_code,
        variables=variables,
    )

    return {
        "tool": "execute_statistical_analysis",
        "thought": thought,
        "stdout": result["stdout"],
        "variables": result["variables"],
    }


def execute_visualization(
    thought: str,
    python_code: str,
    variables: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = execute_python(
        code=python_code,
        variables=variables,
    )

    figures = []

    for value in result["variables"].values():
        if isinstance(value, go.Figure):
            figures.append(
                json.loads(value.to_json())
            )

    return {
        "tool": "execute_visualization",
        "thought": thought,
        "stdout": result["stdout"],
        "variables": result["variables"],
        "figures": figures,
    }