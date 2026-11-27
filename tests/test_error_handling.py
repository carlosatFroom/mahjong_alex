import asyncio
import logging
import os
import sys
from unittest.mock import MagicMock, patch

import pytest
import requests
from fastapi import HTTPException

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main  # noqa: E402


def _ok_response(payload):
    resp = MagicMock()
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None
    return resp


def test_list_models_uses_timeout():
    with patch("main.requests.get", return_value=_ok_response({"models": []})) as mock_get:
        result = asyncio.run(main.health_check())
    assert result["status"] == "healthy"
    assert mock_get.call_args.kwargs.get("timeout") == main.OLLAMA_LIST_TIMEOUT


def test_chat_uses_timeout():
    payload = {"message": {"content": "Discard the 9 bamboo."}, "model": main.OLLAMA_MODEL}
    with patch("main.requests.post", return_value=_ok_response(payload)) as mock_post:
        result = asyncio.run(main.chat_with_ai(message="What should I discard?", image=None))
    assert result["response"] == "Discard the 9 bamboo."
    assert mock_post.call_args.kwargs.get("timeout") == main.OLLAMA_CHAT_TIMEOUT


def test_chat_error_is_logged(caplog):
    with patch("main.requests.post", side_effect=requests.exceptions.ConnectionError("down")) as mock_post:
        with caplog.at_level(logging.ERROR, logger="main"):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(main.chat_with_ai(message="hi", image=None))
    assert exc_info.value.status_code == 500
    assert "timeout" in mock_post.call_args.kwargs
    assert any(r.levelno == logging.ERROR and r.exc_info for r in caplog.records)


def test_models_error_is_logged(caplog):
    with patch("main.requests.get", side_effect=requests.exceptions.Timeout("slow")) as mock_get:
        with caplog.at_level(logging.ERROR, logger="main"):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(main.get_models())
    assert exc_info.value.status_code == 500
    assert "timeout" in mock_get.call_args.kwargs
    assert any(r.levelno == logging.ERROR and r.exc_info for r in caplog.records)


def test_health_check_logs_when_ollama_down(caplog):
    with patch("main.requests.get", side_effect=requests.exceptions.ConnectionError("down")):
        with caplog.at_level(logging.ERROR, logger="main"):
            result = asyncio.run(main.health_check())
    assert result["status"] == "unhealthy"
    assert any("Health check failed" in r.getMessage() for r in caplog.records)
