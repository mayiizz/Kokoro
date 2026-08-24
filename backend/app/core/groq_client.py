import os
import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from groq import APIStatusError, Groq, RateLimitError

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

_client: Optional[Groq] = None
logger = logging.getLogger(__name__)

# llama-3.1-8b-instant was decommissioned for free/developer tiers on 2026-08-16.
DEFAULT_MODEL = "openai/gpt-oss-20b"
MAX_RETRIES = 5


def groq_model() -> str:
    return os.getenv("GROQ_MODEL") or DEFAULT_MODEL


def get_client() -> Groq:
    global _client
    if _client is None:
        key = os.getenv("GROQ_API_KEY")
        if not key:
            raise ValueError("GROQ_API_KEY environment variable is not set")
        _client = Groq(api_key=key)
    return _client


def _extract_json(text: str) -> Dict[str, Any]:
    raw = (text or "").strip()
    if not raw:
        raise ValueError("Empty response from Groq")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
        if fence:
            return json.loads(fence.group(1).strip())
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            return json.loads(raw[start : end + 1])
        raise


def _retry_wait_seconds(exc: Exception, attempt: int) -> float:
    match = re.search(r"try again in ([\d.]+)s", str(exc), re.I)
    if match:
        return min(20.0, float(match.group(1)) + 0.35)
    return min(20.0, 1.5 * (2 ** attempt))


def _is_rate_limit(exc: Exception) -> bool:
    if isinstance(exc, RateLimitError):
        return True
    if isinstance(exc, APIStatusError) and getattr(exc, "status_code", None) == 429:
        return True
    text = str(exc).lower()
    return "429" in text or "rate_limit" in text


def _is_truncated_json(exc: Exception) -> bool:
    text = str(exc).lower()
    return "json_validate_failed" in text or "max completion tokens" in text or "failed_generation" in text


def _create(
    messages: List[Dict[str, Any]],
    *,
    model: str,
    temperature: float,
    response_format=None,
    max_tokens: Optional[int] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    tool_choice: Optional[Any] = None,
):
    kwargs: Dict[str, Any] = {
        "messages": messages,
        "model": model,
        "temperature": temperature,
    }
    if response_format is not None:
        kwargs["response_format"] = response_format
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    if tools:
        kwargs["tools"] = tools
    if tool_choice is not None:
        kwargs["tool_choice"] = tool_choice
    last_error: Optional[Exception] = None
    for attempt in range(MAX_RETRIES):
        try:
            return get_client().chat.completions.create(**kwargs)
        except Exception as exc:
            last_error = exc
            if _is_truncated_json(exc) and kwargs.get("max_tokens") is not None:
                logger.warning("Groq JSON truncated at max_tokens=%s; retrying without a cap", kwargs.get("max_tokens"))
                kwargs.pop("max_tokens", None)
                continue
            if not _is_rate_limit(exc) or attempt == MAX_RETRIES - 1:
                raise
            wait = _retry_wait_seconds(exc, attempt)
            logger.warning("Groq rate limit (attempt %s/%s); waiting %.2fs", attempt + 1, MAX_RETRIES, wait)
            time.sleep(wait)
    raise last_error or RuntimeError("Groq request failed")


def get_groq_response(prompt: str, model: Optional[str] = None, max_tokens: Optional[int] = None) -> Dict[str, Any]:
    """Send a prompt to Groq and return parsed JSON."""
    chosen = model or groq_model()
    completion = _create(
        [
            {
                "role": "system",
                "content": "You are a helpful assistant that outputs only valid JSON. Keep answers compact.",
            },
            {"role": "user", "content": prompt},
        ],
        model=chosen,
        temperature=0,
        response_format={"type": "json_object"},
        max_tokens=max_tokens,
    )
    response_content = completion.choices[0].message.content
    if not response_content:
        raise ValueError("Empty response from Groq")
    try:
        return _extract_json(response_content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON response from Groq: {e}") from e


def get_groq_chat(messages: List[Dict[str, str]], model: Optional[str] = None) -> str:
    """Conversational completion without forcing JSON."""
    chosen = model or groq_model()
    completion = _create(messages, model=chosen, temperature=0.3)
    content = completion.choices[0].message.content
    if not content:
        raise ValueError("Empty response from Groq")
    return content


def get_groq_with_tools(
    messages: List[Dict[str, Any]],
    tools: List[Dict[str, Any]],
    model: Optional[str] = None,
):
    """One chat turn that may return tool calls. Raises if the model rejects tools."""
    chosen = model or groq_model()
    completion = _create(messages, model=chosen, temperature=0, tools=tools, tool_choice="auto")
    return completion.choices[0].message
