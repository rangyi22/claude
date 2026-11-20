from pathlib import Path

from md2short import emoticon_map as em
from md2short.caption_plan import build_caption_line_segments
from md2short.emoticon_map import (
    COMPANY_LOGOS,
    EMOTICON_KEYWORDS,
    all_highlight_keywords,
    plan_company_logo_cues,
    plan_cues,
)
from sample_words import SAMPLE_SENTENCES, build_words

ROOT = Path(__file__).resolve().parent.parent


def test_all_60_files_referenced_and_exist():
    on_disk = {f"emoticon/{p.name}" for p in (ROOT / "emoticon").glob("*.png")}
    assert len(on_disk) == 60
    assert set(EMOTICON_KEYWORDS.values()) == on_disk
    for rel in EMOTICON_KEYWORDS.values():
        assert (ROOT / rel).is_file()
    for f in (*em._UP_FILES, *em._DOWN_FILES, *em._NEUTRAL_FILES):
        assert f in on_disk


def test_determinism():
    words = build_words(SAMPLE_SENTENCES)
    assert plan_cues(words) == plan_cues(words)
    assert plan_cues(words, fill_gaps=False) == plan_cues(words, fill_gaps=False)


def test_one_cue_per_span_and_fill_to_end():
    words = build_words(SAMPLE_SENTENCES)
    segs = build_caption_line_segments(words)
    cues = plan_cues(words, segments=segs)
    assert len(cues) == len(segs) == len(SAMPLE_SENTENCES)
    assert [c["startMs"] for c in cues] == [s["startMs"] for s in segs]
    assert cues[-1]["startMs"] + cues[-1]["durationMs"] == words[-1]["end"]
    for a, b in zip(cues, cues[1:]):
        assert a["startMs"] + a["durationMs"] == b["startMs"]
    for c in cues:
        assert c["assetKind"] == "emoticon" and c["visualMode"] == "emoticon"
        assert c["emoticonFileName"].startswith("emoticon/")
    # segments 미지정이어도 동일 (caption_plan 기본 분할)
    assert plan_cues(words) == cues


def test_no_cue_limit_when_filling():
    words = build_words([f"문장 {i} 입니다." for i in range(60)])
    assert len(plan_cues(words)) == 60


def test_no_consecutive_duplicates():
    words = build_words(["상승했습니다."] * 6)
    files = [c["emoticonFileName"] for c in plan_cues(words)]
    assert all(a != b for a, b in zip(files, files[1:]))


def test_specific_keyword_wins():
    words = build_words(["유가 급등 소식입니다."])
    assert plan_cues(words)[0]["emoticonFileName"] == EMOTICON_KEYWORDS["유가급등"]
    assert plan_cues(words)[0]["keyword"] == "유가급등"
    words = build_words(["반도체 18연속 상승 마감했습니다."])
    assert plan_cues(words)[0]["emoticonFileName"] == EMOTICON_KEYWORDS["상승 마감"]
    words = build_words(["애플, 호실적으로 3.2% 상승했습니다."])
    assert plan_cues(words)[0]["emoticonFileName"] == EMOTICON_KEYWORDS["애플 호실적"]


def test_claim_emoticon_requires_fact_in_text():
    # 그림에 "18연속 / 반도체"가 적힌 컷은 원고에 18연속이 없으면 쓰지 않는다
    cue = plan_cues(build_words(["강하게 상승 마감했습니다."]))[0]
    assert cue["emoticonFileName"] != EMOTICON_KEYWORDS["18연속"]
    # "약세" 만으로 유가하락 컷, 상승 fallback 으로 사상최고치 컷이 나오면 안 된다
    assert plan_cues(build_words(["달러가 약세입니다."]))[0]["emoticonFileName"] != EMOTICON_KEYWORDS["오일약세"]
    for c in plan_cues(build_words(["지수가 많이 올랐습니다."] * 5)):
        assert c["emoticonFileName"] != EMOTICON_KEYWORDS["사상최고치"]
    assert plan_cues(build_words(["나스닥 사상 최고치 경신."]))[0]["emoticonFileName"] == EMOTICON_KEYWORDS["최고치"]
    for fname in em.CLAIM_TOKENS:
        assert fname in EMOTICON_KEYWORDS.values()


