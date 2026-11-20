"""Scribe 발음형 숫자·약어를 대본 원문 표시형으로 복원 (architecture.md §1.3).

timing(start/end)은 Scribe 값을 유지하고 표시 텍스트만 고친다. 여러 단어가 한
토큰으로 합쳐질 때는 첫 단어 start ~ 마지막 단어 end 로 합친다.
대본 토큰 순서대로 단조(monotonic) 정렬하여 엉뚱한 위치 치환을 막는다.
"""

from __future__ import annotations

import copy
import re
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher

ACRONYM_MATCH_THRESHOLD = 0.86
GROUPED_NUMBER_MATCH_THRESHOLD = 0.84
ACRONYM_MAX_SCAN_WORDS = 96
NUMBER_MAX_SCAN_WORDS = 96
_MAX_SPAN_WORDS = 6

_NUM = r"\d[\d,]*(?:\.\d+)?"
# 약어 + 인접 숫자를 하나의 토큰으로 (S&P500, "S&P 500"), 그 외 숫자(+% 단위)는 별도 토큰.
_ACRONYM_TOKEN_RE = re.compile(
    rf"(?<![A-Za-z0-9])(?P<acr>[A-Z][A-Z&]*[A-Z])(?![A-Za-z])(?:(?P<sep>\s?)(?P<acrnum>{_NUM}))?"
    rf"|(?P<num>{_NUM})(?P<pct>%)?"
)

_ACRONYM_KO_VARIANTS: dict[str, tuple[str, ...]] = {
    "S&P": ("에스앤피", "에센피", "에스엔피", "에스앤드피", "에쓰앤피", "에스엔피", "에스앤피"),
    "AI": ("에이아이", "에이아", "에이"),
    "AMD": ("에이엠디", "에이엠디"),
    "GPU": ("지피유", "쥐피유"),
    "CPU": ("씨피유", "시피유"),
    "ETF": ("이티에프",),
    "IPO": ("아이피오",),
    "FOMC": ("에프오엠씨", "에프오엠시"),
    "OPEC": ("오펙",),
    "UAE": ("유에이이",),
    "GDP": ("지디피",),
    "CPI": ("씨피아이", "시피아이"),
    "PPI": ("피피아이",),
    "EPS": ("이피에스",),
    "HBM": ("에이치비엠",),
    "IBM": ("아이비엠",),
    "API": ("에이피아이",),
    "WTI": ("더블유티아이", "더블류티아이"),
    "EV": ("이브이",),
    "IT": ("아이티",),
    "US": ("유에스",),
    "SK": ("에스케이",),
    "LG": ("엘지",),
    "QQQ": ("큐큐큐",),
    "NAND": ("낸드", "엔드"),
}

_LETTER_KO = {
    "A": "에이", "B": "비", "C": "씨", "D": "디", "E": "이", "F": "에프", "G": "지",
    "H": "에이치", "I": "아이", "J": "제이", "K": "케이", "L": "엘", "M": "엠",
    "N": "엔", "O": "오", "P": "피", "Q": "큐", "R": "알", "S": "에스", "T": "티",
    "U": "유", "V": "브이", "W": "더블유", "X": "엑스", "Y": "와이", "Z": "지", "&": "앤",
}

_DIGITS = {"영": 0, "공": 0, "일": 1, "이": 2, "삼": 3, "사": 4, "오": 5, "육": 6, "칠": 7, "팔": 8, "구": 9}
_SMALL_UNITS = {"십": 10, "백": 100, "천": 1000}
_BIG_UNITS = {"만": 10**4, "억": 10**8, "조": 10**12}
_NUMERAL_CHARS = "영공일이삼사오육칠팔구십백천만억조점"
_WORD_NUM_RE = re.compile(rf"^(?P<num>[{_NUMERAL_CHARS}]+|{_NUM})(?P<rest>.*)$", re.S)
# 한 글자 숫자 단어("이", "오" 등 조사/일반어와 충돌)는 이 단위가 뒤따를 때만 인정.
_UNIT_STARTS = "년월일주개명위배조억만원달러%퍼프포"
_PERCENT_READINGS = ("퍼센트", "프로")
_UNIT_WORDS = ("퍼센트", "프로", "포인트", "달러", "원", "년", "월", "주", "개", "명", "위", "배")


