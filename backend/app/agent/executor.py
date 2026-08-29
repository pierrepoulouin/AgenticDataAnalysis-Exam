import ast
import io
from contextlib import redirect_stdout
from typing import Any

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sklearn
from scipy import stats


SAFE_BUILTINS = {
    "len": len,
    "range": range,
    "min": min,
    "max": max,
    "sum": sum,
    "abs": abs,
    "round": round,
    "enumerate": enumerate,
    "zip": zip,
    "sorted": sorted,
    "list": list,
    "dict": dict,
    "set": set,
    "tuple": tuple,
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "print": print,
}


BLOCKED_NAMES = {
    "__import__",
    "open",
    "exec",
    "eval",
    "compile",
    "globals",
    "locals",
    "vars",
    "getattr",
    "setattr",
    "delattr",
    "input",
}


def validate_python_code(code: str) -> None:
    tree = ast.parse(code)

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            raise ValueError(
                "Import statements are not allowed"
            )

        if isinstance(node, ast.Name):
            if (
                node.id in BLOCKED_NAMES
                or node.id.startswith("__")
            ):
                raise ValueError(
                    f"Forbidden name: {node.id}"
                )

        if isinstance(node, ast.Attribute):
            if node.attr.startswith("__"):
                raise ValueError(
                    f"Forbidden attribute: {node.attr}"
                )


def execute_python(
    code: str,
    variables: dict[str, Any] | None = None,
) -> dict[str, Any]:
    validate_python_code(code)

    execution_globals = {
        "__builtins__": SAFE_BUILTINS,
        "pd": pd,
        "np": np,
        "px": px,
        "go": go,
        "stats": stats,
        "sklearn": sklearn,
    }

    execution_locals = dict(variables or {})

    stdout_buffer = io.StringIO()

    with redirect_stdout(stdout_buffer):
        exec(
            code,
            execution_globals,
            execution_locals,
        )

    return {
        "stdout": stdout_buffer.getvalue(),
        "variables": execution_locals,
    }
