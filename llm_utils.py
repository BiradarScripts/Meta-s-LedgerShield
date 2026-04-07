from __future__ import annotations

import json
import re
from typing import Any


_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(\{.*\})\s*```", re.IGNORECASE | re.DOTALL)


def parse_json_dict(content: Any) -> dict[str, Any]:
    text = str(content or "").strip()
    if not text:
        return {}

    candidates: list[str] = [text]
    block_match = _JSON_BLOCK_RE.search(text)
    if block_match:
        candidates.insert(0, block_match.group(1).strip())

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and start < end:
        candidates.append(text[start : end + 1].strip())

    seen: set[str] = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return {}


def create_json_chat_completion(
    client: Any,
    *,
    model: str,
    messages: list[dict[str, str]],
    temperature: float,
    max_output_tokens: int,
    api_base_url: str,
) -> Any:
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if "openai.com" in str(api_base_url or "").lower():
        kwargs["response_format"] = {"type": "json_object"}

    last_exc: Exception | None = None
    for token_key in ("max_completion_tokens", "max_tokens"):
        try:
            return client.chat.completions.create(
                **kwargs,
                **{token_key: max(1, int(max_output_tokens))},
            )
        except TypeError as exc:
            last_exc = exc
            continue
        except Exception as exc:  # noqa: BLE001
            message = str(exc).lower()
            if "response_format" in kwargs and any(
                fragment in message
                for fragment in (
                    "response_format",
                    "json_schema",
                    "json_object",
                    "extra inputs are not permitted",
                )
            ):
                last_exc = exc
                kwargs = dict(kwargs)
                kwargs.pop("response_format", None)
                continue
            if token_key == "max_completion_tokens" and any(
                fragment in message
                for fragment in (
                    "max_completion_tokens",
                    "unexpected keyword",
                    "unknown parameter",
                    "unsupported",
                )
            ):
                last_exc = exc
                continue
            raise

    if last_exc is not None:
        raise last_exc
    raise RuntimeError("Failed to create JSON chat completion.")