def test_mild_vs_severe_decline():
    mild = plan_cues(build_words(["다우는 소폭 하락했습니다."]))[0]
    severe = plan_cues(build_words(["로블록스가 18% 급락했습니다."]))[0]
    assert mild["emoticonFileName"] == EMOTICON_KEYWORDS["관망"]
    assert severe["emoticonFileName"] == EMOTICON_KEYWORDS["급락"]
    # 가격과 무관한 '감소'에는 투자 손실 컷("내 돈…")을 쓰지 않는다
    loss_cuts = (EMOTICON_KEYWORDS["하락"], EMOTICON_KEYWORDS["급락"], EMOTICON_KEYWORDS["폭락"])
    # fallback pool 은 span 순서로 회전하므로 어느 위치에 와도 손실 컷이 나오면 안 된다
    for n in range(6):
        cues = plan_cues(build_words([f"문장 {i} 입니다." for i in range(n)] + ["사용자 감소로 이어졌습니다."]))
        assert cues[-1]["emoticonFileName"] not in loss_cuts


def test_prefers_unused_emoticons():
    files = [c["emoticonFileName"] for c in plan_cues(build_words(SAMPLE_SENTENCES))]
    assert len(set(files)) == len(files)
    # 뒤 문장의 1순위 키워드 컷(좋은 성과 -> 굿굿)은 앞 문장 fallback 이 먼저 가져가지 않는다
    words = build_words(["주가가 상승했습니다.", "랠리가 이어졌습니다.", "상승 랠리입니다.", "좋은 성과입니다."])
    assert plan_cues(words)[-1]["emoticonFileName"] == EMOTICON_KEYWORDS["좋은 성과"]


def test_oneul_is_not_rise_trigger():
    cue = plan_cues(build_words(["오늘 장 흐름도 주목하시기 바랍니다."]))[0]
    assert cue["emoticonFileName"] in em._NEUTRAL_FILES


def test_lead_in_starts_first_cue_early():
    words = [{"text": "가", "start": 3000, "end": 3500}, {"text": "나.", "start": 3600, "end": 4000}]
    assert plan_cues(words, lead_in_ms=2400)[0]["startMs"] == 2400
    assert plan_cues(words, lead_in_ms=2400)[0]["durationMs"] == 4000 - 2400
    assert plan_cues(words)[0]["startMs"] == 3000


def test_fallback_categories_and_neutral():
    up = plan_cues(build_words(["지수가 많이 올랐습니다 확인."]))
    # '올랐' 은 키워드(상승 파일)
    assert up[0]["emoticonFileName"] in em._UP_FILES
    down = plan_cues(build_words(["거래량이 감소했습니다."]))
    assert down[0]["emoticonFileName"] in em._DOWN_FILES and down[0]["keyword"] == ""
    neutral = plan_cues(build_words(["그렇습니다."]))
    assert neutral[0]["emoticonFileName"] in em._NEUTRAL_FILES


def test_lookahead_across_boundary():
    # 키워드 '반도체'는 span 마지막 단어에서 시작하고 다음 단어까지 이어짐 ("반도체" + "급등" -> 반도체급등)
    words = [
        {"text": "오늘", "start": 0, "end": 300},
        {"text": "반도체", "start": 300, "end": 600},
        {"text": "급등했습니다.", "start": 600, "end": 900},
    ]
    segs = [
        {"index": 0, "startMs": 0, "endMs": 600, "text": "오늘 반도체", "wordStart": 0, "wordEnd": 2},
        {"index": 1, "startMs": 600, "endMs": 900, "text": "급등했습니다.", "wordStart": 2, "wordEnd": 3},
    ]
    cues = plan_cues(words, segments=segs)
    assert cues[0]["emoticonFileName"] == EMOTICON_KEYWORDS["반도체급등"]
    # 키워드가 lookahead 영역에서만 시작하면 이 span에는 적용 안 됨
    only_ahead = plan_cues(words[:1] + words[2:], segments=None)
    assert only_ahead


