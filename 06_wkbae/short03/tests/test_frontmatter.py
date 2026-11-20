from datetime import date

import pytest

from md2short.frontmatter import korean_date_label, parse_market_date, split_front_matter


def test_split_front_matter():
    meta, body = split_front_matter("---\ndate: 2026-11-13\ntitle: \"브리핑\"\n---\n본문입니다.\n")
    assert meta == {"date": "2026-11-13", "title": "브리핑"}
    assert body == "본문입니다.\n"


def test_no_front_matter_returns_input():
    md = "지난 금요일 미국 증시.\n---\n구분선 아래"
    assert split_front_matter(md) == ({}, md)


def test_parse_market_date():
    assert parse_market_date("2026-11-13") == date(2026, 11, 13)
    assert parse_market_date("") is None and parse_market_date(None) is None
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        parse_market_date("11/13")


def test_korean_date_label():
    assert korean_date_label(date(2026, 11, 13)) == "11월 13일(금)"
