"""
AI Provider Abstraction Layer for PlannedEducation
Supports multiple AI providers: Gemini, OpenRouter, Ollama, OpenAI-compatible endpoints
"""
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx

from . import crypto

logger = logging.getLogger(__name__)


@dataclass
class AIProviderConfig:
    """Configuration for an AI provider."""
    provider: str  # gemini, openrouter, ollama, openai
    api_key: str
    model_name: str
    base_url: str | None = None


@dataclass
class AIResponse:
    """Standardized AI response."""
    content: str
    usage: dict | None = None
    model: str | None = None
    provider: str | None = None
    error: str | None = None


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    def __init__(
        self,
        config: AIProviderConfig,
        *,
        validated_ips: list[str] | None = None,
        allow_loopback: bool = False,
    ):
        self.config = config
        # F-022 residual: pin outbound connects to IPs validated at configure time
        # and re-check DNS before each request (DNS rebinding defense).
        from .url_safety import create_outbound_async_client

        if config.base_url:
            self.client = create_outbound_async_client(
                validated_ips=validated_ips,
                allow_loopback=allow_loopback,
                timeout=60.0,
            )
        else:
            # Default vendor endpoints — still never follow redirects.
            self.client = httpx.AsyncClient(timeout=60.0, follow_redirects=False)

    @abstractmethod
    async def generate(self, prompt: str, system_prompt: str | None = None, **kwargs) -> AIResponse:
        """Generate a response from the AI provider."""
        pass

    @abstractmethod
    async def generate_structured(
        self, prompt: str, schema: dict, system_prompt: str | None = None, **kwargs
    ) -> AIResponse:
        """Generate a structured response (JSON) from the AI provider."""
        pass

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


class GeminiProvider(AIProvider):
    """Google Gemini API provider."""

    async def generate(self, prompt: str, system_prompt: str | None = None, **kwargs) -> AIResponse:
        base_url = self.config.base_url or "https://generativelanguage.googleapis.com"
        url = f"{base_url}/v1beta/models/{self.config.model_name}:generateContent"
        # F-022: prefer header over query-string key to avoid proxy/access-log leakage.
        headers = {"x-goog-api-key": self.config.api_key}

        contents = []
        if system_prompt:
            contents.append({"role": "user", "parts": [{"text": system_prompt}]})
            ack = "Understood. I'll follow those instructions."
            contents.append({"role": "model", "parts": [{"text": ack}]})
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
            response = await self.client.post(url, headers=headers, json=payload)
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
                return AIResponse(
                    content="", error="No candidates in response", provider="gemini"
                )
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return AIResponse(content="", error=str(e), provider="gemini")

    async def generate_structured(
        self, prompt: str, schema: dict, system_prompt: str | None = None, **kwargs
    ) -> AIResponse:
        # Add JSON schema instruction to prompt
        schema_str = json.dumps(schema, indent=2)
        structured_prompt = (
            f"{prompt}\n\nRespond ONLY with valid JSON matching this schema:\n{schema_str}"
        )
        return await self.generate(structured_prompt, system_prompt, **kwargs)


class OpenRouterProvider(AIProvider):
    """OpenRouter API provider (supports multiple models)."""

    async def generate(self, prompt: str, system_prompt: str | None = None, **kwargs) -> AIResponse:
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
                return AIResponse(
                    content="", error="No choices in response", provider="openrouter"
                )
        except Exception as e:
            logger.error(f"OpenRouter API error: {e}")
            return AIResponse(content="", error=str(e), provider="openrouter")

    async def generate_structured(
        self, prompt: str, schema: dict, system_prompt: str | None = None, **kwargs
    ) -> AIResponse:
        schema_str = json.dumps(schema, indent=2)
        structured_prompt = (
            f"{prompt}\n\nRespond ONLY with valid JSON matching this schema:\n{schema_str}"
        )
        return await self.generate(structured_prompt, system_prompt, **kwargs)


class OllamaProvider(AIProvider):
    """Ollama local API provider."""

    async def generate(self, prompt: str, system_prompt: str | None = None, **kwargs) -> AIResponse:
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
                usage={
                    "prompt_tokens": data.get("prompt_eval_count", 0),
                    "completion_tokens": data.get("eval_count", 0),
                },
                model=self.config.model_name,
                provider="ollama"
            )
        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            return AIResponse(content="", error=str(e), provider="ollama")

    async def generate_structured(
        self, prompt: str, schema: dict, system_prompt: str | None = None, **kwargs
    ) -> AIResponse:
        schema_str = json.dumps(schema, indent=2)
        structured_prompt = (
            f"{prompt}\n\nRespond ONLY with valid JSON matching this schema:\n{schema_str}"
        )
        return await self.generate(structured_prompt, system_prompt, **kwargs)


class OpenAICompatibleProvider(AIProvider):
    """Generic OpenAI-compatible API provider."""

    async def generate(self, prompt: str, system_prompt: str | None = None, **kwargs) -> AIResponse:
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
                return AIResponse(
                    content="",
                    error="No choices in response",
                    provider="openai-compatible",
                )
        except Exception as e:
            logger.error(f"OpenAI-compatible API error: {e}")
            return AIResponse(content="", error=str(e), provider="openai-compatible")

    async def generate_structured(
        self, prompt: str, schema: dict, system_prompt: str | None = None, **kwargs
    ) -> AIResponse:
        schema_str = json.dumps(schema, indent=2)
        structured_prompt = (
            f"{prompt}\n\nRespond ONLY with valid JSON matching this schema:\n{schema_str}"
        )
        return await self.generate(structured_prompt, system_prompt, **kwargs)


