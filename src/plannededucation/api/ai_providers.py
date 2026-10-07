"""
AI Provider Abstraction Layer for PlannedEducation
Supports multiple AI providers: Gemini, OpenRouter, Ollama, OpenAI-compatible endpoints
"""
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

import httpx

from . import crypto

logger = logging.getLogger(__name__)


@dataclass
class AIProviderConfig:
    """Configuration for an AI provider."""
    provider: str  # gemini, openrouter, ollama, openai
    api_key: str
    model_name: str
    base_url: Optional[str] = None


@dataclass
class AIResponse:
    """Standardized AI response."""
    content: str
    usage: Optional[dict] = None
    model: Optional[str] = None
    provider: Optional[str] = None
    error: Optional[str] = None


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    def __init__(self, config: AIProviderConfig):
        self.config = config
        self.client = httpx.AsyncClient(timeout=60.0)

    @abstractmethod
    async def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> AIResponse:
        """Generate a response from the AI provider."""
        pass

    @abstractmethod
    async def generate_structured(self, prompt: str, schema: dict, system_prompt: Optional[str] = None, **kwargs) -> AIResponse:
        """Generate a structured response (JSON) from the AI provider."""
        pass

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


class GeminiProvider(AIProvider):
    """Google Gemini API provider."""

    async def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> AIResponse:
        url = f"{self.config.base_url or 'https://generativelanguage.googleapis.com'}/v1beta/models/{self.config.model_name}:generateContent"
        params = {"key": self.config.api_key}

        contents = []
        if system_prompt:
            contents.append({"role": "user", "parts": [{"text": system_prompt}]})
            contents.append({"role": "model", "parts": [{"text": "Understood. I'll follow those instructions."}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": kwargs.get("temperature", 0.7),
                "maxOutputTokens": kwargs.get("max_tokens", 4096),
                "topP": kwargs.get("top_p", 0.95),
                "topK": kwargs.get("top_k", 40),
            }
        }

        try:
            response = await self.client.post(url, params=params, json=payload)
            response.raise_for_status()
            data = response.json()

            if "candidates" in data and data["candidates"]:
                content = data["candidates"][0]["content"]["parts"][0]["text"]
                usage = data.get("usageMetadata", {})
                return AIResponse(
                    content=content,
                    usage=usage,
                    model=self.config.model_name,
                    provider="gemini"
                )
            else:
                return AIResponse(content="", error="No candidates in response", provider="gemini")
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return AIResponse(content="", error=str(e), provider="gemini")

    async def generate_structured(self, prompt: str, schema: dict, system_prompt: Optional[str] = None, **kwargs) -> AIResponse:
        # Add JSON schema instruction to prompt
        structured_prompt = f"{prompt}\n\nRespond ONLY with valid JSON matching this schema:\n{json.dumps(schema, indent=2)}"
        return await self.generate(structured_prompt, system_prompt, **kwargs)


class OpenRouterProvider(AIProvider):
    """OpenRouter API provider (supports multiple models)."""

    async def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> AIResponse:
        url = f"{self.config.base_url or 'https://openrouter.ai/api'}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://plannededucation.org",
            "X-Title": "PlannedEducation",
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.config.model_name,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 4096),
            "top_p": kwargs.get("top_p", 0.95),
        }

        try:
            response = await self.client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            if "choices" in data and data["choices"]:
                content = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                return AIResponse(
                    content=content,
                    usage=usage,
                    model=self.config.model_name,
                    provider="openrouter"
                )
            else:
                return AIResponse(content="", error="No choices in response", provider="openrouter")
        except Exception as e:
            logger.error(f"OpenRouter API error: {e}")
            return AIResponse(content="", error=str(e), provider="openrouter")

    async def generate_structured(self, prompt: str, schema: dict, system_prompt: Optional[str] = None, **kwargs) -> AIResponse:
        structured_prompt = f"{prompt}\n\nRespond ONLY with valid JSON matching this schema:\n{json.dumps(schema, indent=2)}"
        return await self.generate(structured_prompt, system_prompt, **kwargs)


class OllamaProvider(AIProvider):
    """Ollama local API provider."""

    async def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> AIResponse:
        url = f"{self.config.base_url or 'http://localhost:11434'}/api/generate"

        full_prompt = prompt
        if system_prompt:
            full_prompt = f"System: {system_prompt}\n\nUser: {prompt}"

        payload = {
            "model": self.config.model_name,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", 0.7),
                "num_predict": kwargs.get("max_tokens", 4096),
                "top_p": kwargs.get("top_p", 0.95),
            }
        }

        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

            content = data.get("response", "")
            return AIResponse(
                content=content,
                usage={"prompt_tokens": data.get("prompt_eval_count", 0), "completion_tokens": data.get("eval_count", 0)},
                model=self.config.model_name,
                provider="ollama"
            )
        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            return AIResponse(content="", error=str(e), provider="ollama")

    async def generate_structured(self, prompt: str, schema: dict, system_prompt: Optional[str] = None, **kwargs) -> AIResponse:
        structured_prompt = f"{prompt}\n\nRespond ONLY with valid JSON matching this schema:\n{json.dumps(schema, indent=2)}"
        return await self.generate(structured_prompt, system_prompt, **kwargs)


class OpenAICompatibleProvider(AIProvider):
    """Generic OpenAI-compatible API provider."""

    async def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> AIResponse:
        url = f"{self.config.base_url or 'https://api.openai.com'}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.config.model_name,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 4096),
            "top_p": kwargs.get("top_p", 0.95),
        }

        try:
            response = await self.client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            if "choices" in data and data["choices"]:
                content = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                return AIResponse(
                    content=content,
                    usage=usage,
                    model=self.config.model_name,
                    provider="openai-compatible"
                )
            else:
                return AIResponse(content="", error="No choices in response", provider="openai-compatible")
        except Exception as e:
            logger.error(f"OpenAI-compatible API error: {e}")
            return AIResponse(content="", error=str(e), provider="openai-compatible")

    async def generate_structured(self, prompt: str, schema: dict, system_prompt: Optional[str] = None, **kwargs) -> AIResponse:
        structured_prompt = f"{prompt}\n\nRespond ONLY with valid JSON matching this schema:\n{json.dumps(schema, indent=2)}"
        return await self.generate(structured_prompt, system_prompt, **kwargs)


def get_ai_provider(config: AIProviderConfig) -> AIProvider:
    """Factory function to get the appropriate AI provider."""
    providers = {
        "gemini": GeminiProvider,
        "openrouter": OpenRouterProvider,
        "ollama": OllamaProvider,
        "openai": OpenAICompatibleProvider,
    }

    provider_class = providers.get(config.provider.lower())
    if not provider_class:
        raise ValueError(f"Unsupported AI provider: {config.provider}")

    return provider_class(config)


async def get_teacher_ai_provider(user, db) -> Optional[AIProvider]:
    """Get AI provider configured for a teacher."""
    if not user.ai_api_key_encrypted:
        return None

    try:
        api_key = crypto.decrypt_api_key(user.ai_api_key_encrypted)
        config = AIProviderConfig(
            provider=user.ai_provider or "gemini",
            api_key=api_key,
            model_name=user.ai_model_name or "gemini-2.5-flash",
            base_url=user.ai_base_url,
        )
        return get_ai_provider(config)
    except Exception as e:
        logger.error(f"Failed to create AI provider for user {user.id}: {e}")
        return None