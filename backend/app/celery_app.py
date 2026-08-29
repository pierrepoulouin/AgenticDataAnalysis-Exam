import os

from celery import Celery
from kombu import Queue


celery_app = Celery(
    "agentic_data_analysis",
    broker=os.getenv(
        "CELERY_BROKER_URL",
        "redis://localhost:6379/0",
    ),
    backend=os.getenv(
        "CELERY_RESULT_BACKEND",
        "redis://localhost:6379/1",
    ),
    include=[
        "backend.app.tasks",
    ],
)


celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    broker_connection_retry_on_startup=True,

    # Default queue for lightweight/system tasks.
    task_default_queue="default",

    # Explicit queues avoid sending long analyses
    # to the same logical queue as system tasks.
    task_queues=(
        Queue("default"),
        Queue("analysis"),
    ),

    task_routes={
        "health.ping": {
            "queue": "default",
        },
        "agent.run_turn": {
            "queue": "analysis",
        },
    },

    task_create_missing_queues=False,
)