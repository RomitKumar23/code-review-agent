"""
Celery worker — the async engine of the review agent.

Flow:
  1. FastAPI webhook handler calls process_pr_review.delay(...)
  2. Celery picks the job from Redis queue
  3. Worker fetches PR diff from GitHub
  4. Worker sends diff through the configured LLM provider
  5. Worker posts structured review comments back to GitHub
"""
import os
import sys
import asyncio
from celery import Celery
from celery.utils.log import get_task_logger

# ── Path setup ────────────────────────────────────────────────────────────────
# The worker shares logic with the api package.
# In Docker: api/ is mounted at /app/api  (see docker-compose.yml volumes)
# Locally:   api/ is at ../api relative to this file
_HERE = os.path.dirname(os.path.abspath(__file__))
_API_PATH = os.environ.get("API_PATH") or os.path.join(_HERE, "..", "api")
if _API_PATH not in sys.path:
    sys.path.insert(0, _API_PATH)

from core.config import get_settings
from core.logging import configure_logging, logger
from llm.factory import get_provider
from llm.base import ReviewContext
from services.github import GitHubClient

configure_logging()
settings = get_settings()
task_logger = get_task_logger(__name__)

# ── Celery app ────────────────────────────────────────────────────────────────
celery_app = Celery(
    "code_review_agent",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_acks_late=True,              # task removed from queue only after success
    task_reject_on_worker_lost=True,  # requeue if worker crashes mid-task
    worker_prefetch_multiplier=1,     # process one task at a time per worker
)

# ── Helpers ───────────────────────────────────────────────────────────────────
def run_async(coro):
    """Run an async coroutine from inside a synchronous Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ── Tasks ─────────────────────────────────────────────────────────────────────
@celery_app.task(
    name="tasks.process_pr_review",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,   # 60s → 120s → 240s between retries
)
def process_pr_review(
    self,
    repo: str,
    pr_number: int,
    pr_title: str,
    diff_url: str,     # kept for future use / webhook replay
):
    """
    Orchestrates the full review pipeline for one PR.

    bind=True: gives access to `self` for retry control and task ID.
    autoretry_for=(Exception,): retries on any error up to max_retries.
    retry_backoff=True: doubles the wait between each retry.
    """
    task_id = self.request.id
    logger.info("task.started", task_id=task_id, repo=repo, pr=pr_number)

    result = run_async(_review_pr(repo, pr_number, pr_title))

    logger.info(
        "task.completed",
        task_id=task_id,
        repo=repo,
        pr=pr_number,
        provider=result.get("provider"),
        tokens=result.get("tokens"),
        comments=result.get("comment_count"),
    )
    return result


async def _review_pr(repo: str, pr_number: int, pr_title: str) -> dict:
    """
    Pure async implementation — separated from the Celery task so it's
    independently unit-testable without a running broker.
    """
    github = GitHubClient()
    provider = get_provider()

    # ── 1. Fetch diff ─────────────────────────────────────────────────────────
    diff = await github.get_pr_diff(repo, pr_number)

    if not diff.strip():
        logger.warning("task.empty_diff", repo=repo, pr=pr_number)
        return {"status": "skipped", "reason": "empty diff"}

    # ── 2. Truncate oversized diffs to stay within token budgets ──────────────
    MAX_DIFF_CHARS = 15_000
    if len(diff) > MAX_DIFF_CHARS:
        logger.warning(
            "task.diff_truncated",
            original=len(diff),
            truncated_to=MAX_DIFF_CHARS,
        )
        diff = diff[:MAX_DIFF_CHARS] + "\n\n[... diff truncated due to size ...]"

    # ── 3. LLM review ────────────────────────────────────────────────────────
    ctx = ReviewContext(repo=repo, pr_number=pr_number, pr_title=pr_title)
    review = await provider.review(diff, ctx)

    # ── 4. Post comments back to GitHub ──────────────────────────────────────
    comments_dicts = [
        {
            "file": c.file,
            "line": c.line,
            "severity": c.severity,
            "message": c.message,
            "suggestion": c.suggestion,
        }
        for c in review.comments
    ]

    await github.post_review(
        repo=repo,
        pr_number=pr_number,
        summary=review.summary,
        comments=comments_dicts,
    )

    return {
        "status": "done",
        "provider": review.provider_used,
        "model": review.model_used,
        "tokens": review.tokens_used,
        "comment_count": len(review.comments),
    }
