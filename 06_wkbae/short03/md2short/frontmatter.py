"""원고 front-matter (architecture.md §5.10).

    ---
    date: 2026-11-13
    ---

`date` 는 데이터(시장) 기준일. 배지·아웃트로 출처 표기에만 쓰고, 대본 생성에는 본문만 넘긴다.
"""

from __future__ import annotations

import re
from datetime import date

_FRONT_MATTER_RE = re.compile(r"\A---[ \t]*\n(.*?)\n---[ \t]*(?:\n|\Z)", re.DOTALL)
_WEEKDAYS_KO = "월화수목금토일"


def split_front_matter(markdown: str) -> tuple[dict[str, str], str]:
    """(meta, body). front-matter 가 없으면 ({}, markdown)."""
    m = _FRONT_MATTER_RE.match(markdown)
    if m is None:
        return {}, markdown
    meta: dict[str, str] = {}
    for line in m.group(1).splitlines():
        key, sep, value = line.partition(":")
        if sep and key.strip():
            meta[key.strip().lower()] = value.strip().strip("\"'")
    return meta, markdown[m.end() :]


def parse_market_date(value: str | None) -> date | None:
    """'YYYY-MM-DD' -> date. 빈 값은 None, 형식이 틀리면 ValueError."""
    if value is None or not value.strip():
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        raise ValueError(f"기준일은 YYYY-MM-DD 형식이어야 합니다: {value!r}") from exc


def korean_date_label(d: date) -> str:
    """date(2026, 11, 13) -> '11월 13일(금)'."""
    return f"{d.month}월 {d.day}일({_WEEKDAYS_KO[d.weekday()]})"
