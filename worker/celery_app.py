import os
from celery import Celery


def create_celery_app() -> Celery:
    """Create a Celery application configured from environment variables."""
    broker_url = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
    result_backend = os.getenv("CELERY_RESULT_BACKEND", broker_url)

    app = Celery(
        "rag_tasks",
        broker=broker_url,
        backend=result_backend,
        include=["worker.tasks"],
    )

    app.conf.update(
        task_default_queue=os.getenv("CELERY_DEFAULT_QUEUE", "rag"),
        task_track_started=True,
        worker_prefetch_multiplier=int(os.getenv("CELERY_PREFETCH_MULTIPLIER", "1")),
        task_acks_late=True,
        result_expires=int(os.getenv("CELERY_RESULT_EXPIRES", "3600")),
    )

    return app


celery_app = create_celery_app()
