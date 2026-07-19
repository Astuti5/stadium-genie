"""
ai_assistant.py
----------------
Thin, testable wrapper around the GenAI call. Responsible for:
  1. Grounding the model in verified stadium data (retrieval, not guessing)
  2. Enforcing a strict system prompt so the assistant stays on-task and safe
  3. Keeping the network call isolated so it can be mocked in tests
  4. Reusing a single Anthropic client (module-level, thread-safe) instead of
     constructing a new HTTPS/TLS connection pool on every request

Design choice: the prompt-building function (`build_prompt`) is pure and has
no I/O, so it is fully unit-testable without hitting the network or needing
an API key. Only `get_ai_response` touches the Anthropic client.
"""

from __future__ import annotations

import json
import os
import re
from functools import lru_cache

from anthropic import Anthropic

from exceptions import AIServiceError, InvalidInputError

MODEL_NAME = "claude-sonnet-4-6"
MAX_MESSAGE_LENGTH = 500

FAN_SYSTEM_PROMPT = """You are StadiumGenie, an official on-site assistant for FIFA World Cup 2026
stadium operations, speaking with a FAN.

Rules you must always follow:
- Only state facts that are present in the CONTEXT DATA block you are given.
  Never invent gate numbers, wait times, or locations.
- If the answer isn't in the context data, say so plainly and suggest the
  nearest Fan Info Desk.
- Keep answers short, clear, and easy to skim while walking (2-4 sentences,
  use short lists for directions/steps).
- If a message describes a medical emergency, security threat, or someone in
  danger, your FIRST sentence must direct them to alert the nearest steward
  or call the stadium emergency number, before anything else.
- Be inclusive: proactively mention accessible routes/amenities when the
  user has indicated accessibility needs.
- Never ask the user for personal data (name, card numbers, ID) you don't
  need to answer the question.
"""

OPS_SYSTEM_PROMPT = """You are StadiumGenie Ops, an assistant for FIFA World Cup 2026 tournament
operations STAFF (not the public).

Rules you must always follow:
- Only state facts present in the CONTEXT DATA block (crowd density, active
  incidents, gate status). Never invent numbers.
- Prioritize actionable, concise guidance: if crowd density at a gate is at
  or above 0.85, recommend crowd-control measures (e.g. metering entry,
  opening an alternate gate) explicitly.
- Surface unresolved high/critical severity incidents first.
- Keep responses operational and brief — staff are reading this on the move.
- Never suggest actions outside standard stadium operating procedure (e.g.
  do not suggest closing gates entirely unless a critical incident is active).
"""


def build_prompt(user_message: str, context: dict, persona: str = "fan") -> str:
    """
    Pure function: combines the user's question with a grounded JSON snapshot
    of live stadium data. No network calls here -> easy to unit test.
    """
    context_json = json.dumps(context, indent=2, default=str)
    label = "STAFF QUESTION" if persona == "ops" else "FAN QUESTION"
    return (
        f"CONTEXT DATA (verified, live):\n{context_json}\n\n"
        f"{label}:\n{user_message.strip()}\n\n"
        "Respond following the system rules."
    )


def sanitize_user_message(raw: str, max_len: int = MAX_MESSAGE_LENGTH) -> str:
    """
    Basic input hardening: type-check, strip control/non-printable characters
    (except newline/tab), collapse excessive whitespace, and enforce a length
    ceiling. This is defense-in-depth alongside server-side validation in
    app.py; it does not replace it.
    """
    if not isinstance(raw, str):
        raise InvalidInputError("Message must be a string")
    cleaned = "".join(ch for ch in raw if ch.isprintable() or ch in "\n\t")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        raise InvalidInputError("Message cannot be empty")
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len]
    return cleaned


@lru_cache(maxsize=1)
def _get_client(api_key: str) -> Anthropic:
    """
    Cache a single Anthropic client per API key. Reusing the client reuses
    its underlying HTTP connection pool instead of paying TLS handshake cost
    on every chat message — meaningful under real stadium-scale traffic.
    """
    return Anthropic(api_key=api_key)


def get_ai_response(
    user_message: str,
    context: dict,
    api_key: str | None = None,
    persona: str = "fan",
) -> str:
    """
    Calls the Anthropic API with a grounded prompt. Raises AIServiceError
    with a safe, generic message on failure (never leaks internals/keys to
    users). `persona` selects between the fan-facing and ops-facing system
    prompt so each audience gets appropriately scoped guidance.
    """
    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise AIServiceError("AI service is not configured. Please try again later.")

    clean_message = sanitize_user_message(user_message)
    prompt = build_prompt(clean_message, context, persona=persona)
    system_prompt = OPS_SYSTEM_PROMPT if persona == "ops" else FAN_SYSTEM_PROMPT

    try:
        client = _get_client(key)
        response = client.messages.create(
            model=MODEL_NAME,
            max_tokens=400,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}],
        )
        text_parts: list[str] = [block.text for block in response.content if block.type == "text"]
        return "".join(text_parts).strip()
    except Exception as exc:
        # Don't leak internal error details (security best practice) —
        # but the original exception is available in __cause__ for logging.
        raise AIServiceError(
            "The assistant is temporarily unavailable. Please ask a steward for help."
        ) from exc
