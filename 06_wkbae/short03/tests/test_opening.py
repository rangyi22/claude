from datetime import date

from md2short.opening import OPENING_TEMPLATES, build_opening


def test_ko_only():
    assert set(OPENING_TEMPLATES) == {"ko"}


def test_build_opening():
    o = build_opening(date(2026, 5, 2))
    assert o == {"spoken": "5월 2일 데이브리핑입니다.", "visual": "26년 5월 2일\n데이브리핑"}


def test_double_digit():
    o = build_opening(date(2026, 11, 20))
    assert o["spoken"] == "11월 20일 데이브리핑입니다."
    assert o["visual"] == "26년 11월 20일\n데이브리핑"


def test_opening_duration_from_words():
    from md2short.opening import opening_duration_ms

    words = [
        {"text": "십일월", "start": 0, "end": 400},
        {"text": "이십일", "start": 420, "end": 800},
        {"text": "데이브리핑입니다.", "start": 820, "end": 1650},
        {"text": "지난", "start": 1900, "end": 2100},
    ]
    assert opening_duration_ms(words) == 1650
    assert opening_duration_ms(words[3:]) == 0
    assert opening_duration_ms([]) == 0
