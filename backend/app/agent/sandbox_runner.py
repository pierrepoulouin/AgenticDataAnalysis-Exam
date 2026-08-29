import io
import os
import pickle
import resource
import sys
from contextlib import redirect_stdout

from backend.app.agent.executor import (
    SAFE_BUILTINS,
    go,
    np,
    pd,
    px,
    sklearn,
    stats,
)


def _current_virtual_memory() -> int:
    """
    Return current process virtual memory in bytes.

    Linux-specific implementation, appropriate for
    the project's Linux/Docker deployment target.
    """

    with open(
        "/proc/self/statm",
        "r",
    ) as file:
        pages = int(
            file.read().split()[0]
        )

    page_size = os.sysconf(
        "SC_PAGE_SIZE"
    )

    return pages * page_size


def _apply_memory_limit(
    memory_limit_mb: int,
) -> None:
    """
    Limit additional virtual memory available
    to executed user code.

    Libraries such as pandas/numpy/sklearn have
    already been imported before this limit is set,
    so the allowance is added to current usage.
    """

    current_vms = (
        _current_virtual_memory()
    )

    additional_memory = (
        memory_limit_mb
        * 1024
        * 1024
    )

    desired_limit = (
        current_vms
        + additional_memory
    )

    _, hard_limit = (
        resource.getrlimit(
            resource.RLIMIT_AS
        )
    )

    if (
        hard_limit
        == resource.RLIM_INFINITY
    ):
        soft_limit = desired_limit

    else:
        soft_limit = min(
            desired_limit,
            hard_limit,
        )

    resource.setrlimit(
        resource.RLIMIT_AS,
        (
            soft_limit,
            hard_limit,
        ),
    )


def main() -> None:
    input_path = sys.argv[1]
    output_path = sys.argv[2]

    with open(
        input_path,
        "rb",
    ) as file:
        payload = pickle.load(file)

    code = payload["code"]

    variables = payload.get(
        "variables",
        {},
    )

    memory_limit_mb = payload[
        "memory_limit_mb"
    ]

    try:
        _apply_memory_limit(
            memory_limit_mb
        )

        execution_globals = {
            "__builtins__": SAFE_BUILTINS,
            "pd": pd,
            "np": np,
            "px": px,
            "go": go,
            "stats": stats,
            "sklearn": sklearn,
        }

        execution_locals = dict(
            variables
        )

        stdout_buffer = (
            io.StringIO()
        )

        with redirect_stdout(
            stdout_buffer
        ):
            exec(
                code,
                execution_globals,
                execution_locals,
            )

        result = {
            "status": "ok",
            "result": {
                "stdout": (
                    stdout_buffer.getvalue()
                ),
                "variables": (
                    execution_locals
                ),
            },
        }

    except MemoryError:
        result = {
            "status": "memory_error",
            "message": (
                "Sandbox memory limit exceeded"
            ),
        }

    except BaseException as exc:
        result = {
            "status": "error",
            "error_type": (
                type(exc).__name__
            ),
            "message": str(exc),
        }

    with open(
        output_path,
        "wb",
    ) as file:
        pickle.dump(
            result,
            file,
        )


if __name__ == "__main__":
    main()