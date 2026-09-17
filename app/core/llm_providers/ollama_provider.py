"""Ollama LLM provider - Primary (local, free, private)."""

from __future__ import annotations
import httpx
import json
from typing import AsyncIterator, Optional


class OllamaProvider:
    """Ollama local LLM provider using REST API."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen2.5-coder:14b",
        fallback_model: str = "gemma2:9b",
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.fallback_model = fallback_model
        self.name = "ollama"
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(120.0, connect=10.0),
            )
        return self._client

    async def is_available(self) -> bool:
        """Check if Ollama is running and model is available."""
        try:
            client = await self._get_client()
            resp = await client.get("/api/tags")
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                available = [m["name"] for m in models]
                return any(
                    self.model.split(":")[0] in m for m in available
                )
            return False
        except Exception:
            return False

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        model: Optional[str] = None,
    ) -> str:
        """Send a chat completion request to Ollama."""
        use_model = model or self.model
        client = await self._get_client()

        payload = {
            "model": use_model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_ctx": 8192,
            },
        }

        try:
            resp = await client.post("/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "")
        except Exception as e:
            # Try fallback model
            if use_model != self.fallback_model:
                return await self.chat(
                    messages, temperature, model=self.fallback_model
                )
            raise RuntimeError(f"Ollama error: {e}") from e

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

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
    ) -> AsyncIterator[str]:
        """Stream chat completion tokens."""
        client = await self._get_client()
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": temperature, "num_ctx": 8192},
        }

        async with client.stream("POST", "/api/chat", json=payload) as resp:
            async for line in resp.aiter_lines():
                if line.strip():
                    try:
                        data = json.loads(line)
                        token = data.get("message", {}).get("content", "")
                        if token:
                            yield token
                    except json.JSONDecodeError:
                        continue

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
