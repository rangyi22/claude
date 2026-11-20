"""호랑이 emoticon / 회사 로고 cue planner (architecture.md §5.8).

모든 선택은 deterministic — 같은 입력이면 같은 출력. 시간은 words.json 값만 사용.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from md2short.caption_plan import build_caption_line_segments

# 파일 stem -> 키워드. 키워드는 공백/기호 제거 후 부분 문자열로 매칭한다.
_FILE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "01_정독중_리포트": ("정독", "리포트", "보고서", "브리핑"),  # 마무리 인사("오늘 브리핑은…")
    "02_머리아파_혼란": ("머리아파", "혼란", "복잡", "헷갈"),
    "03_굿굿_칭찬": ("굿굿", "칭찬", "호평", "좋은 성과", "성과"),
    "04_나도울고싶어_하락": ("나도울고싶어", "울고싶", "하락", "내렸"),
    "05_분석중_차트": ("분석중", "차트", "분석", "그래프"),
    # 소폭 하락은 울음("내 돈…")이 아닌 관망 컷으로 (하락 강도 구분)
    "06_움직임없음_관망": ("움직임없음", "관망", "횡보", "보합", "소폭 하락", "소폭 내"),
    "07_승인완료_도장": ("승인완료", "승인", "도장", "공식 합류", "합류"),
    "08_전량매도_급락": ("전량매도", "급락", "매도세", "투매"),
    "09_가즈아_상승": ("가즈아", "상승", "올랐"),
    "10_살까말까_고민": ("살까말까", "고민", "망설"),
    "11_물타기가즈아_하락매수": ("물타기", "하락매수", "저가 매수"),
    "12_리포트작성_공부": ("리포트작성", "공부", "보고서 작성"),
    "13_이게뭔말이야_당황": ("이게뭔말이야", "당황", "어리둥절"),
    "14_상폐_장례식": ("상폐", "상장폐지", "장례식"),
    "15_존버중_버티기": ("존버", "버티기", "버텼"),
    "16_손절_컷": ("손절",),
    "17_익절각_매도": ("익절", "차익실현", "매도"),
    "18_테마주탑승_로켓": ("테마주", "로켓", "급등", "탑승"),
    "19_FOMO_추격매수": ("FOMO", "추격매수"),
    "20_깜짝성장_실적호조": ("깜짝성장", "실적호조", "실적", "호실적", "호조", "성장"),
    "21_소비심리추락_불안": ("소비심리", "불안", "추락"),
    "22_유가비상_원유급등": ("유가비상", "원유", "원유급등", "유가"),
    "23_총파업_초읽기": ("총파업", "파업", "초읽기"),
    "24_연준혼돈_금리불확실": ("연준", "연준혼돈", "금리불확실", "불확실"),
    "25_애플깜짝성장_실적호조": ("애플", "아이폰", "애플 호실적"),
    "26_반도체급등_로켓상승": ("반도체급등", "로켓상승", "반도체"),
    # 군복 + AI 서버 + 계약서 그림: 국방·방산 + AI 문장이 "공식 합류"(4자)보다 우선하도록 "국방부 AI"(5자)
    "27_AI계약_승인": ("AI계약", "AI", "계약", "국방부 AI", "국방부", "국방", "방산"),
    "28_폭락_패닉하락": ("폭락", "패닉"),
    "29_유가하락_오일약세": ("유가하락", "오일약세", "약세"),
    "30_랠리_상승파티": ("랠리", "상승파티", "연속 상승"),
    "31_매파_금리압박": ("매파", "금리압박", "금리 인상", "긴축"),
    "32_매파동결_국채금리급등": ("매파동결", "국채금리", "국채"),
    "33_유가급등_이란봉쇄": ("유가급등", "이란", "봉쇄", "이란봉쇄"),
    "34_내부분열_의견갈등": ("내부분열", "분열", "의견갈등", "갈등"),
    "35_돈태운다_현금소각": ("돈태운다", "현금소각", "소각", "적자"),
    "36_클라우드상승_성장": ("클라우드", "클라우드상승"),
    "37_검색강세_트렌드상승": ("검색", "검색강세", "트렌드"),
    "38_혼조세_증시갈림길": ("혼조", "혼조세", "갈림길"),
    "39_목표미달_AI수익성우려": ("목표미달", "수익성", "AI 수익성"),
    "40_실적대기_발표긴장": ("실적대기", "실적 발표", "발표 대기"),
    "41_반도체매도_주가하락": ("반도체매도", "주가하락", "반도체 하락"),
    "42_유가111달러_호르무즈위기": ("유가111달러", "111달러", "호르무즈"),
    "43_UAE탈퇴_OPEC불확실": ("UAE", "탈퇴", "OPEC", "오펙"),
    "44_평화협상_중동긴장완화": ("평화협상", "중동", "긴장완화", "평화"),
    "45_금리동결_FED기준금리": ("금리동결", "기준금리", "FED", "금리"),
    "46_사상최고치_지수신고가": ("사상최고치", "신고가", "최고치"),
    "47_협상교착_호르무즈긴장": ("협상교착", "교착", "호르무즈 긴장"),
    "48_특사취소_전화협상": ("특사", "전화협상", "취소"),
    "49_반도체18연속상승_강세마감": ("강세마감", "반도체18연속상승", "18연속", "상승 마감", "강세"),
    "50_포테크놀로지폭락_47퍼센트하락": ("47퍼센트", "포테크놀로지"),
    "51_퀄컴오픈AI협력설_AI협업": ("퀄컴", "오픈AI", "협력설", "협업"),
    "52_글로벌금리결정대기_중앙은행회의": ("중앙은행", "금리결정", "중앙은행회의"),
    "53_60일만료_전쟁권한법시한": ("전쟁권한법", "60일", "시한"),
    "54_다크이글배치_극초음속미사일": ("다크이글", "극초음속", "미사일"),
    "55_6500톤수령_군수물자지원": ("6500톤", "군수물자", "군수"),
    "56_아이언빔배치_UAE군사협력": ("아이언빔", "군사협력"),
    "57_여행금지_UAE긴급조치": ("여행금지", "긴급조치"),
    "58_봉쇄지속_유가급등": ("봉쇄지속", "봉쇄 지속"),
    "59_연쇄타격_물가환율압박": ("연쇄타격", "물가", "환율"),
    "60_카운트제외_휴전기간논리": ("휴전", "카운트제외", "카운트"),
}


def _norm(text: str) -> str:
    return re.sub(r"[^0-9a-z가-힣]", "", text.lower())


def _build_keywords() -> dict[str, str]:
    out: dict[str, str] = {}
    seen: dict[str, str] = {}
    for stem, keywords in _FILE_KEYWORDS.items():
        for kw in keywords:
            n = _norm(kw)
            if seen.get(n) == stem:
                continue  # 같은 파일 안의 공백 변형은 하나만 유지
            if n in seen:
                raise ValueError(f"duplicate emoticon keyword {kw!r}: {seen[n]} / {stem}")
            seen[n] = stem
            out[kw] = f"emoticon/{stem}.png"
    return out


EMOTICON_KEYWORDS: dict[str, str] = _build_keywords()

# 그림 안에 구체적 사실(지수·종목·수치)이 적힌 emoticon. 해당 토큰이 원고 span 에
# 실제로 있을 때만 쓴다 — 없는 사실("18연속", "사상 최고치")을 화면이 주장하지 않도록.
CLAIM_TOKENS: dict[str, tuple[str, ...]] = {
    "emoticon/21_소비심리추락_불안.png": ("소비심리",),
    "emoticon/22_유가비상_원유급등.png": ("유가", "원유"),
    "emoticon/24_연준혼돈_금리불확실.png": ("연준", "금리"),
    "emoticon/25_애플깜짝성장_실적호조.png": ("애플", "아이폰"),
    "emoticon/26_반도체급등_로켓상승.png": ("반도체",),
    "emoticon/27_AI계약_승인.png": ("ai",),
    "emoticon/29_유가하락_오일약세.png": ("유가", "오일", "원유"),
    "emoticon/32_매파동결_국채금리급등.png": ("국채",),
    "emoticon/33_유가급등_이란봉쇄.png": ("유가", "이란", "원유"),
    "emoticon/41_반도체매도_주가하락.png": ("반도체",),
    "emoticon/46_사상최고치_지수신고가.png": ("최고치", "신고가"),
    "emoticon/48_특사취소_전화협상.png": ("특사",),
    "emoticon/49_반도체18연속상승_강세마감.png": ("18연속",),
    "emoticon/51_퀄컴오픈AI협력설_AI협업.png": ("퀄컴", "오픈ai"),
    "emoticon/53_60일만료_전쟁권한법시한.png": ("전쟁권한법",),
    "emoticon/58_봉쇄지속_유가급등.png": ("봉쇄",),
    "emoticon/60_카운트제외_휴전기간논리.png": ("휴전",),
}

_UP_FILES = ("emoticon/09_가즈아_상승.png", "emoticon/30_랠리_상승파티.png", "emoticon/03_굿굿_칭찬.png")
# 가격이 아닌 '감소·부진'에도 걸리므로 투자 손실 컷("내 돈…", 전량매도)은 넣지 않는다.
_DOWN_FILES = ("emoticon/02_머리아파_혼란.png", "emoticon/13_이게뭔말이야_당황.png")
# 관망("움직여라 좀…")은 정체를 뜻하므로 중립 fallback 에 넣지 않는다 (보합·소폭 하락 키워드 전용).
_NEUTRAL_FILES = ("emoticon/05_분석중_차트.png", "emoticon/01_정독중_리포트.png", "emoticon/12_리포트작성_공부.png")
DEFAULT_EMOTICON = _NEUTRAL_FILES[0]

FALLBACK_CATEGORIES: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "상승": (("상승", "급등", "오르", "올랐", "강세", "증가", "개선", "돌파", "최고", "호조", "늘었", "늘어"), _UP_FILES),
    "하락": (("하락", "급락", "내리", "떨어", "부진", "감소", "악화", "약세", "줄었", "줄어"), _DOWN_FILES),
    "중립": ((), _NEUTRAL_FILES),
}

# (정규화 키워드, 원본 키워드, 파일, 순서) — 길이 내림차순 스캔용
_INDEXED = [(_norm(k), k, f, i) for i, (k, f) in enumerate(EMOTICON_KEYWORDS.items())]

SPARSE_COOLDOWN_MS = 3000
SPARSE_DURATION_MS = 2200
SPARSE_MAX_CUES = 24
LOOKAHEAD_WORDS = 2
_CROSS_PENALTY = 0.5
_ASCII_LETTER = re.compile(r"[a-z]")


def _find_matches(norm_text: str, core_len: int) -> list[tuple[float, int, str, str]]:
    """norm_text에서 core_len 이전에 시작하는 keyword match. (score, order, keyword, file)."""
    found: list[tuple[float, int, str, str]] = []
    for nkw, kw, fname, order in _INDEXED:
        if not nkw:
            continue
        ascii_only = nkw.isascii() and not nkw.isdigit()
        start = norm_text.find(nkw)
        while start != -1 and start < core_len:
            end = start + len(nkw)
            if ascii_only and (
                (start > 0 and _ASCII_LETTER.match(norm_text[start - 1]))
                or (end < len(norm_text) and _ASCII_LETTER.match(norm_text[end]))
            ):
                start = norm_text.find(nkw, start + 1)
                continue
            score = float(len(nkw)) - (_CROSS_PENALTY if end > core_len else 0.0)
            found.append((score, order, kw, fname))
            break
    found.sort(key=lambda m: (-m[0], m[1]))
    return found


def _span_candidates(words: list[dict], start: int, end: int) -> list[tuple[float, int, str, str]]:
    core = "".join(_norm(str(w["text"])) for w in words[start:end])
    ahead = "".join(_norm(str(w["text"])) for w in words[end : end + LOOKAHEAD_WORDS])
    return _find_matches(core + ahead, len(core))


def _text_candidates(text: str) -> list[tuple[float, int, str, str]]:
    norm = _norm(text)
    return _find_matches(norm, len(norm)) if norm else []


def _claim_ok(file: str, norm_text: str) -> bool:
    tokens = CLAIM_TOKENS.get(file)
    return tokens is None or any(_norm(t) in norm_text for t in tokens)


def _fallback_pool(text: str) -> tuple[str, ...]:
    norm = _norm(text)
    for _name, (triggers, files) in FALLBACK_CATEGORIES.items():
        if triggers and any(t in norm for t in triggers):
            return files
    return _NEUTRAL_FILES


def _rotated(pool: tuple[str, ...], span_index: int) -> list[str]:
    return [pool[(span_index + k) % len(pool)] for k in range(len(pool))]


def _fallback_file(text: str, span_index: int, prev: str | None) -> str:
    rotated = _rotated(_fallback_pool(text), span_index)
    return next((c for c in rotated if c != prev), rotated[0])


def _fresh_fallback(text: str, span_index: int, prev: str | None, avoid: frozenset[str]) -> str | None:
    """카테고리 pool → 중립 pool 순으로 avoid·prev 에 없는 파일. 없으면 None."""
    for pool in (_fallback_pool(text), _NEUTRAL_FILES):
        for choice in _rotated(pool, span_index):
            if choice not in avoid and choice != prev:
                return choice
    return None


def _cue(file: str, start: int, duration: int, keyword: str) -> dict[str, Any]:
    return {
        "emoticonFileName": file,
        "startMs": int(start),
        "durationMs": int(duration),
        "keyword": keyword,
        "assetKind": "emoticon",
        "visualMode": "emoticon",
    }


def _spans(words: list[dict], segments: list[dict] | None) -> list[tuple[int, int, str]]:
    """(wordStart, wordEnd, direction). direction 은 스토리보드 `화면 연출` (없으면 "")."""
    if segments is None:
        segments = build_caption_line_segments(words)
    spans: list[tuple[int, int, str]] = []
    for seg in segments:
        if "wordStart" in seg and "wordEnd" in seg:
            s, e = int(seg["wordStart"]), int(seg["wordEnd"])
        else:
            idx = [i for i, w in enumerate(words) if seg["startMs"] <= w["start"] < seg["endMs"]]
            if not idx:
                continue
            s, e = idx[0], idx[-1] + 1
        if e > s:
            spans.append((s, e, str(seg.get("direction") or "")))
    return spans


# 주제 연속 판단에서 제외할 방향·감정어 (정규화 형태). 이런 단어만 겹치면 같은 주제로 보지 않는다.
_DIRECTION_KEYWORDS = frozenset(
    _norm(k)
    for k in (
        "상승", "하락", "급등", "급락", "올랐", "내렸", "강세", "약세", "폭락", "추락", "매도", "상승 마감",
        "연속 상승", "소폭 하락", "소폭 내", "강세마감", "나도울고싶어", "울고싶", "가즈아", "성장", "성과",
        "좋은 성과", "칭찬", "굿굿", "패닉", "투매", "매도세",
    )
)
_CONTINUATION_PREFIXES = ("이는", "이번", "이로써", "이에", "이 같은", "이와")


def _continues_topic(prev_file: str, text: str) -> bool:
    """지시어로 시작하거나, 직전 컷의 주제 키워드(방향어 제외)가 현재 문장에 있으면 같은 주제."""
    if text.lstrip().startswith(_CONTINUATION_PREFIXES):
        return True
    stem = prev_file.removeprefix("emoticon/").removesuffix(".png")
    norm = _norm(text)
    return any(
        (k := _norm(kw)) and k not in _DIRECTION_KEYWORDS and k in norm for kw in _FILE_KEYWORDS.get(stem, ())
    )


def plan_cues(
    words: list[dict],
    segments: list[dict] | None = None,
    fill_gaps: bool = True,
    max_cues: int = SPARSE_MAX_CUES,
    lead_in_ms: int | None = None,
) -> list[dict[str, Any]]:
    """words -> emoticon cue 목록. fill_gaps=True는 span당 1 cue, 개수 제한 없음.

    선택 우선순위: 아직 안 쓴 키워드 매칭 > (같은 주제면) 직전 컷 유지 > 안 쓴 fallback > 직전과 다른 키워드 매칭 > fallback.
    직전 컷 유지는 새 cue 를 만들지 않고 직전 cue 의 durationMs 를 늘린다 (같은 그림으로 crossfade 하지 않음).
    lead_in_ms 가 주어지면 첫 cue 를 그 시점(예: opening 종료, words.json 기준)부터 시작해 빈 화면을 없앤다.
    """
    if not words:
        return []
    if not fill_gaps:
        return _plan_sparse(words, max_cues)

    spans = _spans(words, segments)
    texts = [" ".join(str(w["text"]) for w in words[s:e]) for s, e, _d in spans]
    # 스토리보드 `화면 연출`이 있으면 그 키워드를 우선 사용한다 (architecture.md §5.1).
    all_cands = [
        [c for c in _text_candidates(d) + _span_candidates(words, s, e) if _claim_ok(c[3], _norm(text + d))]
        for (s, e, d), text in zip(spans, texts)
    ]
    # 각 span 의 1순위 키워드 파일은 fallback 이 먼저 가져가지 않도록 예약한다.
    reserved = {cands[0][3] for cands in all_cands if cands}
    cues: list[dict[str, Any]] = []
    prev: str | None = None
    used: set[str] = set()
    for n, ((s, e, _direction), text, cands) in enumerate(zip(spans, texts, all_cands)):
        fresh = next(((f, kw) for _sc, _o, kw, f in cands if f not in used and f != prev), None)
        last_end = int(words[e - 1]["end"])
        end_ms = max(int(words[spans[n + 1][0]]["start"]), last_end) if n + 1 < len(spans) else last_end
        if fresh is None and prev is not None and cues and _continues_topic(prev, text):
            cues[-1]["durationMs"] = max(1, end_ms - cues[-1]["startMs"])
            continue
        if fresh is not None:
            file, keyword = fresh
        else:
            avoid = frozenset(used | (reserved - {c[3] for c in cands}))
            alt = _fresh_fallback(text, n, prev, avoid)
            reuse = next(((f, kw) for _sc, _o, kw, f in cands if f != prev), None)
            if alt is not None:
                file, keyword = alt, ""
            elif reuse is not None:
                file, keyword = reuse
            else:
                file, keyword = _fallback_file(text, n, prev), ""
        start = int(words[s]["start"])
        if n == 0 and lead_in_ms is not None:
            start = min(start, max(0, int(lead_in_ms)))
        cues.append(_cue(file, start, max(1, end_ms - start), keyword))
        prev = file
        used.add(file)
    return cues


def _plan_sparse(words: list[dict], max_cues: int) -> list[dict[str, Any]]:
    audio_end = int(words[-1]["end"])
    cues: list[dict[str, Any]] = []
    last_start = -SPARSE_COOLDOWN_MS
    for i, w in enumerate(words):
        if len(cues) >= max_cues:
            break
        start = int(w["start"])
        if start - last_start < SPARSE_COOLDOWN_MS:
            continue
        claim_text = "".join(_norm(str(x["text"])) for x in words[max(0, i - 8) : i + 8])
        cands = [c for c in _span_candidates(words, i, i + 1) if _claim_ok(c[3], claim_text)]
        if not cands:
            continue
        _score, _order, keyword, file = cands[0]
        cues.append(_cue(file, start, SPARSE_DURATION_MS, keyword))
        last_start = start
    for k, cue in enumerate(cues):
        limit = cues[k + 1]["startMs"] if k + 1 < len(cues) else audio_end
        cue["durationMs"] = max(1, min(cue["durationMs"], limit - cue["startMs"]))
    return cues


def all_highlight_keywords(source: list[dict] | str) -> list[str]:
    """자막 강조용: source에 등장하는 EMOTICON_KEYWORDS 키워드를 최초 등장 순으로 (중복 제거)."""
    text = source if isinstance(source, str) else " ".join(str(w["text"]) for w in source)
    norm = _norm(text)
    hits = sorted((norm.find(_norm(kw)), order, kw) for _s, order, kw, _f in _find_matches(norm, len(norm)))
    return [kw for _p, _o, kw in hits]


# ---------------------------------------------------------------- 회사 로고

COMPANY_LOGOS: dict[str, dict[str, Any]] = {
    "apple": {"name": "Apple", "ticker": "AAPL", "aliases": ("애플", "Apple")},
    "oracle": {"name": "Oracle", "ticker": "ORCL", "aliases": ("오라클", "Oracle")},
    "roblox": {"name": "Roblox", "ticker": "RBLX", "aliases": ("로블록스", "Roblox")},
    "sandisk": {"name": "SanDisk", "ticker": "SNDK", "aliases": ("샌디스크", "SanDisk")},
    "nvidia": {"name": "NVIDIA", "ticker": "NVDA", "aliases": ("엔비디아", "NVIDIA")},
    "microsoft": {"name": "Microsoft", "ticker": "MSFT", "aliases": ("마이크로소프트", "Microsoft")},
    "google": {"name": "Google", "ticker": "GOOGL", "aliases": ("구글", "Google")},
    "amazon": {"name": "Amazon", "ticker": "AMZN", "aliases": ("아마존", "Amazon")},
    "tesla": {"name": "Tesla", "ticker": "TSLA", "aliases": ("테슬라", "Tesla")},
    "meta": {"name": "Meta", "ticker": "META", "aliases": ("메타", "Meta")},
    "qualcomm": {"name": "Qualcomm", "ticker": "QCOM", "aliases": ("퀄컴", "Qualcomm")},
    "openai": {"name": "OpenAI", "ticker": "", "aliases": ("오픈AI", "오픈에이아이", "OpenAI")},
}
for _slug, _info in COMPANY_LOGOS.items():
    _info["logoFileName"] = f"company/{_slug}.png"
    _info["label"] = _info["aliases"][0]  # 배지에 쓰는 한글 이름

MIN_LOGO_DURATION_MS = 1500
_JOSA = frozenset(
    "은 는 이 가 을 를 의 와 과 도 에 로 만 랑 인 에서 으로 에는 에도 에게 까지 부터 처럼 보다 라고 이라고 이나 나 이란 란 와의 과의 의".split()
)
_ALIAS_INDEX = sorted(
    ((_norm(a), slug) for slug, info in COMPANY_LOGOS.items() for a in info["aliases"]),
    key=lambda t: (-len(t[0]), t[0]),
)


def _company_at(words: list[dict], i: int) -> tuple[str, int] | None:
    for length in (1, 2):
        if i + length > len(words):
            break
        text = "".join(_norm(str(w["text"])) for w in words[i : i + length])
        for alias, slug in _ALIAS_INDEX:
            if text.startswith(alias) and text[len(alias):] in _JOSA | {""}:
                # 2단어 조합은 두 번째 단어가 실제로 쓰일 때만 (alias가 첫 단어를 넘어야 함)
                if length == 2 and len(alias) <= len(_norm(str(words[i]["text"]))):
                    continue
                return slug, length
    return None


def _segment_end_ms(segments: list[dict] | None, word_index: int) -> int | None:
    for seg in segments or []:
        if "wordStart" in seg and "wordEnd" in seg and int(seg["wordStart"]) <= word_index < int(seg["wordEnd"]):
            return int(seg["endMs"])
    return None


def plan_company_logo_cues(
    words: list[dict], segments: list[dict] | None = None, logo_dir: Path | None = None
) -> list[dict[str, Any]]:
    """회사명 언급 -> 로고 cue. segments 가 있으면 그 문장 끝까지 노출 (최소 MIN_LOGO_DURATION_MS).

    `logo_dir/<slug>.png` 실제 로고가 있을 때만 logoFileName 을 채우고, 없으면 "" —
    Remotion 은 이때 한글 이름 + 티커 텍스트 배지를 그린다 (상표 이미지 없이도 표시 가능).
    같은 회사의 cue 구간이 겹치는 재언급은 건너뛴다.
    """
    if not words:
        return []
    audio_end = int(words[-1]["end"])
    cues: list[dict[str, Any]] = []
    active_until: dict[str, int] = {}
    i = 0
    while i < len(words):
        hit = _company_at(words, i)
        if hit is None:
            i += 1
            continue
        slug, length = hit
        start = int(words[i]["start"])
        if start >= active_until.get(slug, -1):
            span_end = _segment_end_ms(segments, i) or int(words[i + length - 1]["end"])
            duration = min(max(MIN_LOGO_DURATION_MS, span_end - start), max(1, audio_end - start))
            info = COMPANY_LOGOS[slug]
            has_logo = logo_dir is not None and (Path(logo_dir) / f"{slug}.png").is_file()
            cues.append(
                {
                    "logoFileName": info["logoFileName"] if has_logo else "",
                    "name": info["name"],
                    "label": info["label"],
                    "ticker": info["ticker"],
                    "startMs": start,
                    "durationMs": duration,
                }
            )
            active_until[slug] = start + duration
        i += length
    return cues
