"""Opening 문구 (architecture.md §5.10). ko 단일 키 (v1.1 락)."""

from __future__ import annotations

from datetime import date

OPENING_TEMPLATES: dict[str, dict[str, str]] = {
    "ko": {
        "spoken": "{month}월 {day}일 데이브리핑입니다.",
        "visual": "{yy}년 {month}월 {day}일\n데이브리핑",
    }
}


def build_opening(today: date) -> dict[str, str]:
    tpl = OPENING_TEMPLATES["ko"]
    fields = {"yy": today.year % 100, "month": today.month, "day": today.day}
    return {"spoken": tpl["spoken"].format(**fields), "visual": tpl["visual"].format(**fields)}

OPENING_ANCHOR = "브리핑"
OPENING_SCAN_WORDS = 8


def opening_duration_ms(words: list[dict]) -> int:
    """words.json 에서 spoken opening 이 끝나는 시점(ms).

    시간은 추정하지 않고, 앞쪽 OPENING_SCAN_WORDS 단어 안에서 "브리핑"을 포함한
    단어의 end 를 사용한다. 찾지 못하면 0 (opening caption suppression 없음).
    """
    for word in words[:OPENING_SCAN_WORDS]:
        if OPENING_ANCHOR in str(word.get("text", "")):
            return int(word["end"])
    return 0
