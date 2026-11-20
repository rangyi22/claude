from md2short.data_extract import plan_number_cards

SAMPLE = (
    "S&P 500 종가 7,230 기록했습니다.\n나스닥은 0.94% 상승했습니다.\n"
    "다우는 소폭 하락했습니다.\n애플, 호실적으로 3.2% 상승했습니다.\n"
    "샌디스크, 8% 급등했습니다.\n로블록스, 18% 급락했습니다."
)


def texts(cards):
    return [c["text"] for c in cards]


def test_percent_variants():
    cards = plan_number_cards("A는 3.2% 올랐고 B는 12퍼센트, C는 5프로 늘었다. " * 1, 60000, cooldown_ms=0)
    assert texts(cards) == ["3.2%", "12%", "5%"]


def test_point_variants():
    cards = plan_number_cards("지수가 30p 오르고 다시 45포인트 올랐다.", 20000, cooldown_ms=0)
    assert texts(cards) == ["30p", "45포인트"]


def test_money_variants():
    cards = plan_number_cards("매출 3조 원, 영업이익 2억 달러, 보너스 5만 원.", 30000, cooldown_ms=0)
    assert texts(cards) == ["3조 원", "2억 달러", "5만 원"]


def test_index_names_with_number():
    cards = plan_number_cards("코스피 2,650 마감, 니케이 38,000 기록, 항셍 17,000 돌파", 30000, cooldown_ms=0)
    assert texts(cards) == ["코스피 2,650", "니케이 38,000", "항셍 17,000"]
    sp = plan_number_cards("S&P 500 종가 7,230 기록했습니다.", 5000)
    assert texts(sp) == ["S&P 500 종가 7,230"]


def test_percent_wins_over_overlapping_index():
    cards = plan_number_cards("나스닥은 0.94% 상승했습니다.", 5000)
    assert texts(cards) == ["0.94%"]


def test_proportional_mapping_and_defaults():
    text = "가" * 50 + " 3.2% " + "나" * 44  # '3' at char 51 of 100
    cards = plan_number_cards(text, 10000)
    assert len(text) == 100
    assert cards == [{"text": "3.2%", "startMs": 5100, "durationMs": 1800, "tone": "neutral"}]


def test_tone_from_sentence_direction():
    cards = plan_number_cards(SAMPLE, 60000, cooldown_ms=0)
    assert [(c["text"], c["tone"]) for c in cards] == [
        ("S&P 500 종가 7,230", "neutral"),
        ("0.94%", "up"),
        ("3.2%", "up"),
        ("8%", "up"),
        ("18%", "down"),
    ]
    signed = plan_number_cards("A는 -2.1% 기록, B는 +4% 기록.", 20000, cooldown_ms=0)
    assert [c["tone"] for c in signed] == ["down", "up"]


def test_cooldown_2500():
    text = "1% 2% 3% " + "x" * 91  # 100자 / 10000ms -> 3자 간격 = 300ms
    assert len(plan_number_cards(text, 10000)) == 1
    spaced = ("1% " + "x" * 47) * 4  # 길이 200, 간격 50자 = 25000ms
    cards = plan_number_cards(spaced, 40000)
    starts = [c["startMs"] for c in cards]
    assert all(b - a >= 2500 for a, b in zip(starts, starts[1:]))
    assert len(cards) == 4


def test_max_cards_6_and_duration_1800():
    text = "".join(f"{i}% " + "x" * 20 for i in range(1, 15))
    cards = plan_number_cards(text, 140000)
    assert len(cards) == 6
    assert {c["durationMs"] for c in cards} == {1800}


def test_clamped_within_audio():
    cards = plan_number_cards("끝에 99% 입니다 99%", 3000, cooldown_ms=0)
    for c in cards:
        assert c["startMs"] + c["durationMs"] <= 3000
    short = plan_number_cards("5%", 1000)
    assert short[0]["durationMs"] == 1000 and short[0]["startMs"] == 0


def test_sample_content():
    cards = plan_number_cards(SAMPLE, 30000)
    assert 1 <= len(cards) <= 6
    assert cards[0]["text"] == "S&P 500 종가 7,230"
    assert [c["startMs"] for c in cards] == sorted(c["startMs"] for c in cards)


def test_empty_inputs():
    assert plan_number_cards("", 1000) == []
    assert plan_number_cards("숫자 없음", 1000) == []
    assert plan_number_cards("5%", 0) == []
