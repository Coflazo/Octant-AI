"""LLM provider abstraction — 3-tier cascade: Free APIs -> Ollama -> Paid Claude."""

import asyncio
import json
import logging
import os
from typing import List, Optional, Protocol, runtime_checkable

from backend.config import get_settings

logger = logging.getLogger(__name__)


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol for LLM text generation providers."""

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        json_mode: bool = False,
    ) -> str: ...


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Protocol for text embedding providers."""

    async def embed(self, text: str) -> List[float]: ...

    @property
    def dimension(self) -> int: ...


class GroqProvider:
    """Groq free tier — llama-3.3-70b-versatile (30 req/min)."""

    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        self.api_key = api_key
        self.model = model

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        json_mode: bool = False,
    ) -> str:
        from groq import Groq

        client = Groq(api_key=self.api_key)
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 4096,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = await asyncio.to_thread(
            client.chat.completions.create, **kwargs
        )
        return response.choices[0].message.content or ""


class GeminiFreeProvider:
    """Google Gemini free tier — gemini-2.0-flash (15 req/min)."""

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        self.api_key = api_key
        self.model_name = model

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        json_mode: bool = False,
    ) -> str:
        import google.generativeai as genai

        genai.configure(api_key=self.api_key)
        gen_config = {}
        if json_mode:
            gen_config["response_mime_type"] = "application/json"

        model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=gen_config if gen_config else None,
        )
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        response = await asyncio.to_thread(model.generate_content, full_prompt)
        return response.text


class OllamaProvider:
    """Local Ollama instance — configurable model."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.2",
    ):
        self.base_url = base_url
        self.model = model

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        json_mode: bool = False,
    ) -> str:
        from ollama import Client

        client = Client(host=self.base_url)
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        kwargs = {"model": self.model, "messages": messages}
        if json_mode:
            kwargs["format"] = "json"

        response = await asyncio.to_thread(client.chat, **kwargs)
        return response["message"]["content"]


class AnthropicProvider:
    """Anthropic Claude — paid fallback."""

    def __init__(
        self, api_key: str, model: str = "claude-sonnet-4-20250514"
    ):
        self.api_key = api_key
        self.model = model

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        json_mode: bool = False,
    ) -> str:
        from anthropic import Anthropic

        client = Anthropic(api_key=self.api_key)
        messages = [{"role": "user", "content": prompt}]
        kwargs = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": messages,
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        response = await asyncio.to_thread(
            client.messages.create, **kwargs
        )
        text = response.content[0].text
        if json_mode:
            text = text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
        return text


# ── Embedding Providers ─────────────────────────────────────────


class SentenceTransformerEmbedder:
    """Local sentence-transformers embeddings (384-dim)."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self._model_name = model_name
        self._model = None

    def _load(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_name)

    async def embed(self, text: str) -> List[float]:
        self._load()
        vec = await asyncio.to_thread(self._model.encode, text)
        return vec.tolist()

    @property
    def dimension(self) -> int:
        return 384


class OllamaEmbedder:
    """Ollama-based embeddings."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "nomic-embed-text",
    ):
        self.base_url = base_url
        self.model = model

    async def embed(self, text: str) -> List[float]:
        from ollama import Client

        client = Client(host=self.base_url)
        response = await asyncio.to_thread(
            client.embeddings, model=self.model, prompt=text
        )
        return response["embedding"]

    @property
    def dimension(self) -> int:
        return 768


# ── Factory / Auto-Detection ────────────────────────────────────


def get_llm_provider(settings=None) -> LLMProvider:
    """Auto-detect the best available LLM provider.

    Cascade: GROQ_API_KEY -> GEMINI_API_KEY -> Ollama ping -> ANTHROPIC_API_KEY
    """
    if settings is None:
        settings = get_settings()

    provider_override = getattr(settings, "LLM_PROVIDER", "auto")

    if provider_override == "groq" and settings.GROQ_API_KEY:
        logger.info("LLM Provider: Groq (forced)")
        return GroqProvider(settings.GROQ_API_KEY)
    if provider_override == "gemini" and settings.GEMINI_API_KEY:
        logger.info("LLM Provider: Gemini Free (forced)")
        return GeminiFreeProvider(settings.GEMINI_API_KEY)
    if provider_override == "ollama":
        logger.info("LLM Provider: Ollama (forced)")
        base = getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434")
        model = getattr(settings, "OLLAMA_MODEL", "llama3.2")
        return OllamaProvider(base, model)
    if provider_override == "anthropic" and settings.ANTHROPIC_API_KEY:
        logger.info("LLM Provider: Anthropic Claude (forced)")
        return AnthropicProvider(settings.ANTHROPIC_API_KEY)

    # Auto-detect cascade
    if settings.GROQ_API_KEY:
        logger.info("LLM Provider: Groq (auto-detected)")
        return GroqProvider(settings.GROQ_API_KEY)

    if settings.GEMINI_API_KEY:
        logger.info("LLM Provider: Gemini Free (auto-detected)")
        return GeminiFreeProvider(settings.GEMINI_API_KEY)

    # Check Ollama availability
    try:
        import httpx
        resp = httpx.get(
            getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434")
            + "/api/tags",
            timeout=2.0,
        )
        if resp.status_code == 200:
            logger.info("LLM Provider: Ollama (auto-detected)")
            base = getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434")
            model = getattr(settings, "OLLAMA_MODEL", "llama3.2")
            return OllamaProvider(base, model)
    except Exception:
        pass

    if settings.ANTHROPIC_API_KEY:
        logger.info("LLM Provider: Anthropic Claude (auto-detected)")
        return AnthropicProvider(settings.ANTHROPIC_API_KEY)

    logger.warning("No LLM provider available — falling back to Groq stub")
    return GroqProvider("")


def get_embedding_provider(settings=None) -> EmbeddingProvider:
    """Auto-detect the best available embedding provider.

    Cascade: sentence-transformers -> Ollama embeddings
    """
    if settings is None:
        settings = get_settings()

    # Try sentence-transformers first
    try:
        from sentence_transformers import SentenceTransformer
        logger.info("Embedding Provider: sentence-transformers (local)")
        return SentenceTransformerEmbedder()
    except ImportError:
        pass

    # Try Ollama
    try:
        import httpx
        base = getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434")
        resp = httpx.get(f"{base}/api/tags", timeout=2.0)
        if resp.status_code == 200:
            logger.info("Embedding Provider: Ollama")
            return OllamaEmbedder(base)
    except Exception:
        pass

    logger.warning("No embedding provider available — embeddings will fail")
    return SentenceTransformerEmbedder()
