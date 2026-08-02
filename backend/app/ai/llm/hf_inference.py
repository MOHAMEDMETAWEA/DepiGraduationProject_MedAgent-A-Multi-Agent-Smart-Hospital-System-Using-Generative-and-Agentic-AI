"""HuggingFace Inference API provider."""

import asyncio
import json
from collections.abc import AsyncGenerator
from contextlib import suppress
from typing import Any

import httpx

from app.ai.llm.base import LLMProvider


class HfInferenceProvider(LLMProvider):
    """LLM provider for HuggingFace Inference API / TGI (Text Generation Inference)."""

    def __init__(
        self,
        #   "https://api-inference.huggingface.co/models/Qwen/Qwen2.5-7B-Instruct"
        base_url: str,
        api_key: str,
        model: str = "",
        timeout: float = 60.0,
        max_retries: int = 3,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _build_prompt(self, messages: list[dict[str, str]]) -> str:

        parts = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            parts.append(f"<|im_start|>{role}\n{content}<|im_end|>")

        parts.append("<|im_start|>assistant\n")
        return "\n".join(parts)

    async def _request(
        self,
        payload: dict,
        stream: bool = False,
    ) -> httpx.Response:
        """POST to HF endpoint with retry."""
        last_exc = None
        for attempt in range(self.max_retries):
            try:
                timeout = httpx.Timeout(
                    self.timeout,
                    read=None if stream else self.timeout,
                )
                client = httpx.AsyncClient(timeout=timeout)
                response = await client.post(
                    self.base_url,
                    headers=self._headers(),
                    json=payload,
                )
                if not stream:
                    await client.aclose()
                return response
            except httpx.HTTPStatusError as e:
                await client.aclose()
                if e.response.status_code in (429, 503) and attempt < self.max_retries - 1:
                    wait = 2**attempt
                    await asyncio.sleep(wait)
                    last_exc = e
                    continue
                raise
            except (httpx.ConnectError, httpx.ReadError) as e:
                await client.aclose()
                if attempt < self.max_retries - 1:
                    wait = 2**attempt
                    await asyncio.sleep(wait)
                    last_exc = e
                    continue
                raise
        raise last_exc  # type: ignore

    async def generate(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        """Non-streaming generation via HF Inference API."""
        prompt = self._build_prompt(messages)

        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": max_tokens,
                "temperature": temperature,
                "return_full_text": False,
            },
        }

        response = await self._request(payload, stream=False)
        data = response.json()

        content = ""
        if isinstance(data, list) and len(data) > 0:
            content = data[0].get("generated_text", "")
        elif isinstance(data, dict):
            content = data.get("generated_text", "")

        return {
            "content": content,
            "tool_calls": [],
            "usage": {},
        }

    async def generate_stream(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream tokens via HF Inference API (SSE)."""
        prompt = self._build_prompt(messages)

        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": max_tokens,
                "temperature": temperature,
                "return_full_text": False,
            },
        }

        response = await self._request(payload, stream=True)

        async for line in response.aiter_lines():
            if not line.startswith("data: "):
                continue

            raw = line[6:]
            if not raw.strip():
                continue

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue

            if "token" in data and "text" in data["token"]:
                token_text = data["token"]["text"]
                if token_text:
                    yield {"type": "token", "content": token_text}
            elif "generated_text" in data:
                pass

        yield {"type": "done", "usage": {}}

        with suppress(AttributeError, Exception):
            await response.aclose()
