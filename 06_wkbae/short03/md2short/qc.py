"""자동 QC + 비용 추정 (architecture.md §5.6)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, TypedDict

SYNC_TAIL_TOLERANCE_MS = 1000
RENDER_AUDIO_TOLERANCE_MS = 100

# ElevenLabs 단가
ELEVENLABS_TTS_USD_PER_1K_CHARS = 0.30
ELEVENLABS_STT_USD_PER_HOUR = 0.40
# OpenAI 텍스트 모델 고정 근사 단가 (USD / 1M tokens). --model 별 pricing table 은 없음.
OPENAI_GPT55_INPUT_USD_PER_1M = 1.25
OPENAI_GPT55_OUTPUT_USD_PER_1M = 10.00
CHARS_PER_TOKEN = 4


class CostEstimate(TypedDict):
    elevenlabs_tts_usd: float
    elevenlabs_stt_usd: float
    openai_text_usd: float
    total_usd: float
    excludes: str


def estimate_cost(
    *,
    tts_chars: int,
    audio_duration_ms: int,
    openai_input_chars: int = 0,
    openai_output_chars: int = 0,
) -> CostEstimate:
    """TTS/STT/텍스트 LLM 근사 비용. photo 모드 이미지 비용은 합산하지 않는다."""
    tts = tts_chars / 1000 * ELEVENLABS_TTS_USD_PER_1K_CHARS
    stt = audio_duration_ms / 1000 / 3600 * ELEVENLABS_STT_USD_PER_HOUR
    in_tokens = openai_input_chars / CHARS_PER_TOKEN
    out_tokens = openai_output_chars / CHARS_PER_TOKEN
    llm = in_tokens / 1e6 * OPENAI_GPT55_INPUT_USD_PER_1M + out_tokens / 1e6 * OPENAI_GPT55_OUTPUT_USD_PER_1M
    return {
        "elevenlabs_tts_usd": round(tts, 6),
        "elevenlabs_stt_usd": round(stt, 6),
        "openai_text_usd": round(llm, 6),
        "total_usd": round(tts + stt + llm, 6),
        "excludes": "gpt-image-2 image generation (check actual OpenAI invoice)",
    }


def run_qc(
    *,
    job_dir: Path,
    audio_path: Path,
    final_mp4: Path,
    words_doc: dict[str, Any],
    cost_inputs: dict[str, int],
    audio_duration_fn: Callable[[Path], int],
    video_info_fn: Callable[[Path], dict[str, int]],
) -> dict[str, Any]:
    """QC 를 실행하고 qc_report.json 을 쓴다. 통과 여부는 report["passed"]."""
    audio_ms = audio_duration_fn(audio_path)
    video = video_info_fn(final_mp4)
    words = words_doc.get("words") or []
    last_word_end = words[-1]["end"] if words else 0

    tail_diff = audio_ms - last_word_end
    render_diff = video["duration_ms"] - audio_ms
    checks = [
        {
            "name": "sync_last_word_vs_audio",
            "audio_duration_ms": audio_ms,
            "last_word_end_ms": last_word_end,
            "diff_ms": tail_diff,
            "tolerance_ms": SYNC_TAIL_TOLERANCE_MS,
            "passed": bool(words) and abs(tail_diff) <= SYNC_TAIL_TOLERANCE_MS,
        },
        {
            "name": "final_mp4_vs_audio",
            "final_mp4_duration_ms": video["duration_ms"],
            "audio_duration_ms": audio_ms,
            "diff_ms": render_diff,
            "tolerance_ms": RENDER_AUDIO_TOLERANCE_MS,
            "passed": abs(render_diff) <= RENDER_AUDIO_TOLERANCE_MS,
        },
    ]
    report = {
        "passed": all(c["passed"] for c in checks),
        "checks": checks,
        "duration_policy": {"source": "tts_audio_duration", "duration_ms": audio_ms},
        "video": video,
        "cost_estimate": estimate_cost(audio_duration_ms=audio_ms, **cost_inputs),
    }
    (job_dir / "qc_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
