"""환경 변수 로딩 (AGENTS.md §4.3). 키 값은 절대 로그/메시지에 포함하지 않는다."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


class MissingEnvError(RuntimeError):
    """필수 환경 변수 누락."""


def load_env(dotenv_path: str | Path | None = None) -> None:
    """`.env` 를 로드한다. 이미 설정된 환경 변수는 덮어쓰지 않는다."""
    if dotenv_path is None:
        load_dotenv(override=False)
    else:
        load_dotenv(dotenv_path=Path(dotenv_path), override=False)


def require_elevenlabs_key() -> str:
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key:
        raise MissingEnvError(
            "ELEVENLABS_API_KEY 가 설정되지 않았습니다. .env 에 ELEVENLABS_API_KEY=... 를 추가하세요."
        )
    return key


def get_openai_key() -> str | None:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    return key or None
