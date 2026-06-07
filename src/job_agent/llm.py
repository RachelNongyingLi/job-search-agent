from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol


class LLMProviderError(RuntimeError):
    """Raised when an optional LLM provider cannot return a usable response."""


@dataclass(frozen=True)
class LLMResponse:
    text: str
    provider: str
    model: str


class LLMClient(Protocol):
    provider: str
    model: str

    def generate(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.1,
        max_tokens: int = 900,
    ) -> LLMResponse:
        ...


class MockLLMClient:
    provider = "mock"

    def __init__(self, model: str = "mock-local") -> None:
        self.model = model

    def generate(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.1,
        max_tokens: int = 900,
    ) -> LLMResponse:
        del prompt, system, temperature, max_tokens
        text = """# LLM CV Draft Plan

## Safe Emphasis

- Reorder existing evidence so matched Python, LLM, workflow, and documentation items appear first.
- Keep final LaTeX CV output exactly one page after any later CV build.

## Evidence Discipline

- Use only claims that appear in the local report or profile evidence.
- Keep learnable gaps in interview prep instead of presenting them as mastered skills.

## Do Not Claim

- Do not invent deployment, leadership, metrics, work authorization, language fluency, or eligibility proof.
"""
        return LLMResponse(text=text, provider=self.provider, model=self.model)


class OpenAICompatibleClient:
    provider = "openai-compatible"

    def __init__(
        self,
        model: str,
        base_url: str = "",
        api_key: str = "",
        timeout_s: int = 60,
    ) -> None:
        if not model:
            raise ValueError("An LLM model is required for openai-compatible provider.")
        self.model = model
        self.base_url = base_url or os.environ.get("JOB_AGENT_LLM_BASE_URL", "http://localhost:11434/v1")
        self.api_key = api_key
        self.timeout_s = timeout_s

    def generate(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.1,
        max_tokens: int = 900,
    ) -> LLMResponse:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = urllib.request.Request(self._endpoint(), data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
                response_body = response.read().decode("utf-8")
        except urllib.error.URLError as exc:
            raise LLMProviderError(f"LLM provider request failed: {exc}") from exc
        except TimeoutError as exc:
            raise LLMProviderError("LLM provider request timed out.") from exc

        try:
            data = json.loads(response_body)
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise LLMProviderError("LLM provider returned an unsupported chat-completions response.") from exc
        if not isinstance(text, str) or not text.strip():
            raise LLMProviderError("LLM provider returned an empty response.")
        return LLMResponse(text=text.strip() + "\n", provider=self.provider, model=self.model)

    def _endpoint(self) -> str:
        endpoint = self.base_url.rstrip("/")
        if endpoint.endswith("/chat/completions"):
            return endpoint
        return f"{endpoint}/chat/completions"


def build_llm_client(
    provider: str = "none",
    model: str = "",
    base_url: str = "",
    api_key_env: str = "OPENAI_API_KEY",
) -> LLMClient | None:
    provider = (provider or "none").strip().lower()
    if provider == "none":
        return None
    if provider == "mock":
        return MockLLMClient(model or "mock-local")
    if provider == "openai-compatible":
        api_key = os.environ.get(api_key_env, "") if api_key_env else ""
        return OpenAICompatibleClient(model=model, base_url=base_url, api_key=api_key)
    raise ValueError(f"Unsupported LLM provider: {provider}")