def test_sparse_path_limits():
    words = build_words(["상승했습니다."] * 200, word_ms=1000)
    cues = plan_cues(words, fill_gaps=False)
    assert 0 < len(cues) <= 24
    starts = [c["startMs"] for c in cues]
    assert all(b - a >= em.SPARSE_COOLDOWN_MS for a, b in zip(starts, starts[1:]))
    assert all(c["durationMs"] <= em.SPARSE_DURATION_MS for c in cues)
    assert cues[-1]["startMs"] + cues[-1]["durationMs"] <= words[-1]["end"]
    assert len(plan_cues(words, fill_gaps=False, max_cues=3)) == 3


def test_empty_words():
    assert plan_cues([]) == []
    assert plan_company_logo_cues([]) == []


def test_all_highlight_keywords():
    kws = all_highlight_keywords("나스닥은 소폭 하락, 애플은 호실적으로 상승했습니다. AI 시장")
    assert "하락" in kws and "호실적" in kws and "AI" in kws
    assert kws == all_highlight_keywords(build_words(["나스닥은 소폭 하락, 애플은 호실적으로 상승했습니다. AI 시장"]))
    assert len(kws) == len(set(kws))
    assert all_highlight_keywords("해당 없음 문장") == []
    assert "AI" not in all_highlight_keywords("mail air")


def test_company_logos_dict():
    for slug in ("apple", "oracle", "roblox", "sandisk", "nvidia", "microsoft", "google",
                 "amazon", "tesla", "meta", "qualcomm", "openai"):
        assert COMPANY_LOGOS[slug]["logoFileName"] == f"company/{slug}.png"


def test_company_logo_cues_sample():
    words = build_words(SAMPLE_SENTENCES)
    audio_end = words[-1]["end"]
    cues = plan_company_logo_cues(words)
    assert [c["logoFileName"] for c in cues] == [
        "company/apple.png", "company/sandisk.png", "company/oracle.png", "company/roblox.png"
    ]
    assert [c["name"] for c in cues] == ["Apple", "SanDisk", "Oracle", "Roblox"]
    for c in cues:
        assert c["durationMs"] >= 1500 or c["startMs"] + c["durationMs"] == audio_end
        assert c["startMs"] + c["durationMs"] <= audio_end
    apple_word = next(w for w in words if w["text"].startswith("애플"))
    assert cues[0]["startMs"] == apple_word["start"]
    assert cues[-1]["startMs"] + cues[-1]["durationMs"] == audio_end  # 오디오 끝에서 clamp


def test_company_logo_english_josa_and_openai():
    words = build_words(["Apple 과 NVIDIA 그리고 오픈 AI 와 메타버스 구글이 퀄컴 마이크로소프트."])
    slugs = [c["logoFileName"] for c in plan_company_logo_cues(words)]
    assert slugs == [
        "company/apple.png", "company/nvidia.png", "company/openai.png",
        "company/google.png", "company/qualcomm.png", "company/microsoft.png",
    ]  # 메타버스는 meta가 아님


def test_company_logo_repeat_mention_inside_active_window_skipped():
    words = build_words(["애플 애플 애플 호실적."], word_ms=300)
    assert len(plan_company_logo_cues(words)) == 1


def test_storyboard_direction_drives_emoticon_choice():
    from md2short.emoticon_map import EMOTICON_KEYWORDS, plan_cues

    words = [
        {"text": "오늘도", "start": 0, "end": 300},
        {"text": "시장을", "start": 320, "end": 600},
        {"text": "봅니다.", "start": 620, "end": 900},
    ]
    seg = {"index": 0, "startMs": 0, "endMs": 900, "text": "오늘도 시장을 봅니다.", "wordStart": 0, "wordEnd": 3, "direction": "호랑이가 로켓을 타고 가즈아"}
    cues = plan_cues(words, segments=[seg])
    assert len(cues) == 1
    assert cues[0]["emoticonFileName"] == EMOTICON_KEYWORDS[cues[0]["keyword"]]
    assert cues[0]["keyword"] in seg["direction"].replace(" ", "")
