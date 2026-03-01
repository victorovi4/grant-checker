import os
from dataclasses import asdict
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from checker_core import verify_grant_text

load_dotenv()

app = FastAPI(title="GrantChecker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000", "http://127.0.0.1:8000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

AVAILABLE_MODELS = {
    "anthropic": ["claude-sonnet-4-6", "claude-opus-4-6", "claude-haiku-4-5-20251001"],
    "yandex": ["yandexgpt/latest", "yandexgpt-lite/latest"],
}


class VerifyRequest(BaseModel):
    text: str
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-6"


@app.post("/verify")
async def verify(req: VerifyRequest):
    report = await verify_grant_text(req.text, req.provider, req.model)
    return asdict(report)


@app.get("/models")
async def models():
    return AVAILABLE_MODELS


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = Path(__file__).parent / "templates" / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