class ChatGptSessionProvider(AIProvider):
    """ChatGPT account session provider via OpenAI device-code OAuth (no API key required)."""

    def __init__(self, config: AIProviderConfig, user_id: str):
        super().__init__(config)
        self.user_id = user_id

    async def generate(self, prompt: str, system_prompt: str | None = None, **kwargs) -> AIResponse:
        import time

        from ..chatgpt import client as chatgpt_client
        from ..chatgpt import models as chatgpt_models
        from ..chatgpt import oauth as chatgpt_oauth
        from ..chatgpt.token_store import clear_tokens, get_tokens, put_tokens

        tokens = get_tokens(self.user_id)
        if tokens is None:
            return AIResponse(content="", error="ChatGPT session not connected", provider="chatgpt")

        if tokens.expires_at <= time.time() + 60:
            try:
                tokens = await chatgpt_oauth.refresh_tokens(tokens.refresh_token)
                put_tokens(self.user_id, tokens)
            except Exception as e:
                clear_tokens(self.user_id)
                return AIResponse(
                    content="",
                    error=f"ChatGPT session expired: {e}",
                    provider="chatgpt",
                )

        try:
            snapshot = await chatgpt_models.get_chatgpt_options(self.user_id, tokens)
            model_candidates = chatgpt_models.model_fallback_chain(snapshot, self.config.model_name)
            reply = await chatgpt_client.create_response(
                tokens,
                message=prompt,
                instructions=(system_prompt or "").strip(),
                model=model_candidates[0],
                model_candidates=model_candidates,
            )
            return AIResponse(
                content=reply,
                usage={"prompt_tokens": len(prompt) // 4, "completion_tokens": len(reply) // 4},
                model=model_candidates[0],
                provider="chatgpt",
            )
        except Exception as e:
            logger.error(f"ChatGPT session provider error: {e}")
            return AIResponse(content="", error=str(e), provider="chatgpt")

    async def generate_structured(
        self, prompt: str, schema: dict, system_prompt: str | None = None, **kwargs
    ) -> AIResponse:
        schema_str = json.dumps(schema, indent=2)
        structured_prompt = (
            f"{prompt}\n\nRespond ONLY with valid JSON matching this schema:\n{schema_str}"
        )
        return await self.generate(structured_prompt, system_prompt, **kwargs)


def get_ai_provider(
    config: AIProviderConfig,
    *,
    validated_ips: list[str] | None = None,
    allow_loopback: bool = False,
) -> AIProvider:
    """Factory function to get the appropriate AI provider."""
    providers: dict[str, type[AIProvider]] = {
        "gemini": GeminiProvider,
        "openrouter": OpenRouterProvider,
        "ollama": OllamaProvider,
        "openai": OpenAICompatibleProvider,
    }

    provider_class = providers.get(config.provider.lower())
    if not provider_class:
        raise ValueError(f"Unsupported AI provider: {config.provider}")

    return provider_class(
        config,
        validated_ips=validated_ips,
        allow_loopback=allow_loopback,
    )


async def get_teacher_ai_provider(user, db) -> AIProvider | None:
    """Get AI provider configured for a teacher (prefers active ChatGPT session)."""
    from ..chatgpt.token_store import get_tokens

    chatgpt_tokens = get_tokens(user.id)
    if chatgpt_tokens is not None and (
        (user.ai_provider or "").lower() == "chatgpt" or not user.ai_api_key_encrypted
    ):
        config = AIProviderConfig(
            provider="chatgpt",
            api_key="",
            model_name=user.ai_model_name or "gpt-5.4-mini",
        )
        return ChatGptSessionProvider(config, user_id=user.id)

    if not user.ai_api_key_encrypted:
        return None

    try:
        from .url_safety import UnsafeURLError, validate_ai_base_url

        provider_name = user.ai_provider or "gemini"
        validated_ips: list[str] | None = None
        allow_loopback = provider_name.lower() == "ollama"
        try:
            if user.ai_base_url:
                validated = validate_ai_base_url(
                    user.ai_base_url, provider=provider_name, return_ips=True
                )
                if validated is None:
                    safe_base = None
                else:
                    safe_base, validated_ips = validated
            else:
                safe_base = None
        except UnsafeURLError:
            # F-022: fail closed — do not call an unvalidated custom endpoint with the API key.
            logger.error(
                "Rejected unsafe AI base URL for user %s (provider=%s)",
                user.id,
                provider_name,
            )
            return None

        api_key = crypto.decrypt_api_key(user.ai_api_key_encrypted)
        config = AIProviderConfig(
            provider=provider_name,
            api_key=api_key,
            model_name=user.ai_model_name or "gemini-2.5-flash",
            base_url=safe_base,
        )
        return get_ai_provider(
            config,
            validated_ips=validated_ips,
            allow_loopback=allow_loopback,
        )
    except Exception as e:
        logger.error(f"Failed to create AI provider for user {user.id}: {e}")
        return None
