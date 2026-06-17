from openai import AsyncOpenAI
import json
from .base import BaseLLMProvider, ReviewContext, ReviewResult, ReviewComment
from core.config import get_settings
from core.logging import logger

class OpenAIProvider(BaseLLMProvider):
    def __init__(self):
        settings = get_settings()
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.active_llm_model

    async def review(self, diff: str, ctx: ReviewContext) -> ReviewResult:
        prompt = self._build_prompt(diff, ctx)
        logger.info("llm.request", provider="openai", model=self.model)

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},  # enforces JSON output
                temperature=0.1,   # low temp = consistent, deterministic reviews
            )
            raw = response.choices[0].message.content
            data = json.loads(raw)

            return ReviewResult(
                summary=data["summary"],
                comments=[ReviewComment(**c) for c in data.get("comments", [])],
                provider_used="openai",
                model_used=self.model,
                tokens_used=response.usage.total_tokens,
            )
        except Exception as e:
            logger.error("llm.request_failed", provider="openai", error=str(e))
            raise