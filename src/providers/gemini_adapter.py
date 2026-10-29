from __future__ import annotations

from src.providers.openai_adapter import OpenAIProvider


class GeminiProvider(OpenAIProvider):
    """Opt-in Gemini adapter using Google's OpenAI-compatible endpoint (needs the [openai] extra)."""

    name = "gemini"
    api_key_env = "GEMINI_API_KEY"
    base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
    default_model = "gemini-2.5-flash"
