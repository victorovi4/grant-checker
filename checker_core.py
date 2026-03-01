import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import anthropic
import httpx


@dataclass
class VerificationItem:
    quote: str
    issue: str
    recommendation: str


@dataclass
class VerificationReport:
    critical: list[VerificationItem] = field(default_factory=list)
    significant: list[VerificationItem] = field(default_factory=list)
    minor: list[VerificationItem] = field(default_factory=list)
    confirmed: list[VerificationItem] = field(default_factory=list)
    needs_manual: list[VerificationItem] = field(default_factory=list)
    raw_response: str = ""


STUB_SYSTEM_PROMPT = (
    "Ты — эксперт по верификации грантовых заявок российских НКО. "
    "Проанализируй текст и выдай структурированный отчёт с секциями:\n"
    "## Критические ошибки\n## Существенные замечания\n"
    "## Незначительные замечания\n## Подтверждённые факты\n"
    "## Требует ручной проверки\n\n"
    "Каждый пункт оформляй строкой вида:\n"
    '- **Цитата:** "..." | **Проблема:** ... | **Рекомендация:** ...'
)


def load_system_prompt() -> str:
    path = Path(__file__).parent / "system_prompt.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return STUB_SYSTEM_PROMPT


# Section headers mapped to VerificationReport field names
_SECTION_MAP = {
    "критические ошибки": "critical",
    "существенные замечания": "significant",
    "незначительные замечания": "minor",
    "подтверждённые факты": "confirmed",
    "требует ручной проверки": "needs_manual",
}


def _parse_item(line: str) -> VerificationItem:
    """Parse a bullet line into a VerificationItem."""
    # Try structured format: - **Цитата:** "..." | **Проблема:** ... | **Рекомендация:** ...
    m = re.search(
        r'\*\*Цитата:\*\*\s*"?([^"|]*)"?\s*\|\s*\*\*Проблема:\*\*\s*([^|]*)\|\s*\*\*Рекомендация:\*\*\s*(.*)',
        line,
    )
    if m:
        return VerificationItem(
            quote=m.group(1).strip(),
            issue=m.group(2).strip(),
            recommendation=m.group(3).strip(),
        )
    # Fallback: treat the whole line as issue
    text = re.sub(r"^-\s*", "", line).strip()
    return VerificationItem(quote="", issue=text, recommendation="")


def _parse_response(text: str) -> VerificationReport:
    report = VerificationReport(raw_response=text)
    current_field: str | None = None

    for line in text.splitlines():
        stripped = line.strip()

        # Detect section header
        header_match = re.match(r"^##\s+(.+)", stripped)
        if header_match:
            header = header_match.group(1).strip().lower()
            current_field = _SECTION_MAP.get(header)
            continue

        # Collect bullet items under current section
        if current_field and stripped.startswith("- "):
            item = _parse_item(stripped)
            getattr(report, current_field).append(item)

    return report


def _get_yandex_iam_token() -> str:
    """Return IAM token from env or generate via yc CLI (local dev only)."""
    token = os.getenv("YANDEX_IAM_TOKEN", "")
    if token:
        return token
    try:
        result = subprocess.run(
            ["yc", "iam", "create-token"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except FileNotFoundError:
        raise RuntimeError(
            "YANDEX_IAM_TOKEN не задан, а yc CLI не найден. "
            "Установите переменную окружения YANDEX_IAM_TOKEN."
        )


async def _call_yandex_gpt(text: str, model: str, system_prompt: str) -> str:
    """Call YandexGPT API and return the response text."""
    folder_id = os.getenv("YANDEX_FOLDER_ID", "")
    iam_token = _get_yandex_iam_token()

    model_uri = f"gpt://{folder_id}/{model}"
    payload = {
        "modelUri": model_uri,
        "completionOptions": {
            "stream": False,
            "temperature": 0.3,
            "maxTokens": "4096",
        },
        "messages": [
            {"role": "system", "text": system_prompt},
            {"role": "user", "text": text},
        ],
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            "https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
            headers={
                "Authorization": f"Bearer {iam_token}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        if not response.is_success:
            raise RuntimeError(
                f"YandexGPT API error {response.status_code}: {response.text}"
            )
        data = response.json()
        return data["result"]["alternatives"][0]["message"]["text"]


async def verify_grant_text(
    text: str,
    provider: str = "anthropic",
    model: str = "claude-sonnet-4-6",
) -> VerificationReport:
    system_prompt = load_system_prompt()

    if provider == "anthropic":
        client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        message = await client.messages.create(
            model=model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": text}],
        )
        raw = message.content[0].text
    elif provider == "yandex":
        raw = await _call_yandex_gpt(text, model, system_prompt)
    else:
        raise ValueError(f"Unknown provider: {provider}")

    return _parse_response(raw)
