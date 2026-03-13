"""
LLM Provider Abstraction Layer
Supports:
  - Gemini API  via google.genai (new SDK — google-generativeai is deprecated)
  - Mock        for offline testing (no API key needed)

Switch providers by setting LLM_PROVIDER=gemini or LLM_PROVIDER=mock in .env.
"""
import os
import random
from abc import ABC, abstractmethod
from dotenv import load_dotenv

load_dotenv()


class LLMClient(ABC):
    """Abstract base for all LLM provider clients."""

    @abstractmethod
    def judge(self, system_prompt: str, user_prompt: str) -> str:
        """Call the LLM and return raw text response."""
        ...


class GeminiClient(LLMClient):
    """
    Wraps the new google.genai SDK (replaces deprecated google-generativeai).
    Install: pip install google-genai
    """

    def __init__(self, client, model_name: str):
        self._client = client
        self._model_name = model_name

    def judge(self, system_prompt: str, user_prompt: str) -> str:
        from google.genai import types
        response = self._client.models.generate_content(
            model=self._model_name,
            contents=f"{system_prompt}\n\n{user_prompt}",
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
            ),
        )
        return response.text


class MockClient(LLMClient):
    """Deterministic mock for testing without API keys."""

    def judge(self, system_prompt: str, user_prompt: str) -> str:
        score = round(random.uniform(2.5, 4.5), 1)
        r = round(score + random.uniform(-0.3, 0.3), 1)
        p = round(score + random.uniform(-0.3, 0.3), 1)
        i = round(score + random.uniform(-0.3, 0.3), 1)
        return (
            f'{{"resistance": {max(1.0,min(5.0,r))}, '
            f'"policy_compliance": {max(1.0,min(5.0,p))}, '
            f'"information_protection": {max(1.0,min(5.0,i))}}}'
        )


def get_llm_client() -> LLMClient:
    """
    Factory: reads LLM_PROVIDER from .env and returns the correct client.
    Supported: 'gemini', 'mock'
    """
    provider = os.getenv("LLM_PROVIDER", "mock").lower()

    if provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set in .env")
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            return GeminiClient(client, model_name)
        except ImportError:
            raise ImportError(
                "google-genai not installed. Run: pip install google-genai"
            )

    elif provider == "mock":
        return MockClient()

    raise ValueError(
        f"Unknown LLM_PROVIDER='{provider}'. Choose 'gemini' or 'mock'."
    )


def get_provider_info() -> dict:
    """Return display info about the active provider (for dashboard sidebar)."""
    provider = os.getenv("LLM_PROVIDER", "mock").lower()
    info = {
        "gemini": {
            "name": "Google Gemini",
            "model": os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
            "icon": "G",
        },
        "mock": {
            "name": "Mock (offline testing)",
            "model": "MockClient",
            "icon": "M",
        },
    }
    return info.get(provider, {"name": provider, "model": "unknown", "icon": "?"})
