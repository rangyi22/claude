"""마크다운 → 한국어 내레이션 텍스트 fallback 추출 (architecture.md §5.1).

정보 보존 우선: 문장을 줄이거나 요약하지 않고 마크다운 문법만 제거한다.
"""

from __future__ import annotations

import re

_FENCE_RE = re.compile(r"^\s*(```|~~~)")
_TABLE_SEP_RE = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")
_HR_RE = re.compile(r"^\s*([-*_])(\s*\1){2,}\s*$")
_TERMINAL = ".!?。…"


def _strip_inline(line: str) -> str:
    line = re.sub(r"<!--.*?-->", "", line)
    line = re.sub(r"<[^>]+>", "", line)
    line = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", line)
    line = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", line)
    line = re.sub(r"\[([^\]]+)\]\[[^\]]*\]", r"\1", line)
    line = re.sub(r"`+([^`]*)`+", r"\1", line)
    line = re.sub(r"(\*\*|__)(.+?)\1", r"\2", line)
    line = re.sub(r"(?<![\w*])([*_])(?!\s)(.+?)(?<!\s)\1(?![\w*])", r"\2", line)
    line = re.sub(r"~~(.+?)~~", r"\1", line)
    return re.sub(r"\s+", " ", line).strip()


def extract_narration(markdown: str) -> str:
    """마크다운 문법을 제거한 내레이션 텍스트. 모든 문장 보존."""
    out: list[str] = []
    in_fence = False
    for raw in markdown.splitlines():
        if _FENCE_RE.match(raw):
            in_fence = not in_fence
            continue
        if in_fence or not raw.strip() or _HR_RE.match(raw) or _TABLE_SEP_RE.match(raw):
            continue
        line = raw
        if "|" in line and line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            line = ", ".join(c for c in cells if c)
        line = re.sub(r"^\s{0,3}#{1,6}\s+", "", line)
        line = re.sub(r"^\s*>+\s?", "", line)
        line = re.sub(r"^\s*([-*+]|\d+[.)])\s+", "", line)
        line = re.sub(r"^\[[ xX]\]\s+", "", line)
        line = _strip_inline(line)
        if not line:
            continue
        if line[-1] not in _TERMINAL:
            line += "."
        out.append(line)
    return " ".join(out)
