from celery import Celery
from core.config import get_settings

settings = get_settings()

celery_client = Celery(
    "code_review_agent_client",
    broker=settings.redis_url,
    backend=settings.redis_url,
)


def enqueue_pr_review(repo: str, pr_number: int, pr_title: str, diff_url: str):
    return celery_client.send_task(
        "tasks.process_pr_review",
        kwargs={
            "repo": repo,
            "pr_number": pr_number,
            "pr_title": pr_title,
            "diff_url": diff_url,
        },
    )
