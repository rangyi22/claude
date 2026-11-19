"""TTS 전용 텍스트 보정 (architecture.md §2.2). display script 는 변경하지 않는다. 결정적."""

from __future__ import annotations

import re

_KNOWN_ACRONYMS = {
    "AI": "에이아이",
    "AMD": "에이엠디",
    "NVIDIA": "엔비디아",
    "GPU": "지피유",
    "CPU": "씨피유",
    "ETF": "이티에프",
    "IPO": "아이피오",
    "CEO": "씨이오",
    "GDP": "지디피",
    "CPI": "씨피아이",
    "FOMC": "에프오엠씨",
    "KOSPI": "코스피",
    "KOSDAQ": "코스닥",
    "AWS": "에이더블유에스",
    "API": "에이피아이",
}
_LETTERS = dict(
    zip(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "에이 비 씨 디 이 에프 지 에이치 아이 제이 케이 엘 엠 엔 오 피 큐 알 에스 티 유 브이 더블유 엑스 와이 지".split(),
    )
)
_SINO = "영일이삼사오육칠팔구"
_SMALL_UNITS = ("", "십", "백", "천")
_BIG_UNITS = ("", "만", "억", "조")
_NATIVE_ONES = ("", "한", "두", "세", "네", "다섯", "여섯", "일곱", "여덟", "아홉")
_NATIVE_TENS = ("", "열", "스물", "서른", "마흔", "쉰", "예순", "일흔", "여든", "아흔")
_NATIVE_COUNTERS = ("개", "명", "살", "번", "곳", "가지", "시")
_SPECIAL_MONTHS = {"6": "유", "10": "시"}

_NUMBER_RE = re.compile(
    r"(?P<neg>(?<![\w.])-(?=\d))?(?P<cur>\$)?(?P<int>\d{1,3}(?:,\d{3})+|\d+)(?:\.(?P<frac>\d+))?(?P<pct>%)?"
)
_ACRONYM_RE = re.compile(r"(?<![A-Za-z])[A-Z]{2,}(?![a-z])")
_EMOJI_RE = re.compile("[\U0001F000-\U0001FAFF☀-➿️]")


def _sino_int(digits: str) -> str:
    n = int(digits)
    if n == 0:
        return "영"
    if len(digits.lstrip("0")) > 16 or (len(digits) > 1 and digits[0] == "0"):
        return "".join(_SINO[int(d)] for d in digits)
    groups: list[str] = []
    for gi in range(4):
        part = (n // 10 ** (4 * gi)) % 10000
        if part == 0:
            continue
        s = ""
        for pos in range(3, -1, -1):
            d = (part // 10**pos) % 10
            if d == 0:
                continue
            s += ("" if d == 1 and pos > 0 else _SINO[d]) + _SMALL_UNITS[pos]
        if gi == 1 and part == 1:
            s = ""
        groups.append(s + _BIG_UNITS[gi])
    return "".join(reversed(groups))


def _native_int(n: int) -> str:
    tens, ones = divmod(n, 10)
    if n == 20:
        return "스무"
    return _NATIVE_TENS[tens] + _NATIVE_ONES[ones]


def _read_number(m: re.Match[str]) -> str:
    text = m.string
    digits = m.group("int").replace(",", "")
    frac = m.group("frac")
    after = text[m.end():]
    if frac is None and not m.group("pct") and not m.group("cur") and 1 <= int(digits) <= 99 and digits[0] != "0":
        if any(after.startswith(c) for c in _NATIVE_COUNTERS):
            return _native_int(int(digits))
        if after.startswith("월") and digits in _SPECIAL_MONTHS:
            return _SPECIAL_MONTHS[digits]
    out = _sino_int(digits)
    if frac is not None:
        out += " 점 " + " ".join(_SINO[int(d)] for d in frac)
    if m.group("neg"):
        out = "마이너스 " + out
    if m.group("pct"):
        out += " 퍼센트"
    if m.group("cur"):
        out += " 달러"
    return out


def _read_acronym(m: re.Match[str]) -> str:
    tok = m.group(0)
    return _KNOWN_ACRONYMS.get(tok) or "".join(_LETTERS[c] for c in tok)


def prepare_tts_text(display_text: str) -> str:
    t = display_text
    t = _EMOJI_RE.sub("", t)
    t = t.replace("S&P", "에스앤피").replace("&", " 앤드 ")
    t = _ACRONYM_RE.sub(_read_acronym, t)
    t = _NUMBER_RE.sub(_read_number, t)
    # pause-heavy punctuation 평탄화
    t = re.sub(r"(?m)^\s*(?:[-*•▪◦·]|\d+[.)])\s+", "", t)
    t = re.sub(r"\.{2,}|…+", ".", t)
    t = re.sub(r"([!?,.])\1+", r"\1", t)
    t = re.sub(r"[‘’“”\"'`]", "", t)
    t = t.replace("·", " ").replace("/", " ")
    t = re.sub(r"[()\[\]{}]", " ", t)
    t = re.sub(r"(?<![.!?])\s*\n+\s*", ". ", t)
    t = re.sub(r"\s*\n+\s*", " ", t)
    t = re.sub(r"\s+([,.!?])", r"\1", t)
    t = re.sub(r"([,.!?])(?=[^\s,.!?])", r"\1 ", t)
    t = re.sub(r"\s{2,}", " ", t)
    return t.strip()
