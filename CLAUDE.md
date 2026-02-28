# CLAUDE.md — GrantChecker

## Project Overview

GrantChecker — инструмент adversarial-верификации ИИ-контента в грантовых заявках российских НКО.
Пользователь вставляет текст раздела заявки (обоснование социальной значимости и др.),
получает структурированный отчёт: критические ошибки, существенные замечания, подтверждённые факты.

Методологическая основа: github.com/lenapirogova/nko-ai-redteam (AGPL-3.0).

## Stack

- **Backend:** Python, FastAPI
- **LLM:** Claude API (claude-sonnet-4-6) через anthropic SDK
- **Frontend:** MVP — простая HTML-форма (один файл), v2 — отдельный фронт
- **DB:** SQLite (история проверок, опционально)
- **Deploy:** Railway или аналог

## Architecture

```
checker_core.py      — движок верификации (LLM-вызовы, парсинг отчёта)
api.py               — FastAPI endpoints
system_prompt.md     — системный промпт фактчекера (владелец: quality-analyst)
sources.md           — иерархия источников (владелец: grants-researcher)
templates/index.html — веб-форма
tests/               — pytest (владелец: sdet)
```

## Key Commands

```bash
# Install
pip install -r requirements.txt

# Run dev server
uvicorn api:app --reload

# Tests
python -m pytest tests/ -v
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Claude API key |
| `TAVILY_API_KEY` | No | Web search для верификации фактов |

## Agents

- **grants-researcher** — иерархия источников, база знаний по ФПГ, типичные паттерны ошибок
- **quality-analyst** — системный промпт фактчекера, методология верификации
- **backend-dev** — checker_core.py, api.py, интеграция с Claude API

## Language

UI, сообщения, промпты — на русском. Идентификаторы кода и комментарии — на английском.
