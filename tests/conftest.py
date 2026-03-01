from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def make_llm_response(sections: dict[str, list[str]]) -> str:
    """Build an LLM response string with ## sections and bullet items.

    Args:
        sections: mapping of section title to list of bullet strings.
            Each bullet string should NOT include the leading "- ".
    """
    parts: list[str] = []
    for title, items in sections.items():
        parts.append(f"## {title}")
        for item in items:
            parts.append(f"- {item}")
        parts.append("")  # blank line between sections
    return "\n".join(parts)


@pytest.fixture()
def mock_anthropic():
    """Patch checker_core.anthropic.AsyncAnthropic so no real API call is made.

    Yields a helper object with:
        - set_response(text): configure what the mock returns
        - mock_client: the mock AsyncAnthropic instance
    """

    class _Helper:
        def __init__(self):
            self.response_text = ""
            self.mock_client = None

        def set_response(self, text: str):
            self.response_text = text

    helper = _Helper()

    with patch("checker_core.anthropic.AsyncAnthropic") as MockCls:
        mock_instance = MagicMock()
        MockCls.return_value = mock_instance

        # message.content[0].text
        content_block = MagicMock()
        content_block.text = ""  # default; updated via property

        mock_message = MagicMock()
        mock_message.content = [content_block]

        mock_instance.messages.create = AsyncMock(return_value=mock_message)

        # Wire up set_response so it updates the content block text
        original_set = helper.set_response

        def _set_response(text: str):
            original_set(text)
            content_block.text = text

        helper.set_response = _set_response
        helper.mock_client = mock_instance

        yield helper


@pytest.fixture()
def mock_yandex_gpt():
    """Patch checker_core._call_yandex_gpt so no real API call is made.

    Yields a helper object with:
        - set_response(text): configure what the mock returns
    """

    class _Helper:
        def __init__(self):
            self.response_text = ""
            self._mock = AsyncMock(return_value="")

        def set_response(self, text: str):
            self.response_text = text
            self._mock.return_value = text

    helper = _Helper()

    with patch("checker_core._call_yandex_gpt", helper._mock):
        yield helper
