"""ms ↔ frame 변환 단일 헬퍼 (AGENTS.md §4.2).

다른 모듈은 ms/frame 변환을 직접 계산하지 않고 반드시 이 모듈을 사용한다.
"""

from __future__ import annotations

FPS = 30


def ms_to_frames(ms: float, fps: int = FPS) -> int:
    """ms를 frame 수로 변환 (round)."""
    return int(round(ms * fps / 1000))


def frames_to_ms(frames: int, fps: int = FPS) -> int:
    """frame 수를 ms로 변환 (round)."""
    return int(round(frames * 1000 / fps))


def seconds_to_ms(seconds: float) -> int:
    """Scribe 초 단위 timestamp를 ms 정수로 반올림."""
    return int(round(seconds * 1000))
