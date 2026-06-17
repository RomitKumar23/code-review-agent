"""
Unit tests for the Celery worker pipeline.
Mocks GitHub and LLM calls so no real API calls are made.
"""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))

from unittest.mock import AsyncMock, patch, MagicMock
from llm.base import ReviewResult, ReviewComment, ReviewContext


@pytest.mark.asyncio
async def test_review_pr_calls_github_and_llm():
    """
    Full pipeline test: verifies that _review_pr fetches diff,
    calls the LLM, and posts results back to GitHub.
    """
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "worker"))

    mock_diff = "--- a/app.py\n+++ b/app.py\n@@ -1,3 +1,4 @@\n+import os\n def main():\n     pass"
    mock_review = ReviewResult(
        summary="Good change, minor issues found.",
        comments=[
            ReviewComment(
                file="app.py", line=1,
                severity="suggestion",
                message="Consider using pathlib instead of os",
                suggestion="from pathlib import Path"
            )
        ],
        provider_used="openai",
        model_used="gpt-4o",
        tokens_used=512,
    )

    with patch("worker.tasks.GitHubClient") as MockGitHub, \
         patch("worker.tasks.get_provider") as mock_get_provider:

        # Set up mock GitHub client
        mock_gh = AsyncMock()
        mock_gh.get_pr_diff.return_value = mock_diff
        mock_gh.post_review.return_value = None
        MockGitHub.return_value = mock_gh

        # Set up mock LLM provider
        mock_provider = AsyncMock()
        mock_provider.review.return_value = mock_review
        mock_get_provider.return_value = mock_provider

        from worker.tasks import _review_pr
        result = await _review_pr("owner/repo", 42, "Add import")

    assert result["status"] == "done"
    assert result["provider"] == "openai"
    assert result["tokens"] == 512
    assert result["comment_count"] == 1

    mock_gh.get_pr_diff.assert_called_once_with("owner/repo", 42)
    mock_gh.post_review.assert_called_once()


@pytest.mark.asyncio
async def test_empty_diff_is_skipped():
    """Worker should gracefully skip PRs with no diff (e.g. draft with no changes)."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "worker"))

    with patch("worker.tasks.GitHubClient") as MockGitHub, \
         patch("worker.tasks.get_provider"):

        mock_gh = AsyncMock()
        mock_gh.get_pr_diff.return_value = "   "   # empty/whitespace diff
        MockGitHub.return_value = mock_gh

        from worker.tasks import _review_pr
        result = await _review_pr("owner/repo", 99, "Empty PR")

    assert result["status"] == "skipped"
    assert result["reason"] == "empty diff"
