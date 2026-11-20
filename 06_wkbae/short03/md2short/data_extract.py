"""대본 원문에서 숫자 모션 그래픽 카드 추출 (architecture.md §5.9).

주의: 카드 시작 시각은 `글자 위치 / 전체 글자 수 * 오디오 길이` 비례 매핑이다.
이는 words.json 타이밍이 아닌 시각 효과용 근사값(visual cue)이며,
자막·음성 동기 기준으로 사용하지 않는다 (AGENTS.md §3.2는 음성/자막 시간에 적용).
"""

from __future__ import annotations

import re
from typing import Any

DEFAULT_MAX_CARDS = 6
DEFAULT_COOLDOWN_MS = 2500
DEFAULT_DURATION_MS = 1800

_NUM = r"\d[\d,]*(?:\.\d+)?"
_INDEX_NAMES = r"(?:코스피|코스닥|S&P\s?500|나스닥|다우|니케이|항셍)"

# (이름, 정규식) — 앞쪽일수록 우선순위가 높다 (겹치면 우선순위 높은 쪽만 유지).
_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("percent", re.compile(rf"[+\-−]?{_NUM}\s?(?:%|퍼센트|프로)")),
    ("point", re.compile(rf"{_NUM}\s?(?:[pP](?![A-Za-z])|포인트)")),
    ("money", re.compile(rf"(?:{_NUM}\s?(?:조|억|만)\s?)+(?:원|달러)")),
    ("index", re.compile(rf"{_INDEX_NAMES}[^\d\n.]{{0,8}}?{_NUM}")),
]


_DOWN_RE = re.compile(r"하락|급락|폭락|추락|감소|약세|내렸|내린|떨어")
_UP_RE = re.compile(r"상승|급등|폭등|증가|강세|올랐|오른|뛰었")


def _tone(script_text: str, start: int, end: int) -> str:
    """숫자가 속한 문장 안의 등락 단어로 카드 색 톤 결정 ("down" | "up" | "neutral")."""
    raw = script_text[start:end].lstrip()
    if raw[:1] in "-−":
        return "down"
    if raw[:1] == "+":
        return "up"
    sentence_end = re.search(r"[.!?\n]", script_text[end:])
    rest = script_text[end : end + sentence_end.start() if sentence_end else len(script_text)]
    down, up = _DOWN_RE.search(rest), _UP_RE.search(rest)
    if down and (not up or down.start() < up.start()):
        return "down"
    return "up" if up else "neutral"


def _normalize(kind: str, raw: str) -> str:
    text = re.sub(r"\s+", " ", raw.strip())
    if kind == "percent":
        text = re.sub(r"\s?(?:퍼센트|프로)$", "%", text).replace(" %", "%")
    return text


def plan_number_cards(
    script_text: str,
    audio_duration_ms: int,
    max_cards: int = DEFAULT_MAX_CARDS,
    cooldown_ms: int = DEFAULT_COOLDOWN_MS,
    duration_ms: int = DEFAULT_DURATION_MS,
) -> list[dict[str, Any]]:
    """script_text -> [{"text", "startMs", "durationMs", "tone"}] (시간순)."""
    total = len(script_text)
    if total == 0 or audio_duration_ms <= 0 or max_cards <= 0:
        return []

    found: list[tuple[int, int, int, str]] = []  # (start, end, priority, text)
    for priority, (kind, pattern) in enumerate(_PATTERNS):
        for m in pattern.finditer(script_text):
            found.append((m.start(), m.end(), priority, _normalize(kind, m.group(0))))

    kept: list[tuple[int, int, int, str]] = []
    for cand in sorted(found, key=lambda c: (c[2], c[0])):
        if all(cand[1] <= k[0] or cand[0] >= k[1] for k in kept):
            kept.append(cand)
    kept.sort(key=lambda c: c[0])

    duration = min(duration_ms, audio_duration_ms)
    latest_start = max(0, audio_duration_ms - duration)
    cards: list[dict[str, Any]] = []
    for start_char, end_char, _prio, text in kept:
        if len(cards) >= max_cards:
            break
        start_ms = min(int(start_char / total * audio_duration_ms), latest_start)
        if cards and start_ms - cards[-1]["startMs"] < cooldown_ms:
            continue
        cards.append(
            {
                "text": text,
                "startMs": start_ms,
                "durationMs": duration,
                "tone": _tone(script_text, start_char, end_char),
            }
        )
    return cards
