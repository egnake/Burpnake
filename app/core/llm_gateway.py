"""LLM Gateway - Multi-provider with auto-failover."""

from __future__ import annotations
import logging
from typing import Optional

from app.config import settings
from app.core.llm_providers.ollama_provider import OllamaProvider
from app.core.llm_providers.gemini_provider import GeminiProvider
from app.core.llm_providers.g4f_provider import G4FProvider

logger = logging.getLogger("burpnake.llm")


class LLMGateway:
    """
    Multi-provider LLM gateway with automatic failover.
    
    Priority: Ollama (local) → Gemini Free → g4f → Gemini Pro
    """

    def __init__(self):
        self.ollama = OllamaProvider(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
            fallback_model=settings.OLLAMA_FALLBACK_MODEL,
        )
        self.gemini = GeminiProvider(
            api_key=settings.GEMINI_API_KEY,
            model=settings.GEMINI_MODEL,
            pro_enabled=settings.GEMINI_PRO_ENABLED,
            pro_model=settings.GEMINI_PRO_MODEL,
        )
        self.g4f = G4FProvider(enabled=settings.G4F_ENABLED)
        
        self._providers = [self.ollama, self.gemini, self.g4f]
        self._last_used: Optional[str] = None

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        prefer: Optional[str] = None,
        use_pro: bool = False,
    ) -> str:
        """
        Send chat to the best available provider with auto-failover.
        
        Args:
            messages: Chat messages (system, user, assistant roles)
            temperature: Sampling temperature
            prefer: Preferred provider name ('ollama', 'gemini', 'g4f')
            use_pro: Use Gemini Pro if available (for complex analysis)
        """
        # If Gemini Pro specifically requested
        if use_pro and self.gemini.api_key and self.gemini.pro_enabled:
            try:
                result = await self.gemini.chat(messages, temperature, use_pro=True)
                self._last_used = "gemini_pro"
                return result
            except Exception as e:
                logger.warning(f"Gemini Pro failed: {e}")

        # If specific provider preferred
        if prefer:
            provider = self._get_provider(prefer)
            if provider:
                try:
                    result = await provider.chat(messages, temperature)
                    self._last_used = provider.name
                    return result
                except Exception as e:
                    logger.warning(f"Preferred provider {prefer} failed: {e}")

        # Auto-failover through providers
        errors: list[str] = []
        for provider in self._providers:
            try:
                result = await provider.chat(messages, temperature)
                self._last_used = provider.name
                logger.info(f"Response from {provider.name}")
                return result
            except Exception as e:
                errors.append(f"{provider.name}: {e}")
                logger.warning(f"Provider {provider.name} failed: {e}")
                continue

        raise RuntimeError(
            f"All LLM providers failed:\n" + "\n".join(errors)
        )

    async def generate(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.3,
        prefer: Optional[str] = None,
    ) -> str:
        """Simple generation with auto-failover."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return await self.chat(messages, temperature, prefer=prefer)

    async def check_providers(self) -> dict[str, bool]:
        """Check availability of all providers."""
        status = {}
        for provider in self._providers:
            try:
                available = await provider.is_available()
                status[provider.name] = available
            except Exception:
                status[provider.name] = False
        return status

    def _get_provider(self, name: str):
        for p in self._providers:
            if p.name == name:
                return p
        return None

    @property
    def last_used(self) -> str:
        return self._last_used or "none"

    async def close(self) -> None:
        await self.ollama.close()


# Singleton instance
llm_gateway = LLMGateway()
