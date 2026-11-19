from md2short.caption_plan import (
    DEFAULT_CHUNK_SIZE,
    GAP_BOUNDARY_MS,
    MAX_CHUNK_SIZE,
    SENTENCE_END_CHARS,
    build_caption_line_segments,
)
from sample_words import SAMPLE_SENTENCES, build_words


def test_constants():
    assert SENTENCE_END_CHARS == ".!?。！？…"
    assert GAP_BOUNDARY_MS == 600
    assert DEFAULT_CHUNK_SIZE == 14
    assert MAX_CHUNK_SIZE == 24


def test_sentence_punctuation_boundaries():
    words = build_words(SAMPLE_SENTENCES[:3])
    segs = build_caption_line_segments(words)
    assert [s["text"] for s in segs] == [
        "지난 금요일 미국 증시, 강하게 상승 마감했습니다.",
        "5주 연속 상승, 2024년 이후 최장 랠리입니다.",
        "S&P 500 종가 7,230 기록했습니다.",
    ]
    assert [s["index"] for s in segs] == [0, 1, 2]
    assert segs[0]["wordStart"] == 0 and segs[0]["wordEnd"] == 7
    assert segs[1]["wordStart"] == 7
    assert segs[0]["startMs"] == words[0]["start"]
    assert segs[0]["endMs"] == words[6]["end"]


def test_all_sentence_end_chars():
    for ch in SENTENCE_END_CHARS:
        words = [
            {"text": f"가나{ch}", "start": 0, "end": 100},
            {"text": "다라", "start": 100, "end": 200},
        ]
        assert [s["text"] for s in build_caption_line_segments(words)] == [f"가나{ch}", "다라"]


def test_gap_boundary_at_600ms_inclusive():
    words = [
        {"text": "가", "start": 0, "end": 100},
        {"text": "나", "start": 700, "end": 800},  # gap 600 -> 경계
        {"text": "다", "start": 1399, "end": 1500},  # gap 599 -> 경계 아님
    ]
    segs = build_caption_line_segments(words)
    assert [s["text"] for s in segs] == ["가", "나 다"]


def test_chunk_size_cap_and_clamp():
    words = [{"text": f"w{i}", "start": i * 100, "end": i * 100 + 90} for i in range(10)]
    assert [len(s["text"].split()) for s in build_caption_line_segments(words, chunk_size=4)] == [4, 4, 2]
    assert len(build_caption_line_segments(words, chunk_size=0)) == 1  # 1 미만 → 기본 14 (Captions.tsx clampChunkSize)
    big = [{"text": f"w{i}", "start": i * 100, "end": i * 100 + 90} for i in range(30)]
    assert [len(s["text"].split()) for s in build_caption_line_segments(big, chunk_size=99)] == [24, 6]
    assert [len(s["text"].split()) for s in build_caption_line_segments(big)] == [14, 14, 2]


def test_skip_until_ms_excludes_opening_words():
    words = build_words(["오프닝 문구입니다.", "본문 시작입니다."])
    skip = words[1]["end"] + 1
    segs = build_caption_line_segments(words, skip_until_ms=skip)
    assert [s["text"] for s in segs] == ["본문 시작입니다."]
    assert segs[0]["wordStart"] == 2 and segs[0]["wordEnd"] == 4
    assert segs[0]["index"] == 0


def test_empty():
    assert build_caption_line_segments([]) == []


def test_skip_boundary_matches_captions_tsx():
    # Captions.tsx: visible = w.end > suppressUntilMs  →  end == skip 인 단어도 제외
    words = build_words(["오프닝 문구입니다.", "본문 시작입니다."])
    segs = build_caption_line_segments(words, skip_until_ms=words[1]["end"])
    assert segs[0]["wordStart"] == 2
