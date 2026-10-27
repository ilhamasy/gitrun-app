"""
OpenAI-compatible LLM client for 9router / standard gateways.
Supports JSON mode, chat completions, streaming SSE, and fallback mechanisms.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, AsyncIterator, Dict, List, Optional
import httpx


class LLMClient:
    def __init__(
        self,
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_base = (
            api_base
            or os.environ.get("ROUTER_API_BASE")
            or os.environ.get("OPENAI_BASE_URL")
            or "https://api.openai.com/v1"
        ).rstrip("/")
        self.api_key = (
            api_key
            or os.environ.get("ROUTER_API_KEY")
            or os.environ.get("OPENAI_API_KEY")
            or ""
        )
        self.model = (
            model
            or os.environ.get("ROUTER_MODEL")
            or os.environ.get("OPENAI_MODEL")
            or "gpt-4o-mini"
        )

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    async def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.2,
    ) -> str:
        """Execute a non-streaming chat completion."""
        if not self.is_configured():
            raise RuntimeError("LLM API key is not configured")

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            text = resp.text.strip()
            if text.startswith("data:") or "text/event-stream" in resp.headers.get("content-type", ""):
                collected = []
                for line in text.split("\n"):
                    line = line.strip()
                    if line.startswith("data: "):
                        raw_data = line[len("data: ") :].strip()
                        if raw_data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(raw_data)
                            delta = chunk["choices"][0].get("delta", {})
                            content = delta.get("content")
                            if content:
                                collected.append(content)
                            msg = chunk["choices"][0].get("message", {})
                            if msg and msg.get("content"):
                                collected.append(msg["content"])
                        except Exception:
                            continue
                if collected:
                    return "".join(collected)
            data = resp.json()
            return data["choices"][0]["message"]["content"]
    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        temperature: float = 0.2,
    ) -> AsyncIterator[str]:
        """Stream response tokens from LLM chat completions endpoint."""
        if not self.is_configured():
            raise RuntimeError("LLM API key is not configured")

        full_messages = []
        if system:
            full_messages.append({"role": "system", "content": system})
        full_messages.extend(messages)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": full_messages,
            "temperature": temperature,
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    if line.startswith("data: "):
                        raw_data = line[len("data: ") :].strip()
                        if raw_data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(raw_data)
                            delta = chunk["choices"][0].get("delta", {})
                            content = delta.get("content")
                            if content:
                                yield content
                        except Exception:
                            continue


def fallback_summarize(title: str, content: str) -> str:
    """
    High-precision deterministic extractive summarizer when LLM is offline.
    Extracts the first 1-2 informative sentences or key bullet items.
    """
    clean_lines = []
    for line in content.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Remove code blocks or tables
        if line.startswith("```") or line.startswith("|"):
            continue
        # Clean markdown bold/links
        clean = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", line)
        clean = re.sub(r"[*_`]", "", clean)
        clean_lines.append(clean)

    if not clean_lines:
        return f"Covers {title} implementation details and configuration specifications."

    text = " ".join(clean_lines)
    # Split into sentences
    sentences = re.split(r"(?<=[.!?])\s+", text)
    selected = []
    for s in sentences:
        s = s.strip()
        if len(s) > 15:
            selected.append(s)
        if len(selected) >= 2:
            break

    if selected:
        res = " ".join(selected)
        if not res.endswith("."):
            res += "."
        return res

    return f"Details and specifications for {title}."
