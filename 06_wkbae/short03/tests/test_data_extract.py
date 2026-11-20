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
    assert texts(sp) == ["S&P 500 7,230"]


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
        ("S&P 500 7,230", "neutral"),
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
    assert cards[0]["text"] == "S&P 500 7,230"
    assert [c["startMs"] for c in cards] == sorted(c["startMs"] for c in cards)


def test_empty_inputs():
    assert plan_number_cards("", 1000) == []
    assert plan_number_cards("숫자 없음", 1000) == []
    assert plan_number_cards("5%", 0) == []


def test_index_card_drops_particles():
    assert texts(plan_number_cards("S&P 500 종가는 7,230을 기록했습니다.", 5000)) == ["S&P 500 7,230"]


def test_tone_ignores_decimal_point():
    from md2short.data_extract import _tone

    text = "나스닥은 0.94% 상승했습니다."
    assert _tone(text, 0, 3) == "up"


SEGS = [
    {"startMs": 0, "endMs": 1000, "text": "지난 금요일 상승 마감했습니다."},
    {"startMs": 1000, "endMs": 2000, "text": "S&P 500 종가는 7,230을 기록했습니다."},
    {"startMs": 2000, "endMs": 3000, "text": "나스닥은 0.94% 상승했습니다."},
    {"startMs": 3000, "endMs": 4000, "text": "다우는 소폭 하락했습니다."},
    {"startMs": 4000, "endMs": 5000, "text": "애플은 3.2% 상승했습니다."},
]


def test_index_board_rows_and_timing():
    from md2short.data_extract import plan_index_board

    board = plan_index_board(SEGS)
    assert board == {
        "rows": [
            {"name": "S&P 500", "value": "7,230", "tone": "neutral", "startMs": 1000},
            {"name": "나스닥", "value": "0.94%", "tone": "up", "startMs": 2000},
            {"name": "다우", "value": "", "tone": "down", "startMs": 3000},
        ],
        "startMs": 1000,
        "durationMs": 3000,
    }
    assert plan_index_board(SEGS[:2]) is None  # 지수 1개면 보드 없음
    assert plan_index_board([]) is None


def test_cards_inside_board_window_are_dropped():
    from md2short.data_extract import drop_cards_in_window

    cards = [{"text": "a", "startMs": 500}, {"text": "b", "startMs": 2500}, {"text": "c", "startMs": 4500}]
    board = {"rows": [], "startMs": 1000, "durationMs": 3000}
    assert [c["text"] for c in drop_cards_in_window(cards, board)] == ["a", "c"]
    assert drop_cards_in_window(cards, None) == cards



def test_card_start_uses_words_json_timing():
    words = [
        {"text": "애플은", "start": 0, "end": 300},
        {"text": "3.2%", "start": 400, "end": 900},
        {"text": "상승.", "start": 950, "end": 1200},
        {"text": "로블록스는", "start": 5000, "end": 5400},
        {"text": "18%", "start": 5500, "end": 5900},
        {"text": "급락.", "start": 6000, "end": 6300},
    ]
    script = "애플은 3.2% 상승. 로블록스는 18% 급락."
    cards = plan_number_cards(script, 10000, words=words)
    assert [(c["text"], c["startMs"]) for c in cards] == [("3.2%", 400), ("18%", 5500)]


def test_card_word_match_respects_number_boundary():
    # "8%" 카드가 앞의 "18%" 단어에 잘못 매칭되면 안 된다
    words = [{"text": "18%", "start": 100, "end": 400}, {"text": "8%", "start": 3000, "end": 3300}]
    cards = plan_number_cards("A 18% B 8%", 10000, cooldown_ms=0, words=words)
    assert [c["startMs"] for c in cards] == [100, 3000]


def test_card_falls_back_to_proportional_when_no_word():
    cards = plan_number_cards("가" * 50 + " 3.2% " + "나" * 44, 10000, words=[{"text": "없음", "start": 0, "end": 1}])
    assert cards[0]["startMs"] == 5100


def test_headline_from_hook_segment():
    from md2short.data_extract import plan_headline

    seg = {"startMs": 280, "endMs": 5560, "text": "5주 연속 상승을 기록하며 2024년 이후 최장 랠리를 이어갔습니다."}
    assert plan_headline([seg]) == {"lines": ["5주 연속 상승", "2024년 이후 최장"], "startMs": 280, "durationMs": 5280}
    ordinal = {"startMs": 0, "endMs": 10, "text": "4월 기준으로는 1950년 이후 두 번째로 좋은 성과입니다."}
    ordinal_headline = plan_headline([ordinal])
    assert ordinal_headline is not None and ordinal_headline["lines"] == ["1950년 이후 두 번째"]
    assert plan_headline([{"startMs": 0, "endMs": 10, "text": "지난 금요일 상승했습니다."}]) is None
    assert plan_headline([]) is None


def test_cards_dropped_in_headline_and_board_windows():
    from md2short.data_extract import drop_cards_in_window

    cards = [{"text": "a", "startMs": 100}, {"text": "b", "startMs": 2500}, {"text": "c", "startMs": 9000}]
    head = {"startMs": 0, "durationMs": 1000}
    board = {"startMs": 2000, "durationMs": 1000}
    assert [c["text"] for c in drop_cards_in_window(cards, head, board)] == ["c"]



def test_headline_strips_verb_endings():
    from md2short.data_extract import plan_headline

    def lines(text):
        h = plan_headline([{"startMs": 0, "endMs": 10, "text": text}])
        return h["lines"] if h else None

    # 조사 + 서술 어미(하며/하고/했고/했으며/하면서/하는/했다)는 명사구에서 제거된다
    assert lines("미국 증시가 5주 연속 상승하며 2024년 이후 최장 랠리를 기록했습니다.") == ["5주 연속 상승", "2024년 이후 최장"]
    assert lines("5주 연속 상승하고 있습니다.") == ["5주 연속 상승"]
    assert lines("3일 연속 하락했고 반등했습니다.") == ["3일 연속 하락"]
    assert lines("5주 연속 상승했으며 안정적입니다.") == ["5주 연속 상승"]
    assert lines("5주 연속 상승하면서 마감했습니다.") == ["5주 연속 상승"]
    assert lines("5주 연속 상승하는 흐름입니다.") == ["5주 연속 상승"]
    assert lines("5주 연속 하락했다.") == ["5주 연속 하락"]
    # 기존 조사 규칙은 그대로
    assert lines("5주 연속 상승을 기록했습니다.") == ["5주 연속 상승"]
