import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api import app, AVAILABLE_MODELS
from tests.conftest import make_llm_response


client = TestClient(app)


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data == {"status": "ok", "version": "1.0.0"}


# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------

def test_index_returns_html():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "GrantChecker" in response.text


# ---------------------------------------------------------------------------
# GET /models
# ---------------------------------------------------------------------------

def test_models_endpoint():
    """GET /models returns expected structure with anthropic and yandex keys."""
    response = client.get("/models")
    assert response.status_code == 200
    data = response.json()
    assert "anthropic" in data
    assert "yandex" in data
    assert isinstance(data["anthropic"], list)
    assert isinstance(data["yandex"], list)
    assert "claude-sonnet-4-6" in data["anthropic"]
    assert "yandexgpt/latest" in data["yandex"]


# ---------------------------------------------------------------------------
# POST /verify
# ---------------------------------------------------------------------------

def test_verify_returns_report():
    """POST /verify with mocked Anthropic returns JSON with expected keys."""
    response_text = make_llm_response({
        "Критические ошибки": [
            '**Цитата:** "Тест" | **Проблема:** Ошибка | **Рекомендация:** Исправить'
        ],
        "Существенные замечания": [],
        "Незначительные замечания": [],
        "Подтверждённые факты": [],
        "Требует ручной проверки": [],
    })

    content_block = MagicMock()
    content_block.text = response_text

    mock_message = MagicMock()
    mock_message.content = [content_block]

    with patch("checker_core.anthropic.AsyncAnthropic") as MockCls:
        mock_instance = MagicMock()
        MockCls.return_value = mock_instance
        mock_instance.messages.create = AsyncMock(return_value=mock_message)

        response = client.post("/verify", json={"text": "Тестовый текст"})

    assert response.status_code == 200
    data = response.json()
    for key in ("critical", "significant", "minor", "confirmed", "needs_manual"):
        assert key in data


def test_verify_empty_text():
    """POST /verify with empty text should not crash with 500."""
    response_text = make_llm_response({
        "Критические ошибки": [],
        "Существенные замечания": [],
        "Незначительные замечания": [],
        "Подтверждённые факты": [],
        "Требует ручной проверки": [],
    })

    content_block = MagicMock()
    content_block.text = response_text

    mock_message = MagicMock()
    mock_message.content = [content_block]

    with patch("checker_core.anthropic.AsyncAnthropic") as MockCls:
        mock_instance = MagicMock()
        MockCls.return_value = mock_instance
        mock_instance.messages.create = AsyncMock(return_value=mock_message)

        response = client.post("/verify", json={"text": ""})

    assert response.status_code != 500


def test_verify_missing_field():
    """POST /verify without 'text' field returns 422 Unprocessable Entity."""
    response = client.post("/verify", json={"wrong_field": "data"})
    assert response.status_code == 422


def test_verify_with_explicit_provider_and_model():
    """POST /verify with explicit provider and model passes them to core."""
    response_text = make_llm_response({
        "Критические ошибки": [],
        "Существенные замечания": [],
        "Незначительные замечания": [],
        "Подтверждённые факты": [],
        "Требует ручной проверки": [],
    })

    with patch("checker_core._call_yandex_gpt", new_callable=AsyncMock) as mock_yandex:
        mock_yandex.return_value = response_text

        response = client.post("/verify", json={
            "text": "Тестовый текст",
            "provider": "yandex",
            "model": "yandexgpt/latest",
        })

    assert response.status_code == 200
    mock_yandex.assert_called_once()
    call_args = mock_yandex.call_args
    assert call_args.args[1] == "yandexgpt/latest"
