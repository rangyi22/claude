import json

import pytest

from md2short.storyboard import (
    is_storyboard,
    map_cuts_to_segments,
    narration_text,
    parse_storyboard,
    write_storyboard_json,
)
from sample_words import build_words

MD_DASH = """# 제목

### 1컷
- 자막: 지난 금요일 미국 증시, 강하게 상승 마감했습니다.
- 화면 연출: 상승 차트 확대
- 이미지 프롬프트: bull market chart, evening skyline

### 2컷
- 자막: S&P 500 종가 7,230 기록했습니다.
- 화면 연출: 숫자 카운트업
- 이미지 프롬프트: stock board

### 3컷
- 자막: 나스닥은 0.94% 상승했습니다.
- 화면 연출: 나스닥 로고
- 이미지 프롬프트: nasdaq tower
"""

MD_BOLD = """## 1컷
**자막**: 샌디스크, 8% 급등했습니다.
**화면 연출**: 로켓
**이미지 프롬프트**: rocket

## 2 컷
- **자막:** 로블록스, 18% 급락했습니다.
- **화면 연출:** 하락
  차트 이어서
- **이미지 프롬프트:** falling chart
"""


def test_is_storyboard():
    assert is_storyboard(MD_DASH) and is_storyboard(MD_BOLD)
    assert not is_storyboard("# 일반 문서\n\n본문 3컷 만화")


def test_parse_both_formats():
    sb = parse_storyboard(MD_DASH)
    assert [c["index"] for c in sb["cuts"]] == [1, 2, 3]
    assert sb["cuts"][0] == {
        "index": 1,
        "subtitle": "지난 금요일 미국 증시, 강하게 상승 마감했습니다.",
        "direction": "상승 차트 확대",
        "image_prompt": "bull market chart, evening skyline",
    }
    sb2 = parse_storyboard(MD_BOLD)
    assert sb2["cuts"][0]["subtitle"] == "샌디스크, 8% 급등했습니다."
    assert sb2["cuts"][1]["subtitle"] == "로블록스, 18% 급락했습니다."
    assert sb2["cuts"][1]["direction"] == "하락 차트 이어서"
    assert sb2["cuts"][1]["image_prompt"] == "falling chart"


def test_narration_only_subtitles():
    text = narration_text(parse_storyboard(MD_DASH))
    assert "S&P 500 종가 7,230 기록했습니다." in text
    assert "차트" not in text and "bull" not in text and "카운트업" not in text


def test_map_cuts_one_to_one():
    sb = parse_storyboard(MD_DASH)
    words = build_words([c["subtitle"] for c in sb["cuts"]])
    segs = map_cuts_to_segments(sb, words)
    assert len(segs) == 3
    assert [s["cutIndex"] for s in segs] == [1, 2, 3]
    assert segs[0]["text"] == sb["cuts"][0]["subtitle"]
    assert segs[0]["wordStart"] == 0 and segs[-1]["wordEnd"] == len(words)
    assert segs[1]["direction"] == "숫자 카운트업"
    assert segs[2]["imagePrompt"] == "nasdaq tower"
    assert [s["index"] for s in segs] == [0, 1, 2]


def test_scribe_split_around_numbers_is_merged():
    sb = parse_storyboard(MD_DASH)
    # Scribe가 숫자·비율 주변에서 문장부호/긴 gap으로 추가 분할 (컷 3개 -> 문장 5개)
    sentences = [
        "지난 금요일 미국 증시, 강하게 상승 마감했습니다.",
        "에센피 오백 종가.",
        "칠천이백삼십 기록했습니다.",
        "나스닥은 영점구사 퍼센트.",
        "상승했습니다.",
    ]
    words = build_words(sentences)
    segs = map_cuts_to_segments(sb, words)
    assert len(segs) == 3
    assert segs[0]["wordEnd"] == 7
    assert segs[1]["text"].startswith("에센피") and segs[1]["text"].endswith("기록했습니다.")
    assert segs[2]["text"] == "나스닥은 영점구사 퍼센트. 상승했습니다."
    assert segs[1]["wordEnd"] == segs[2]["wordStart"]


def test_fewer_sentences_than_cuts_snaps_by_words():
    sb = parse_storyboard(MD_BOLD)
    words = build_words(["샌디스크, 팔 퍼센트 급등했습니다 로블록스, 십팔 퍼센트 급락했습니다."])
    segs = map_cuts_to_segments(sb, words)
    assert len(segs) == 2
    assert segs[0]["text"].startswith("샌디스크") and segs[1]["text"].startswith("로블록스")


def test_too_few_words_raises():
    sb = parse_storyboard(MD_DASH)
    with pytest.raises(ValueError):
        map_cuts_to_segments(sb, build_words(["하나 둘."]))


def test_write_storyboard_json(tmp_path):
    sb = parse_storyboard(MD_DASH)
    out = write_storyboard_json(sb, tmp_path / "inputs" / "storyboard.json")
    assert json.loads(out.read_text(encoding="utf-8")) == sb
