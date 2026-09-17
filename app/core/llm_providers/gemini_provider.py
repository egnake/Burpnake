"""Gemini LLM provider - Free tier + Google One Pro."""

from __future__ import annotations
from typing import Optional
import google.generativeai as genai


class GeminiProvider:
    """Google Gemini provider supporting Free tier and Pro (Google One)."""

    def __init__(
        self,
        api_key: str = "",
        model: str = "gemini-2.0-flash",
        pro_enabled: bool = False,
        pro_model: str = "gemini-1.5-pro",
    ):
        self.api_key = api_key
        self.model_name = model
        self.pro_enabled = pro_enabled
        self.pro_model = pro_model
        self.name = "gemini"
        self._configured = False

    def _configure(self) -> None:
        if not self._configured and self.api_key:
            genai.configure(api_key=self.api_key)
            self._configured = True

    async def is_available(self) -> bool:
        """Check if Gemini API is configured and reachable."""
        if not self.api_key:
            return False
        try:
            self._configure()
            model = genai.GenerativeModel(self.model_name)
            response = await model.generate_content_async("test")
            return bool(response.text)
        except Exception:
            return False

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        use_pro: bool = False,
    ) -> str:
        """Send a chat completion request to Gemini."""
        self._configure()

        model_name = (
            self.pro_model if use_pro and self.pro_enabled else self.model_name
        )
        model = genai.GenerativeModel(model_name)

        # Convert messages to Gemini format
        gemini_history = []
        system_instruction = ""

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                system_instruction = content
            elif role == "user":
                gemini_history.append({"role": "user", "parts": [content]})
            elif role == "assistant":
                gemini_history.append({"role": "model", "parts": [content]})

        if system_instruction:
            model = genai.GenerativeModel(
                model_name,
                system_instruction=system_instruction,
            )

        # Build the chat or single generation
        generation_config = genai.types.GenerationConfig(
            temperature=temperature,
            max_output_tokens=8192,
        )

        try:
            if len(gemini_history) > 1:
                chat = model.start_chat(history=gemini_history[:-1])
                last_msg = gemini_history[-1]["parts"][0]
                response = await chat.send_message_async(
                    last_msg, generation_config=generation_config
                )
            else:
                prompt = (
                    gemini_history[0]["parts"][0] if gemini_history else ""
                )
                response = await model.generate_content_async(
                    prompt, generation_config=generation_config
                )

            return response.text or ""
        except Exception as e:
            # Try fallback to free model if pro failed
            if use_pro and self.model_name != model_name:
                return await self.chat(messages, temperature, use_pro=False)
            raise RuntimeError(f"Gemini error: {e}") from e

    async def generate(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.3,
        use_pro: bool = False,
    ) -> str:
        """Simple text generation."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return await self.chat(messages, temperature, use_pro=use_pro)
