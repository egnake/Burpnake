"""g4f LLM provider - Free cloud backup."""

from __future__ import annotations
from typing import Optional


DEFAULT_PROVIDER = "Yqcloud"
DEFAULT_MODEL = "gpt-4o-mini"

FALLBACK_PROVIDERS = ["Yqcloud", "PollinationsAI", "TeachAnything", "GLM"]


class G4FProvider:
    """g4f (GPT4Free) provider as backup LLM."""

    def __init__(self, enabled: bool = True, provider: str = DEFAULT_PROVIDER,
                 model: str = DEFAULT_MODEL):
        self.enabled = enabled
        self.name = "g4f"
        self.provider = provider
        self.model = model
        self._client = None

    def _get_client(self, provider: str | None = None):
        from g4f.client import Client
        return Client(provider=provider or self.provider)

    async def is_available(self) -> bool:
        """Check if g4f is importable and working."""
        if not self.enabled:
            return False
        try:
            import asyncio
            return await asyncio.to_thread(self._sync_is_available)
        except Exception:
            return False

    def _sync_is_available(self) -> bool:
        for provider in [self.provider, *FALLBACK_PROVIDERS]:
            try:
                client = self._get_client(provider)
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": "ping"}],
                )
                if response.choices[0].message.content:
                    self.provider = provider
                    return True
            except Exception:
                continue
        return False

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        model: Optional[str] = None,
    ) -> str:
        """Send a chat completion via g4f."""
        try:
            import asyncio
            result = await asyncio.to_thread(self._sync_chat, messages, temperature, model)
            return result
        except Exception as e:
            raise RuntimeError(f"g4f error: {e}") from e

    def _sync_chat(self, messages, temperature=0.3, model=None):
        last_error: Exception | None = None
        for provider in [self.provider, *FALLBACK_PROVIDERS]:
            try:
                client = self._get_client(provider)
                response = client.chat.completions.create(
                    model=model or self.model,
                    messages=messages,
                )
                content = response.choices[0].message.content
                if content:
                    self.provider = provider
                    return content
            except Exception as e:
                last_error = e
                continue
        raise last_error or RuntimeError("g4f returned empty response")

    async def generate(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.3,
    ) -> str:
        """Simple text generation."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return await self.chat(messages, temperature)
