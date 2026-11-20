"""호랑이 emoticon / 회사 로고 cue planner (architecture.md §5.8).

모든 선택은 deterministic — 같은 입력이면 같은 출력. 시간은 words.json 값만 사용.
"""

from __future__ import annotations

import re
from typing import Any

from md2short.caption_plan import build_caption_line_segments

# 파일 stem -> 키워드. 키워드는 공백/기호 제거 후 부분 문자열로 매칭한다.
_FILE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "01_정독중_리포트": ("정독", "리포트", "보고서"),
    "02_머리아파_혼란": ("머리아파", "혼란", "복잡", "헷갈"),
    "03_굿굿_칭찬": ("굿굿", "칭찬", "호평", "좋은 성과", "성과"),
    "04_나도울고싶어_하락": ("나도울고싶어", "울고싶", "하락", "소폭 하락", "내렸"),
    "05_분석중_차트": ("분석중", "차트", "분석", "그래프"),
    "06_움직임없음_관망": ("움직임없음", "관망", "횡보", "보합"),
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
    "27_AI계약_승인": ("AI계약", "AI", "계약"),
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

_UP_FILES = ("emoticon/09_가즈아_상승.png", "emoticon/30_랠리_상승파티.png", "emoticon/46_사상최고치_지수신고가.png")
_DOWN_FILES = ("emoticon/04_나도울고싶어_하락.png", "emoticon/08_전량매도_급락.png", "emoticon/28_폭락_패닉하락.png")
_NEUTRAL_FILES = ("emoticon/06_움직임없음_관망.png", "emoticon/05_분석중_차트.png", "emoticon/01_정독중_리포트.png")
DEFAULT_EMOTICON = _NEUTRAL_FILES[0]

FALLBACK_CATEGORIES: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "상승": (("오르", "올랐", "강세", "증가", "개선", "돌파", "최고", "호조", "늘"), _UP_FILES),
    "하락": (("내리", "떨어", "부진", "감소", "악화", "약세", "줄"), _DOWN_FILES),
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


def _fallback_file(text: str, span_index: int, prev: str | None) -> str:
    norm = _norm(text)
    pool: tuple[str, ...] = _NEUTRAL_FILES
    for _name, (triggers, files) in FALLBACK_CATEGORIES.items():
        if triggers and any(t in norm for t in triggers):
            pool = files
            break
    choice = pool[span_index % len(pool)]
    if choice == prev:
        choice = pool[(span_index + 1) % len(pool)]
    return choice


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


def plan_cues(
    words: list[dict],
    segments: list[dict] | None = None,
    fill_gaps: bool = True,
    max_cues: int = SPARSE_MAX_CUES,
) -> list[dict[str, Any]]:
    """words -> emoticon cue 목록. fill_gaps=True는 span당 1 cue, 개수 제한 없음."""
    if not words:
        return []
    if not fill_gaps:
        return _plan_sparse(words, max_cues)

    spans = _spans(words, segments)
    cues: list[dict[str, Any]] = []
    prev: str | None = None
    for n, (s, e, direction) in enumerate(spans):
        # 스토리보드 `화면 연출`이 있으면 그 키워드를 우선 사용한다 (architecture.md §5.1).
        cands = _text_candidates(direction) + _span_candidates(words, s, e)
        text = " ".join(str(w["text"]) for w in words[s:e])
        file: str | None = None
        keyword = ""
        for _score, _order, kw, fname in cands:
            if fname != prev:
                file, keyword = fname, kw
                break
        if file is None and cands:
            alt = _fallback_file(text, n, prev)
            if alt != prev:
                file, keyword = alt, ""
            else:
                file, keyword = cands[0][3], cands[0][2]
        if file is None:
            file, keyword = _fallback_file(text, n, prev), ""
        start = int(words[s]["start"])
        last_end = int(words[e - 1]["end"])
        end_ms = max(int(words[spans[n + 1][0]]["start"]), last_end) if n + 1 < len(spans) else last_end
        cues.append(_cue(file, start, max(1, end_ms - start), keyword))
        prev = file
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
        cands = _span_candidates(words, i, i + 1)
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
    "apple": {"name": "Apple", "aliases": ("애플", "Apple")},
    "oracle": {"name": "Oracle", "aliases": ("오라클", "Oracle")},
    "roblox": {"name": "Roblox", "aliases": ("로블록스", "Roblox")},
    "sandisk": {"name": "SanDisk", "aliases": ("샌디스크", "SanDisk")},
    "nvidia": {"name": "NVIDIA", "aliases": ("엔비디아", "NVIDIA")},
    "microsoft": {"name": "Microsoft", "aliases": ("마이크로소프트", "Microsoft")},
    "google": {"name": "Google", "aliases": ("구글", "Google")},
    "amazon": {"name": "Amazon", "aliases": ("아마존", "Amazon")},
    "tesla": {"name": "Tesla", "aliases": ("테슬라", "Tesla")},
    "meta": {"name": "Meta", "aliases": ("메타", "Meta")},
    "qualcomm": {"name": "Qualcomm", "aliases": ("퀄컴", "Qualcomm")},
    "openai": {"name": "OpenAI", "aliases": ("오픈AI", "오픈에이아이", "OpenAI")},
}
for _slug, _info in COMPANY_LOGOS.items():
    _info["logoFileName"] = f"company/{_slug}.png"

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


def plan_company_logo_cues(words: list[dict]) -> list[dict[str, Any]]:
    """회사명 언급 -> 로고 cue. 같은 회사의 cue 구간이 겹치는 재언급은 건너뛴다."""
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
            span_end = int(words[i + length - 1]["end"])
            duration = min(max(MIN_LOGO_DURATION_MS, span_end - start), max(1, audio_end - start))
            info = COMPANY_LOGOS[slug]
            cues.append(
                {
                    "logoFileName": info["logoFileName"],
                    "name": info["name"],
                    "startMs": start,
                    "durationMs": duration,
                }
            )
            active_until[slug] = start + duration
        i += length
    return cues
