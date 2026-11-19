"""데이터 모델 (architecture.md §4.1, §4.2)."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

# v1.1+ 한국어 락: 모든 언어별 매핑은 ko 단일 키만 노출한다.
DEFAULT_VOICES: dict[str, str] = {"ko": "v1jVu1Ky28piIPEJqRrm"}
CTA_TEXT: dict[str, str] = {"ko": "🐯 구독 + 알람"}
SCRIBE_LANG: dict[str, str] = {"ko": "kor"}


class VisualMode(str, Enum):
    EMOTICON = "emoticon"
    PHOTO = "photo"


class JobConfig(BaseModel):
    platform: Literal["youtube_shorts", "instagram_reels", "tiktok"] = "youtube_shorts"
    language: Literal["ko"] = "ko"  # 한국어 락 (v1.1+). en/ja는 v2.
    voice_id: str = DEFAULT_VOICES["ko"]
    voice_speed: float = Field(default=1.0, ge=0.7, le=1.2)
    template_id: str = "tech_explainer"  # 현재 분기 미적용
    bg_color: str = "0xFFFFFF"
    chunk_size: int = Field(default=14, ge=1, le=24)  # 자막 segment 최대 단어 수 안전 상한
    engine: Literal["remotion"] = "remotion"  # ffmpeg 렌더 엔진 미지원
    visual_mode: Literal["emoticon", "photo"] = "emoticon"  # photo 는 OPENAI_API_KEY 필요
    show_opening: bool = True
    show_outro: bool = False


class CaptionWord(BaseModel):
    text: str
    start: int  # ms
    end: int  # ms


class WordsDoc(BaseModel):
    language_code: str = "kor"
    audio_duration_ms: int
    text: str = ""
    words: list[CaptionWord]