def _next_is_unit(words: list[dict], end: int) -> bool:
    """다음 단어가 (조사 1글자까지 허용한) 단위 단어인가."""
    if end >= len(words):
        return False
    nxt = re.sub(r"[^0-9A-Za-z가-힣]", "", str(words[end]["text"]))
    return any(nxt.startswith(u) and len(nxt) <= len(u) + 1 for u in _UNIT_WORDS)


def parse_korean_number(text: str) -> Decimal | None:
    """한글 수사 읽기("칠천이백삼십", "영점구사")를 Decimal로. 해석 불가면 None."""
    s = re.sub(r"[\s,]", "", text)
    if not s:
        return None
    if "점" in s:
        head, _, frac = s.partition("점")
        if not head or not frac or "점" in frac or any(c not in _DIGITS for c in frac):
            return None
        whole = _parse_int(head)
        if whole is None:
            return None
        return Decimal(f"{whole}.{''.join(str(_DIGITS[c]) for c in frac)}")
    whole = _parse_int(s)
    return None if whole is None else Decimal(whole)


def _parse_int(s: str) -> int | None:
    total = section = 0
    pending: int | None = None
    last_small = 10**4
    last_big = 10**13
    consumed = False
    for ch in s:
        if ch in _DIGITS:
            if pending is not None:
                return None
            pending = _DIGITS[ch]
        elif ch in _SMALL_UNITS:
            unit = _SMALL_UNITS[ch]
            if unit >= last_small or pending == 0:
                return None
            section += (1 if pending is None else pending) * unit
            last_small, pending = unit, None
        elif ch in _BIG_UNITS:
            unit = _BIG_UNITS[ch]
            if unit >= last_big:
                return None
            section += pending or 0
            total += (section or 1) * unit
            section, pending, last_small, last_big = 0, None, 10**4, unit
        else:
            return None
        consumed = True
    if not consumed:
        return None
    return total + section + (pending or 0)


def int_to_korean(n: int) -> str:
    """정수를 한글 수사로 (fuzzy 비교용 기준 읽기)."""
    if n == 0:
        return "영"
    digits = "영일이삼사오육칠팔구"
    out = ""
    for big_unit, big_name in ((10**12, "조"), (10**8, "억"), (10**4, "만"), (1, "")):
        part, n = divmod(n, big_unit)
        if not part:
            continue
        sec = ""
        for unit, name in ((1000, "천"), (100, "백"), (10, "십"), (1, "")):
            d, part = divmod(part, unit)
            if d:
                sec += ("" if d == 1 and unit > 1 else digits[d]) + name
        out += sec + big_name
    return out


def _norm(s: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣&]", "", s)


def _ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def _acronym_variants(acronym: str) -> tuple[str, ...]:
    out: list[str] = [acronym.upper()]
    out.extend(_ACRONYM_KO_VARIANTS.get(acronym, ()))
    generated = "".join(_LETTER_KO.get(c, "") for c in acronym)
    if generated:
        out.append(generated)
    seen: dict[str, None] = {}
    for v in out:
        seen.setdefault(v, None)
    return tuple(seen)


def _match_acronym(words: list[dict], i: int, acronym: str) -> tuple[int, str] | None:
    """words[i:]에서 약어의 한글 음역/원문 매칭. (end index exclusive, 뒤에 붙은 조사/잔여) 반환."""
    variants = _acronym_variants(acronym)
    acc = ""
    for j in range(i, min(i + 3, len(words))):
        acc += _norm(str(words[j]["text"]))
        if not acc:
            continue
        best: tuple[float, str] | None = None
        for v in variants:
            cand: tuple[float, str] | None
            if acc.upper().startswith(v) and (len(acc) == len(v) or not acc[len(v)].isalpha() or not acc[len(v)].isascii()):
                cand = (1.0, acc[len(v):])
            else:
                r = _ratio(acc, v)
                cand = (r, "") if r >= ACRONYM_MATCH_THRESHOLD else None
            if cand and (best is None or cand[0] > best[0]):
                best = cand
        if best:
            return j + 1, best[1]
    return None


