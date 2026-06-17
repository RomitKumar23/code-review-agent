"""
Lightweight Celery client used by the API to ENQUEUE jobs.

This is deliberately separate from worker/tasks.py. The API should never
import the worker's task implementation (GitHub client, LLM providers, etc.) —
it only needs to know how to publish a message onto the Redis queue.

This keeps api/ and worker/ as independently deployable services that share
nothing but a message contract (task name + arguments), not Python code.
"""
from celery import Celery
from core.config import get_settings

settings = get_settings()

celery_client = Celery(
    "code_review_agent_client",
    broker=settings.redis_url,
    backend=settings.redis_url,
)


def enqueue_pr_review(repo: str, pr_number: int, pr_title: str, diff_url: str):
    """
    Sends a task onto the queue BY NAME — no import of the task function itself.
    The string "tasks.process_pr_review" must exactly match the `name=` used
    in worker/tasks.py's @celery_app.task(name=...) decorator.
    """
    return celery_client.send_task(
        "tasks.process_pr_review",
        kwargs={
            "repo": repo,
            "pr_number": pr_number,
            "pr_title": pr_title,
            "diff_url": diff_url,
        },
    )
