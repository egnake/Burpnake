"""g4f LLM provider - Free cloud backup."""

from __future__ import annotations
from typing import Optional


class G4FProvider:
    """g4f (GPT4Free) provider as backup LLM."""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.name = "g4f"
        self._client = None

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
        from g4f.client import Client
        client = Client()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "ping"}],
        )
        return bool(response.choices[0].message.content)

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
        from g4f.client import Client
        client = Client()
        response = client.chat.completions.create(
            model=model or "gpt-4o-mini",
            messages=messages,
        )
        return response.choices[0].message.content or ""

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
