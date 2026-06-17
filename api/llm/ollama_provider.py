import httpx
import json
from .base import BaseLLMProvider, ReviewContext, ReviewResult, ReviewComment
from core.config import get_settings
from core.logging import logger


class OllamaProvider(BaseLLMProvider):
    def __init__(self):
        settings = get_settings()
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.model = settings.active_llm_model  # e.g. "llama3", "mistral"

    async def review(self, diff: str, ctx: ReviewContext) -> ReviewResult:
        prompt = self._build_prompt(diff, ctx)
        logger.info("llm.request", provider="ollama", model=self.model)

        # Correct Ollama API: POST /api/generate (not /run/<model>)
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,   # wait for full response
            "format": "json",  # ask Ollama to enforce JSON output
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                body = resp.json()

                # Ollama /api/generate returns {"response": "...", "done": true, ...}
                raw = body.get("response", "")

                # Strip markdown fences if present
                clean = raw.strip().removeprefix("```json").removesuffix("```").strip()
                data = json.loads(clean)

                return ReviewResult(
                    summary=data["summary"],
                    comments=[ReviewComment(**c) for c in data.get("comments", [])],
                    provider_used="ollama",
                    model_used=self.model,
                    tokens_used=body.get("eval_count", 0),  # Ollama reports token count here
                )

            except json.JSONDecodeError as e:
                logger.error("llm.json_parse_failed", provider="ollama", error=str(e), raw=raw[:200])
                raise
            except Exception as e:
                logger.error("llm.request_failed", provider="ollama", error=str(e))
                raise
