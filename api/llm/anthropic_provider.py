from anthropic import AsyncAnthropic
import json
from .base import BaseLLMProvider, ReviewContext, ReviewResult, ReviewComment
from core.config import get_settings
from core.logging import logger

class AnthropicProvider(BaseLLMProvider):
    def __init__(self):
        settings = get_settings()
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = settings.active_llm_model   # e.g. "claude-opus-4-6"

    async def review(self, diff: str, ctx: ReviewContext) -> ReviewResult:
        prompt = self._build_prompt(diff, ctx)
        logger.info("llm.request", provider="anthropic", model=self.model)

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text
        # Strip markdown fences if model wraps output
        clean = raw.strip().removeprefix("```json").removesuffix("```").strip()
        data = json.loads(clean)

        return ReviewResult(
            summary=data["summary"],
            comments=[ReviewComment(**c) for c in data.get("comments", [])],
            provider_used="anthropic",
            model_used=self.model,
            tokens_used=response.usage.input_tokens + response.usage.output_tokens,
        )