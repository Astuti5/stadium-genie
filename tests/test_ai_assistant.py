import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ai_assistant import build_prompt, get_ai_response, sanitize_user_message
from exceptions import AIServiceError, InvalidInputError


def test_sanitize_strips_and_truncates():
    assert sanitize_user_message("  hello  ") == "hello"
    long_input = "a" * 1000
    assert len(sanitize_user_message(long_input, max_len=50)) == 50


def test_sanitize_collapses_whitespace():
    assert sanitize_user_message("hello    world\n\n") == "hello world"


def test_sanitize_rejects_empty():
    with pytest.raises(InvalidInputError):
        sanitize_user_message("   ")


def test_sanitize_rejects_non_string():
    with pytest.raises(InvalidInputError):
        sanitize_user_message(12345)


def test_build_prompt_includes_context_and_question():
    context = {"nearest_gate": {"code": "A"}}
    prompt = build_prompt("Where is the restroom?", context)
    assert "Where is the restroom?" in prompt
    assert '"code": "A"' in prompt


def test_get_ai_response_without_api_key_raises():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(AIServiceError, match="not configured"):
            get_ai_response("hello", {}, api_key=None)


def test_get_ai_response_success_mocked():
    import ai_assistant

    ai_assistant._get_client.cache_clear()

    mock_block = MagicMock()
    mock_block.type = "text"
    mock_block.text = "The nearest restroom is 20 meters away."

    mock_response = MagicMock()
    mock_response.content = [mock_block]

    with patch("ai_assistant.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = mock_response
        reply = get_ai_response(
            "Where's the restroom?", {"nearest_gate": {"code": "A"}}, api_key="test-key-1"
        )

    assert "restroom" in reply.lower()


def test_get_ai_response_uses_ops_persona():
    import ai_assistant

    ai_assistant._get_client.cache_clear()

    mock_block = MagicMock()
    mock_block.type = "text"
    mock_block.text = "Gate C at 91% — recommend metering entry."

    mock_response = MagicMock()
    mock_response.content = [mock_block]

    with patch("ai_assistant.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = mock_response
        reply = get_ai_response("Status?", {"gate": "C"}, api_key="test-key-2", persona="ops")

    call_kwargs = MockClient.return_value.messages.create.call_args.kwargs
    assert "STAFF" in call_kwargs["system"] or "staff" in call_kwargs["system"].lower()
    assert "metering" in reply.lower()


def test_get_ai_response_handles_api_failure_gracefully():
    import ai_assistant

    ai_assistant._get_client.cache_clear()

    with patch("ai_assistant.Anthropic") as MockClient:
        MockClient.return_value.messages.create.side_effect = Exception("network down")
        with pytest.raises(AIServiceError, match="temporarily unavailable"):
            get_ai_response("hello", {}, api_key="test-key-3")
