"""ElevenLabs Scribe (architecture.md §5.3). 초 → ms 변환은 timeutil.seconds_to_ms 만 사용."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

from ._retry import post_with_retry
from .env import MissingEnvError
from .schema import SCRIBE_LANG
from .timeutil import seconds_to_ms

STT_URL = "https://api.elevenlabs.io/v1/speech-to-text"
STT_MODEL = "scribe_v1"
STT_TIMEOUT = 300.0


def transcribe(
    audio_path: Path,
    api_key: str | None,
    *,
    audio_duration_ms: int,
    language: str = "ko",
    out_path: Path | None = None,
    raw_log_path: Path | None = None,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """words 문서(§4.2)를 반환하고 out_path/raw_log_path 에 저장한다.

    audio_duration_ms 는 호출자가 ffprobe 로 측정해 전달한다 (추정 금지).
    """
    if not api_key:
        raise MissingEnvError("ELEVENLABS_API_KEY 가 없어 Scribe 를 호출할 수 없습니다.")
    if language not in SCRIBE_LANG:
        raise ValueError(f"지원하지 않는 언어: {language!r} (v1 은 ko 만 지원)")
    lang_code = SCRIBE_LANG[language]
    audio_path = Path(audio_path)
    resp = post_with_retry(
        client,
        STT_URL,
        timeout=STT_TIMEOUT,
        headers={"xi-api-key": api_key},
        data={"model_id": STT_MODEL, "language_code": lang_code, "timestamps_granularity": "word"},
        files={"file": (audio_path.name, audio_path.read_bytes(), "audio/mpeg")},
    )
    raw = resp.json()
    if raw_log_path is not None:
        raw_log_path = Path(raw_log_path)
        raw_log_path.parent.mkdir(parents=True, exist_ok=True)
        raw_log_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

    words = []
    for w in raw.get("words", []):
        if w.get("type", "word") != "word":  # spacing / audio_event 제외
            continue
        if w.get("start") is None or w.get("end") is None:
            continue
        words.append(
            {
                "text": w["text"],
                "start": seconds_to_ms(w["start"]),
                "end": seconds_to_ms(w["end"]),
            }
        )
    doc = {
        "language_code": lang_code,
        "audio_duration_ms": int(audio_duration_ms),
        "text": raw.get("text") or " ".join(w["text"] for w in words),
        "words": words,
    }
    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return doc
