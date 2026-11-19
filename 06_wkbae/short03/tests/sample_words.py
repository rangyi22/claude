"""테스트용 words.json 합성 헬퍼 (sample.md 문장 기반)."""

from __future__ import annotations

WORD_MS = 300
SENTENCE_GAP_MS = 100  # 문장부호 경계는 gap 없이도 분할됨


def build_words(sentences: list[str], word_ms: int = WORD_MS, gap_ms: int = SENTENCE_GAP_MS) -> list[dict]:
    words: list[dict] = []
    t = 0
    for sentence in sentences:
        for token in sentence.split():
            words.append({"text": token, "start": t, "end": t + word_ms})
            t += word_ms
        t += gap_ms
    return words


SAMPLE_SENTENCES = [
    "지난 금요일 미국 증시, 강하게 상승 마감했습니다.",
    "5주 연속 상승, 2024년 이후 최장 랠리입니다.",
    "S&P 500 종가 7,230 기록했습니다.",
    "나스닥은 0.94% 상승했습니다.",
    "다우는 소폭 하락했습니다.",
    "애플, 호실적으로 3.2% 상승했습니다.",
    "샌디스크, 8% 급등했습니다.",
    "오라클이 미 국방부 AI 네트워크 프로젝트에 공식 합류했습니다.",
    "로블록스, 18% 급락했습니다.",
]
