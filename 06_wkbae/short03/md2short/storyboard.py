"""`### N컷` 스토리보드 입력 처리 (architecture.md §5.4, §5.1).

`자막`만 TTS 내레이션이 되고, `화면 연출`/`이미지 프롬프트`는 cue 선택용 메타데이터로만 쓴다.
컷 <-> words.json 매핑은 실제 TTS/Scribe 결과의 문장 boundary에 snap한다 (시간 추정 없음).
"""

from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path
from typing import Any

from md2short.caption_plan import MAX_CHUNK_SIZE, build_caption_line_segments

_HEADING_RE = re.compile(r"^\s*#{2,4}\s*(\d+)\s*컷\b.*$", re.M)
_FIELD_RE = re.compile(
    r"^\s*(?:[-*+]\s*)?(?:\*\*)?\s*(자막|화면\s*연출|이미지\s*프롬프트)\s*(?:\*\*)?\s*[:：]\s*(?:\*\*)?\s*(.*)$"
)
_FIELD_KEYS = {"자막": "subtitle", "화면연출": "direction", "이미지프롬프트": "image_prompt"}


def is_storyboard(md: str) -> bool:
    return _HEADING_RE.search(md) is not None


def _clean(value: str) -> str:
    value = value.strip()
    value = re.sub(r"^\*\*|\*\*$", "", value).strip()
    if len(value) >= 2 and value[0] in "\"'“‘「" and value[-1] in "\"'”’」":
        value = value[1:-1].strip()
    return value


def parse_storyboard(md: str) -> dict[str, list[dict[str, Any]]]:
    cuts: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    field: str | None = None
    for line in md.splitlines():
        heading = _HEADING_RE.match(line)
        if heading:
            current = {"index": int(heading.group(1)), "subtitle": "", "direction": "", "image_prompt": ""}
            cuts.append(current)
            field = None
            continue
        if current is None:
            continue
        m = _FIELD_RE.match(line)
        if m:
            field = _FIELD_KEYS[re.sub(r"\s+", "", m.group(1))]
            current[field] = m.group(2).strip()
        elif field and line.strip() and not line.lstrip().startswith(("#", "---")):
            current[field] = (current[field] + " " + line.strip()).strip()
    for cut in cuts:
        for key in ("subtitle", "direction", "image_prompt"):
            cut[key] = _clean(cut[key])
    return {"cuts": cuts}


def narration_text(storyboard: dict) -> str:
    """TTS 내레이션: 컷의 자막만 이어붙인다."""
    return " ".join(c["subtitle"] for c in storyboard["cuts"] if c["subtitle"])


def _norm(text: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣]", "", text)


def _partition(cut_texts: list[str], unit_texts: list[str]) -> list[tuple[int, int]]:
    """unit을 연속 그룹 N개로 나눠 컷 자막과의 유사도 합이 최대인 경계를 DP로 찾는다."""
    n, m = len(cut_texts), len(unit_texts)

    @lru_cache(maxsize=None)
    def sim(k: int, i: int, j: int) -> float:
        return SequenceMatcher(None, cut_texts[k], "".join(unit_texts[i:j])).ratio()

    neg = float("-inf")
    best = [[neg] * (m + 1) for _ in range(n + 1)]
    back = [[0] * (m + 1) for _ in range(n + 1)]
    best[0][0] = 0.0
    for k in range(1, n + 1):
        for j in range(k, m - (n - k) + 1):
            for i in range(k - 1, j):
                if best[k - 1][i] == neg:
                    continue
                score = best[k - 1][i] + sim(k - 1, i, j)
                if score > best[k][j]:
                    best[k][j], back[k][j] = score, i
    bounds: list[tuple[int, int]] = []
    j = m
    for k in range(n, 0, -1):
        i = back[k][j]
        bounds.append((i, j))
        j = i
    return bounds[::-1]


def map_cuts_to_segments(storyboard: dict, words: list[dict]) -> list[dict[str, Any]]:
    """컷마다 정확히 1개의 caption segment (caption_plan 형식 + cutIndex/direction/imagePrompt)."""
    cuts = storyboard["cuts"]
    if not cuts:
        return []
    if len(words) < len(cuts):
        raise ValueError(f"words({len(words)}) < cuts({len(cuts)}): 컷을 words.json에 매핑할 수 없음")

    base = build_caption_line_segments(words, chunk_size=MAX_CHUNK_SIZE)
    if len(base) >= len(cuts):
        units = [(s["wordStart"], s["wordEnd"]) for s in base]
    else:  # 문장 boundary가 컷보다 적으면 단어 단위로 snap
        units = [(i, i + 1) for i in range(len(words))]
    unit_texts = [_norm("".join(str(w["text"]) for w in words[s:e])) for s, e in units]
    cut_texts = [_norm(c["subtitle"]) for c in cuts]

    segments: list[dict[str, Any]] = []
    for k, (ui, uj) in enumerate(_partition(cut_texts, unit_texts)):
        ws, we = units[ui][0], units[uj - 1][1]
        cut = cuts[k]
        segments.append(
            {
                "index": k,
                "startMs": int(words[ws]["start"]),
                "endMs": int(words[we - 1]["end"]),
                "text": " ".join(str(w["text"]).strip() for w in words[ws:we]),
                "wordStart": ws,
                "wordEnd": we,
                "cutIndex": cut["index"],
                "direction": cut["direction"],
                "imagePrompt": cut["image_prompt"],
            }
        )
    return segments


def write_storyboard_json(storyboard: dict, path: str | Path) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8")
    return out
