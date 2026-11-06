"""
LLM provider abstraction for the Mahjong practice coach
Groq provider for fast cloud inference
"""

import time
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict

from groq import Groq

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    @abstractmethod
    def chat(self, system: str, message: str) -> Dict[str, Any]:
        """Send a system prompt plus one user message"""


class GroqProvider(LLMProvider):
    """Groq provider for fast cloud inference"""

    def __init__(self, api_key: str, model: str):
        self.client = Groq(api_key=api_key)
        self.model = model

    def chat(self, system: str, message: str) -> Dict[str, Any]:
        start_time = time.time()
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": message},
                ],
                temperature=0.4,
                max_tokens=700,
            )
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            raise RuntimeError(f"Groq API error: {e}") from e

        usage = completion.usage
        return {
            "content": completion.choices[0].message.content,
            "model": self.model,
            "total_time": round(time.time() - start_time, 2),
            "total_tokens": usage.total_tokens if usage else 0,
        }


def get_llm_provider(provider_type: str, **kwargs) -> LLMProvider:
    """Factory function to get the Groq LLM provider"""
    if provider_type.lower() == "groq":
        api_key = kwargs.get("api_key")
        if not api_key:
            raise ValueError("Groq API key is required")
        return GroqProvider(api_key, kwargs.get("model", "openai/gpt-oss-20b"))
    raise ValueError(f"Unsupported provider: {provider_type}")
