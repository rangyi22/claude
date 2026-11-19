from md2short.tts_text import prepare_tts_text as p


def test_numbers():
    assert p("종가 7,230 기록") == "종가 칠천이백삼십 기록"
    assert p("0.94% 상승") == "영 점 구 사 퍼센트 상승"
    assert p("2024년") == "이천이십사년"
    assert p("-3%") == "마이너스 삼 퍼센트"
    assert p("100000000") == "일억"


def test_native_counters_and_months():
    assert p("3개") == "세개"
    assert p("20명") == "스무명"
    assert p("6월 10월 5월") == "유월 시월 오월"


def test_acronyms():
    assert p("S&P 500") == "에스앤피 오백"
    assert p("S&P500") == "에스앤피오백"
    assert p("AI와 AMD") == "에이아이와 에이엠디"
    assert p("XYZ") == "엑스와이지"


def test_punctuation_flatten():
    assert p("- 첫째\n- 둘째") == "첫째. 둘째"
    assert p("A·B") == "A B"
    assert p("그런데... 정말??") == "그런데. 정말?"
    assert p("핵심은 ‘5주 연속’입니다") == "핵심은 오주 연속입니다"
    assert p("🐯 구독") == "구독"


def test_deterministic_and_input_untouched():
    s = "S&P 500, 0.94% — AI"
    assert p(s) == p(s)
    assert s == "S&P 500, 0.94% — AI"
