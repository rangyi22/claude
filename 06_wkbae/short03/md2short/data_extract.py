"""대본 원문에서 숫자 모션 그래픽 카드 추출 (architecture.md §5.9).

카드 시작 시각은 `words` 가 주어지면 같은 숫자를 담은 words.json 단어의 start 를 쓴다
(numeric_display 가 단어를 원문 표기 "3.2%" 로 복원해 둠). 매칭에 실패한 카드만
`글자 위치 / 전체 글자 수 * 오디오 길이` 비례 근사값(visual cue)으로 fallback 한다.
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
    sentence_end = re.search(r"[!?\n]|\.(?!\d)", script_text[end:])  # "0.94" 의 소수점은 문장 끝이 아님
    rest = script_text[end : end + sentence_end.start() if sentence_end else len(script_text)]
    down, up = _DOWN_RE.search(rest), _UP_RE.search(rest)
    if down and (not up or down.start() < up.start()):
        return "down"
    return "up" if up else "neutral"


def _normalize(kind: str, raw: str) -> str:
    text = re.sub(r"\s+", " ", raw.strip())
    if kind == "percent":
        text = re.sub(r"\s?(?:퍼센트|프로)$", "%", text).replace(" %", "%")
    elif kind == "index":
        # "S&P 500 종가는 7,230" -> "S&P 500 7,230" (지수명과 숫자 사이 조사·서술어 제거)
        name = re.match(_INDEX_NAMES, text)
        value = re.search(rf"{_NUM}$", text)
        if name and value:
            text = f"{name.group(0)} {value.group(0)}"
    return text


def _find_word(words: list[dict[str, Any]], card_text: str, cursor: int) -> int | None:
    """card_text 의 마지막 숫자("3.2%" -> "3.2")를 경계 포함으로 담은 첫 단어 index (cursor 이후)."""
    nums = re.findall(_NUM, card_text)
    if not nums:
        return None
    value = re.compile(rf"(?<![\d.,]){re.escape(nums[-1])}(?![\d,]|\.\d)")
    for i in range(cursor, len(words)):
        if value.search(str(words[i].get("text", ""))):
            return i
    return None


def plan_number_cards(
    script_text: str,
    audio_duration_ms: int,
    max_cards: int = DEFAULT_MAX_CARDS,
    cooldown_ms: int = DEFAULT_COOLDOWN_MS,
    duration_ms: int = DEFAULT_DURATION_MS,
    words: list[dict[str, Any]] | None = None,
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
    cursor = 0  # words 는 순서대로 소비 (같은 숫자가 두 번 나와도 앞에서부터 매칭)
    for start_char, end_char, _prio, text in kept:
        if len(cards) >= max_cards:
            break
        hit = _find_word(words, text, cursor) if words else None
        if hit is not None:
            cursor = hit + 1
            start_ms = min(int(words[hit]["start"]), latest_start)  # type: ignore[index]
        else:
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


# ---------------------------------------------------------------- 지수 비교 보드

_INDEX_RE = re.compile(r"S&P\s?500|코스피|코스닥|나스닥|다우|니케이|항셍")
_PERCENT_RE = re.compile(rf"[+\-−]?{_NUM}\s?(?:%|퍼센트|프로)")
_INDEX_VALUE_RE = re.compile(rf"{_NUM}")


def _index_row(text: str, start_ms: int) -> dict[str, Any] | None:
    m = _INDEX_RE.search(text)
    if m is None:
        return None
    rest = text[m.end() :]
    pct = _PERCENT_RE.search(rest)
    value = _normalize("percent", pct.group(0)) if pct else ""
    if not value:
        num = _INDEX_VALUE_RE.search(rest)
        value = num.group(0) if num and num.group(0).replace(",", "").replace(".", "").isdigit() else ""
    tone = _tone(text, m.start(), m.end())
    name = "S&P 500" if m.group(0).startswith("S&P") else m.group(0)
    return {"name": name, "value": value, "tone": tone, "startMs": int(start_ms)}


def plan_index_board(segments: list[dict[str, Any]], min_rows: int = 2) -> dict[str, Any] | None:
    """연속된 자막 segment 에서 서로 다른 지수가 min_rows 개 이상 나오면 비교 보드 1개.

    시간은 segment(= words.json) 값만 사용한다. 행은 해당 지수 문장이 시작될 때 나타난다.
    """
    best: list[tuple[dict[str, Any], dict[str, Any]]] = []
    run: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for seg in segments:
        row = _index_row(str(seg.get("text", "")), int(seg["startMs"]))
        if row is not None and all(r["name"] != row["name"] for r, _s in run):
            run.append((row, seg))
            continue
        if len(run) > len(best):
            best = run
        run = [(row, seg)] if row is not None else []
    if len(run) > len(best):
        best = run
    if len(best) < min_rows:
        return None
    start = int(best[0][1]["startMs"])
    end = int(best[-1][1]["endMs"])
    return {"rows": [r for r, _s in best], "startMs": start, "durationMs": max(1, end - start)}


def drop_cards_in_window(cards: list[dict[str, Any]], *windows: dict[str, Any] | None) -> list[dict[str, Any]]:
    """보드·헤드라인이 떠 있는 구간의 숫자 카드는 같은 자리·같은 정보라 생략한다."""
    spans = [(w["startMs"], w["startMs"] + w["durationMs"]) for w in windows if w is not None]
    return [c for c in cards if not any(lo <= c["startMs"] < hi for lo, hi in spans)]


# ---------------------------------------------------------------- hook 헤드라인

# "5주 연속 상승을/상승하며" -> "5주 연속 상승", "2024년 이후 최장 랠리를" -> "2024년 이후 최장"
_HEADLINE_RE = re.compile(
    r"\d[\d,.]*\s?(?:년|주|개월|월|일|분기|거래일)\s?(?:연속|이후|이래|만에|들어|째)\s+([가-힣A-Za-z]+(?:\s+번째[가-힣]*)?)"
)
# 조사 + 서술 어미. 헤드라인은 명사구만 남긴다: "상승을/상승하며/상승했고" -> "상승".
# 검색은 가장 왼쪽 매치가 이기므로 긴 어미가 짧은 조사보다 먼저 잘린다 ("하며"의 "며" 단독 규칙은 없음).
_JOSA_TAIL = re.compile(
    r"(?:으로는|으로|에서|이라는|라는|했습니다|합니다|했으며|하면서|했고|하며|하고|하는|하여|해서|했다|을|를|이|가|은|는|의|에|로|와|과|도)$"
)
HEADLINE_MAX_LINES = 2


def plan_headline(segments: list[dict[str, Any]]) -> dict[str, Any] | None:
    """첫 자막 segment(hook 문장)의 숫자+기간 구를 최대 2줄 헤드라인으로. 시간은 segment 값."""
    if not segments:
        return None
    first = segments[0]
    lines: list[str] = []
    for m in _HEADLINE_RE.finditer(str(first.get("text", ""))):
        word = _JOSA_TAIL.sub("", m.group(1)) or m.group(1)
        line = m.group(0)[: m.start(1) - m.start()] + word
        lines.append(re.sub(r"\s+", " ", line).strip())
        if len(lines) >= HEADLINE_MAX_LINES:
            break
    if not lines:
        return None
    start = int(first["startMs"])
    return {"lines": lines, "startMs": start, "durationMs": max(1, int(first["endMs"]) - start)}
