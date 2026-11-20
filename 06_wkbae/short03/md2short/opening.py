"""Opening 날짜 배지 + 출처 표기 (architecture.md §5.10). ko 단일 키 (v1.1 락).

날짜는 음성으로 읽지 않는다 — 첫 문장부터 바로 hook 을 읽고, 날짜는 hook 과 동시에
상단 배지로만 OPENING_BADGE_MS 동안 보여 준다 (시각 효과 길이이며 음성 타이밍이 아님).
배지 날짜는 렌더 날짜가 아니라 원고의 데이터 기준일(front-matter `date:` 또는 `--date`)이다.
"""

from __future__ import annotations

from datetime import date

from md2short.frontmatter import korean_date_label

OPENING_TEMPLATES: dict[str, dict[str, str]] = {
    "ko": {
        "spoken": "",
        "visual": "{date} 데이브리핑",
        "visual_no_date": "데이브리핑",
        "source": "데이터 기준: {date}",
    }
}

OPENING_BADGE_MS = 2500


def build_opening(market_date: date | None) -> dict[str, str]:
    """기준일이 있으면 '11월 13일(금) 데이브리핑', 없으면 '데이브리핑' (렌더 날짜는 쓰지 않음)."""
    tpl = OPENING_TEMPLATES["ko"]
    if market_date is None:
        return {"spoken": tpl["spoken"], "visual": tpl["visual_no_date"], "source": ""}
    label = korean_date_label(market_date)
    return {"spoken": tpl["spoken"], "visual": tpl["visual"].format(date=label), "source": tpl["source"].format(date=label)}
