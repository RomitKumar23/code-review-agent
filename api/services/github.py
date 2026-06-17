"""
GitHub API client — two responsibilities:
  1. Fetch the unified diff for a PR
  2. Post structured inline review comments back to the PR
"""
import httpx
from core.config import get_settings
from core.logging import logger


class GitHubClient:
    BASE = "https://api.github.com"

    def __init__(self):
        settings = get_settings()
        self.token = settings.github_app_token
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3.diff",   # diff media type
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def get_pr_diff(self, repo: str, pr_number: int) -> str:
        """
        Returns the unified diff string for the given PR.
        GitHub returns raw diff when Accept: application/vnd.github.v3.diff is set.
        """
        url = f"{self.BASE}/repos/{repo}/pulls/{pr_number}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=self.headers)
            resp.raise_for_status()
            diff = resp.text
            logger.info("github.diff_fetched", repo=repo, pr=pr_number, bytes=len(diff))
            return diff

    async def post_review(self, repo: str, pr_number: int, summary: str, comments: list) -> None:
        """
        Posts a PR review with inline comments using GitHub's Reviews API.
        Each comment is pinned to a specific file and line in the diff.
        """
        url = f"{self.BASE}/repos/{repo}/pulls/{pr_number}/reviews"

        # Build the GitHub review payload
        # GitHub requires comments to reference the diff position or commit SHA
        # We use COMMENT body only for simplicity — upgrade to inline later
        review_body = self._format_review_body(summary, comments)

        payload = {
            "body": review_body,
            "event": "COMMENT",   # APPROVE | REQUEST_CHANGES | COMMENT
        }

        json_headers = {**self.headers, "Accept": "application/vnd.github+json"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=json_headers, json=payload)
            if resp.status_code not in (200, 201):
                logger.error(
                    "github.post_review_failed",
                    status=resp.status_code,
                    body=resp.text[:200],
                )
                resp.raise_for_status()
            logger.info("github.review_posted", repo=repo, pr=pr_number)

    def _format_review_body(self, summary: str, comments: list) -> str:
        """Formats the AI review as a readable GitHub markdown comment."""
        lines = [
            "## 🤖 AI Code Review",
            "",
            "### Summary",
            summary,
            "",
            "---",
            "",
            "### Comments",
        ]

        if not comments:
            lines.append("_No specific issues found._")
        else:
            for c in comments:
                severity_emoji = {"error": "🔴", "warning": "🟡", "suggestion": "🟢"}.get(
                    c.get("severity", "suggestion"), "💬"
                )
                lines.append(
                    f"{severity_emoji} **`{c.get('file', 'unknown')}`** "
                    f"(line {c.get('line', '?')}): {c.get('message', '')}"
                )
                if c.get("suggestion"):
                    lines.append(f"  > 💡 Suggestion: {c['suggestion']}")
                lines.append("")

        return "\n".join(lines)
