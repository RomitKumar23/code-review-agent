from core.config import get_settings
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider
from .ollama_provider import OllamaProvider
from .base import BaseLLMProvider

_REGISTRY = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "ollama": OllamaProvider,
}

def get_provider() -> BaseLLMProvider:
    """
    Single place in the codebase that knows about providers.
    Switch providers by changing one env var — zero code changes.
    """
    settings = get_settings()
    provider_class = _REGISTRY.get(settings.active_llm_provider)
    if not provider_class:
        raise ValueError(f"Unknown provider: {settings.active_llm_provider}")
    return provider_class()