def _match_number(
    words: list[dict], i: int, value: Decimal, percent: bool
) -> tuple[int, str, bool] | None:
    """words[i:]에서 숫자 값 매칭. (end exclusive, 단위 뒤 잔여 텍스트, 퍼센트 소비 여부)."""
    grouped = value == value.to_integral_value() and value >= 1000
    reading = int_to_korean(int(value)) if grouped else ""
    acc = ""
    for j in range(i, min(i + _MAX_SPAN_WORDS, len(words))):
        m = _WORD_NUM_RE.match(str(words[j]["text"]).strip())
        if not m:
            return None
        num, rest = m["num"], m["rest"]
        arabic = num[0].isdigit()
        if arabic and acc:
            return None
        acc += num
        if arabic:
            try:
                got: Decimal | None = Decimal(num.replace(",", ""))
            except InvalidOperation:
                got = None
        else:
            got = parse_korean_number(acc)
        ok = got == value
        if not ok and grouped and not arabic and got is not None:
            ok = _ratio(reading, acc) >= GROUPED_NUMBER_MATCH_THRESHOLD and len(acc) > 2
        if ok:
            if not arabic and len(acc) == 1:
                ok = bool(rest and rest[0] in _UNIT_STARTS) or (not rest and _next_is_unit(words, j + 1))
        if ok:
            end = j + 1
            consumed_pct = False
            if percent:
                for pr in _PERCENT_READINGS:
                    if rest.startswith(pr):
                        rest, consumed_pct = rest[len(pr):], True
                        break
                if not consumed_pct and not rest and end < len(words):
                    nxt = str(words[end]["text"]).strip()
                    for pr in _PERCENT_READINGS:
                        if nxt.startswith(pr):
                            rest, consumed_pct, end = nxt[len(pr):], True, end + 1
                            break
            return end, rest, consumed_pct
        if rest:  # 수사 뒤에 다른 글자가 붙으면 더 이어붙일 수 없다
            return None
    return None


def _merge(words: list[dict], i: int, end: int, text: str) -> dict:
    merged = dict(words[i])
    merged["text"] = text
    merged["start"] = words[i]["start"]
    merged["end"] = words[end - 1]["end"]
    return merged


def apply_numeric_display_overrides(words_doc: dict, script_text: str) -> dict:
    """words_doc(words.json)의 표시 텍스트를 script_text의 숫자/약어 원문 형태로 복원한 새 doc."""
    doc = copy.deepcopy(words_doc)
    words: list[dict] = doc.get("words", [])
    out: list[dict] = []
    pos = 0  # words 단조 커서
    for tok in _ACRONYM_TOKEN_RE.finditer(script_text):
        if tok["acr"]:
            hit = _scan_acronym(words, pos, tok)
        else:
            hit = _scan_number(words, pos, tok)
        if hit is None:
            continue
        start, end, text = hit
        out.extend(words[pos:start])
        out.append(_merge(words, start, end, text))
        pos = end
    out.extend(words[pos:])
    doc["words"] = out
    return doc


def _scan_acronym(words: list[dict], pos: int, tok: re.Match[str]) -> tuple[int, int, str] | None:
    acronym = tok["acr"]
    # 약어 + 숫자 토큰(S&P 500)은 "S&P" 음역 뒤에 숫자가 따라올 때만 한 토큰으로 인정.
    for i in range(pos, min(pos + ACRONYM_MAX_SCAN_WORDS, len(words))):
        base = _match_acronym(words, i, acronym)
        if base is None:
            continue
        end, rest = base
        display = acronym
        if tok["acrnum"]:
            value = Decimal(tok["acrnum"].replace(",", ""))
            if rest and (rest == tok["acrnum"] or parse_korean_number(rest) == value):
                # 음역 단어에 숫자가 붙어 나온 경우("에센피오백")
                return i, end, acronym + tok["sep"] + tok["acrnum"]
            num = _match_number(words, end, value, False)
            if num is not None:  # 실패하면 약어만 복원
                end, rest, _ = num
                display = acronym + tok["sep"] + tok["acrnum"]
        return i, end, display + rest
    return None


def _scan_number(words: list[dict], pos: int, tok: re.Match[str]) -> tuple[int, int, str] | None:
    raw = tok["num"]
    value = Decimal(raw.replace(",", ""))
    percent = bool(tok["pct"])
    for i in range(pos, min(pos + NUMBER_MAX_SCAN_WORDS, len(words))):
        hit = _match_number(words, i, value, percent)
        if hit is None:
            continue
        end, rest, consumed_pct = hit
        display = raw + ("%" if percent and consumed_pct else "")
        # 이미 '%'가 붙어 있는 Arabic 단어는 rest가 '%...'로 남아 그대로 이어붙는다.
        return i, end, display + rest
    return None
