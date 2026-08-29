from backend.app.celery_app import celery_app


@celery_app.task(name="health.ping")
def celery_ping() -> dict[str, str]:
    return {
        "status": "ok",
        "worker": "celery",
    }