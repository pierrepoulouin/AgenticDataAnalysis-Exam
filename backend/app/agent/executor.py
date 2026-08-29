import ast
import os
import pickle
import subprocess
import sys
import tempfile
from pathlib import Path
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


BLOCKED_ATTRIBUTES = {
    # Lecture filesystem / données externes
    "read_csv",
    "read_table",
    "read_fwf",
    "read_excel",
    "read_json",
    "read_html",
    "read_xml",
    "read_pickle",
    "read_parquet",
    "read_feather",
    "read_orc",
    "read_sas",
    "read_spss",
    "read_sql",
    "read_sql_query",
    "read_sql_table",
    "read_clipboard",
    "HDFStore",

    # Écriture filesystem
    "to_csv",
    "to_excel",
    "to_json",
    "to_html",
    "to_xml",
    "to_pickle",
    "to_parquet",
    "to_feather",
    "to_sql",

    # NumPy filesystem
    "load",
    "save",
    "savez",
    "savez_compressed",
    "fromfile",
    "tofile",
    "memmap",

    # Helpers potentiellement dangereux
    "urlopen",
    "urlretrieve",
    "request",
    "eval",
}


BLOCKED_ATTRIBUTE_PREFIXES = (
    "write_",
    "fetch_",
)


DEFAULT_TIMEOUT_SECONDS = float(
    os.getenv(
        "SANDBOX_TIMEOUT_SECONDS",
        "10",
    )
)

DEFAULT_MEMORY_LIMIT_MB = int(
    os.getenv(
        "SANDBOX_MEMORY_LIMIT_MB",
        "512",
    )
)


class SandboxTimeoutError(TimeoutError):
    """Raised when sandbox execution exceeds its time limit."""


class SandboxMemoryLimitError(MemoryError):
    """Raised when sandbox execution exceeds its memory limit."""


def validate_python_code(
    code: str,
) -> None:
    """
    Validate generated Python code before execution.

    Imports, dangerous builtins, dunder access and
    filesystem/network-oriented helpers are rejected.
    """

    tree = ast.parse(code)

    for node in ast.walk(tree):
        if isinstance(
            node,
            (
                ast.Import,
                ast.ImportFrom,
            ),
        ):
            raise ValueError(
                "Import statements are not allowed"
            )

        if isinstance(
            node,
            ast.Name,
        ):
            if (
                node.id in BLOCKED_NAMES
                or node.id.startswith("__")
            ):
                raise ValueError(
                    f"Forbidden name: {node.id}"
                )

        if isinstance(
            node,
            ast.Attribute,
        ):
            if node.attr.startswith("__"):
                raise ValueError(
                    f"Forbidden attribute: {node.attr}"
                )

            if (
                node.attr
                in BLOCKED_ATTRIBUTES
            ):
                raise ValueError(
                    f"Forbidden attribute: {node.attr}"
                )

            if node.attr.startswith(
                BLOCKED_ATTRIBUTE_PREFIXES
            ):
                raise ValueError(
                    f"Forbidden attribute: {node.attr}"
                )


def execute_python(
    code: str,
    variables: dict[str, Any] | None = None,
    *,
    timeout_seconds: float | None = None,
    memory_limit_mb: int | None = None,
) -> dict[str, Any]:
    """
    Execute validated Python in an isolated subprocess.

    Security layers:
    - AST validation
    - restricted builtins
    - separate process
    - execution timeout
    - memory limit
    """

    validate_python_code(code)

    timeout = (
        timeout_seconds
        if timeout_seconds is not None
        else DEFAULT_TIMEOUT_SECONDS
    )

    memory_limit = (
        memory_limit_mb
        if memory_limit_mb is not None
        else DEFAULT_MEMORY_LIMIT_MB
    )

    if timeout <= 0:
        raise ValueError(
            "timeout_seconds must be positive"
        )

    if memory_limit <= 0:
        raise ValueError(
            "memory_limit_mb must be positive"
        )

    payload = {
        "code": code,
        "variables": dict(
            variables or {}
        ),
        "memory_limit_mb": memory_limit,
    }

    # executor.py:
    # repo/backend/app/agent/executor.py
    #
    # parents[3] => repo root
    project_root = (
        Path(__file__)
        .resolve()
        .parents[3]
    )

    child_env = os.environ.copy()

    existing_pythonpath = (
        child_env.get(
            "PYTHONPATH",
            "",
        )
    )

    child_env["PYTHONPATH"] = (
        str(project_root)
        if not existing_pythonpath
        else (
            f"{project_root}"
            f"{os.pathsep}"
            f"{existing_pythonpath}"
        )
    )

    with tempfile.TemporaryDirectory() as directory:
        input_path = os.path.join(
            directory,
            "input.pkl",
        )

        output_path = os.path.join(
            directory,
            "output.pkl",
        )

        with open(
            input_path,
            "wb",
        ) as file:
            pickle.dump(
                payload,
                file,
            )

        try:
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    (
                        "backend.app.agent."
                        "sandbox_runner"
                    ),
                    input_path,
                    output_path,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
                check=False,

                # Important:
                # le test d'intégration peut changer
                # le cwd vers tmp_path.
                cwd=str(project_root),

                # Rend backend importable explicitement
                # dans le processus enfant.
                env=child_env,
            )

        except subprocess.TimeoutExpired as exc:
            raise SandboxTimeoutError(
                (
                    "Sandbox execution exceeded "
                    f"{timeout} seconds"
                )
            ) from exc

        if not os.path.exists(
            output_path
        ):
            stderr = (
                completed.stderr.strip()
                or "<empty stderr>"
            )

            raise RuntimeError(
                (
                    "Sandbox process terminated "
                    "without a result "
                    f"(exit code "
                    f"{completed.returncode}). "
                    f"stderr: {stderr}"
                )
            )

        with open(
            output_path,
            "rb",
        ) as file:
            response = pickle.load(file)

    status = response.get("status")

    if status == "ok":
        return response["result"]

    if status == "memory_error":
        raise SandboxMemoryLimitError(
            response.get(
                "message",
                "Sandbox memory limit exceeded",
            )
        )

    raise RuntimeError(
        (
            response.get(
                "error_type",
                "SandboxError",
            )
            + ": "
            + response.get(
                "message",
                "Execution failed",
            )
        )
    )