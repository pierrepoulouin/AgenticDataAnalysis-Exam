import logging
import time
import uuid

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from prometheus_client import (
    Counter,
    Histogram,
    CONTENT_TYPE_LATEST,
    generate_latest,
)

from backend.app.routers.agent import router as agent_router
from backend.app.routers.auth import router as auth_router
from backend.app.routers.datasets import router as datasets_router
from backend.app.routers.sessions import router as sessions_router
from backend.app.routers.visualizations import (
    router as visualizations_router,
)


# ------------------------------------------------------------------
# Structured JSON logging
# ------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.TimeStamper(
            fmt="iso",
            utc=True,
        ),
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        logging.INFO
    ),
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


# ------------------------------------------------------------------
# Prometheus metrics
# ------------------------------------------------------------------

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    [
        "method",
        "path",
        "status_code",
    ],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    [
        "method",
        "path",
    ],
)


# ------------------------------------------------------------------
# FastAPI application
# ------------------------------------------------------------------

app = FastAPI(
    title="Agentic Data Analysis API",
    version="0.1.0",
)


# Explicit origins only.
# Wildcard origins are intentionally avoided when credentials
# are enabled.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",
        "http://127.0.0.1:8501",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------
# Routers
# ------------------------------------------------------------------

app.include_router(auth_router)
app.include_router(sessions_router)
app.include_router(datasets_router)
app.include_router(visualizations_router)
app.include_router(agent_router)


# ------------------------------------------------------------------
# Request context / metrics / logs
# ------------------------------------------------------------------

@app.middleware("http")
async def request_context_middleware(
    request: Request,
    call_next,
):
    request_id = str(uuid.uuid4())
    start_time = time.perf_counter()

    request.state.request_id = request_id

    structlog.contextvars.bind_contextvars(
        request_id=request_id,
    )

    logger.info(
        "request_started",
        method=request.method,
        path=request.url.path,
    )

    try:
        response = await call_next(
            request
        )

        duration_seconds = (
            time.perf_counter()
            - start_time
        )

        duration_ms = round(
            duration_seconds * 1000,
            2,
        )

        # After routing, FastAPI normally exposes
        # the route template.
        #
        # This prevents IDs such as /sessions/1,
        # /sessions/2, ... from creating excessive
        # Prometheus label cardinality.
        route = request.scope.get("route")

        metric_path = (
            getattr(
                route,
                "path",
                request.url.path,
            )
        )

        REQUEST_COUNT.labels(
            method=request.method,
            path=metric_path,
            status_code=response.status_code,
        ).inc()

        REQUEST_LATENCY.labels(
            method=request.method,
            path=metric_path,
        ).observe(
            duration_seconds
        )

        response.headers[
            "X-Request-ID"
        ] = request_id

        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        return response

    finally:
        structlog.contextvars.clear_contextvars()


# ------------------------------------------------------------------
# Global exception handling
# ------------------------------------------------------------------

@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request,
    exc: Exception,
):
    request_id = getattr(
        request.state,
        "request_id",
        "unknown",
    )

    logger.exception(
        "unhandled_exception",
        request_id=request_id,
        method=request.method,
        path=request.url.path,

        # Useful internally, while the API response
        # deliberately hides the stack trace.
        error_type=type(exc).__name__,
        error=str(exc),
    )

    return JSONResponse(
        status_code=500,
        content={
            "detail": (
                "Internal server error"
            ),
            "request_id": request_id,
        },
    )


# ------------------------------------------------------------------
# Operational endpoints
# ------------------------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "backend",
    }


@app.get("/metrics")
def metrics():
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )