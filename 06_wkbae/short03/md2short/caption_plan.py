"""자막 segment 분할 (architecture.md §5.4).

Remotion `Captions.tsx::chunkBySentences()`와 동일한 규칙을 Python에서 재현한다.
경계: 단어 끝 문장부호(`.!?。！？…`) 또는 다음 단어와의 gap >= 600ms,
그리고 chunk가 chunk_size 단어에 도달하면 강제 분할.
시간은 words.json 값만 사용한다 (AGENTS.md §3.2).
"""

from __future__ import annotations

from typing import Any

SENTENCE_END_CHARS = ".!?。！？…"
GAP_BOUNDARY_MS = 600
DEFAULT_CHUNK_SIZE = 14
MAX_CHUNK_SIZE = 24


def clamp_chunk_size(chunk_size: int) -> int:
    """Captions.tsx `clampChunkSize` 와 동일: 1 미만이면 기본값, 상한 24."""
    if chunk_size < 1:
        return DEFAULT_CHUNK_SIZE
    return min(MAX_CHUNK_SIZE, int(chunk_size))


def build_caption_line_segments(
    words: list[dict[str, Any]],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    skip_until_ms: int = 0,
) -> list[dict[str, Any]]:
    """words -> 자막 segment 목록.

    wordStart(inclusive)/wordEnd(exclusive)는 입력 `words` 리스트의 인덱스.
    `skip_until_ms`(opening suppression) 시점까지 끝나는 단어(end <= skip_until_ms)는 제외한다. Captions.tsx `w.end > suppressUntilMs` 와 동일.
    """
    size = clamp_chunk_size(chunk_size)
    segments: list[dict[str, Any]] = []
    current: list[int] = []

    def flush() -> None:
        if not current:
            return
        first, last = current[0], current[-1]
        segments.append(
            {
                "index": len(segments),
                "startMs": int(words[first]["start"]),
                "endMs": int(words[last]["end"]),
                "text": " ".join(str(words[i]["text"]).strip() for i in current),
                "wordStart": first,
                "wordEnd": last + 1,
            }
        )
        current.clear()

    for i, word in enumerate(words):
        if int(word["end"]) <= skip_until_ms:
            continue
        current.append(i)
        text = str(word["text"]).strip()
        boundary = bool(text) and text[-1] in SENTENCE_END_CHARS
        if not boundary and i + 1 < len(words):
            boundary = int(words[i + 1]["start"]) - int(word["end"]) >= GAP_BOUNDARY_MS
        if boundary or len(current) >= size:
            flush()
    flush()
    return segments
