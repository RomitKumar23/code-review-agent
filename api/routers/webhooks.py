import hashlib, hmac
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, Depends
from core.config import get_settings, Settings
from core.logging import logger
from core.celery_client import enqueue_pr_review

router = APIRouter()

def verify_github_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    GitHub signs every webhook with HMAC-SHA256.
    We MUST verify this before trusting the payload.
    Never skip this in production — anyone could POST to your endpoint.
    """
    expected = "sha256=" + hmac.new(
        secret.encode(), payload, hashlib.sha256
    ).hexdigest()
    # Use compare_digest to prevent timing attacks
    return hmac.compare_digest(expected, signature)

@router.post("/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings),
):
    payload_bytes = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")
    event_type = request.headers.get("X-GitHub-Event", "")

    # Security gate — reject anything that doesn't pass HMAC check
    if not verify_github_signature(payload_bytes, signature, settings.github_webhook_secret):
        logger.warning("webhook.signature_invalid", ip=request.client.host)
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = await request.json()

    # We only care about PR open/sync events
    if event_type == "pull_request" and payload.get("action") in ("opened", "synchronize"):
        pr = payload["pull_request"]
        logger.info(
            "webhook.pr_received",
            repo=payload["repository"]["full_name"],
            pr=pr["number"],
        )
        # Enqueue asynchronously — webhook must return fast (< 10s or GitHub retries)
        enqueue_pr_review(
            repo=payload["repository"]["full_name"],
            pr_number=pr["number"],
            pr_title=pr["title"],
            diff_url=pr["url"],
        )

    return {"status": "queued"}