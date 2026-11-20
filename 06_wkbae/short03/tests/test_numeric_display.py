import copy
from decimal import Decimal

from md2short import numeric_display as nd
from md2short.numeric_display import apply_numeric_display_overrides, parse_korean_number
from sample_words import build_words

SAMPLE_SCRIPT = (
    "S&P 500 종가 7,230 기록했습니다.\n나스닥은 0.94% 상승했습니다.\n"
    "5주 연속 상승, 2024년 이후 최장 랠리입니다.\n애플, 호실적으로 3.2% 상승했습니다.\n"
    "샌디스크, 8% 급등했습니다.\n오라클이 미 국방부 AI 네트워크 프로젝트에 공식 합류했습니다.\n"
    "로블록스, 18% 급락했습니다."
)


def doc(sentences):
    words = build_words(sentences)
    return {"language_code": "kor", "audio_duration_ms": words[-1]["end"], "words": words}


def texts(d):
    return [w["text"] for w in d["words"]]


def test_threshold_constants():
    assert nd.ACRONYM_MATCH_THRESHOLD == 0.86
    assert nd.GROUPED_NUMBER_MATCH_THRESHOLD == 0.84
    assert nd.ACRONYM_MAX_SCAN_WORDS == 96
    assert nd.NUMBER_MAX_SCAN_WORDS == 96
    assert "에센피" in nd._ACRONYM_KO_VARIANTS["S&P"]
    m1 = nd._ACRONYM_TOKEN_RE.search("S&P500")
    m2 = nd._ACRONYM_TOKEN_RE.search("S&P 500")
    assert m1 and m1["acr"] == "S&P"
    assert m2 and m2["acrnum"] == "500"


def test_parse_korean_number():
    assert parse_korean_number("칠천이백삼십") == Decimal(7230)
    assert parse_korean_number("영점구사") == Decimal("0.94")
    assert parse_korean_number("삼점이") == Decimal("3.2")
    assert parse_korean_number("이천이십사") == Decimal(2024)
    assert parse_korean_number("천구백오십") == Decimal(1950)
    assert parse_korean_number("만") == Decimal(10000)
    assert parse_korean_number("삼조이천억") == Decimal(3_200_000_000_000)
    assert parse_korean_number("십팔") == Decimal(18)
    assert parse_korean_number("천천") is None
    assert parse_korean_number("이삼") is None
    assert parse_korean_number("가나") is None
    assert nd.int_to_korean(7230) == "칠천이백삼십"
    assert nd.int_to_korean(2024) == "이천이십사"


def test_sp500_restored_from_scribe_transliteration():
    d = doc(["에센피 오백 종가 칠천이백삼십 기록했습니다."])
    out = apply_numeric_display_overrides(d, "S&P500 종가 7,230 기록했습니다.")
    assert texts(out) == ["S&P500", "종가", "7,230", "기록했습니다."]


def test_sp500_with_space_and_variant_forms():
    for reading in (["에스앤피", "오백"], ["에스앤피오백"], ["에센피오백"], ["에스엔피", "오백"]):
        d = doc([" ".join(reading + ["종가"]) + "."])
        out = apply_numeric_display_overrides(d, "S&P 500 종가")
        assert texts(out)[0] == "S&P 500", reading


def test_number_and_percent_restored():
    d = doc(["영점구사퍼센트 상승했습니다.", "나스닥은 삼점이 퍼센트 올랐다."])
    out = apply_numeric_display_overrides(d, "0.94% 상승했습니다. 나스닥은 3.2% 올랐다.")
    assert texts(out) == ["0.94%", "상승했습니다.", "나스닥은", "3.2%", "올랐다."]


def test_split_words_and_arabic_percent():
    d = doc(["영 점 구 사 퍼센트 올랐고 0.94퍼센트 였다"])
    out = apply_numeric_display_overrides(d, "0.94% 올랐고 0.94% 였다")
    assert texts(out)[0] == "0.94%"
    assert "0.94%" in texts(out)[2:]


def test_timings_unchanged_for_single_word_replacements():
    d = doc(["칠천이백삼십 기록", "에이아이 시장"])
    before = copy.deepcopy(d)
    out = apply_numeric_display_overrides(d, "7,230 기록 AI 시장")
    assert d == before  # 입력 불변
    assert texts(out) == ["7,230", "기록", "AI", "시장"]
    for a, b in zip(before["words"], out["words"]):
        assert (a["start"], a["end"]) == (b["start"], b["end"])
    assert out["audio_duration_ms"] == before["audio_duration_ms"]


def test_merged_span_keeps_outer_timing():
    d = doc(["칠천 이백삼십 기록"])
    out = apply_numeric_display_overrides(d, "7,230 기록")
    assert texts(out) == ["7,230", "기록"]
    assert out["words"][0]["start"] == d["words"][0]["start"]
    assert out["words"][0]["end"] == d["words"][1]["end"]


def test_acronym_variants_and_josa():
    d = doc(["에이엠디가 에이아이를 말했다"])
    out = apply_numeric_display_overrides(d, "AMD가 AI를 말했다")
    assert texts(out) == ["AMD가", "AI를", "말했다"]


def test_no_false_positive_on_common_words():
    d = doc(["이 일본 오라클이 삼성 이상 오 주 공식"])
    out = apply_numeric_display_overrides(d, "2 5주")
    assert texts(out)[:5] == ["이", "일본", "오라클이", "삼성", "이상"]


def test_monotonic_order_prevents_wrong_replacement():
    # 대본의 7,230은 첫 번째 칠천이백삼십이 아니라 스크립트 순서상 두 번째 8%보다 앞
    d = doc(["팔 퍼센트 하락 뒤 칠천이백삼십 기록"])
    out = apply_numeric_display_overrides(d, "8% 하락 뒤 7,230 기록")
    assert texts(out) == ["8%", "하락", "뒤", "7,230", "기록"]


def test_fuzzy_grouped_number():
    d = doc(["칠천이백삼십이 기록"])  # Scribe 오탈자: 이 추가 -> 파싱 불가 -> fuzzy
    out = apply_numeric_display_overrides(d, "7,230 기록")
    assert texts(out)[0] == "7,230"


def test_sample_md_content():
    d = doc(
        [
            "에센피 오백 종가 칠천이백삼십 기록했습니다.",
            "나스닥은 영점구사 퍼센트 상승했습니다.",
            "오 주 연속 상승, 이천이십사년 이후 최장 랠리입니다.",
            "애플, 호실적으로 삼점이 퍼센트 상승했습니다.",
            "샌디스크, 팔 퍼센트 급등했습니다.",
            "오라클이 미 국방부 에이아이 네트워크 프로젝트에 공식 합류했습니다.",
            "로블록스, 십팔 퍼센트 급락했습니다.",
        ]
    )
    out = apply_numeric_display_overrides(d, SAMPLE_SCRIPT)
    joined = " ".join(texts(out))
    for expected in ("S&P 500", "7,230", "0.94%", "5 주", "2024년", "3.2%", "8%", "AI", "18%"):
        assert expected in joined, (expected, joined)
    assert "에센피" not in joined and "퍼센트" not in joined
    assert out["words"][0]["start"] == d["words"][0]["start"]
    assert out["words"][-1]["end"] == d["words"][-1]["end"]
