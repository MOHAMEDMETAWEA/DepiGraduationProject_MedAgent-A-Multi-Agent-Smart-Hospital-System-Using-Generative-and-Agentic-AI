import asyncio
from collections.abc import AsyncGenerator
from contextlib import suppress
from typing import Any

import httpx
import structlog

from app.ai.llm.base import LLMProvider

logger = structlog.get_logger(__name__)


class OpenAICompatProvider(LLMProvider):
    """LLM provider for any OpenAI-compatible API (vLLM, Ollama, Groq, etc.)."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float = 90.0,  # OpenRouter cloud latency
        max_retries: int = 3,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries

    def _headers(self) -> dict:
        """Build Authorization + Content-Type headers."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        body: dict,
        stream: bool = False,
    ) -> httpx.Response:
        """Send POST to /chat/completions with exponential backoff retry."""
        last_exc = None
        for attempt in range(self.max_retries):
            try:
                # For streaming, use a longer-lived client that stays open
                timeout = httpx.Timeout(self.timeout, read=None if stream else self.timeout)
                client = httpx.AsyncClient(timeout=timeout)
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._headers(),
                    json=body,
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
        """Non-streaming generation — waits for full response."""
        body = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"

        response = await self._request(body, stream=False)
        data = response.json()
        # -------------------
        # 🟢 الحماية في حالة عدم وجود الـ choices
        if "error" in data:
            err_msg = data["error"].get("message", str(data["error"]))
            logger.error("llm_generate_error", error=err_msg)
            return {"content": f"API Error: {err_msg}", "tool_calls": [], "usage": {}}

        choices = data.get("choices")
        if not choices:
            return {"content": "API Error: No choices returned.", "tool_calls": [], "usage": {}}
        # -----------------

        choice = data["choices"][0]
        message = choice["message"]
        usage = data.get("usage", {})
        logger.info("llm_generate", model=self.model, usage=usage)
        return {
            "content": message.get("content"),
            "tool_calls": message.get("tool_calls", []),
            "usage": usage,
        }

    async def generate_stream(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> AsyncGenerator[dict[str, Any], None]:

        body = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"

        response = await self._request(body, stream=True)

        # Check for non-200 responses (e.g., 402 Payment Required, 401 Unauthorized)
        if response.status_code != 200:
            try:
                err_body = response.json()
                err_msg = err_body.get("error", {}).get(
                    "message", f"API returned {response.status_code}"
                )
            except Exception:
                err_msg = f"API returned {response.status_code}"
            yield {"type": "error", "content": err_msg}
            yield {"type": "done", "usage": {}}
            with suppress(AttributeError, Exception):
                await response.aclose()
            return

        # Accumulate tool calls across streaming chunks
        pending_tool_calls: dict[int, dict] = {}

        async for line in response.aiter_lines():
            if not line.startswith("data: "):
                continue

            if line == "data: [DONE]":
                # Yield any accumulated tool calls before done
                for tc in pending_tool_calls.values():
                    yield {
                        "type": "tool_call",
                        "name": tc.get("name", ""),
                        "args": tc.get("arguments", ""),
                    }
                yield {"type": "done", "usage": {}}
                break

            import json

            # data = json.loads(line[6:])
            # ------------
            try:
                data = json.loads(line[6:])
            except json.JSONDecodeError:
                continue

            # 🟢 درع الحماية: التأكد من وجود Error من الـ API داخل الستريم
            if "error" in data:
                err_obj = data["error"]
                err_msg = err_obj.get("message", str(err_obj))
                # Groq returns ``failed_generation`` with the model's malformed
                # tool call — that's gold for debugging which tool blew up.
                failed_gen = err_obj.get("failed_generation")
                logger.error(
                    "llm_stream_error",
                    model=self.model,
                    error=err_msg,
                    failed_generation=(
                        failed_gen[:500] if isinstance(failed_gen, str) else failed_gen
                    ),
                    error_type=err_obj.get("type"),
                    error_code=err_obj.get("code"),
                )
                yield {"type": "error", "content": f"Provider API Error: {err_msg}"}
                yield {"type": "done", "usage": {}}
                break

            # 🟢 الحماية من غياب الـ choices
            choices = data.get("choices")
            if not choices:
                continue
            # ------------
            choice = data["choices"][0]

            finish = choice.get("finish_reason")
            if finish:
                for tc in pending_tool_calls.values():
                    yield {
                        "type": "tool_call",
                        "name": tc.get("name", ""),
                        "args": tc.get("arguments", ""),
                    }
                yield {"type": "done", "usage": data.get("usage", {})}
                break

            delta = choice.get("delta", {})

            if "tool_calls" in delta:
                for tc in delta["tool_calls"]:
                    idx = tc.get("index", 0)
                    if idx not in pending_tool_calls:
                        pending_tool_calls[idx] = {"name": "", "arguments": ""}
                    if "name" in tc.get("function", {}):
                        pending_tool_calls[idx]["name"] = tc["function"]["name"]
                    if "arguments" in tc.get("function", {}):
                        pending_tool_calls[idx]["arguments"] += tc["function"]["arguments"]
                continue

            content = delta.get("content", "")
            if content:
                yield {"type": "token", "content": content}

        with suppress(AttributeError, Exception):
            await response.aclose()
