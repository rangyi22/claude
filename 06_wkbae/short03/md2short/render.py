"""Remotion staging/props/render subprocess + ffprobe 보조 (architecture.md §2.3, §4.3, §5.5).

자막·오버레이 합성은 Remotion 단독 책임이다. 이 모듈의 ffmpeg/ffprobe 사용은
pre-flight 와 duration/해상도 측정에 한정하며, 자막 필터나 이미지 합성 필터를 쓰지 않는다.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from md2short.schema import CTA_TEXT
from md2short.timeutil import ms_to_frames, seconds_to_ms

PROJECT_ROOT = Path(os.environ.get("MD2SHORT_ROOT") or Path(__file__).resolve().parent.parent)

COMPOSITION_ID = "TechExplainer"
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
RENDER_TIMEOUT_S = int(os.environ.get("MD2SHORT_RENDER_TIMEOUT", "1800"))
FFPROBE_TIMEOUT_S = 60
LOG_TAIL_LINES = 40

# remotion/public/<name> -> ../../<name> (symlink, copy fallback)
SHARED_ASSET_DIRS = ("emoticon", "img", "company", "font")

_HEX_COLOR_RE = re.compile(r"^[0-9A-Fa-f]{6}$|^[0-9A-Fa-f]{3}$")


def _root(root: Path | str | None) -> Path:
    return Path(root) if root is not None else PROJECT_ROOT


def remotion_dir(root: Path | str | None = None) -> Path:
    return _root(root) / "remotion"


def public_job_dir(job_id: str, root: Path | str | None = None) -> Path:
    return remotion_dir(root) / "public" / "jobs" / job_id


# --------------------------------------------------------------------------- pre-flight


def ensure_ffmpeg_available() -> None:
    """ffmpeg + ffprobe 가 PATH 에 없으면 즉시 RuntimeError."""
    missing = [tool for tool in ("ffmpeg", "ffprobe") if shutil.which(tool) is None]
    if missing:
        raise RuntimeError(
            f"필수 도구가 PATH 에 없습니다: {', '.join(missing)}. "
            "macOS 에서는 `brew install ffmpeg` 로 설치하세요."
        )


def ensure_remotion_available(root: Path | str | None = None) -> None:
    """remotion/, remotion/node_modules, npx 가 없으면 즉시 RuntimeError."""
    rdir = remotion_dir(root)
    if not rdir.is_dir():
        raise RuntimeError(f"Remotion 프로젝트 디렉터리가 없습니다: {rdir}")
    if not (rdir / "node_modules").is_dir():
        raise RuntimeError(
            f"Remotion 의존성이 설치되지 않았습니다: {rdir / 'node_modules'}. "
            "`cd remotion && npm install` 을 먼저 실행하세요."
        )
    if shutil.which("npx") is None:
        raise RuntimeError("npx 가 PATH 에 없습니다. Node.js(npm 포함)를 설치하세요.")


# --------------------------------------------------------------------------- ffprobe


def _ffprobe_json(args: list[str]) -> dict[str, Any]:
    cmd = ["ffprobe", "-v", "error", *args, "-of", "json"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=FFPROBE_TIMEOUT_S)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"ffprobe 시간 초과 ({FFPROBE_TIMEOUT_S}s): {' '.join(cmd)}") from exc
    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe 실패 (exit {proc.returncode}): {proc.stderr.strip()}")
    return json.loads(proc.stdout or "{}")


def get_audio_duration_ms(path: Path | str) -> int:
    """ffprobe 로 오디오 길이(ms 정수)를 측정한다."""
    data = _ffprobe_json(["-show_entries", "format=duration", str(path)])
    try:
        seconds = float(data["format"]["duration"])
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError(f"오디오 duration 을 읽을 수 없습니다: {path}") from exc
    return seconds_to_ms(seconds)


def get_video_info(path: Path | str) -> dict[str, int]:
    """ffprobe 로 {duration_ms, width, height} 를 측정한다."""
    data = _ffprobe_json(
        [
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height:format=duration",
            str(path),
        ]
    )
    try:
        stream = data["streams"][0]
        return {
            "duration_ms": seconds_to_ms(float(data["format"]["duration"])),
            "width": int(stream["width"]),
            "height": int(stream["height"]),
        }
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise RuntimeError(f"비디오 정보를 읽을 수 없습니다: {path}") from exc


# --------------------------------------------------------------------------- props


def normalize_bg_color(color: str) -> str:
    """'0xFFFFFF' / 'FFFFFF' / '#FFFFFF' → '#FFFFFF'."""
    value = color.strip()
    if value[:2].lower() == "0x":
        value = value[2:]
    elif value.startswith("#"):
        value = value[1:]
    if not _HEX_COLOR_RE.match(value):
        raise ValueError(f"bg color 형식이 잘못되었습니다: {color!r} (예: 0xFFFFFF)")
    return f"#{value.upper()}"


def build_props(
    job_id: str,
    audio_ms: int,
    *,
    bg_color: str = "0xFFFFFF",
    chunk_size: int = 14,
    emoticon_cues: list[dict[str, Any]] | None = None,
    caption_segments: list[dict[str, Any]] | None = None,
    company_logo_cues: list[dict[str, Any]] | None = None,
    number_cards: list[dict[str, Any]] | None = None,
    index_board: dict[str, Any] | None = None,
    headline: dict[str, Any] | None = None,
    highlight_keywords: list[str] | None = None,
    opening_text: str = "",
    source_text: str = "",
    opening_duration_ms: int = 0,
    show_opening: bool = True,
    cta_text: str = CTA_TEXT["ko"],
    show_outro: bool = False,
) -> dict[str, Any]:
    """architecture.md §4.3 키 그대로의 Remotion props 를 만든다.

    durationInFrames 는 실제 TTS 오디오 길이(§1.4)로만 결정한다.
    openingDurationMs 는 날짜 배지 표시 시간이며 show_opening=False 이면 0 (§5.10).
    """
    return {
        "audioFileName": f"jobs/{job_id}/narration.mp3",
        "wordsFileName": f"jobs/{job_id}/words.json",
        "bgColor": normalize_bg_color(bg_color),
        "chunkSize": int(chunk_size),
        "emoticonCues": list(emoticon_cues or []),
        "captionSegments": list(caption_segments or []),
        "companyLogoCues": list(company_logo_cues or []),
        "numberCards": list(number_cards or []),
        "indexBoard": index_board,
        "headline": headline,
        "highlightKeywords": list(highlight_keywords or []),
        "openingText": opening_text if show_opening else "",
        "sourceText": source_text,
        "openingDurationMs": int(opening_duration_ms) if show_opening else 0,
        "showOpening": bool(show_opening),
        "ctaText": cta_text,
        "showOutro": bool(show_outro),
        "durationInFrames": max(1, ms_to_frames(audio_ms)),
    }


# --------------------------------------------------------------------------- staging


def _link_or_copy_dir(link: Path, target_rel: str, source: Path) -> None:
    """link -> target_rel 상대 symlink. 실패하면 source 를 복사한다."""
    if link.is_symlink():
        if link.resolve() == source.resolve():
            return
        link.unlink()
    elif link.is_dir():
        # 이전 copy fallback 결과: 최신 asset 으로 갱신
        shutil.copytree(source, link, dirs_exist_ok=True)
        return
    try:
        link.symlink_to(target_rel, target_is_directory=True)
    except OSError:
        shutil.copytree(source, link, dirs_exist_ok=True)


def stage_assets(
    job_id: str,
    audio_path: Path | str,
    words_path: Path | str,
    root: Path | str | None = None,
) -> dict[str, Path]:
    """narration/words 를 remotion/public/jobs/<job_id>/ 에 복사하고 공용 asset 을 링크한다."""
    base = _root(root)
    public = remotion_dir(base) / "public"
    job_dir = public_job_dir(job_id, base)
    job_dir.mkdir(parents=True, exist_ok=True)

    audio_dst = job_dir / "narration.mp3"
    words_dst = job_dir / "words.json"
    shutil.copyfile(audio_path, audio_dst)
    shutil.copyfile(words_path, words_dst)

    staged: dict[str, Path] = {"job_dir": job_dir, "audio": audio_dst, "words": words_dst}
    for name in SHARED_ASSET_DIRS:
        source = base / name
        if not source.is_dir():
            raise RuntimeError(f"공용 asset 디렉터리가 없습니다: {source}")
        link = public / name
        _link_or_copy_dir(link, f"../../{name}", source)
        staged[name] = link
    return staged


# --------------------------------------------------------------------------- render


def build_render_command(output_path: Path | str, props_path: Path | str) -> list[str]:
    """architecture.md §5.5 render command (cwd=remotion/)."""
    return [
        "npx",
        "remotion",
        "render",
        "src/index.ts",
        COMPOSITION_ID,
        str(output_path),
        f"--props={props_path}",
        "--codec=h264",
        "--audio-bitrate=192k",  # 음성 위주 — 기본 320k 는 과함
        f"--width={VIDEO_WIDTH}",
        f"--height={VIDEO_HEIGHT}",
        "--log=warn",
        "--overwrite",
    ]


def _tail(text: str, lines: int = LOG_TAIL_LINES) -> str:
    return "\n".join(text.strip().splitlines()[-lines:])


def _write_log(log_path: Path, cmd: list[str], stdout: str, stderr: str, footer: str) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        f"$ {' '.join(cmd)}\n\n--- stdout ---\n{stdout}\n--- stderr ---\n{stderr}\n--- {footer} ---\n",
        encoding="utf-8",
    )


def render_remotion(
    job_id: str,
    audio_path: Path | str,
    words_path: Path | str,
    props: dict[str, Any],
    output_path: Path | str,
    log_path: Path | str,
    root: Path | str | None = None,
    timeout_s: int = RENDER_TIMEOUT_S,
) -> Path:
    """assets staging → props.json 기록 → `npx remotion render` 실행 → output_path 반환."""
    base = _root(root)
    ensure_remotion_available(base)
    staged = stage_assets(job_id, audio_path, words_path, base)

    audio_ms = get_audio_duration_ms(staged["audio"])
    final_props = dict(props)
    final_props["audioFileName"] = f"jobs/{job_id}/narration.mp3"
    final_props["wordsFileName"] = f"jobs/{job_id}/words.json"
    final_props["bgColor"] = normalize_bg_color(str(final_props.get("bgColor", "#FFFFFF")))
    final_props["durationInFrames"] = max(1, ms_to_frames(audio_ms))

    props_path = staged["job_dir"] / "props.json"
    props_path.write_text(json.dumps(final_props, ensure_ascii=False, indent=2), encoding="utf-8")

    output = Path(output_path).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    log = Path(log_path)
    cmd = build_render_command(output, props_path.resolve())

    try:
        proc = subprocess.run(
            cmd,
            cwd=remotion_dir(base),
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        _write_log(log, cmd, stdout, stderr, f"timeout after {timeout_s}s")
        raise RuntimeError(
            f"Remotion 렌더 시간 초과 ({timeout_s}s). 로그: {log}\n{_tail(stderr or stdout)}"
        ) from exc

    _write_log(log, cmd, proc.stdout, proc.stderr, f"exit {proc.returncode}")
    if proc.returncode != 0:
        raise RuntimeError(
            f"Remotion 렌더 실패 (exit {proc.returncode}). 로그: {log}\n"
            f"{_tail(proc.stderr or proc.stdout)}"
        )
    if not output.is_file():
        raise RuntimeError(f"Remotion 렌더 결과 파일이 없습니다: {output}. 로그: {log}")
    return output
