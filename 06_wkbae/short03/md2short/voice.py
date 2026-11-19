"""ElevenLabs TTS (architecture.md §5.2)."""

from __future__ import annotations

from pathlib import Path

import httpx

from ._retry import post_with_retry
from .env import MissingEnvError

TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
TTS_MODEL = "eleven_multilingual_v2"
TTS_OUTPUT_FORMAT = "mp3_44100_128"
TTS_TIMEOUT = 120.0


def synthesize(
    text: str,
    voice_id: str,
    out_path: Path,
    api_key: str | None,
    speed: float = 1.0,
    log_dir: Path | None = None,
    client: httpx.Client | None = None,
) -> Path:
    """text 를 mp3 로 합성해 out_path 에 저장한다 (보통 audio/narration.mp3)."""
    if not api_key:
        raise MissingEnvError("ELEVENLABS_API_KEY 가 없어 TTS 를 호출할 수 없습니다.")
    if not text.strip():
        raise ValueError("TTS 입력 텍스트가 비어 있습니다.")
    out_path = Path(out_path)
    if log_dir is not None:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / "tts_input.txt").write_text(text, encoding="utf-8")
    resp = post_with_retry(
        client,
        TTS_URL.format(voice_id=voice_id),
        timeout=TTS_TIMEOUT,
        params={"output_format": TTS_OUTPUT_FORMAT},
        headers={"xi-api-key": api_key, "Content-Type": "application/json", "Accept": "audio/mpeg"},
        json={"text": text, "model_id": TTS_MODEL, "voice_settings": {"speed": speed}},
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(resp.content)
    return out_path
