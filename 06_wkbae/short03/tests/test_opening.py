from datetime import date

from md2short.opening import OPENING_BADGE_MS, OPENING_TEMPLATES, build_opening


def test_ko_only():
    assert set(OPENING_TEMPLATES) == {"ko"}


def test_badge_uses_market_date_not_render_date():
    # 날짜는 음성으로 읽지 않고, 배지·출처는 데이터 기준일로 표시한다
    o = build_opening(date(2026, 11, 13))
    assert o == {"spoken": "", "visual": "11월 13일(금) 데이브리핑", "source": "데이터 기준: 11월 13일(금)"}


def test_no_market_date_shows_label_only():
    assert build_opening(None) == {"spoken": "", "visual": "데이브리핑", "source": ""}


def test_badge_duration_constant():
    assert OPENING_BADGE_MS == 2500
