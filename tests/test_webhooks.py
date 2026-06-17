"""
Unit tests for the GitHub webhook handler.
Tests HMAC verification and event filtering without hitting GitHub.
"""
import hashlib
import hmac
import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# We need to mock settings before importing the app
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))

# Mock settings so we don't need a real .env
with patch("core.config.Settings") as MockSettings:
    MockSettings.return_value.github_webhook_secret = "test_secret"
    MockSettings.return_value.github_app_token = "test_token"
    MockSettings.return_value.active_llm_provider = "openai"
    MockSettings.return_value.active_llm_model = "gpt-4o"
    MockSettings.return_value.database_url = "postgresql+asyncpg://x:x@localhost/x"
    MockSettings.return_value.redis_url = "redis://localhost:6379/0"


def _make_signature(payload: bytes, secret: str) -> str:
    """Helper to generate a valid HMAC-SHA256 signature."""
    return "sha256=" + hmac.new(
        secret.encode(), payload, hashlib.sha256
    ).hexdigest()


class TestSignatureVerification:
    """Tests for the HMAC signature verification logic."""

    def test_valid_signature(self):
        from routers.webhooks import verify_github_signature
        payload = b'{"action": "opened"}'
        secret = "my_secret"
        sig = _make_signature(payload, secret)
        assert verify_github_signature(payload, sig, secret) is True

    def test_invalid_signature_rejected(self):
        from routers.webhooks import verify_github_signature
        payload = b'{"action": "opened"}'
        assert verify_github_signature(payload, "sha256=fakesig", "my_secret") is False

    def test_tampered_payload_rejected(self):
        from routers.webhooks import verify_github_signature
        payload = b'{"action": "opened"}'
        sig = _make_signature(payload, "my_secret")
        tampered = b'{"action": "opened", "extra": "injected"}'
        assert verify_github_signature(tampered, sig, "my_secret") is False

    def test_missing_sha256_prefix_rejected(self):
        from routers.webhooks import verify_github_signature
        payload = b'test'
        bare_hex = hmac.new(b"secret", payload, hashlib.sha256).hexdigest()
        # Without "sha256=" prefix — should fail
        assert verify_github_signature(payload, bare_hex, "secret") is False


class TestLLMProviderAbstraction:
    """Tests for the provider factory and base contract."""

    def test_factory_returns_correct_provider(self):
        from llm.factory import get_provider
        from llm.openai_provider import OpenAIProvider

        with patch("llm.factory.get_settings") as mock_settings:
            mock_settings.return_value.active_llm_provider = "openai"
            mock_settings.return_value.active_llm_model = "gpt-4o"
            mock_settings.return_value.openai_api_key = "sk-test"
            provider = get_provider()
            assert isinstance(provider, OpenAIProvider)

    def test_factory_raises_on_unknown_provider(self):
        from llm.factory import get_provider

        with patch("llm.factory.get_settings") as mock_settings:
            mock_settings.return_value.active_llm_provider = "nonexistent"
            with pytest.raises(ValueError, match="Unknown provider"):
                get_provider()

    def test_base_provider_prompt_contains_diff(self):
        from llm.base import BaseLLMProvider, ReviewContext

        class ConcreteProvider(BaseLLMProvider):
            async def review(self, diff, ctx):
                return None

        provider = ConcreteProvider()
        ctx = ReviewContext(repo="owner/repo", pr_number=1, pr_title="test")
        prompt = provider._build_prompt("--- a/file.py\n+++ b/file.py", ctx)

        assert "owner/repo" in prompt
        assert "file.py" in prompt
        assert "summary" in prompt   # JSON structure is in the prompt
